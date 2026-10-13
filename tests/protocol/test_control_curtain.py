"""Spec: docs/protocol/control_curtain.md"""

from __future__ import annotations

import pytest

from custom_components.ha_moorgen_home.core.protocol.codec import parse_protocol_packet
from custom_components.ha_moorgen_home.core.protocol.commands import (
    control_device,
    curtain_set_position,
)

from tests.protocol._shared import extract_tlv_value_bytes
from tests.protocol.fixtures.control_curtain_assets import (
    CURTAIN_MAC,
    REQ_CURTAIN_DOWN_HEX,
    REQ_CURTAIN_POINT_50_HEX,
    REQ_CURTAIN_STOP_HEX,
    REQ_CURTAIN_UP_HEX,
)


@pytest.mark.parametrize(
    ("cmd", "expected_hex"),
    [
        ("curtain-up", REQ_CURTAIN_UP_HEX),
        ("curtain-down", REQ_CURTAIN_DOWN_HEX),
        ("curtain-stop", REQ_CURTAIN_STOP_HEX),
    ],
)
def test_control_curtain_move_request_encode_decode_matches_sample(cmd, expected_hex):
    assert control_device(CURTAIN_MAC, cmd).hex() == expected_hex
    packet = parse_protocol_packet(bytes.fromhex(expected_hex))
    assert (packet.proto_type, packet.link_code) == (4, 9)
    assert extract_tlv_value_bytes(expected_hex, 9) == cmd.encode()


def test_control_curtain_point_request_encode_decode_matches_sample():
    assert curtain_set_position(CURTAIN_MAC, 50).hex() == REQ_CURTAIN_POINT_50_HEX
    assert extract_tlv_value_bytes(REQ_CURTAIN_POINT_50_HEX, 9) == b"curtain-point"
    assert extract_tlv_value_bytes(REQ_CURTAIN_POINT_50_HEX, 10) == bytes([50])


@pytest.mark.parametrize(("requested", "sent"), [(-5, 0), (0, 0), (100, 100), (130, 100)])
def test_control_curtain_point_command_clamps_position(requested, sent):
    data = extract_tlv_value_bytes(curtain_set_position(CURTAIN_MAC, requested).hex(), 10)
    assert data == bytes([sent])
