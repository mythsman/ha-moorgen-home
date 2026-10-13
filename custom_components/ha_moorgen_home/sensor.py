import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN
from .core.protocol.codec import aircon_temperatures, device_room_id, infer_device_type

_LOGGER = logging.getLogger(__name__)

# (key, name, index into aircon_temperatures(), state_class)
AIRCON_SENSORS = (
    ("room_temperature", "室温", 1, SensorStateClass.MEASUREMENT),
    ("target_temperature", "设定温度", 0, None),
)


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

        device_info = DeviceInfo(
            identifiers={(DOMAIN, str(device_mac))},
            name=device_name,
            manufacturer="Moorgen",
            model="Air conditioner",
            suggested_area=room_names.get(device_room_id(device)),
        )
        for key, name, index, state_class in AIRCON_SENSORS:
            entities.append(
                MoorgenAirconTemperatureSensor(
                    coordinator, device_mac, device_info, key, name, index, state_class
                )
            )

    async_add_entities(entities)
    _LOGGER.info("%s air conditioner sensors initialized", len(entities))


class MoorgenAirconTemperatureSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator,
        device_mac: int,
        device_info,
        key: str,
        name: str,
        index: int,
        state_class,
    ):
        super().__init__(coordinator, context=str(device_mac))
        self._device_mac = device_mac
        self._index = index
        self._attr_name = name
        self._attr_state_class = state_class
        self._attr_unique_id = f"moorgen_aircon_{device_mac}_{key}"
        self._attr_device_info = device_info

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
    def native_value(self) -> float | None:
        temps = aircon_temperatures(self._device or {})
        return None if temps is None else temps[self._index]
