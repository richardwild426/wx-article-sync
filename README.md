# wx-article-sync

## 项目作用

`wx-article-sync` 依赖 mptext 在线 API，定时拉取微信公众号文章列表，下载新增文章，并保存到本地目录。已同步过的文章 URL 会记录在状态文件里，后续运行不会重复下载。

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

常驻定时同步：

```bash
uv run wx-article-sync --config config.json --daemon
```

## 运维注意事项

- API key 有效期跟 mptext 登录会话一致，过期后同步会失败，需要重新登录并更新 `MP_TEXT_API_KEY`。
- 优先在 `config.json` 里配置公众号 `fakeid`；只配置 `keyword` 时会使用 API 搜索结果的第一项，账号重名时可能选错。
- 默认文章保存到 `data/articles`，同步状态保存到 `data/state.json`；备份或迁移时要一起保留 `data/state.json`。
- 用 cron 调度时建议运行单次同步命令，不要在 cron 里加 `--daemon`。
- 每次改代码后运行测试：

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```
