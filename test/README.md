# Tests

Run the tests from the repository root.

```sh
uv run --locked pytest
uv run --locked mypy sgb_validator
uv run --locked ruff check .
uv run --locked ruff format --check .
```

The tests use local fixtures and mock HTTP responses. The recovery drill skips if you do not set the test instance URLs. See the [recovery guide](../docs/recovery.md) for the drill procedure.
