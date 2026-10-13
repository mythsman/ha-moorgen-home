from .codec import build_protocol_packet


def query_room_info():
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=3,
        linkCode=7,
        serialNum=0,
        fields=[{"type": 15, "value": 11}],
    )


def query_user_info():
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=3,
        linkCode=7,
        serialNum=0,
        fields=[{"type": 15, "value": 9}],
    )


def query_device_details():
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=3,
        linkCode=7,
        serialNum=0,
        fields=[{"type": 15, "value": 1}],
    )


def query_scene_details():
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=3,
        linkCode=7,
        serialNum=0,
        fields=[{"type": 15, "value": 17}],
    )


def activate_scene(scene_name):
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=4,
        linkCode=9,
        serialNum=0,
        fields=[{"type": 16, "value": 5}, {"type": 2, "value": scene_name}],
    )


def control_device(device_mac: int, device_cmd: str):
    cmd_numeric = int.from_bytes(device_cmd.encode("utf-8"), "little")
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=4,
        linkCode=9,
        serialNum=0,
        fields=[
            {"type": 16, "value": 1},
            {"type": 4, "value": device_mac},
            {"type": 9, "value": cmd_numeric},
        ],
    )


def control_device_dimming(device_mac: int, level: int):
    level = max(0, min(100, int(level)))
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=4,
        linkCode=9,
        serialNum=0,
        fields=[
            {"type": 16, "value": 1},
            {"type": 4, "value": device_mac},
            {"type": 9, "value": int.from_bytes("random-light-dimming".encode("utf-8"), "little")},
            {"type": 10, "value": chr(level)},
        ],
    )


# Mode / fan values used by aircon-scne-exec (CmdTools$AirconMode / $AirconSpeed in the app).
AIRCON_MODE_VALUES = {"cool": 1, "dry": 2, "fan_only": 3, "heat": 4, "auto": 5}
AIRCON_FAN_VALUES = {"auto": 0, "low": 1, "medium": 2, "high": 3}


def aircon_set_state(device_mac: int, power_on: bool, mode: str, fan: str, temperature: float):
    """Set power, mode, fan and setpoint in one go (temperature-controller layout, version < 106).

    Data: [0x52 on / 0x53 off, (mode << 4) | fan, round(temperature * 2)].
    The gateway ignores this while the unit is off unless power_on is set.
    """
    data = bytes(
        [
            0x52 if power_on else 0x53,
            ((AIRCON_MODE_VALUES[mode] << 4) & 0xF0) | (AIRCON_FAN_VALUES[fan] & 0x0F),
            round(temperature * 2) & 0xFF,
        ]
    )
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=4,
        linkCode=9,
        serialNum=0,
        fields=[
            {"type": 16, "value": 1},
            {"type": 4, "value": device_mac},
            {"type": 9, "value": int.from_bytes(b"aircon-scne-exec", "little")},
            {"type": 10, "value": data},
        ],
    )


def curtain_set_position(device_mac: int, gateway_position: int):
    """curtain-point: move to a gateway position (0 = fully open/up, 100 = fully closed/down)."""
    return build_protocol_packet(
        msgFlag=0x23,
        protoName="dooyashcp",
        protoNum=1,
        protoType=4,
        linkCode=9,
        serialNum=0,
        fields=[
            {"type": 16, "value": 1},
            {"type": 4, "value": device_mac},
            {"type": 9, "value": int.from_bytes(b"curtain-point", "little")},
            {"type": 10, "value": bytes([max(0, min(100, int(gateway_position)))])},
        ],
    )
