# Overstats Replica Plan

## 目标

在 AstrBot 插件内复刻 Overstats 的非 Web 能力，不启动 Overstats HTTP/Web 服务。AstrBot 只负责命令解析、配置读取和消息回复；数据请求、图片渲染、AI 锐评尽量复用 Overstats 原版核心模块。

## 范围

纳入：

- Dashen 数据客户端、BattleTag 解析、账号池/限流能力
- 玩家资料、战绩列表、战绩详情、全员详细数据图
- AI 锐评逻辑与原版 AI 分析图
- 同玩、总结、强度、榜单、英雄相关等非 Web 模块
- 原版字体解析、图片压缩、资源缓存逻辑

排除：

- `src/server.py`
- `src/http_server/`
- Overstats 本地 Web 控制台和 HTTP API 服务入口

## 资源与授权边界

Overstats 的 `THIRD_PARTY_NOTICES.md` 明确说明 `res/` 下的图片、字体、游戏素材、缓存数据不默认随源码授权。当前复刻会保留该说明，并把素材作为兼容运行资源处理。后续公开发布前需要再次确认：

- 字体是否可再分发；如果不能，替换为可再分发中文字体或改为用户挂载字体。
- 游戏图标、地图、段位素材是否可随插件仓库分发；如果不能，改为运行时下载缓存。
- 不提交真实 `role_id`、`token`、AI key、Cookie。

## 架构

```text
AstrBot command layer
  -> owsearch.overstats_bridge
  -> vendored overstats core modules
  -> Dashen / AI / Pillow render / ffmpeg audio transcode
  -> AstrBot ReplyItem image/text/audio
```

## 阶段计划

### Phase 1: Vendor 与桥接

- [x] 拉取原版 Overstats 作为参考：`F:\codex\_refs\Overstats`
- [x] 将非 Web 核心复制进插件内置 `overstats/` 包
- [x] 保留第三方资源说明
- [x] 建立 `owsearch.overstats_bridge`，把插件配置注入 Overstats runtime
- [x] 添加渲染结果到 AstrBot 图片/音频回复的转换

### Phase 2: 核心命令复刻

- [x] `/ow 战绩 玩家#12345 10` 使用原版 `dashen_match` 列表图
- [x] `/ow 详情 玩家#12345 1` 使用原版详情图
- [x] `/ow 1 / 1* / 1**` 接入原版上下文回复
- [x] `/ow 开庭 玩家#12345 [n]` 使用原版主战绩图、全员瀑布图、AI 锐评图
- [x] 保留 `/开庭 玩家#12345 [n]` 直达入口

### Phase 3: AI 稳定性

- [x] 使用原版 `_build_ai_analysis` 提示词、JSON schema、`render_analysis_report`
- [x] 移除当前简化 AI 请求中的固定 `max_tokens`
- [x] 对 400/401/403/429 等错误显示服务端响应摘要，敏感字段脱敏
- [x] 增加 `/ow debug ai` 或并入 `/ow debug 配置`

### Phase 4: 非 Web 模块补齐

- [x] `dashen_profile`
- [x] `dashen_sameplay`
- [x] `dashen_summary`
- [x] `dashen_quick_strength`
- [x] `dashen_competitive_strength`
- [x] `dashen_rank_history`
- [x] `dashen_rank_leaderboard`
- [x] `dashen_hero_leaderboard`
- [x] `dashen_hero_treemap`
- [x] `ow_hero_pick_rate`
- [x] `ow_hero_perk`
- [x] `ow_hero_wiki`
- [x] `ow_shop`
- [x] `patch_notes`
- [x] `ow_esports`
- [x] `bnet_search` 内部复用
- [x] `query_tool` 内部复用
- [x] `ow_hero_leaderboard` 作为 `ow_hero_pick_rate` 的本地数据同步支撑模块保留
- [x] `player_identity_search`
- [x] `auto_route` 替代方案：注册 AstrBot LLM 工具函数，由 AstrBot 判断自然语言应调用哪个工具
- [x] `ow_guess` 图片/文字/音频回复桥接；音频统一转码为 AstrBot `Record` 支持的 wav
- [x] `ow_guess` 可选资源包策略：配置 `ow_guess.asset_root`，默认自动查找常见目录，debug 输出资源状态

