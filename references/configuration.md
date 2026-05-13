# Configuration Guide

## 首次使用前置准备

本 skill 严重依赖 mptext 网站侧已经准备好目标公众号和文章链接库。首次使用时，先引导用户按官方教程完成准备：

```text
https://docs.mptext.top/tutorials/export-article-links.html
```

准备流程要点：

1. 准备一个微信订阅号或服务号；如果已经有可用的订阅号或服务号，可以跳过注册。
2. 进入 mptext 网站登录页，用微信扫码，并选择公众号或服务号登录。
3. 不要选择小程序登录；小程序登录后续无法获取文章数据。
4. 在 mptext 的公众号管理页面添加目标公众号。
5. 点击同步，先让 mptext 拉取目标公众号的文章链接。
6. 如果目标公众号关闭了搜索功能，这条准备路径不可用，需要先解决公众号搜索可见性问题。

完成以上准备后，再生成或修改本项目的 `config.json`。

首次配置时通过对话逐步确认，不要一次性输出配置字段清单。先确认前置要求，再做初始化设置。推荐顺序：

1. mptext 前置准备完成了吗：目标公众号是否已经在 mptext 公众号管理页添加并同步过文章链接？
2. 你想同步几个公众号？
3. 你是否已经拿到每个公众号的 `fakeid`？
4. 同步的文章数量：每个公众号每天同步最新几篇？必须告知：默认每个公众号每次最多请求 20 篇；日更归档通常建议每天同步最新 1 篇。
5. 同步频率：每天一次、每小时一次，还是只手动同步？
6. 是否需要联动 IMA？
7. 如果需要联动 IMA，IMA 怎么配置：使用 `~/.config/ima/client_id` / `~/.config/ima/api_key`，还是使用 `IMA_OPENAPI_CLIENTID` / `IMA_OPENAPI_APIKEY` 环境变量？

用户回答后，再把答案转成 `config.json`。如果用户没有明确选择，不要静默沿用默认 20 篇；先追问或按“每天同步最新 1 篇”的业务建议生成配置，并在回复中说明这个选择。

## Minimal Daily Latest Article Config

Use this for a business user who wants the latest article from two accounts each day:

```json
{
  "api_base_url": "https://down.mptext.top",
  "api_key_env": "MP_TEXT_API_KEY",
  "output_dir": "data/articles",
  "state_path": "data/state.json",
  "content_format": "markdown",
  "page_size": 1,
  "max_pages": 1,
  "accounts": [
    {
      "fakeid": "FIRST_ACCOUNT_FAKEID"
    },
    {
      "fakeid": "SECOND_ACCOUNT_FAKEID"
    }
  ]
}
```

## Required Fields

- `accounts`: A non-empty list. Each item must contain either `fakeid` or `keyword`.
- API key source: Either `api_key` or `api_key_env`. Prefer `api_key_env` in generated examples.

## Account Rules

- Prefer `fakeid`. It is stable and avoids selecting the wrong account when names are similar.
- Use `keyword` only when the user does not have a `fakeid`.
- Do not configure the same account twice.
- Do not create one item with `fakeid` and another item with `keyword` for the same account.
- Use `article_keyword` only when the user explicitly wants title filtering.

## Count Rules

- `page_size` is sent to mptext as the requested page size.
- `max_pages` controls how many pages are requested for each account.
- If omitted, `page_size` defaults to `20`, capped at `20`.
- For daily latest article sync, set `page_size` to `1` and `max_pages` to `1`.
- Expected upper bound is usually `accounts * page_size * max_pages`.
- If mptext returns more records than requested, the current synchronizer processes the returned records.

## Format Rules

- `markdown`: Good default for local archives and later processing.
- `html`: Saves HTML and also generates PDF.
- `text`: Useful for plain text workflows.
- `json`: Useful when downstream processing needs raw structured content.

## Validation

Use the bundled validator:

```bash
python scripts/validate_config.py config.json
```

The validator checks business-safe shape and common mistakes. It does not verify whether the API key is valid or whether a `fakeid` exists in mptext.
