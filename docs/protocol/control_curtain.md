# 控制窗帘（curtain，c140）

## 1. 业务说明

- 业务目标：窗帘电机（`Device_Desc` 含 `c140`）的开、关、停与定位控制，以及位置/运动状态解析。
- 触发时机：HA `cover` 实体操作。
- 当前状态：**已验证（中）**（APK 命令表/状态判定代码 + 实机验证）。

## 2. 协议映射

- 请求：`proto_type=4`, `link_code=9`，`Operate_Type(16)=1`，`Device_Mac(4)`，`Device_Cmd(9)`，可选 `Device_CmdData(10)`
- 回推：`proto_type=5`, `link_code=12`，运动过程中约每 3 秒一次

| 命令（`Device_Cmd`） | `Device_CmdData` | 作用 |
|---|---|---|
| `curtain-up` | 无 | 向位置 0 运动（打开） |
| `curtain-down` | 无 | 向位置 100 运动（关闭） |
| `curtain-stop` | 无 | 停止 |
| `curtain-point` | 1 字节，目标位置 0~100 | 运动到指定位置 |
| `curtain-reverse-exe` | 无 | 翻转 |

命令名来自 APK `CmdTools$MotoCmd`。

## 3. 请求样本

```text
curtain-point（位置 50）：
233800646f6f796173686370010409000027001000010001040008000090ffffffffffff09000d006375727461696e2d706f696e740a0001003223
```

## 4. 状态字段

- `Device_CmdData` 字节 0：网关位置，**0 = 全开（up），100 = 全关（down）**；HA 中换算为 `100 - 位置`。
- `Device_State(11)`（APK `StatusUtils#isMotoDown/isMotoUp/isMotoStop`）：

| 值 | 含义 |
|---|---|
| 16 / 19 | 下行（关闭中） |
| 17 / 20 | 上行（打开中） |
| 18 / 21 | 停止 |

19~21，或位置字节为 `0xFF`/`0xFE`，表示行程未设置（位置不可用）。

## 5. 实机验证记录

| 操作 | 结果 |
|---|---|
| 位置 100 时 `curtain-down` | 无响应（已到底） |
| `curtain-point` + 50 | 100 → 57 → 50，停止 |
| `curtain-up` | 50 → 5 → 0，停止 |
| `curtain-down` 后 2 秒 `curtain-stop` | 停在 26 |
| `curtain-down` | 26 → 74 → 100，停止 |

## 6. 单测映射

- 测试文件：`tests/protocol/test_control_curtain.py`
  - `test_control_curtain_move_request_encode_decode_matches_sample`：up/down/stop 请求与样本一致
  - `test_control_curtain_point_request_encode_decode_matches_sample`：定位请求与样本一致
  - `test_control_curtain_point_command_clamps_position`：位置限制在 0~100