### Phase 5: 发布

- [x] 全量测试与自检
- [x] README 更新为 v0.3.0 说明
- [x] metadata/version 升级
- [x] commit author 使用 `wswayin`
- [x] tag 并推送

## 当前进度

- 2026-06-10：确认当前 v0.2.0 工作区干净。
- 2026-06-10：确认 Overstats 原版是本地 HTTP API 服务，但核心能力可通过模块直接调用。
- 2026-06-10：确认字体/素材存在第三方授权边界，需要保留 notices，并在发布前处理资源许可。
- 2026-06-10：创建本计划文档。
- 2026-06-10：复制 Overstats 非 Web 核心到插件内置 `overstats/` 包，排除 `src/server.py` 与 `src/http_server/`。
- 2026-06-10：新增 `owsearch.overstats_bridge`，完成 Overstats image/text replies 到 AstrBot `ReplyItem` 的转换。
- 2026-06-10：确认 AstrBot 语音发送走 `message_components.Record`，并新增 Overstats `audio` reply 到 `ReplyItem.audio` 的桥接；`mp3/ogg` 等音频会通过 ffmpeg 转码为 16kHz 单声道 wav 后发送。
- 2026-06-10：`/ow 战绩`、`/ow 详情 玩家#12345 1`、`/ow 1/1*/1**`、`/ow 开庭 玩家#12345 [n]` 切到原版 `dashen_match` 渲染/AI 管线。
- 2026-06-10：`/ow 资料 玩家#12345` 切到原版 `dashen_profile` 渲染。
- 2026-06-10：AI 请求切换到原版 `_build_ai_analysis`；补充 HTTP 400/401/403/429 等错误响应摘要，便于定位模型/参数/key 问题。
- 2026-06-10：单元测试 `25 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐 `dashen_sameplay` 桥接与命令：`/ow 同玩 A#12345 B#67890 [limit]`、`/ow 同玩详情 A#12345 B#67890 1**`、`/ow 同玩开庭 A#12345 B#67890 [n]`，并支持同玩列表后的 `/ow 1/1*/1**` 上下文回复。
- 2026-06-10：同玩迁移后单元测试 `29 tests OK`，自检 `result: OK`；确认 `overstats/src/server.py` 与 `overstats/src/http_server/` 未被打包。
- 2026-06-10：补齐 `dashen_summary` 桥接与命令：`/ow 总结 玩家#12345`、`/ow 昨日总结 玩家#12345`、`/ow 周报 玩家#12345`；修正 summary runtime 全局 Dashen client 指向插件配置凭据。
- 2026-06-10：总结迁移后单元测试 `33 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐 `dashen_quick_strength` 与 `dashen_competitive_strength`：`/ow 快速强度 玩家#12345 [limit]`、`/ow 竞技强度 玩家#12345 [limit]`。
- 2026-06-10：强度模块迁移后单元测试 `37 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐 `dashen_rank_history`、`dashen_rank_leaderboard`、`dashen_hero_leaderboard`：`/ow 段位历史 玩家#12345 [start] [end]`、`/ow 省榜 省份 职责`、`/ow 英雄榜 省份 英雄 [预设|开放]`。
- 2026-06-10：榜单模块迁移后单元测试 `43 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐 `ow_hero_pick_rate`、`ow_hero_perk`、`ow_hero_wiki`：`/ow 登场率 [快速|竞技] [段位]`、`/ow 登场率历史 英雄 [快速|竞技] [段位] [limit]`、`/ow 威能 英雄`、`/ow 英雄资料 英雄 [问题]`。
- 2026-06-10：英雄公共数据模块迁移后单元测试 `51 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐 `ow_shop`、`patch_notes`、`ow_esports`：`/ow 商店`、`/ow 补丁 [最新|小补丁|大补丁]`、`/ow 电竞`；新增 `ow_esports_api_key` 配置并在 debug 输出中脱敏。
- 2026-06-10：商店/补丁/电竞迁移后单元测试 `57 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐原计划遗漏的 `dashen_hero_treemap`：`/ow 英雄占比 玩家#12345 [竞技|快速] [season]`。
- 2026-06-10：英雄占比迁移后单元测试 `59 tests OK`，自检 `result: OK`；再次确认 `overstats/src/server.py` 与 `overstats/src/http_server/` 未打包，且无 web server 引用残留。
- 2026-06-10：补齐 `/ow debug ai`，只做 AI 配置诊断与脱敏展示，不真实请求模型。
- 2026-06-10：补齐 `player_identity_search`：`/ow 反查 bnet_id [limit]`，从本地 SQLite 身份记录反查 BattleTag。
- 2026-06-10：身份反查迁移后单元测试 `63 tests OK`，自检 `result: OK`。
- 2026-06-10：补齐 `ow_guess` 音频桥接：Overstats `audio` base64 保存后通过 ffmpeg 转码为 16kHz 单声道 wav，再用 AstrBot `Record` 发送；单元测试 `69 tests OK`，自检 `result: OK`，真实小样本转码通过。
- 2026-06-10：补齐 `ow_guess` 资源包策略：新增 `ow_guess.asset_root` 配置、默认目录探测、`/ow debug 配置` 资源状态展示，以及缺资源时的中文可操作提示。
- 2026-06-10：资源包策略补齐后单元测试 `70 tests OK`，自检 `result: OK`。
- 2026-06-10：按用户决策放弃插件内置 `auto_route` 自行请求 AI 的方案，改为注册 AstrBot `llm_tool` 工具函数；插件只提供白名单工具，工具选择交给 AstrBot。
- 2026-06-10：AstrBot LLM 工具层接入后单元测试 `71 tests OK`，自检 `result: OK`。
- 2026-06-10：发布准备阶段将插件版本升级到 v0.3.0，并在 README 补充本版迁移摘要。
- 2026-06-10：发布前验收通过：`71 tests OK`、`owsearch.self_check result: OK`；确认 `overstats/src/server.py` 与 `overstats/src/http_server/` 未打包，且无 web server 引用残留。
- 2026-06-10：推送前一度出现 GitHub HTTPS TLS 握手失败，`gh` keyring token 失效，SSH 443 可连通但当前机器没有可用 GitHub 公钥；随后 HTTPS push 恢复，`main` 与 `v0.3.0` tag 已推送到 GitHub。

