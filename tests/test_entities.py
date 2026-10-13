"""Entity-level behaviour that does not need a running Home Assistant."""

from __future__ import annotations

import pytest

from custom_components.ha_moorgen_home.light import (
    MoorgenLightEntity,
    brightness_to_level,
    level_to_brightness,
)

MAC = 0x1101


class _FakeCoordinator:
    def __init__(self, devices, last_update_success=True):
        self.data = {"devices": devices}
        self.last_update_success = last_update_success


@pytest.mark.parametrize(
    ("brightness", "level"),
    [(0, 0), (1, 1), (2, 1), (3, 1), (128, 50), (254, 100), (255, 100), (300, 100)],
)
def test_light_brightness_to_level_never_turns_off_when_non_zero(brightness, level):
    assert brightness_to_level(brightness) == level


@pytest.mark.parametrize(("level", "brightness"), [(0, 0), (1, 3), (50, 128), (100, 255)])
def test_light_level_to_brightness(level, brightness):
    assert level_to_brightness(level) == brightness


@pytest.mark.parametrize(
    ("online", "last_update_success", "available"),
    [(1, True, True), (0, True, False), (1, False, False)],
)
def test_light_available_follows_device_and_gateway(online, last_update_success, available):
    device = {"Device_Mac": MAC, "Device_is_online": online, "Device_State": 1}
    coordinator = _FakeCoordinator([device], last_update_success)
    light = MoorgenLightEntity(coordinator, MAC, "灯", supports_brightness=False)
    assert light.available is available
