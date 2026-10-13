# 开发文档（DEVELOPER GUIDE）

本文档面向插件开发者，包含架构说明、关键实现与调试建议。

---

## 0. 文档分工（单一事实源）

- `README.md`：**仅面向使用者**（安装、配置、运行、日志与更新）。不放架构设计、刷新策略、重连策略等实现细节。
- `docs/DEVELOPER_GUIDE.md`：面向开发者（架构设计、实现细节、开发规范与测试规范**权威来源**）。
- `agent.md`：面向 AI/自动化协作的执行约束（简版规则，引用本指南）。
- `docs/protocol/README.md`：协议业务索引与状态面板。
- `docs/protocol/TEMPLATE.md`：新增协议文档模板。

---

## 1. 架构概览

集成代码根目录：`custom_components/ha_moorgen_home/`

核心链路：

1. `custom_components/ha_moorgen_home/config_flow.py` 接收 host/port 配置
2. `custom_components/ha_moorgen_home/__init__.py` 初始化 coordinator 并加载 `button` / `climate` / `cover` / `light` / `sensor` 平台
3. `custom_components/ha_moorgen_home/core/coordinator.py` 周期刷新数据（10s）并协调首次同步策略
4. `custom_components/ha_moorgen_home/core/refresh_scheduler.py` 负责操作后刷新调度（1/2/4s）、合并与节流（>=1s）
5. `custom_components/ha_moorgen_home/core/socket_client.py` 维护 TCP 连接、收发包
6. `custom_components/ha_moorgen_home/core/protocol/*` 负责协议模型、编解码、命令构造
7. `custom_components/ha_moorgen_home/button.py` 将场景映射为按钮实体并触发执行
8. `light.py` / `climate.py` / `cover.py` / `sensor.py` 将灯、空调、窗帘、空调温度映射为实体；每个物理设备注册为 HA 设备，并按 `Device_Desc` 中的房间 ID 设置 `suggested_area`

---

## 2. 代码结构

以下路径均相对 `custom_components/ha_moorgen_home/`：

- `__init__.py`：集成入口与卸载
- `config_flow.py`：UI 配置流程
- `button.py`：ButtonEntity 实现（场景触发）
- `light.py`：LightEntity 实现（普通灯开/关、调光灯亮度）
- `climate.py`：ClimateEntity 实现（空调开关、模式、风速、设定温度）
- `cover.py`：CoverEntity 实现（窗帘开/关/停/定位）
- `sensor.py`：空调室温、设定温度传感器
- `const.py`：全局常量（`DOMAIN`、`COORDINATOR`）
- `core/coordinator.py`：DataUpdateCoordinator 逻辑
- `core/socket_client.py`：连接生命周期、重连策略、收发包
- `core/refresh_scheduler.py`：操作后刷新调度、合并与节流
- `core/protocol/models.py`：协议字段映射与 dataclass 模型
- `core/protocol/codec.py`：协议构包/解包、路由与解析
- `core/protocol/commands.py`：业务命令封装

---

## 3. 重连策略设计（单连接服务端适配）

针对“服务端只允许单连接”的场景：

- 普通连接异常：不在 socket 层快速死循环重连；等待下次 coordinator 刷新触发按需连接。
- 服务端主动断开（`ServerDisconnectedError`）：进入冷却期（默认 600 秒）。
- 心跳：网关每约 10 秒下发 `6/13`，约 60 秒收不到 `6/14` 回应即断开连接；`_read_loop` 收到后立即回应（见 `docs/protocol/keepalive.md`）。
- 实测网关允许多个客户端同时连接。
- 刷新时网关不可达（`ConnectionError`，含冷却期）会抛出 `UpdateFailed`，各实体随之显示为不可用，而不是继续展示旧状态。
- 冷却时间可在 `custom_components/ha_moorgen_home/core/socket_client.py` 的 `_kick_cooldown_seconds` 调整。

目的：避免调试期间 HA 频繁抢占连接。

---

## 4. 生命周期与热更新相关

