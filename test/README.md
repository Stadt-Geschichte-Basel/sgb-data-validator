# Tests

Run the tests from the repository root.

```sh
uv run --locked pytest
uv run --locked mypy sgb_validator
uv run --locked ruff check .
uv run --locked ruff format --check .
```

| Purpose                        | Command                                                |
| ------------------------------ | ------------------------------------------------------ |
| Run all tests                  | `uv run --locked pytest`                               |
| Check validation and snapshots | `uv run --locked pytest test/test_offline_workflow.py` |
| Check guarded writes           | `uv run --locked pytest test/test_creation.py`         |
| Check recovery                 | `uv run --locked pytest test/test_recovery.py`         |

The tests use local fixtures and mock HTTP responses. The recovery drill skips if you do not set the test instance URLs. See the [recovery guide](../docs/recovery.md) for the drill procedure.
