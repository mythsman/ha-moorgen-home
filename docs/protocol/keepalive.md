# 心跳保活（keepalive）

## 1. 业务说明

- 业务目标：保持与网关的 TCP 长连接。
- 触发时机：连接建立后，网关每约 10 秒主动下发一次心跳。
- 当前状态：**已验证（中）**（实机抓包 + 实机对照实验）。

## 2. 协议映射

- 网关 -> 客户端：`proto_type=6`, `link_code=13`，无 TLV
- 客户端 -> 网关：`proto_type=6`, `link_code=14`，无 TLV（原样回显，仅改 `link_code`）

## 3. 抓包样本

```text
网关心跳： 231100646f6f79617368637001060d0000000023
客户端回应：231100646f6f79617368637001060e0000000023
```

## 4. 实机对照实验

| 实验 | 结果 |
|---|---|
| 建立连接后不发送任何数据、不回应心跳 | 收到 5 次 `6/13`（+10s ~ +50s），**+60s 网关主动断开** |
| 建立连接后对每个 `6/13` 回应 `6/14` | 95s 内连接保持，未断开 |

## 5. 解析结论与边界

- 已确认：网关约 60 秒内收不到心跳回应即断开连接。
- 影响：旧实现不回应心跳，被断开后触发 `ServerDisconnectedError` 并进入 600 秒冷却，期间无法控制设备。
- 实现：`codec.is_heartbeat_ping` / `codec.build_heartbeat_ack`，在 `socket_client._read_loop` 中收到后立即回应。
- 已确认：网关允许多个客户端同时连接（HA 与调试脚本并存时 HA 未被断开）。

## 6. 单测映射

- 测试文件：`tests/protocol/test_keepalive.py`
  - `test_keepalive_ping_decode_is_heartbeat`：心跳包解析为 `6/13` 且无 TLV
  - `test_keepalive_ack_encode_matches_sample`：回应包与样本一致
