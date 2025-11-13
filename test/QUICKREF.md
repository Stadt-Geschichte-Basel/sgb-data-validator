# Test Organization Quick Reference

## Test Categories

```
┌──────────────────────────────────────────────────────────────┐
│ SGB Data Validator Test Suite                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  📦 UNIT TESTS (72)           ⚡ Fast, isolated tests        │
│  ├─ Core Functionality        - API, models, validation     │
│  ├─ Transformations           - Text normalization          │
│  ├─ Validation Rules          - Field presence, URLs        │
│  └─ Vocabularies              - ICONCLASS, ISO639           │
│                                                              │
│  🔗 INTEGRATION TESTS (24)    🔄 Component interactions      │
│  ├─ Workflows                 - Offline, transformation     │
│  ├─ Creation                  - Items, media                │
│  └─ Real-world scenarios      - Complex examples            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  Total: 96 tests                                             │
└──────────────────────────────────────────────────────────────┘
```

## Common Commands

| Command | Description | Tests Run |
|---------|-------------|-----------||
| `uv run pytest` | Default run | 96 |
| `uv run pytest -m unit` | Unit tests only | 72 |
| `uv run pytest -m integration` | Integration tests only | 24 |
| `uv run pytest -v` | Verbose output | 96 |
| `uv run pytest -q` | Quiet output | 96 |

## Test Files by Type

### Unit Tests

```
test_api.py                      # API basics
test_transformations.py          # Text normalization
test_issue31_transformations.py  # Advanced transformations
test_issue36_private_flag.py     # Private flag propagation
test_https_upgrade.py            # HTTPS upgrading
test_validation.py               # Core validation
test_issue16_validation.py       # Field validation rules
test_issue22_url_in_literals.py  # URL detection
test_uri_checking.py             # URI validation
test_iconclass.py                # ICONCLASS notation
test_iso639.py                   # Language codes
```

### Integration Tests

```
test_integration_issue31.py      # Complete transformation workflow
test_iconclass_integration.py    # ICONCLASS with real data
test_offline_workflow.py         # Download-transform-upload
test_creation.py                 # Item/media creation
```

## Feature Coverage

| Feature                              | Test File                         | Category    |
| ------------------------------------ | --------------------------------- | ----------- |
| Private flag propagation (Issue #36) | `test_issue36_private_flag.py`    | Unit        |
| Text transformations (Issue #31)     | `test_issue31_transformations.py` | Unit        |
| Field validation (Issue #16)         | `test_issue16_validation.py`      | Unit        |
| URL in literals (Issue #22)          | `test_issue22_url_in_literals.py` | Unit        |
| HTTPS upgrade                        | `test_https_upgrade.py`           | Unit        |
| ICONCLASS validation                 | `test_iconclass.py`               | Unit        |
| ISO 639 codes                        | `test_iso639.py`                  | Unit        |
| Complete workflows                   | `test_integration_issue31.py`     | Integration |
| Offline processing                   | `test_offline_workflow.py`        | Integration |
| Item/media creation                  | `test_creation.py`                | Integration |

## Automatic Categorization

Tests are automatically categorized by `conftest.py`:

- **Integration**: Files matching patterns like `integration`, `offline_workflow`, `creation`, `api.py`
- **Unit**: Everything else (default)

## Running Specific Tests

```bash
# By file
uv run pytest test/test_issue36_private_flag.py

# By pattern
uv run pytest test/test_issue*.py

# By function name
uv run pytest -k "private_flag"

# Multiple categories
uv run pytest -m "unit or integration"
```

## Adding New Tests

1. **Choose file**: Add to existing file if theme matches
2. **Create file**: Use pattern `test_<feature>.py` or `test_issue<N>_<desc>.py`
3. **Categorization**: Automatic based on filename

## Performance

| Category      | Typical Runtime |
| ------------- | --------------- |
| Unit          | ~3-5 seconds    |
| Integration   | ~5-7 seconds    |
| All (default) | ~7-8 seconds    |
