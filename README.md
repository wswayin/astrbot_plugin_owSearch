# astrbot_plugin_owSearch

AstrBot 守望先锋查询插件，参考 [AddOneSecondL/Overstats](https://github.com/AddOneSecondL/Overstats) 的 Dashen 数据链路实现。

## 功能

- 查询玩家公开资料和竞技职责概览
- 查询最近对局列表
- 按序号或 matchId 查询单局详情
- 生成单局战绩图、全员数据图、AI 分析图
- 提供 `/ow 开庭 玩家#12345` 一键查询最近一局可分析对局
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

## AI 分析

原版 Overstats 的 AI 锐评模块是 OpenAI-compatible 调用，需要自己配置 API，不是调用网易大神 AI。

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
/ow 分析 1
/ow 开庭 玩家#12345
/ow 刷新 玩家#12345
/ow debug 配置
/ow debug 图片
/ow debug 接口 玩家#12345 5
/ow debug 战绩 玩家#12345 5
```

快捷命令说明：

- `/ow 1`：查看上一条战绩列表中的第 1 局
- `/ow 1*`：查看第 1 局并返回全员数据图
- `/ow 1**`：查看第 1 局并返回全员数据图和 AI 分析图

## 联调顺序

建议按这个顺序排查：

1. `/ow debug 配置`
2. `/ow debug 图片`
3. `/ow debug 接口 玩家#12345 5`
4. `/ow debug 战绩 玩家#12345 5`
5. `/ow 开庭 玩家#12345`

`/ow debug 接口` 会标记每一步 `[OK]` / `[FAIL]`。如果失败在 `searchBnetAccount`，优先检查 Dashen 凭据和 BattleTag；如果失败在 `queryMatchList` 或 `queryMatchInfo`，优先确认玩家公开战绩、token 是否过期、接口是否限流；如果只失败在 AI 阶段，Dashen 数据链路通常已经可用。

## 数据说明

数据来自网易大神公开战绩接口。玩家关闭公开战绩、BattleTag 写错、大神 token 失效或上游接口调整时，查询会失败。

`/ow 开庭` 会跳过角斗模式，因为角斗模式暂不支持全员详细数据和完整 AI 分析。
