# ISO 639-1 Language Code Validation

This document describes the ISO 639-1 language code validation feature implemented in the sgb-data-validator.

## Overview

The validator now supports full ISO 639-1 standard validation for language codes used in metadata fields like `dcterms:language`. This replaces the previous limited validation that only checked against a small subset of language codes.

## Features

- **Complete ISO 639-1 coverage**: All 184 two-letter language codes
- **Case-insensitive**: Accepts both lowercase and uppercase codes (e.g., "en", "EN", "En")
- **Efficient validation**: Uses immutable frozenset for fast lookups
- **Standalone module**: Can be used independently of the full validator

## Usage

### In Validation

Language codes in `dcterms:language` fields are automatically validated:

```bash
uv run python validate.py --item-set-id 10780
```

If an invalid language code is detected, you'll see an error like:

```
[Item 12345] dcterms:language[0]: Invalid language code (must be valid ISO 639-1 two-letter code): xyz
```

### Programmatic Usage

You can use the ISO 639-1 validation module directly in your Python code:

```python
from src.iso639 import is_valid_iso639_1_code, get_all_codes

# Validate a single code
if is_valid_iso639_1_code("en"):
    print("Valid language code!")

# Get all valid codes
all_codes = get_all_codes()
print(f"Total codes: {len(all_codes)}")
```

See `examples/iso639_usage.py` for more examples.

## Valid Language Codes

The validator accepts all 184 ISO 639-1 two-letter codes, including but not limited to:

| Code | Language | Code | Language | Code | Language   |
| ---- | -------- | ---- | -------- | ---- | ---------- |
| de   | German   | en   | English  | es   | Spanish    |
| fr   | French   | it   | Italian  | pt   | Portuguese |
| nl   | Dutch    | ru   | Russian  | zh   | Chinese    |
| ja   | Japanese | ar   | Arabic   | hi   | Hindi      |
| ko   | Korean   | la   | Latin    | el   | Greek      |

For a complete list, see the [ISO 639-1 standard](https://www.loc.gov/standards/iso639-2/php/code_list.php).

## Migration from Previous Version

The previous version only validated against 4 language codes (de, fr, nl, la). The new implementation:

- ✅ Still accepts all previously valid codes
- ✅ Now accepts 180 additional valid ISO 639-1 codes
- ✅ Provides clearer error messages
- ✅ Is case-insensitive (previously case-sensitive)

**No breaking changes** - all previously valid codes remain valid.

## Testing

Run the ISO 639-1 test suite:

```bash
uv run python test/test_iso639.py
```

The test suite covers:

- Valid and invalid codes
- Case-insensitive validation
- Edge cases (None, empty strings, non-strings)
- Code count verification
- Immutability of the code set

## Implementation Details

### Module: `src/iso639.py`

The module provides:

- `ISO_639_1_CODES`: Frozenset of all 184 valid codes
- `is_valid_iso639_1_code(code: str) -> bool`: Validate a language code
- `get_all_codes() -> frozenset[str]`: Get all valid codes

### Integration

The validation is integrated into:

1. **`src/vocabularies.py`**: The `is_valid_language()` method now uses ISO 639-1 validation
2. **`validate.py`**: The `_validate_vocabularies()` method validates `dcterms:language` fields
3. **Error messages**: Updated to reflect full ISO 639-1 standard

## Examples

See `examples/iso639_usage.py` for practical examples:

```bash
uv run python examples/iso639_usage.py
```

## References

- [ISO 639-1 Standard](https://www.loc.gov/standards/iso639-2/php/code_list.php)
- [Library of Congress ISO 639 Codes](https://www.loc.gov/standards/iso639-2/)
- [Wikipedia: List of ISO 639-1 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
