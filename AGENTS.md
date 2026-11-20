# AGENTS.md

## Workflow

- Use `sgb_validator` and the `sgb` CLI for all collections.
- Keep validation and transformations free of network and file access.
- Use the shared Omeka client for API calls. Use a separate client for external links.
- Preserve snapshot filenames, report columns, and edit links.
- Preserve write previews, edit checks, private copies, and read-back checks.
- Keep credentials, live snapshots, and private evidence out of Git.
- Use public records for published reports.

## Checks

Run these commands from the repository root.

```sh
uv run --locked pytest
uv run --locked mypy sgb_validator
uv run --locked ruff check .
uv run --locked ruff format --check .
```

Run `npm run check` after documentation changes.

## Omeka recovery drill

Use disposable loopback instances of Omeka S 3.2.3 and 4.2.1. The drill creates and deletes fixture records.

Set `SGB_DRILL_URLS` to both instance URLs, separated by commas. Set `SGB_DRILL_KEY_IDENTITY` and `SGB_DRILL_KEY_CREDENTIAL` to the test API key shared by both instances. For containers, set `SGB_DRILL_INGEST_BASE` to the URL that Omeka uses to reach itself.

Run `uv run --locked pytest test/test_recovery.py`. See the [recovery guide](docs/recovery.md).
