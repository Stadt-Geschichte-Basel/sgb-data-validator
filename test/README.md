# Test Organization

This directory contains a comprehensive test suite for the SGB Data Validator, organized by type and functionality.

## Test Categories

Tests are automatically categorized using pytest markers:

- **`unit`**: Fast, isolated unit tests
- **`integration`**: Integration tests across components
- **`slow`**: Slow-running tests

## Running Tests

### Run all tests

```bash
uv run pytest
```

### Run specific test categories

```bash
# Unit tests only (fast)
uv run pytest -m unit

# Integration tests only
uv run pytest -m integration
```

### Run tests by file pattern

```bash
# All issue-specific tests
uv run pytest test/test_issue*.py

# All transformation tests
uv run pytest test/test_transformations.py test/test_issue31_transformations.py

# Validation tests
uv run pytest test/test_validation.py test/test_issue16_validation.py
```

### Verbose output

```bash
uv run pytest -v
```

## Test Files by Category

### Core Functionality (Unit Tests)

- `test_api.py` - API initialization and basic operations
- `test_models.py` - Data model validation (Item, Media)
- `test_validation.py` - Core validation logic
- `test_vocabularies.py` - Vocabulary validation (ICONCLASS, ISO639, etc.)

### Data Transformation (Unit Tests)

- `test_transformations.py` - Basic text normalization and transformation
- `test_issue31_transformations.py` - Advanced transformations (HTML entities, abbreviations, URLs)
- `test_https_upgrade.py` - HTTP to HTTPS URL upgrading
- `test_issue36_private_flag.py` - Private flag propagation from media to items

### Validation Rules (Unit Tests)

- `test_issue16_validation.py` - Field presence validation rules
- `test_issue22_url_in_literals.py` - URL detection in literal fields
- `test_uri_checking.py` - URI validation and checking

### Vocabulary Validation (Unit Tests)

- `test_iconclass.py` - ICONCLASS notation validation
- `test_iso639.py` - ISO 639 language code validation

### Integration Tests

- `test_integration_issue31.py` - Complete transformation workflow
- `test_iconclass_integration.py` - ICONCLASS with real data
- `test_offline_workflow.py` - Offline download-transform-upload workflow
- `test_creation.py` - Item and media creation workflows

## Test Structure

Each test file follows this structure:

```python
"""
Brief description of what this test file covers.
"""

def test_feature_name():
    """Test description with specific scenario."""
    # Arrange
    # Act
    # Assert
```

## Adding New Tests

1. **Choose the right file**: Add to an existing file if it fits the theme
2. **Create new file if needed**: Use pattern `test_<feature>.py` or `test_issue<number>_<description>.py`
3. **Add markers manually** (if needed):

   ```python
   import pytest

   @pytest.mark.network
   def test_external_api():
       """Test that requires external API."""
       pass
   ```

## Test Coverage Summary

| Category    | Tests  | Coverage                                              |
| ----------- | ------ | ----------------------------------------------------- |
| Unit        | 72     | Core functionality, transformations, validation rules |
| Integration | 24     | Workflows, offline processing, creation               |
| **Total**   | **96** | **Comprehensive coverage**                            |

## Key Features Tested

### Issue-Specific Tests

- **Issue #16**: Field presence validation (errors and warnings)
- **Issue #22**: URL detection in literal fields
- **Issue #31**: Advanced text transformations (HTML, abbreviations, URLs)
- **Issue #36**: Private flag propagation from placeholder media to items

### Core Features

- ✅ Data model validation (Pydantic models)
- ✅ Omeka S API interaction
- ✅ ICONCLASS notation validation
- ✅ ISO 639 language code validation
- ✅ Text normalization and transformation
- ✅ Offline workflow (download, transform, upload)
- ✅ Item and media creation
- ✅ URI validation
- ✅ HTTPS upgrade

## Quick Reference

```bash
# Fast test run (unit only)
uv run pytest -m unit -q

# Full test run
uv run pytest

# Test specific feature
uv run pytest test/test_issue36_private_flag.py -v

# Test with coverage
uv run pytest --cov=src --cov-report=html
```

## Troubleshooting

### Slow Tests

Some tests make real HTTP requests. Use `-m unit` for fast feedback during development.
