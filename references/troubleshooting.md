# Troubleshooting Guide

## Unexpected scanned/downloaded Counts

Use this model:

```text
scanned = article records returned by mptext
downloaded = records not present in state_path
skipped = records already present in state_path
```

If `page_size` is `2`, `max_pages` is `1`, and there are two accounts, the expected request is two records per account. If `scanned` is greater than `4`, mptext likely returned more records than requested.

## API Key Failures

Symptoms:

- Auth validation fails.
- Every API request fails.
- Sync worked before and now fails.

Actions:

1. Do not print the API key.
2. Confirm whether config uses `api_key` or `api_key_env`.
3. If using `api_key_env`, confirm the process environment contains that variable.
4. Re-login to `https://down.mptext.top` and update the key if it expired. The mptext auth-key expires with the login session after 4 days.

## Duplicate or Repeated Downloads

Check:

- `state_path` points to the expected file.
- The state file was preserved across migrations.
- The same account is not configured twice.
- `keyword` did not resolve to a different account than expected.

## Missing PDFs

PDF generation only runs when:

```json
"content_format": "html"
```

If HTML sync runs but PDF is missing, install the Playwright browser:

```bash
uv run playwright install chromium
```

## Network Errors

Transient remote failures such as `SSL: UNEXPECTED_EOF_WHILE_READING` are retried by the client. Use:

```bash
uv run wx-article-sync --config config.json --log-level DEBUG
```

Then inspect `logs/wx-article-sync.log`.
