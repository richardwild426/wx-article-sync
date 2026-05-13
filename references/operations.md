# Operations Guide

## One-Time Sync

Run from the project root:

```bash
uv run wx-article-sync --config config.json
```

Use debug logging for API or network diagnosis:

```bash
uv run wx-article-sync --config config.json --log-level DEBUG
```

## Logs

The synchronizer writes logs to both console and:

```text
logs/wx-article-sync.log
```

Each log file rotates at 2MB. Use the newest file first when diagnosing.

## State Inspection

The state file records already-seen article URLs. Inspect it without exposing full URLs:

```bash
python scripts/inspect_state.py data/state.json
```

Keep `state_path` when migrating machines. Losing it can make old articles look new again.

## Scheduling

For external schedulers, run a one-shot sync command. Do not combine an external scheduler with `--daemon`.

Daily command shape:

```bash
cd /path/to/wx-article-sync
uv run wx-article-sync --config config.json
```

If the workflow also needs IMA linkage, keep the operations serial: local sync first, then IMA manifest/import. Do not attempt IMA import when local sync failed.

## macOS launchd

Use `assets/launchd.example.plist` as a template. Update:

- `WorkingDirectory`
- absolute path to `uv`
- stdout and stderr paths
- `StartCalendarInterval`

If using `api_key_env`, remember that launchd does not inherit a terminal's exported environment. For unattended local runs, either configure launchd environment variables correctly or store `api_key` in the local untracked `config.json`.
