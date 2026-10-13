import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][COORDINATOR]
    scene_buttons = [
        VirtualSceneButton(coordinator, scene.name, scene.id)
        for scene in coordinator.data["scenes"]
    ]
    async_add_entities(scene_buttons)
    _LOGGER.info("%s buttons initialized", len(scene_buttons))


class VirtualSceneButton(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, name, unique_id):
        super().__init__(coordinator, context=unique_id)
        self._attr_name = name
        self._attr_unique_id = unique_id

    async def async_press(self):
        await self.coordinator.activate_scene(self._attr_unique_id)
        _LOGGER.info("Scene '%s' triggered", self._attr_name)
