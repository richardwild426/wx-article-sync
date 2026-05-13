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

首次配置时通过对话逐步确认，不要一次性输出配置字段清单。推荐顺序：

1. 你想同步几个公众号？
2. 这些公众号是否已经在 mptext 公众号管理页添加并同步过文章链接？
3. 你是否已经拿到每个公众号的 `fakeid`？
4. 每个公众号每天同步最新几篇？
5. 是否需要同步到 ima 知识库？

用户回答后，再把答案转成 `config.json`。不要要求用户理解全部配置字段。

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
