# 协议分析总览

本目录按**业务逻辑**组织协议分析文档，而不是按 `proto_type/link_code` 命名。

## 文档索引

| 业务名称 | 文档 | proto_type | link_code | 关键 TLV | 请求/响应 | Java 入口 | 单测 |
|---|---|---:|---:|---|---|---|---|
| 查询场景简表 | `query_scene_simple.md` | 3 | 7 / 8 | `15=17/18`, `2`, `1`, `94`, `148` | req/rsp | `MainAction.get_Byte_Data_Req` | `tests/protocol/test_query_scene_simple.py` |
| 执行场景（scene id） | `activate_scene.md` | 4 / 5 / 6 | 9 / 12 / 13 / 14 | `16=5`, `2(scene_id)`, 推送`11` | req + push + keepalive | `MainAction.get_Byte_Data_Req`（待补） | `tests/protocol/test_activate_scene.py` |
| 控制设备开关（device cmd） | `control_device.md` | 4 / 5 / 6 | 9 / 12 / 13 / 14 | `16=1`, `4(device_mac)`, `9(light-on/off)`, 推送`11` | req + push + keepalive | 待补 | `tests/protocol/test_control_device.py` |
| 控制设备调光（dimming） | `control_device_dimming.md` | 4 / 5 / 6 | 9 / 12 / 13 / 14 | `16=1`, `4(device_mac)`, `9=random-light-dimming`, `10=brightness`, 推送`151` | req + push + keepalive | 待补 | `tests/protocol/test_control_device_dimming.py` |
| 查询房间信息 | `query_room_info.md` | 3 | 7 / 8 | `15=11/12`, `53`, `48`, `54`, `55`, `148` | req/rsp | `MainAction.get_Byte_Data_Req` | `tests/protocol/test_query_room_info.py` |
| 查询设备详情 | `query_device_details.md` | 3 | 7 / 8 | `15=1/4`, `17`, `4`, `6`, `48`, `148` | req/rsp（多包） | `MainAction.get_Byte_Data_Req` | `tests/protocol/test_query_device_details.py` |
| 控制空调（a170） | `control_aircon.md` | 4 / 5 | 9 / 12 | `16=1`, `4`, `9=aircon-*`, `10`（scne-exec 3 字节） | req + push | `CmdTools$AirConditonCmd`, `CmdUtils#doGetAirconSceneCmd` | `tests/protocol/test_control_aircon.py` |
| 控制窗帘（c140） | `control_curtain.md` | 4 / 5 | 9 / 12 | `16=1`, `4`, `9=curtain-*`, `10`（point 1 字节） | req + push | `CmdTools$MotoCmd`, `StatusUtils#isMoto*` | `tests/protocol/test_control_curtain.py` |
| 心跳保活 | `keepalive.md` | 6 | 13 / 14 | 无 TLV | ping + ack | — | `tests/protocol/test_keepalive.py` |

## 状态说明

- 证据等级：
  - **高**：抓包 + Java 代码双证据，且测试覆盖
  - **中**：抓包或代码单边证据
  - **低**：推测，待样本验证

当前已完成：
- 查询场景简表（证据等级：高）
- 执行场景（证据等级：中，抓包已验证）
- 控制设备开关（证据等级：中，抓包已验证）
- 控制设备调光（证据等级：中，抓包已验证）
- 查询房间信息（证据等级：高）
- 查询设备详情（证据等级：高；含多包合并）
- 控制空调（证据等级：中，APK + 实机验证）
- 控制窗帘（证据等级：中，APK + 实机验证）
- 心跳保活（证据等级：中，抓包 + 实机对照实验）

## 维护规则

1. 每新增一种业务协议，先在本索引表登记。
2. 每条协议结论都要在对应单测有可追踪断言。
3. 协议测试详细规范以 `docs/DEVELOPER_GUIDE.md` 第 `9.1` 节为准。
4. 业务文档仅保留该业务证据与结论，避免在此重复展开全局规范。
