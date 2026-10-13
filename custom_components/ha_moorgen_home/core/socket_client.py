import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress

from .protocol.codec import (
    build_heartbeat_ack,
    is_heartbeat_ping,
    parse_protocol_packet,
    route,
)

_LOGGER = logging.getLogger(__name__)


class ServerDisconnectedError(ConnectionError):
    """Raised when server actively closes the socket."""


class AsyncSocketClient:
    def __init__(self, host, port, on_server_push: Callable[[], None] | None = None):
        self.host = host
        self.port = port
        self._on_server_push = on_server_push
        self._reader = None
        self._writer = None
        self._lock = asyncio.Lock()
        self._connected = False
        self._connect_task = None
        self._stopped = False
        self._connected_event = asyncio.Event()
        self._scene_event = asyncio.Event()
        self._scene_version = 0
        self._device_event = asyncio.Event()
        self._device_version = 0
        self._kick_cooldown_seconds = 600
        self._cooldown_until = 0.0
        self.data = {"scenes": [], "rooms": [], "devices": []}

    @property
    def scene_version(self):
        return self._scene_version

    @property
    def device_version(self):
        return self._device_version

    @property
    def cooldown_remaining_seconds(self) -> int:
        now = asyncio.get_running_loop().time()
        return max(0, int(self._cooldown_until - now))

    def _ensure_not_in_cooldown(self):
        if self.cooldown_remaining_seconds > 0:
            raise ConnectionError(
                f"Reconnect cooldown active, retry in {self.cooldown_remaining_seconds}s"
            )

    async def start(self):
        if self._connect_task and not self._connect_task.done():
            return
        self._stopped = False
        self._connect_task = asyncio.create_task(self._connect_loop())

    async def stop(self):
        self._stopped = True
        self._connected = False
        self._connected_event.clear()

        if self._connect_task:
            self._connect_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._connect_task
            self._connect_task = None

        await self._close_writer()

    async def wait_until_connected(self, timeout=5):
        self._ensure_not_in_cooldown()

        if (
            not self._connected
            and not self._stopped
            and (self._connect_task is None or self._connect_task.done())
        ):
            await self.start()

        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=timeout)
        except TimeoutError as err:
            raise ConnectionError(f"Connect timeout after {timeout}s") from err

    async def wait_for_scene_update(self, previous_version: int, timeout=5):
        if self._scene_version > previous_version:
            return

        self._scene_event.clear()
        if self._scene_version > previous_version:
            return

        await asyncio.wait_for(self._scene_event.wait(), timeout=timeout)

    async def wait_for_device_update(self, previous_version: int, timeout=5):
        if self._device_version > previous_version:
            return

        self._device_event.clear()
        if self._device_version > previous_version:
            return

        await asyncio.wait_for(self._device_event.wait(), timeout=timeout)

    async def _connect_loop(self):
        while not self._stopped:
            should_retry = False
            retry_delay = self._kick_cooldown_seconds
            try:
                await self._connect_once()
            except asyncio.CancelledError:
                raise
            except ServerDisconnectedError as err:
                _LOGGER.warning("[Connection error] %s", err)
                should_retry = True
                _LOGGER.warning(
                    "Detected server-side disconnect, enter cooldown for %s seconds",
                    retry_delay,
                )
            except Exception as err:
                _LOGGER.warning("[Connection error] %s", err)
            finally:
                self._connected = False
                self._connected_event.clear()
                await self._close_writer()

            if self._stopped:
                break

            if not should_retry:
                _LOGGER.info(
                    "Connection loop paused. It will reconnect on next coordinator refresh."
                )
                break

            self._cooldown_until = asyncio.get_running_loop().time() + retry_delay
            _LOGGER.info("Connection lost, retrying in %s seconds...", retry_delay)
            await asyncio.sleep(retry_delay)
            self._cooldown_until = 0.0

    async def _connect_once(self):
        _LOGGER.info("Connecting to %s:%s", self.host, self.port)
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self.data.pop("_pending_devices", None)
        self._connected = True
        self._connected_event.set()
        _LOGGER.info("Connected to server")
        await self._read_loop()

    async def _close_writer(self):
        if self._writer is None:
            return

        writer = self._writer
        self._writer = None
        self._reader = None

        writer.close()
        with suppress(Exception):
            await writer.wait_closed()
        _LOGGER.info("Connection closed")

    async def _read_loop(self):
        buf = b""
        while not self._stopped:
            data = await self._reader.read(4096)
            if not data:
                raise ServerDisconnectedError("Server closed the connection")

            buf += data
            while len(buf) >= 3:
                start = buf.find(b"\x23")
                if start < 0:
                    buf = b""
                    break
                if start > 0:
                    buf = buf[start:]
                    if len(buf) < 3:
                        break

                pkt_len = buf[1] + (buf[2] << 8)
                full_len = pkt_len + 3

                if full_len < 19:
                    buf = buf[1:]
                    continue

                if len(buf) < full_len:
                    break

                pkt = buf[:full_len]
                if pkt[-1] != 0x23:
                    buf = buf[1:]
                    continue

                buf = buf[full_len:]

                try:
                    data_packet = parse_protocol_packet(pkt)
                    if is_heartbeat_ping(data_packet):
                        await self._send_raw(build_heartbeat_ack(pkt))
                        continue
                    if (
                        data_packet.proto_num == 1
                        and data_packet.proto_type == 5
                        and data_packet.link_code == 12
                        and self._on_server_push is not None
                    ):
                        self._on_server_push()

                    updated = route(data_packet, self.data)
                    if updated == "scenes":
                        self._scene_version += 1
                        self._scene_event.set()
                    if updated == "devices":
                        self._device_version += 1
                        self._device_event.set()
                except Exception as err:
                    _LOGGER.warning(
                        "[Packet handling error] %s, packet_hex=%s",
                        err,
                        pkt.hex(),
                    )

    async def _send_raw(self, data: bytes):
        async with self._lock:
            if self._writer:
                self._writer.write(data)
                await self._writer.drain()

    async def send_command(self, data: bytes):
        """Send raw bytes to the server."""
        self._ensure_not_in_cooldown()

        async with self._lock:
            if not self._connected or not self._writer:
                raise ConnectionError("Not connected, cannot send data")
            self._writer.write(data)
            await self._writer.drain()
            _LOGGER.info("[TX] Sent: %s", data.hex())
