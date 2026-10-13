import logging

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .core.protocol.codec import device_room_id, infer_device_type

_LOGGER = logging.getLogger(__name__)

# c140 Device_State, from StatusUtils.isMotoDown/isMotoUp/isMotoStop in the app.
# 19-21 are the same states while the travel limits are not configured.
STATE_CLOSING = (16, 19)
STATE_OPENING = (17, 20)
STATE_UNSET_TRAVEL = (19, 20, 21)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][COORDINATOR]
    entities = []
    room_names = {room.id: room.name for room in coordinator.data.get("rooms", [])}

    for device in coordinator.data["devices"]:
        if infer_device_type(device) != "curtain":
            continue

        device_mac = device.get("Device_Mac")
        device_name = device.get("Device_Name")
        if device_mac is None or not device_name:
            continue

        entities.append(
            MoorgenCurtain(
                coordinator,
                device_mac,
                device_name,
                area=room_names.get(device_room_id(device)),
            )
        )

    async_add_entities(entities)
    _LOGGER.info("%s curtains initialized", len(entities))


class MoorgenCurtain(CoordinatorEntity, CoverEntity):
    """Curtain motor. Gateway position is 0 = fully open (up) .. 100 = fully closed (down)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator, device_mac: int, name: str, area: str | None = None):
        super().__init__(coordinator, context=str(device_mac))
        self._device_mac = device_mac
        self._attr_unique_id = f"moorgen_curtain_{device_mac}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_mac))},
            name=name,
            manufacturer="Moorgen",
            model="Curtain motor",
            suggested_area=area,
        )

    @property
    def _device(self) -> dict | None:
        for device in self.coordinator.data.get("devices", []):
            if device.get("Device_Mac") == self._device_mac:
                return device
        return None

    @property
    def available(self) -> bool:
        device = self._device
        return super().available and bool(device) and device.get("Device_is_online", 1) == 1

    @property
    def _gateway_position(self) -> int | None:
        device = self._device or {}
        if device.get("Device_State") in STATE_UNSET_TRAVEL:
            return None
        raw = device.get("Device_CmdData")
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if not isinstance(raw, (bytes, bytearray)) or not raw or raw[0] > 100:
            return None
        return raw[0]

    @property
    def current_cover_position(self) -> int | None:
        position = self._gateway_position
        return None if position is None else 100 - position

    @property
    def is_closed(self) -> bool | None:
        position = self._gateway_position
        return None if position is None else position >= 100

    @property
    def is_opening(self) -> bool:
        device = self._device or {}
        return device.get("Device_State") in STATE_OPENING

    @property
    def is_closing(self) -> bool:
        device = self._device or {}
        return device.get("Device_State") in STATE_CLOSING

    async def async_open_cover(self, **kwargs) -> None:
        await self.coordinator.curtain_command(self._device_mac, "curtain-up")

    async def async_close_cover(self, **kwargs) -> None:
        await self.coordinator.curtain_command(self._device_mac, "curtain-down")

    async def async_stop_cover(self, **kwargs) -> None:
        await self.coordinator.curtain_command(self._device_mac, "curtain-stop")

    async def async_set_cover_position(self, **kwargs) -> None:
        await self.coordinator.set_curtain_position(
            self._device_mac, 100 - int(kwargs[ATTR_POSITION])
        )
