"""Assets for docs/protocol/control_aircon.md.

Requests were sent to an a170 unit and confirmed by the 5/12 push that followed.
"""

AIRCON_MAC = 0xFFFFFFFFFFFF2100

REQ_AIRCON_POWER_ON_HEX = "233500646f6f796173686370010409000024001000010001040008000021ffffffffffff09000f00616972636f6e2d706f7765722d6f6e23"
REQ_AIRCON_POWER_OFF_HEX = "233600646f6f796173686370010409000025001000010001040008000021ffffffffffff09001000616972636f6e2d706f7765722d6f666623"
REQ_AIRCON_SET_COOL_HIGH_26_HEX = "233d00646f6f79617368637001040900002c001000010001040008000021ffffffffffff09001000616972636f6e2d73636e652d657865630a00030052133423"
REQ_AIRCON_SET_FAN_ONLY_HIGH_26_HEX = "233d00646f6f79617368637001040900002c001000010001040008000021ffffffffffff09001000616972636f6e2d73636e652d657865630a00030052333423"
REQ_AIRCON_SET_COOL_HIGH_25_HEX = "233d00646f6f79617368637001040900002c001000010001040008000021ffffffffffff09001000616972636f6e2d73636e652d657865630a00030052133223"

# Device_CmdData of 5/12 pushes observed while switching modes / fan speeds on the wall panel:
# [mode << 5 | fan << 3, setpoint * 2, room_temp * 10, 0]
STATUS_SAMPLES = [
    # (raw bytes, expected mode, expected fan, setpoint, room temperature)
    (bytes([0x20, 52, 240, 0]), "cool", "auto", 26.0, 24.0),
    (bytes([0x28, 52, 240, 0]), "cool", "low", 26.0, 24.0),
    (bytes([0x30, 52, 240, 0]), "cool", "medium", 26.0, 24.0),
    (bytes([0x38, 52, 240, 0]), "cool", "high", 26.0, 24.0),
    (bytes([0x70, 52, 240, 0]), "fan_only", "medium", 26.0, 24.0),
    (bytes([0x90, 52, 240, 0]), "heat", "medium", 26.0, 24.0),
    (bytes([0x88, 50, 220, 0]), "heat", "low", 25.0, 22.0),
]
