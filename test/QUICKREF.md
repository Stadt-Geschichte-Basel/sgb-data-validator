# Test commands

| Purpose                        | Command                                                |
| ------------------------------ | ------------------------------------------------------ |
| Run all tests                  | `uv run --locked pytest`                               |
| Check validation and snapshots | `uv run --locked pytest test/test_offline_workflow.py` |
| Check guarded writes           | `uv run --locked pytest test/test_creation.py`         |
| Check recovery                 | `uv run --locked pytest test/test_recovery.py`         |

See the [test guide](README.md) for type checks and the recovery drill.
