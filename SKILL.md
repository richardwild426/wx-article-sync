---
name: wx-article-sync
description: Synchronizes WeChat Official Account articles with the mptext API. Use when users want to configure, run, schedule, inspect, or troubleshoot WeChat article sync jobs, including daily sync, fakeid setup, config.json generation, local article archives, logs, and sync state.
compatibility: Requires Python 3.11+, uv, network access to mptext, and a local wx-article-sync project or installed CLI.
---

# wx-article-sync

## 用途

使用本 skill 帮用户完成一个业务流程：通过 `wx-article-sync` CLI 和 mptext API，把微信公众号文章持续同步并归档到本地。

这个 skill 是操作指南，不替代 Python 同步器。配置校验和状态检查优先使用 `scripts/` 下的确定性脚本；真正同步文章时继续调用现有 CLI。

## 对话体验规则

- 默认用业务语言引导用户，不要把内部路径、依赖包、安装命令、CLI 参数一次性倒给用户。
- 一次只问一个问题；用户回答后再进入下一步。
- 只有在用户要求“给我命令”“自己配置”“排查失败”时，才展示具体命令。
- 对用户说“我来检查/我来配置/我来验证”，然后执行；不要把可自动完成的技术步骤变成用户任务。
- 安装完成后的回复要短，只确认能力已可用，然后先确认前置要求；不要跳过 mptext 准备直接问配置项。

安装完成后的回复模板：

```text
wx-article-sync 已安装好。首次使用前需要先确认 mptext 前置准备完成了吗：你已经在 mptext 里添加目标公众号，并同步过文章链接了吗？
```

不要输出克隆路径、安装目录、`uv sync` 细节、依赖包列表、`--help` 输出、内部文件结构。不要列出依赖包。不要直接说“复制 config.example.json → config.json”。这些由智能体在需要时处理。

## 安全规则

- 不要读取或打印真实 API key、`.env` 文件、私钥，或状态文件里的完整文章 URL。
- 把 `config.json` 视为敏感文件，因为它可能包含 `api_key`。
- 生成可共享示例时，优先使用 `api_key_env`，不要把 key 写进示例。
- 如果用户在消息里提供了密钥，不要原样复述；用“用户提供的 API key”指代。
- 覆盖已有 `config.json` 前，先在响应外保留当前内容。

## 先判断任务类型

先给用户请求分类，再只读取相关参考文档：

- 首次使用、没有 mptext 账号准备、没有 `fakeid`、不知道 API key 来源：先阅读 [configuration](references/configuration.md) 的“首次使用前置准备”。
- 创建或修正配置：阅读 [configuration](references/configuration.md)。
- 运行一次同步或设置周期同步：阅读 [operations](references/operations.md)。
- 同步到 ima 知识库、查询 ima 中已同步文章、结合 ima 询问文章内容：阅读 [ima](references/ima.md)。
- 解释失败、计数异常、重复下载、文件缺失、PDF 失败或 API 错误：阅读 [troubleshooting](references/troubleshooting.md)。

## 安装后引导流程

安装完成后分两段走：先确认前置要求，再做初始化设置。

### 先确认前置要求

先问用户：

```text
mptext 前置准备完成了吗：你已经在 mptext 里添加目标公众号，并同步过文章链接了吗？
```

如果用户回答没有完成，先引导用户按 `https://docs.mptext.top/tutorials/export-article-links.html` 完成准备，不要生成配置。

### 初始化设置

前置要求完成后，再进入初始化设置。初始化设置必须覆盖：

