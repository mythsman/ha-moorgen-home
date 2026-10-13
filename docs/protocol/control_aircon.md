# 控制空调（aircon，a170）

## 1. 业务说明

- 业务目标：空调（`Device_Desc` 含 `a170`，多联机内机）的开关、模式、风速、设定温度控制与状态解析。
- 触发时机：HA `climate` 实体操作。
- 当前状态：**已验证（中）**（APK 命令表/构包代码 + 实机验证；未抓 App 原始包）。

## 2. 协议映射

- 请求：`proto_type=4`, `link_code=9`，`Operate_Type(16)=1`，`Device_Mac(4)`，`Device_Cmd(9)`，可选 `Device_CmdData(10)`
- 回推：`proto_type=5`, `link_code=12`，含 `Device_State(11)`、`Device_CmdData(10)`

| 命令（`Device_Cmd`） | `Device_CmdData` | 作用 | 实机结果 |
|---|---|---|---|
| `aircon-power-on` | 无 | 开机（幂等） | 已开机时再次发送保持开机 |
| `aircon-power-off` | 无 | 关机（幂等） | 已关机时再次发送保持关机 |
| `aircon-reverse-exe` | 无 | 开关翻转 | 翻转 |
| `aircon-scne-exec` | 3 字节，见 4.1 | 一次性设置开关/模式/风速/温度 | 0.2~5 秒内回推新状态 |

APK 中还定义了 `aircon-mode`、`aircon-temp-add`、`aircon-temp-del`、`aircon-wind-adjust`、`aircon-wind`、`aircon-backlight`，参数格式未确认，本实现未使用。

## 3. 请求样本

```text
aircon-power-on：
233500646f6f796173686370010409000024001000010001040008000021ffffffffffff09000f00616972636f6e2d706f7765722d6f6e23

aircon-scne-exec（开 / 制冷 / 高风 / 26℃）：
233d00646f6f79617368637001040900002c001000010001040008000021ffffffffffff09001000616972636f6e2d73636e652d657865630a00030052133423
```

## 4. 字段说明

### 4.1 `aircon-scne-exec` 数据（温控器类型，设备版本 < 106）

| 字节 | 含义 |
|---|---|
| 0 | `0x52` 开机 / `0x53` 关机 |
| 1 | `(模式 << 4) \| 风速` |
| 2 | `round(设定温度 × 2)`（设备版本 ≥ 36） |

- 模式（APK `CmdTools$AirconMode`）：制冷 1、除湿 2、送风 3、制热 4、自动 5
- 风速（APK `CmdTools$AirconSpeed`）：自动 0、低 1、中 2、高 3
- 来源：APK `CmdUtils#doGetAirconSceneCmd` 中 `TEMP_CONTROLLER` 分支；版本 ≥ 106 时数据为 4~6 字节（未实现）。

### 4.2 状态 `Device_CmdData`（4 字节）

| 字节 | 含义 |
|---|---|
| 0 | `模式 << 5 \| 风速 << 3`（模式值同上：`0x20` 制冷、`0x60` 送风、`0x80` 制热；风速 `0x00` 自动、`0x08` 低、`0x10` 中、`0x18` 高） |
| 1 | 设定温度 × 2 |
| 2 | 室温 × 10（实测为整数度） |
| 3 | 未知（恒为 0） |

`Device_State(11)`：`1` 开机，`0` 关机。模式/风速映射通过在墙面面板上逐一切换并抓取回推确认。

## 5. 解析结论与边界

- 已确认：`aircon-scne-exec` 带关机标志（`0x53`）时网关无响应，**关机状态下无法单独修改温度/风速**；需带开机标志一并下发。
- 已确认：多联机同一外机下的内机须同为制冷或同为制热；与正在运行的内机模式冲突时，切换后数秒内会被系统拉回原模式。
- 已确认：面板上的部分按键（如背光）不会体现在状态字节中。
- 未确认：`aircon-mode` / `aircon-wind-adjust` / `aircon-temp-add` 的参数格式。

## 6. 单测映射

- 测试文件：`tests/protocol/test_control_aircon.py`
  - `test_control_aircon_power_request_encode_decode_matches_sample`：开/关机请求与样本一致，且无 `Device_CmdData`
  - `test_control_aircon_set_state_request_encode_decode_matches_sample`：`aircon-scne-exec` 请求与样本一致
  - `test_control_aircon_set_state_command_off_flag_and_half_degree`：关机标志与 0.5℃ 编码
  - `test_control_aircon_status_decode_matches_panel`：状态字节解析与面板操作一致
