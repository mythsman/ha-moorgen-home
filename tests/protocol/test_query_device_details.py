"""Spec: docs/protocol/query_device_details.md"""

from __future__ import annotations

from custom_components.ha_moorgen_home.core.protocol.codec import (
    build_protocol_packet,
    infer_device_type,
    parse_protocol_packet,
    route,
)
from custom_components.ha_moorgen_home.core.protocol.commands import query_device_details

# 抓包样本请求（query device details）
from tests.protocol.fixtures.query_device_details_assets import (
    EXPECTED_REQ_JSON,
    EXPECTED_RSP_JSON,
    REQ_DEVICE_HEX,
    RSP_DEVICE_HEX,
)


def _request_json_to_hex(payload: dict) -> str:
    packet = build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=payload["proto_type"],
        linkCode=payload["link_code"],
        serialNum=payload.get("serial_num", 0),
        fields=[{"type": 15, "value": payload["datareq_type"]}],
    )
    return packet.hex()


def _request_hex_to_json(packet_hex: str) -> dict:
    packet = parse_protocol_packet(bytes.fromhex(packet_hex))
    datareq_type = next((f.value for f in packet.fields if f.id == 15), None)
    return {
        "action": "query_device_details",
        "proto_type": packet.proto_type,
        "link_code": packet.link_code,
        "serial_num": packet.serial_num,
        "datareq_type": datareq_type,
    }


def _response_hex_to_json(packet_hex: str) -> dict:
    packet = parse_protocol_packet(bytes.fromhex(packet_hex))

    datareq_type = next((f.value for f in packet.fields if f.id == 15), None)
    device_count = next((f.value for f in packet.fields if f.id == 17), None)
    request_data_over = next((f.value for f in packet.fields if f.id == 148), None)

    data = {}
    routed = route(packet, data)
    assert routed == "devices"

    return {
        "action": "query_device_details",
        "proto_type": packet.proto_type,
        "link_code": packet.link_code,
        "serial_num": packet.serial_num,
        "datareq_type": datareq_type,
        "device_count": device_count,
        "request_data_over": request_data_over,
        "devices": data.get("devices", []),
    }


def test_query_device_details_request_encode_decode_and_command_default_serial():
    # JSON -> HEX（与抓包原样一致）
    req_hex = _request_json_to_hex(EXPECTED_REQ_JSON)
    assert req_hex == REQ_DEVICE_HEX

    # 对比现有 commands 默认 serial=0 的固定构包
    assert query_device_details().hex() == "231600646f6f796173686370010307000005000f0001000123"

    # HEX -> JSON（抓包样本）
    req_json_back = _request_hex_to_json(REQ_DEVICE_HEX)
    assert req_json_back == EXPECTED_REQ_JSON


def test_query_device_details_response_decode_matches_expected_json():
    rsp_json = _response_hex_to_json(RSP_DEVICE_HEX)
    assert rsp_json == EXPECTED_RSP_JSON


def test_query_device_details_infer_device_type_matrix():
    packet = parse_protocol_packet(bytes.fromhex(RSP_DEVICE_HEX))
    data = {}
    assert route(packet, data) == "devices"

    actual = {
        d.get("Device_Name"): infer_device_type(d)
        for d in data.get("devices", [])
    }

    expected = {
        "床头射灯": "light",
        "右阅读灯": "light",
        "灯带": "light",
        "飘窗射灯": "light",
        "左阅读灯": "light",
        "2-4": "light",
        "2-5": "light",
        "2-60": "light",
        "一键断电": "light",
        "玄关灯带": "light",
        "天花灯带": "light",
        "客餐射灯": "light",
        "客厅主灯": "light",
        "餐厅主灯": "light",
        "过道射灯": "light",
        "主灯": "light",
        "背景射灯": "light",
        "玄关面板": "light_dimmer",
        "客厅面板": "light_dimmer",
        "主卧进门面板": "light_dimmer",
        "主卧床头左": "light_dimmer",
        "主卧床头右": "light_dimmer",
        "客厅地暖": "floor_heating",
        "客厅新风": "fresh_air",
        "客厅空调": "air_conditioner",
        "餐厅地暖": "floor_heating",
        "餐厅新风": "fresh_air",
        "餐厅空调": "air_conditioner",
        "主卧地暖": "floor_heating",
        "主卧新风": "fresh_air",
        "主卧空调": "air_conditioner",
        "北次卧1地暖": "floor_heating",
        "北次卧1新风": "fresh_air",
        "北次卧1空调": "air_conditioner",
        "北次卧2地暖": "floor_heating",
        "北次卧2新风": "fresh_air",
        "北次卧2空调": "air_conditioner",
        "南次卧地暖": "floor_heating",
        "南次卧新风": "fresh_air",
        "南次卧空调": "air_conditioner",
        "新风-1": "fresh_air",
        "客餐厅1": "hvac_group",
        "北次卧2": "hvac_group",
        "客餐厅2": "hvac_group",
        "主卧": "hvac_group",
        "书房": "hvac_group",
        "南次卧": "hvac_group",
    }

    assert actual == expected


def _device_list_packet(macs: list[int], last: bool) -> bytes:
    fields = [{"type": 15, "value": 4}, {"type": 17, "value": len(macs)}]
    for mac in macs:
        fields += [
            {"type": 4, "value": mac},
            {"type": 6, "value": f"dev-{mac & 0xFF}"},
            {"type": 11, "value": 0},
        ]
    if last:
        fields.append({"type": 148, "value": 1})
    return build_protocol_packet(0x23, "dooyashcp", 1, 3, 8, 0, fields)


def test_query_device_details_multi_packet_response_merges_until_data_over():
    data = {"devices": []}
    first = parse_protocol_packet(_device_list_packet([0x1101, 0x1102], last=False))
    second = parse_protocol_packet(_device_list_packet([0x1103], last=False))
    final = parse_protocol_packet(_device_list_packet([0x1104], last=True))

    assert route(first, data) is None
    assert route(second, data) is None
    assert data["devices"] == []

    assert route(final, data) == "devices"
    assert [d["Device_Mac"] for d in data["devices"]] == [0x1101, 0x1102, 0x1103, 0x1104]
    assert "_pending_devices" not in data


def test_query_device_details_infer_r153_without_panel_state_is_panel():
    assert infer_device_type({"Device_Desc": b"dooyar0200r153\x300", "Device_Name": "x"}) == "panel"
    assert (
        infer_device_type({"Device_Desc": b"dooyar0100r153\x800", "PANEL_STATE": 65280})
        == "light_dimmer"
    )
    assert infer_device_type({"Device_Desc": b"dooyar0300c140\x100"}) == "curtain"