- 已实现 `async_unload_entry` → `coordinator.async_shutdown()` → `client.stop()`，可正确释放后台连接任务。
- 但 Python 模块级热更新不保证 100% 安全；代码更新后建议重启 HA Core。

---

## 5. 协议层拆分说明

- `models.py`：`data_types`、`get_type_by_id`、`DataPacket` 等
- `codec.py`：`parse_protocol_packet`、`build_protocol_packet`、`route`、`parse_*_info`
- `commands.py`：`query_scene_details`、`activate_scene` 等命令构造

---

## 6. 本地开发

建议 Python 3.13+。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

代码检查：

```bash
ruff check .
ruff check . --fix
ruff format .
```

测试：

```bash
pytest -q
```

---

## 7. 数据刷新与同步策略

- 兜底刷新：`DataUpdateCoordinator.update_interval = 10s`。
- 设备详情可能分多个包下发，`route` 暂存直到收到 `REQUEST_DATA_OVER(148)` 才更新 `devices` 并递增 `device_version`（见 `query_device_details.md` 附录 A）。
- 首次刷新（`async_config_entry_first_refresh`）：
  - 发送 `query_scene_details` + `query_device_details`
  - 等待 `scene_version` / `device_version` 变化后返回数据
  - 目的：保证首次平台初始化时 `scenes/devices` 尽量完整
- 后续刷新：仅发送查询，不再 `wait_for_*_update`（降低阻塞）。
- 操作后加速刷新：
  - 场景触发、灯开关后调度 `1s/2s/4s` 三次 `async_request_refresh`
  - 多操作并发时做同 delay 合并
  - 刷新最小间隔 `>=1s`（锁 + 节流）
- 当前不处理设备推送（`proto_type=5/link=12`）的实体直更，状态以拉取结果为准。

## 8. 当前已知限制

- 实体在平台初始化时创建，设备或场景动态增减不会自动重建实体（重启 HA 后生效）。
- 调光灯（`light_dimmer`）已接入亮度控制；普通灯仍为开/关模式。`r153` 面板仅在带 `PANEL_STATE` 时视为调光灯。
- 空调：关机状态下网关不接受单独修改温度/风速（`climate` 中会提示先开机）；多联机同一外机下的内机须同为制冷或制热，模式冲突时会被系统拉回。
- 空调设置下发后 0.2~5 秒才回推新状态，`climate` 在此期间显示请求值（最长 10 秒）。
- 窗帘位置：网关 0 = 全开、100 = 全关，`cover` 中已换算为 HA 约定（100 = 全开）。
- 未接入：地暖、新风、干触点；空调扫风与背光。
- 协议字段映射依赖网关返回格式，不同固件可能需要适配。

---

## 9. 协议文档与测试组织

协议分析目录：`docs/protocol/`

- 总览索引：`docs/protocol/README.md`
- 文档模板：`docs/protocol/TEMPLATE.md`

协议测试目录：`tests/protocol/`

- 业务测试：`test_*.py`
- 测试资产：`fixtures/`（固化请求/响应 HEX 与业务 JSON）
- 通用工具：`_shared.py`

运行：

```bash
pytest tests/protocol -q
```

### 9.1 协议测试规范（权威）

1. 禁止在测试执行路径中读取/解析 pcap（仅允许离线提取后固化为常量）。
2. 样本资产统一放在 `tests/protocol/fixtures/`；测试逻辑文件通过 import 使用。
3. 每个协议测试至少覆盖：
   - 请求 `JSON -> HEX` 对齐抓包样本
   - 请求 `HEX -> JSON` 反解
   - 响应 `HEX -> JSON` 反解
   - 命令函数默认包断言（如适用）
4. 响应 JSON 断言应尽量完整保留可解析字段（未知字段使用 `unknown_<id>`）。
5. 测试命名遵循：`test_<biz>_<phase>_<expected>`（如 `request_encode_decode...`）。

---

## 10. 建议后续优化

- 增加 config flow 连通性校验与唯一 ID
- 增加 options flow（轮询间隔/冷却时间可配置）
- 扩展协议单测（认证/设备列表/心跳/执行链路）
