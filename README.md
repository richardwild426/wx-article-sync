# wx-article-sync

`wx-article-sync` uses the mptext public API to periodically sync WeChat public-account articles into local files.

## API

The implementation follows `https://docs.mptext.top/advanced/api.html`:

- `X-Auth-Key` is sent on every request.
- `/api/public/v1/authkey` validates the key before a sync run.
- `/api/public/v1/account` resolves a keyword to a `fakeid` when needed.
- `/api/public/v1/article` lists articles for a `fakeid`.
- `/api/public/v1/download` downloads each new article in `html`, `markdown`, `text`, or `json` format.

## Configure

Copy `config.example.json` to `config.json`, then set the API key in the environment:

```bash
export MP_TEXT_API_KEY="your-api-key"
```

Prefer `fakeid` in `accounts` when it is known. A `keyword` account works too, but it uses the first search result returned by the API.

## Run Once

```bash
uv run wx-article-sync --config config.json
```

The command writes article content to `data/articles` and records synced URLs in `data/state.json`.

## Run As A Timer

For a long-running process:

```bash
uv run wx-article-sync --config config.json --daemon
```

For cron, keep the command as a one-shot sync and let cron handle scheduling:

```cron
0 * * * * cd /path/to/wx-article-sync && MP_TEXT_API_KEY=your-api-key uv run wx-article-sync --config config.json
```

## Test

```bash
uv run python -m unittest discover -s tests -p 'test_*.py'
```

