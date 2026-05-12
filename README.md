# wx-article-sync

`wx-article-sync` 通过 mptext 公共 API 定时同步微信公众号文章，并把文章内容保存为本地文件。

## API

实现依据 `https://docs.mptext.top/advanced/api.html`：

- 每个请求都会携带 `X-Auth-Key`。
- 同步前通过 `/api/public/v1/authkey` 校验 API key。
- 需要时通过 `/api/public/v1/account` 把公众号关键词解析成 `fakeid`。
- 通过 `/api/public/v1/article` 获取指定 `fakeid` 的文章列表。
- 通过 `/api/public/v1/download` 下载新增文章，支持 `html`、`markdown`、`text`、`json` 格式。

## 配置

复制 `config.example.json` 为 `config.json`，然后在环境变量中设置 API key：

```bash
export MP_TEXT_API_KEY="your-api-key"
```

如果已经知道公众号的 `fakeid`，优先在 `accounts` 中直接配置 `fakeid`。也可以只配置 `keyword`，程序会使用 API 返回的第一个搜索结果。

## 单次运行

```bash
uv run wx-article-sync --config config.json
```

命令会把文章内容写入 `data/articles`，并在 `data/state.json` 中记录已经同步过的 URL，避免重复下载。

## 定时运行

作为常驻进程运行：

```bash
uv run wx-article-sync --config config.json --daemon
```

如果使用 cron，建议让程序保持单次同步，由 cron 负责调度：

```cron
0 * * * * cd /path/to/wx-article-sync && MP_TEXT_API_KEY=your-api-key uv run wx-article-sync --config config.json
```

## 测试

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```
