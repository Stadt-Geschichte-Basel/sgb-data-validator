# Iconclass Validator Documentation

This document describes the Pydantic validator for Iconclass notation implemented for the sgb-data-validator project.

## Overview

Iconclass is a hierarchical classification system for art and iconography. This validator ensures that Iconclass codes conform to the proper format and can validate them against a controlled vocabulary.

## Implementation

### Files Created

- `src/iconclass.py` - Core validator module with `IconclassNotation` model
- `test/test_iconclass.py` - Unit tests for the validator
- `test/test_iconclass_integration.py` - Integration tests with VocabularyLoader
- `examples/iconclass_usage.py` - Usage examples

### Files Modified

- `src/vocabularies.py` - Enhanced `is_valid_iconclass()` method to use the new validator
- `src/__init__.py` - Added exports for `IconclassNotation` and `validate_iconclass_notation`

## Features

### 1. Format Validation

Validates that Iconclass notation contains only allowed characters:

- Digits (0-9)
- Uppercase letters (A-Z)
- Lowercase 'q' (for qualifiers)
- Parentheses () for qualifiers and additions
- Plus signs + for incremental additions
- Spaces and dots for formatting

```python
from src.iconclass import IconclassNotation

# Valid
notation = IconclassNotation(notation="11H")
notation = IconclassNotation(notation="25F23")

# Invalid - will raise ValidationError
notation = IconclassNotation(notation="11H@")  # @ not allowed
```

### 2. Hierarchical Parts Splitting

Breaks down notation into hierarchical parts following the iconclass/data repository logic:

```python
notation = IconclassNotation(notation="25F23")
print(notation.parts)
# Output: ['2', '25', '25F', '25F2', '25F23']

notation = IconclassNotation(notation="11H(JEROME)")
print(notation.parts)
# Output: ['1', '11', '11H', '11H(...)', '11H(JEROME)']
```

### 3. Vocabulary Validation

Validates codes against the controlled vocabulary:

```python
from pathlib import Path
from src.vocabularies import VocabularyLoader

vocab_file = Path("data/raw/vocabularies.json")
loader = VocabularyLoader(vocab_file)

loader.is_valid_iconclass("11H")        # True - in vocabulary
loader.is_valid_iconclass("ZZZ999")     # False - not in vocabulary
```

## Usage Examples

### Basic Usage

```python
from src.iconclass import IconclassNotation, validate_iconclass_notation

# Using the model directly
notation = IconclassNotation(notation="11H")
print(f"Notation: {notation.notation}")
print(f"Parts: {notation.parts}")

# Using the helper function
notation = validate_iconclass_notation("11H")
```

### Complex Notation

```python
# Notation with parenthetical qualifier
notation = IconclassNotation(notation="11H(JEROME)")

# Notation with plus addition
notation = IconclassNotation(notation="11H(+3)")

# Multiple qualifiers
notation = IconclassNotation(notation="11H(JEROME)(+3)")
```

### Integration with Vocabulary

```python
from pathlib import Path
from src.vocabularies import VocabularyLoader

vocab_file = Path("data/raw/vocabularies.json")
loader = VocabularyLoader(vocab_file)

# Validate format and vocabulary
code = "11H"
try:
    notation = IconclassNotation(notation=code)
    if loader.is_valid_iconclass(code):
        print(f"✓ {code} is valid")
    else:
        print(f"✗ {code} not in vocabulary")
except ValidationError as e:
    print(f"✗ Invalid format: {e}")
```

## Running Tests

```bash
# Unit tests
uv run python test/test_iconclass.py

# Integration tests
uv run python test/test_iconclass_integration.py

# All validation tests
uv run python test/test_validation.py
```

## Example Output

Run the example script to see the validator in action:

```bash
uv run python examples/iconclass_usage.py
```

This will demonstrate:

1. Basic format validation
2. Complex notation with qualifiers
3. Validation against vocabulary
4. Helper function usage
5. Hierarchical parts splitting

## References

- **Issue**: [#8 Add Pydantic validator for Iconclass notation](https://github.com/Stadt-Geschichte-Basel/sgb-data-validator/issues/8)
- **Iconclass data**: https://github.com/iconclass/data
- **Iconclass website**: https://iconclass.org/

## Implementation Notes

The implementation follows the repository's coding style:

- Uses Pydantic BaseModel with field validators
- Follows patterns from `src/models.py` and `src/vocabularies.py`
- Comprehensive docstrings for all functions and classes
- Tests follow pattern from `test/test_validation.py`

The hierarchical parts splitting logic is based on the `get_parts` function from the [iconclass/data](https://github.com/iconclass/data) repository's `make_index.py`.
