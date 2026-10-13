"""Spec: docs/protocol/control_aircon.md"""

from __future__ import annotations

import pytest

from custom_components.ha_moorgen_home.core.protocol.codec import (
    aircon_mode_and_fan,
    aircon_temperatures,
    parse_protocol_packet,
)
from custom_components.ha_moorgen_home.core.protocol.commands import (
    aircon_set_state,
    control_device,
)

from tests.protocol._shared import extract_tlv_value_bytes
from tests.protocol.fixtures.control_aircon_assets import (
    AIRCON_MAC,
    REQ_AIRCON_POWER_OFF_HEX,
    REQ_AIRCON_POWER_ON_HEX,
    REQ_AIRCON_SET_COOL_HIGH_25_HEX,
    REQ_AIRCON_SET_COOL_HIGH_26_HEX,
    REQ_AIRCON_SET_FAN_ONLY_HIGH_26_HEX,
    STATUS_SAMPLES,
)


@pytest.mark.parametrize(
    ("cmd", "expected_hex"),
    [
        ("aircon-power-on", REQ_AIRCON_POWER_ON_HEX),
        ("aircon-power-off", REQ_AIRCON_POWER_OFF_HEX),
    ],
)
def test_control_aircon_power_request_encode_decode_matches_sample(cmd, expected_hex):
    assert control_device(AIRCON_MAC, cmd).hex() == expected_hex

    packet = parse_protocol_packet(bytes.fromhex(expected_hex))
    assert (packet.proto_type, packet.link_code) == (4, 9)
    assert extract_tlv_value_bytes(expected_hex, 9) == cmd.encode()
    assert extract_tlv_value_bytes(expected_hex, 10) is None


@pytest.mark.parametrize(
    ("mode", "fan", "temperature", "expected_hex", "expected_data"),
    [
        ("cool", "high", 26, REQ_AIRCON_SET_COOL_HIGH_26_HEX, bytes([0x52, 0x13, 52])),
        ("fan_only", "high", 26, REQ_AIRCON_SET_FAN_ONLY_HIGH_26_HEX, bytes([0x52, 0x33, 52])),
        ("cool", "high", 25, REQ_AIRCON_SET_COOL_HIGH_25_HEX, bytes([0x52, 0x13, 50])),
    ],
)
def test_control_aircon_set_state_request_encode_decode_matches_sample(
    mode, fan, temperature, expected_hex, expected_data
):
    assert aircon_set_state(AIRCON_MAC, True, mode, fan, temperature).hex() == expected_hex

    assert extract_tlv_value_bytes(expected_hex, 9) == b"aircon-scne-exec"
    assert extract_tlv_value_bytes(expected_hex, 10) == expected_data


def test_control_aircon_set_state_command_off_flag_and_half_degree():
    data = extract_tlv_value_bytes(
        aircon_set_state(AIRCON_MAC, False, "heat", "low", 22.5).hex(), 10
    )
    assert data == bytes([0x53, 0x41, 45])


@pytest.mark.parametrize(("raw", "mode", "fan", "setpoint", "room"), STATUS_SAMPLES)
def test_control_aircon_status_decode_matches_panel(raw, mode, fan, setpoint, room):
    device = {"Device_CmdData": raw}
    assert aircon_mode_and_fan(device) == (mode, fan)
    assert aircon_temperatures(device) == (setpoint, room)


def test_control_aircon_status_decode_short_payload_returns_none():
    assert aircon_temperatures({"Device_CmdData": b"\x20"}) is None
    assert aircon_mode_and_fan({}) == (None, None)
