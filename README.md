# astrbot_plugin_owSearch

AstrBot 守望先锋查询插件，参考 [AddOneSecondL/Overstats](https://github.com/AddOneSecondL/Overstats) 的 Dashen 数据链路实现。

## v0.3.4 更新

- 新增 AstrBot LLM 工具函数，让 AstrBot 根据自然语言选择可调用工具；插件不再内置原版 `auto_route` 自行请求 AI 的路由逻辑。
- 正式查询图片和 `/ow debug 图片 玩家#12345` 强制走 Overstats 原版渲染。
- 渲染前会按当前对局预缓存地图、英雄图标、玩家头像和已选威能图标，减少白色占位和空背景。
- 主战绩图可在缺少 `heroGuid` 时通过已选威能反推英雄头像。
- 主战绩图小字指标改为中文标识：终结、目标、承伤、受疗、收割。
- AI 锐评默认人设改为毒舌守望评论员，`EXTRA` 结语改为 200 字以内的人格化毒舌小结。
- AI 锐评遇到 `429/500/502/503/504` 或临时网络错误时会短重试；如果服务端持续过载，仍会返回明确失败提示。
- 修正最近对局为空时的错误提示：不再显示误导性的 `Use an index from 0 to 0`，会明确提示没有可用最近对局。
- 移除 OW 猜题模块和音频转码依赖。
- 移除英雄威能查询模块和 `ow_hero_perk` LLM 工具。
- 继续使用 `Pillow>=10,<13`，避免与 AstrBot 核心依赖保护冲突。

## 功能

- 查询玩家公开资料和竞技职责概览
- 查询最近对局列表
- 按序号或 matchId 查询单局详情
- 生成单局战绩图、全员数据图、AI 分析图
- 提供 `/ow 开庭 玩家#12345 1` 查询指定玩家最近第 N 局可分析对局；不填序号时默认最近第 1 局
- 提供 `/ow 同玩 玩家A#12345 玩家B#67890` 查询双目标同玩对局和同玩详情
- 提供 `/ow 总结 玩家#12345`、`/ow 昨日总结 玩家#12345`、`/ow 周报 玩家#12345` 生成原版 Overstats 总结图
- 提供 `/ow 快速强度 玩家#12345`、`/ow 竞技强度 玩家#12345` 生成原版强度趋势图
- 提供 `/ow 段位历史 玩家#12345`、`/ow 省榜 北京 输出`、`/ow 英雄榜 北京 猎空` 查询原版榜单图
- 提供 `/ow 英雄占比 玩家#12345` 查询玩家英雄使用占比树图
- 提供 `/ow 登场率`、`/ow 英雄资料 安娜` 查询原版英雄公共数据图
- 提供 `/ow 商店`、`/ow 补丁 最新`、`/ow 电竞` 查询商店、补丁和电竞赛程
- 提供 `/ow 反查 123456789` 查询本地记录中的 bnetId 对应 BattleTag
- 提供联调命令，方便定位 Dashen 凭据、接口、渲染、AI 的问题

## 依赖

Python 3.11+。

```txt
httpx>=0.27,<1
Pillow>=10,<13
tzdata>=2024.1
```

Linux/Docker 环境建议安装中文字体，否则图片里的中文可能显示为方框：

```bash
apt-get update && apt-get install -y fonts-noto-cjk
```

如果 AstrBot Docker 镜像里已经有中文字体，但图片仍然是方框，先执行 `/ow debug 配置` 查看实际加载的 `常规字体`/`粗体字体`。如果显示为 `DejaVuSans.ttf` 或 `-`，可以把中文字体文件或字体目录填到 `render.font_paths`，多个路径用英文分号分隔，例如：

```text
/usr/share/fonts
/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc;/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
```

## 安装

把本目录放到 AstrBot 插件目录中，确保依赖已安装。若 AstrBot 没有自动安装 `requirements.txt`，手动在 AstrBot 的 Python 环境执行：

```bash
pip install -r requirements.txt
```

本地交付自检：

```bash
python -m owsearch.self_check
```

自检不会连接 Dashen，也不需要 token；它会检查依赖、schema、入口文本和三张样例图渲染。

## 配置

在 AstrBot 插件配置里填写 `_conf_schema.json` 中的字段。最重要的是：

- `dashen.role_id`
- `dashen.token`
- `dashen.server`：通常是 `1`
- `dashen.dts`：当前按 Overstats 默认 `2026`

`dashen.token` 和 `role_id` 需要来自已登录的网易大神环境。插件不会在 debug 输出中明文展示 `token`、`api_key`、`customer_token`。

图片会写入插件数据目录的 `renders/` 下。默认最多保留 300 张，最低保留 20 张，避免长期运行后目录无限增长。

`/ow 电竞` 需要配置 `ow_esports_api_key`，使用 PandaScore OW 赛事 API Key。未填写时只会提示未配置，不影响其他查询。

## AI 分析

原版 Overstats 的 AI 锐评模块是 OpenAI-compatible 调用，需要自己配置 API，不是调用网易大神 AI。
本插件的单局 AI 提示词、JSON schema 和 AI 分析图布局均直接使用 Overstats 原版
`dashen_match.service._build_ai_analysis` 与 `dashen_match.enhanced_render.render_analysis_report`。

本插件同样使用：

- `ai.enabled`
- `ai.base_url`
- `ai.api_key`
- `ai.model`

示例：

```text
base_url = https://api.deepseek.com/v1
model = deepseek-chat
```

如果未配置 AI，`/ow 开庭` 仍会返回第三张“AI 未配置”的提示图，方便确认前两张数据链路正常。
如果看到 `system_cpu_overloaded`、`HTTP 503` 一类错误，说明 AI 服务端当前过载。插件会自动短重试，持续失败时需要稍后再试，或更换更稳定的 `base_url` / `model`。

## 命令

```text
/ow
/ow 资料 玩家#12345
/ow 战绩 玩家#12345 10
/ow 详情 1
/ow 1
/ow 1*
/ow 1**
/ow 详情 玩家#12345 1
/ow 开庭 玩家#12345
/ow 开庭 玩家#12345 2
/开庭 玩家#12345 1
/ow 同玩 玩家A#12345 玩家B#67890
/ow 同玩详情 玩家A#12345 玩家B#67890 1**
/ow 同玩开庭 玩家A#12345 玩家B#67890 1
/ow 总结 玩家#12345
/ow 昨日总结 玩家#12345
/ow 周报 玩家#12345
/ow 快速强度 玩家#12345 12
/ow 竞技强度 玩家#12345 12
/ow 段位历史 玩家#12345 15 22
/ow 省榜 北京 输出
/ow 英雄榜 北京 猎空 预设
/ow 英雄占比 玩家#12345 竞技
/ow 登场率 竞技 钻石
/ow 登场率历史 安娜 竞技 钻石 20
/ow 英雄资料 安娜 技能冷却是多少
/ow 商店
/ow 补丁 最新
/ow 电竞
/ow 反查 123456789 10
/ow 刷新 玩家#12345
/ow debug 配置
/ow debug ai
/ow debug 图片 玩家#12345
/ow debug 接口 玩家#12345 5
/ow debug 战绩 玩家#12345 5
```

快捷命令说明：

- `/ow 1`：查看上一条战绩列表中的第 1 局
- `/ow 1*`：查看第 1 局并返回全员数据图
- `/ow 1**`：查看上一条战绩列表中的第 1 局，并返回全员数据图和 AI 分析图
- `/ow 开庭 玩家#12345`：查询该玩家最近第 1 场可分析对局，返回战绩图、全员数据图和 AI 分析图
- `/ow 开庭 玩家#12345 2`：查询该玩家最近第 2 场可分析对局
- `/开庭 玩家#12345 1`：等同于 `/ow 开庭 玩家#12345 1`
- `/ow 同玩 玩家A#12345 玩家B#67890`：查询两个玩家的同玩对局列表
- `/ow 同玩详情 玩家A#12345 玩家B#67890 1**`：查询同玩第 1 局，并返回双人详情、全员数据和 AI 分析
- `/ow 同玩开庭 玩家A#12345 玩家B#67890 1`：等同于同玩详情的完整开庭模式
- `/ow 总结 玩家#12345`：生成今日总结图
- `/ow 昨日总结 玩家#12345`：生成昨日总结图
- `/ow 周报 玩家#12345`：生成本周总结图
- `/ow 快速强度 玩家#12345 12`：查询最近快速对局强度趋势，末尾数量可省略
- `/ow 竞技强度 玩家#12345 12`：查询最近竞技对局强度趋势，末尾数量可省略
- `/ow 段位历史 玩家#12345 15 22`：查询第 15 到第 22 赛季段位历史，赛季范围可省略
- `/ow 省榜 北京 输出`：查询省份职责榜；职责支持重装/输出/支援/开放等别名
- `/ow 英雄榜 北京 猎空 预设`：查询英雄省榜；模式支持预设/开放，默认预设
- `/ow 英雄占比 玩家#12345 竞技`：查询玩家英雄使用占比树图；模式支持竞技/快速，默认竞技
- `/ow 登场率 竞技 钻石`：查询英雄登场率排行；模式默认快速，段位默认全部
- `/ow 登场率历史 安娜 竞技 钻石 20`：查询单个英雄登场率历史
- `/ow 英雄资料 安娜 技能冷却是多少`：查询英雄资料图；后面的提问需要 AI 配置才会有完整问答
- `/ow 商店`：查询当前国服商店图
- `/ow 补丁 最新`：查询补丁说明；类型支持最新/小补丁/大补丁
- `/ow 电竞`：查询 OW 电竞赛程，需要 `ow_esports_api_key`
- `/ow 反查 123456789 10`：从本地 SQLite 记录反查 BattleTag；是否有结果取决于本地是否积累过对应记录
- `/ow debug 图片 玩家#12345`：使用 Overstats 原版开庭渲染测试图片链路，返回内容与 `/ow 开庭 玩家#12345` 同源

## AstrBot LLM 工具

插件会把主要查询能力注册为 AstrBot LLM 工具，由 AstrBot 自己判断自然语言要调用哪个工具；插件不再内置原版 `auto_route` 那套自行请求 AI 的路由逻辑。显式 `/ow ...` 命令仍然可用。

已注册工具包括：

```text
ow_player_profile
ow_match_list
ow_match_detail
ow_courtroom
ow_sameplay
ow_sameplay_courtroom
ow_summary
ow_strength
ow_rank_history
ow_rank_leaderboard
ow_hero_leaderboard
ow_hero_treemap
ow_hero_pick_rate
ow_hero_wiki
ow_shop
ow_patch_notes
ow_esports
```

## 联调顺序

建议按这个顺序排查：

1. `/ow debug 配置`
2. `/ow debug ai`
3. `/ow debug 图片 玩家#12345`
4. `/ow debug 接口 玩家#12345 5`
5. `/ow debug 战绩 玩家#12345 5`
6. `/ow 开庭 玩家#12345`

`/ow debug ai` 只检查配置是否完整，不会真实请求模型。`/ow debug 图片 玩家#12345` 会真实调用 Overstats 原版渲染链路。`/ow debug 接口` 会标记每一步 `[OK]` / `[FAIL]`。如果失败在 `searchBnetAccount`，优先检查 Dashen 凭据和 BattleTag；如果失败在 `queryMatchList` 或 `queryMatchInfo`，优先确认玩家公开战绩、token 是否过期、接口是否限流；如果只失败在 AI 阶段，Dashen 数据链路通常已经可用。

## 数据说明

数据来自网易大神公开战绩接口。玩家关闭公开战绩、BattleTag 写错、大神 token 失效或上游接口调整时，查询会失败。

`/ow 开庭 玩家#12345 2` 会跳过角斗模式，按最近快速/竞技对局排序取第 2 场，因为角斗模式暂不支持全员详细数据和完整 AI 分析。不填末尾数字时默认第 1 场。