## 交接

如果中途换人或恢复上下文，优先检查：

1. `OVERSTATS_REPLICA_PLAN.md` 的阶段进度。
2. `git status --short`，确认是否有未提交迁移文件。
3. `overstats/` 是否存在且不包含 `src/server.py`、`src/http_server/`。
4. `owsearch/overstats_bridge.py` 是否已接入 `OwCommandHandler`。
5. 运行：

```bash
python -B -m unittest discover -s tests
python -B -m owsearch.self_check
```

验收优先级：

1. `/ow debug 配置` 不泄露敏感信息。
2. `/ow debug 图片` 能生成原版风格样例图。
3. `/ow 战绩 玩家#12345 10` 能返回原版列表图。
4. `/ow 开庭 玩家#12345` 能返回主战绩图、全员瀑布图、AI 图或明确 AI 错误文本。
5. `/ow 同玩 A#12345 B#67890` 能返回原版同玩列表图，列表后 `/ow 1**` 能返回同玩详情、全员瀑布图与 AI 图或明确 AI 错误文本。
6. `/ow 总结 玩家#12345`、`/ow 昨日总结 玩家#12345`、`/ow 周报 玩家#12345` 能返回原版总结图。
7. `/ow 快速强度 玩家#12345` 与 `/ow 竞技强度 玩家#12345` 能返回原版强度趋势图。
8. `/ow 段位历史 玩家#12345`、`/ow 省榜 北京 输出`、`/ow 英雄榜 北京 猎空` 能返回原版榜单图。
9. `/ow 登场率`、`/ow 威能 安娜`、`/ow 英雄资料 安娜` 能返回原版英雄公共数据图。
10. `/ow 商店`、`/ow 补丁 最新`、`/ow 电竞` 能返回原版公共数据图；电竞需要配置 `ow_esports_api_key`。
11. `/ow 英雄占比 玩家#12345` 能返回原版英雄使用占比树图。
12. `/ow debug ai` 不泄露 AI key；`/ow 反查 123456789` 能返回本地身份匹配或明确未找到。
13. `/ow 猜 地图音乐`、`/ow 猜 大招语音` 在资源包存在时能返回 AstrBot 语音消息；若转码失败，应返回明确错误文本。
