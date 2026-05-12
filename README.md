# wx-article-sync

## 项目作用

`wx-article-sync` 依赖 mptext 在线 API，定时拉取微信公众号文章列表，下载新增文章，并保存到本地目录。每篇文章会保存到 `YYYY-MM-DD_文章标题` 文件夹中，已同步过的文章 URL 会记录在状态文件里，后续运行不会重复下载。

## 最小启动

复制配置文件并填写要同步的公众号：

```bash
cp config.example.json config.json
```

设置 mptext API key：

```bash
export MP_TEXT_API_KEY="your-api-key"
```

单次同步：

```bash
uv run wx-article-sync --config config.json
```

排查网络或第三方 API 问题时打开调试日志：

```bash
uv run wx-article-sync --config config.json --log-level DEBUG
```

如果 `content_format` 配置为 `html`，首次运行前安装 PDF 转换所需浏览器：

```bash
uv run playwright install chromium
```

常驻定时同步：

```bash
uv run wx-article-sync --config config.json --daemon
```

## macOS 定时任务

macOS 推荐用 `launchd` 定时执行单次同步，不要在定时任务里使用 `--daemon`。

先确认 `uv` 的绝对路径：

```bash
which uv
```

创建日志目录：

```bash
mkdir -p "$HOME/Library/Logs/wx-article-sync"
```

创建 `~/Library/LaunchAgents/com.wx-article-sync.plist`，把 `WorkingDirectory` 改成你的项目目录，把 `/opt/homebrew/bin/uv` 改成 `which uv` 输出的路径：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.wx-article-sync</string>

  <key>WorkingDirectory</key>
  <string>/Users/zvector/ws/workflow/wx-article-sync</string>

  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/uv</string>
    <string>run</string>
    <string>wx-article-sync</string>
    <string>--config</string>
    <string>config.json</string>
  </array>

  <key>StartInterval</key>
  <integer>3600</integer>

  <key>StandardOutPath</key>
  <string>/Users/zvector/Library/Logs/wx-article-sync/stdout.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/zvector/Library/Logs/wx-article-sync/stderr.log</string>
</dict>
</plist>
```

加载并启动任务：

```bash
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.wx-article-sync.plist"
launchctl kickstart -k gui/$(id -u)/com.wx-article-sync
```

查看任务状态和日志：

```bash
launchctl print gui/$(id -u)/com.wx-article-sync
tail -f "$HOME/Library/Logs/wx-article-sync/stdout.log" "$HOME/Library/Logs/wx-article-sync/stderr.log"
```

修改 plist 后重新加载：

```bash
launchctl bootout gui/$(id -u)/com.wx-article-sync
launchctl bootstrap gui/$(id -u) "$HOME/Library/LaunchAgents/com.wx-article-sync.plist"
```

如果用环境变量提供 API key，不要只在终端里 `export MP_TEXT_API_KEY`，`launchd` 默认读不到终端环境变量。更稳妥的方式是把 `api_key` 写入本机 `config.json`，并确认 `config.json` 不会提交到仓库。

## 运维注意事项

- API key 有效期跟 mptext 登录会话一致，过期后同步会失败，需要重新登录并更新 `MP_TEXT_API_KEY`。
- 优先在 `config.json` 里配置公众号 `fakeid`；只配置 `keyword` 时会使用 API 搜索结果的第一项，账号重名时可能选错。
- `accounts` 里的每一项都会单独拉取 `page_size * max_pages` 篇文章；同一个公众号不要同时用 `fakeid` 和 `keyword` 配两次，否则会重复查询。
- 默认文章保存到 `data/articles/YYYY-MM-DD_文章标题`，同步状态保存到 `data/state.json`；备份或迁移时要一起保留 `data/state.json`。
- `content_format` 为 `html` 时会额外生成 PDF，文件保存在同一文章目录，命名为 `YYYY-MM-DD_文章标题.pdf`。
- 遇到 `SSL: UNEXPECTED_EOF_WHILE_READING` 这类远端连接中断时，程序会自动重试；需要定位具体接口时用 `--log-level DEBUG` 查看请求阶段和重试记录。
- 用 cron 调度时建议运行单次同步命令，不要在 cron 里加 `--daemon`。
- `config.json` 可配置项：
  - `api_base_url`：mptext API 地址，默认 `https://down.mptext.top`。
  - `api_key`：直接写入 API key；本地单机运行可用，提交代码前不要把真实 key 放进仓库。
  - `api_key_env`：读取 API key 的环境变量名，默认 `MP_TEXT_API_KEY`；这里填的是变量名，不是 key 本身。
  - `output_dir`：文章内容和元数据保存目录，默认 `data/articles`。
  - `state_path`：已同步 URL 状态文件，默认 `data/state.json`。
  - `content_format`：下载格式，可用 `html`、`markdown`、`text`、`json`。
  - `interval_seconds`：`--daemon` 模式下两次同步的间隔秒数，默认 `3600`。
  - `page_size`：每页文章数，最大 `20`。
  - `max_pages`：每次同步每个账号最多拉取页数，默认 `1`。
  - `timeout_seconds`：API 请求超时时间，默认 `30`。
  - `accounts`：要同步的公众号列表；每个公众号只保留一项，优先写 `fakeid`，没有 `fakeid` 时再用 `keyword`，可选 `article_keyword` 过滤文章标题。
- 每次改代码后运行测试：

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```
