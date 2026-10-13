"""Spec: docs/protocol/keepalive.md"""

from __future__ import annotations

from custom_components.ha_moorgen_home.core.protocol.codec import (
    build_heartbeat_ack,
    is_heartbeat_ping,
    parse_protocol_packet,
)

from tests.protocol.fixtures.keepalive_assets import ACK_HEX, PING_HEX


def test_keepalive_ping_decode_is_heartbeat():
    packet = parse_protocol_packet(bytes.fromhex(PING_HEX))
    assert (packet.proto_type, packet.link_code) == (6, 13)
    assert packet.fields == []
    assert is_heartbeat_ping(packet)


def test_keepalive_ack_encode_matches_sample():
    assert build_heartbeat_ack(bytes.fromhex(PING_HEX)).hex() == ACK_HEX
    ack = parse_protocol_packet(bytes.fromhex(ACK_HEX))
    assert (ack.proto_type, ack.link_code) == (6, 14)
    assert not is_heartbeat_ping(ack)
