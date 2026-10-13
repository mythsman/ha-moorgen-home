import logging
import time

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .core.protocol.codec import (
    aircon_mode_and_fan,
    aircon_temperatures,
    device_room_id,
    infer_device_type,
)

_LOGGER = logging.getLogger(__name__)

PANEL_MODE_TO_HVAC = {
    "cool": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "fan_only": HVACMode.FAN_ONLY,
}
HVAC_TO_PANEL_MODE = {hvac: panel for panel, hvac in PANEL_MODE_TO_HVAC.items()}

# The unit reports a new setting 0.2-5 s after a command; show the requested
# value meanwhile so the UI does not bounce back.
PENDING_SECONDS = 10


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][COORDINATOR]
    entities = []
    room_names = {room.id: room.name for room in coordinator.data.get("rooms", [])}

    for device in coordinator.data["devices"]:
        if infer_device_type(device) != "air_conditioner":
            continue

        device_mac = device.get("Device_Mac")
        device_name = device.get("Device_Name")
        if device_mac is None or not device_name:
            continue

        entities.append(
            MoorgenAirconClimate(
                coordinator,
                device_mac,
                device_name,
                area=room_names.get(device_room_id(device)),
            )
        )

    async_add_entities(entities)
    _LOGGER.info("%s air conditioners initialized", len(entities))


class MoorgenAirconClimate(CoordinatorEntity, ClimateEntity):
    """Air conditioner behind the Moorgen gateway.

    Power uses aircon-power-on/off. Mode, fan speed and setpoint are set together with
    aircon-scne-exec, which the gateway only accepts while turning the unit on.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
    _attr_fan_modes = ["auto", "low", "medium", "high"]
    _attr_supported_features = (
        ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
    )

    def __init__(self, coordinator, device_mac: int, name: str, area: str | None = None):
        super().__init__(coordinator, context=str(device_mac))
        self._device_mac = device_mac
        self._pending: dict = {}
        self._pending_until = 0.0
        self._attr_unique_id = f"moorgen_climate_{device_mac}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_mac))},
            name=name,
            manufacturer="Moorgen",
            model="Air conditioner",
            suggested_area=area,
        )

    @property
    def _device(self) -> dict | None:
        for device in self.coordinator.data.get("devices", []):
            if device.get("Device_Mac") == self._device_mac:
                return device
        return None

    def _reported(self) -> dict:
        device = self._device or {}
        mode, fan = aircon_mode_and_fan(device)
        temps = aircon_temperatures(device)
        return {
            "power": device.get("Device_State") == 1,
            "mode": mode,
            "fan": fan,
            "target": None if temps is None else temps[0],
            "current": None if temps is None else temps[1],
        }

    def _state(self) -> dict:
        state = self._reported()
        if self._pending and time.monotonic() < self._pending_until:
            state.update(self._pending)
        return state

    def _set_pending(self, **values) -> None:
        self._pending = values
        self._pending_until = time.monotonic() + PENDING_SECONDS
        self.async_write_ha_state()

    def _handle_coordinator_update(self) -> None:
        if self._pending:
            reported = self._reported()
            if all(reported.get(k) == v for k, v in self._pending.items()):
                self._pending = {}
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        device = self._device
        return super().available and bool(device) and device.get("Device_is_online", 1) == 1

    @property
    def hvac_mode(self) -> HVACMode | None:
        state = self._state()
        if not state["power"]:
            return HVACMode.OFF
        return PANEL_MODE_TO_HVAC.get(state["mode"])

    @property
    def fan_mode(self) -> str | None:
        return self._state()["fan"]

    @property
    def current_temperature(self) -> float | None:
        return self._state()["current"]

    @property
    def target_temperature(self) -> float | None:
        return self._state()["target"]

    async def async_turn_on(self) -> None:
        await self.coordinator.set_aircon_power(self._device_mac, True)
        self._set_pending(power=True)

    async def async_turn_off(self) -> None:
        await self.coordinator.set_aircon_power(self._device_mac, False)
        self._set_pending(power=False)

    async def _async_apply(self, mode: str, fan: str, target: float) -> None:
        target = min(self.max_temp, max(self.min_temp, target))
        await self.coordinator.set_aircon_state(self._device_mac, mode, fan, target)
        self._set_pending(power=True, mode=mode, fan=fan, target=target)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return
        state = self._state()
        await self._async_apply(
            HVAC_TO_PANEL_MODE[hvac_mode], state["fan"] or "auto", state["target"] or 26
        )

    async def async_set_temperature(self, **kwargs) -> None:
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            return
        state = self._state()
        if hvac_mode is None and not state["power"]:
            raise HomeAssistantError("空调关机时无法调温，请先开机或选择一个模式")
        mode = HVAC_TO_PANEL_MODE[hvac_mode] if hvac_mode else state["mode"] or "cool"
        target = kwargs.get(ATTR_TEMPERATURE, state["target"] or 26)
        await self._async_apply(mode, state["fan"] or "auto", float(target))

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        state = self._state()
        if not state["power"]:
            raise HomeAssistantError("空调关机时无法调风速，请先开机")
        await self._async_apply(state["mode"] or "cool", fan_mode, state["target"] or 26)