- 需要同步的公众号：公众号数量，以及每个公众号的 `fakeid`。
- 同步的文章数量：默认每个公众号每次最多请求 20 篇；日更归档建议每天同步最新 1 篇。
- 同步频率：例如每天一次、每小时一次，或只手动同步。
- 是否需要联动 IMA：如果需要，继续确认 IMA 怎么配置。
- IMA 怎么配置：引导用户选择 `~/.config/ima/client_id` / `~/.config/ima/api_key`，或 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY` 环境变量。

## 首次配置对话顺序

不要一次性问完所有配置。按下面顺序逐步推进：

1. 先确认：mptext 前置准备完成了吗？
2. 再问：你想同步几个公众号？
3. 再收集每个公众号的 `fakeid`；用户没有时，引导其按 mptext 准备文档获取。
4. 再问同步的文章数量：每天最新几篇？必须说明默认每个公众号每次最多请求 20 篇；如果只是每天同步最新文章，推荐选择每天同步最新 1 篇。
5. 再问同步频率：每天一次、每小时一次，还是只手动同步？
6. 再问是否需要联动 IMA；如果需要，引导用户配置 IMA 凭证。
7. 最后才生成或更新 `config.json`，并运行校验。

同步篇数引导示例：

```text
默认每个公众号每次最多请求 20 篇。你想每天同步最新几篇？如果只是做日更归档，我建议每天同步最新 1 篇。
```

## 首次使用必须先完成准备

如果用户是第一次使用，或还没有在 mptext 网站里添加并同步目标公众号，不要直接生成最终配置或运行同步。先引导用户完成 mptext 官方教程的准备流程：

```text
https://docs.mptext.top/tutorials/export-article-links.html
```

准备完成的最低标准：

1. 用户有一个可用的微信订阅号或服务号用于登录 mptext。
2. 用户已经用公众号或服务号扫码登录 mptext，不能用小程序登录。
3. 用户已经在 mptext 的公众号管理页添加目标公众号，并点击同步拉取文章链接。
4. 目标公众号没有关闭搜索功能；如果关闭搜索，该准备流程不可用。
5. 用户能够提供目标公众号的 `fakeid`，或能确认用 `keyword` 搜索时不会选错账号。

## 常见业务流程

### 每日同步最新文章

当用户想要“每日同步”“最新文章”“两个公众号”等场景时，使用这个模式：

1. 先确认用户已完成“首次使用必须先完成准备”。
2. 获取或使用每个公众号已知的 `fakeid`。
3. 明确询问同步篇数；如果用户选择每天同步最新 1 篇，将 `page_size` 设为 `1`，将 `max_pages` 设为 `1`。
4. `accounts` 中每个公众号只保留一项。
5. 用 `scripts/validate_config.py` 校验配置。
6. 设置定时任务前，先手动运行一次同步。
7. 用 cron、launchd、systemd 或用户现有调度器执行单次同步命令。外部调度器里不要再加 `--daemon`。

### 排查计数异常

当同步结果和预期不一致时，用这个模型解释计数：

```text
scanned = sum of article records returned by mptext for all configured accounts and pages
downloaded = scanned articles whose URLs were not already in state_path
skipped = scanned articles whose URLs were already in state_path
```

如果 mptext 返回的记录数超过 `page_size` 请求值，当前同步器会按 API 实际返回内容计数并处理。

### 本地保存后联动 ima

当用户想把文章同步到 ima 知识库，或想基于 ima 询问文章内容时，先确保本地同步已经成功，再进入 ima 流程：

1. 用 `uv run wx-article-sync --config config.json` 完成本地保存。
2. 用 `scripts/ima_check.py` 检查 ima 凭证是否已配置。
3. 用 `scripts/ima_manifest.py data/articles --output data/ima-manifest.jsonl` 生成导入清单。
4. 读取已安装 ima-skills 的 `knowledge-base/SKILL.md`，按 `create_media → COS → add_knowledge` 把清单中的文件导入目标知识库。
5. 查询文章时，先用本地清单确认文章已保存；需要知识库问答时，再使用 ima 知识库搜索或问答能力。

## 工具

在 skill 根目录运行辅助脚本，或使用绝对路径运行：

```bash
python scripts/validate_config.py config.json
python scripts/inspect_state.py data/state.json
python scripts/ima_check.py
python scripts/ima_manifest.py data/articles --output data/ima-manifest.jsonl
```

在项目根目录运行同步器：

```bash
uv run wx-article-sync --config config.json
```

排查 mptext 或网络问题时打开调试日志：

```bash
uv run wx-article-sync --config config.json --log-level DEBUG
```

运行日志写入 `logs/wx-article-sync.log`，单个日志文件达到 2MB 后自动轮转。
