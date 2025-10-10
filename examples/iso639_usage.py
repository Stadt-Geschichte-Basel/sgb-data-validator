"""Example usage of ISO 639-1 language code validation

This example demonstrates how to use the ISO 639-1 validator in the
sgb-data-validator package.
"""

from src.iso639 import get_all_codes, is_valid_iso639_1_code


def example_basic_validation() -> None:
    """Example: Basic language code validation"""
    print("\n" + "=" * 60)
    print("Example 1: Basic Language Code Validation")
    print("=" * 60)

    test_codes = [
        ("en", "English"),
        ("de", "German"),
        ("fr", "French"),
        ("es", "Spanish"),
        ("xx", "Invalid code"),
        ("eng", "Three-letter code (ISO 639-2, not 639-1)"),
    ]

    for code, description in test_codes:
        is_valid = is_valid_iso639_1_code(code)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"{status}: '{code}' - {description}")


def example_case_insensitive() -> None:
    """Example: Case-insensitive validation"""
    print("\n" + "=" * 60)
    print("Example 2: Case-Insensitive Validation")
    print("=" * 60)

    test_codes = ["en", "EN", "En", "eN"]

    for code in test_codes:
        is_valid = is_valid_iso639_1_code(code)
        print(f"'{code}' is valid: {is_valid}")


def example_all_codes() -> None:
    """Example: Getting all ISO 639-1 codes"""
    print("\n" + "=" * 60)
    print("Example 3: All ISO 639-1 Codes")
    print("=" * 60)

    all_codes = get_all_codes()
    print(f"Total number of ISO 639-1 codes: {len(all_codes)}")
    print("\nFirst 20 codes (alphabetically):")
    for i, code in enumerate(sorted(all_codes)[:20], 1):
        print(f"  {i:2d}. {code}")
    print(f"  ... and {len(all_codes) - 20} more")


def example_validation_in_context() -> None:
    """Example: Using validation in a metadata context"""
    print("\n" + "=" * 60)
    print("Example 4: Validation in Metadata Context")
    print("=" * 60)

    # Simulate metadata records with language fields
    records = [
        {"id": 1, "title": "Document 1", "language": "en"},
        {"id": 2, "title": "Document 2", "language": "de"},
        {"id": 3, "title": "Document 3", "language": "xyz"},  # Invalid
        {"id": 4, "title": "Document 4", "language": "EN"},  # Uppercase, but valid
        {"id": 5, "title": "Document 5", "language": "eng"},  # Invalid (3-letter)
    ]

    print("\nValidating language codes in metadata records:")
    for record in records:
        lang = record["language"]
        is_valid = is_valid_iso639_1_code(lang)
        status = "✓" if is_valid else "✗"
        print(
            f"  {status} Record {record['id']}: language='{lang}' "
            f"({'valid' if is_valid else 'invalid'})"
        )


def example_common_languages() -> None:
    """Example: Common language codes"""
    print("\n" + "=" * 60)
    print("Example 5: Common Language Codes")
    print("=" * 60)

    common_languages = [
        ("en", "English"),
        ("de", "German"),
        ("fr", "French"),
        ("es", "Spanish"),
        ("it", "Italian"),
        ("pt", "Portuguese"),
        ("nl", "Dutch"),
        ("ru", "Russian"),
        ("zh", "Chinese"),
        ("ja", "Japanese"),
        ("ar", "Arabic"),
        ("hi", "Hindi"),
        ("ko", "Korean"),
        ("la", "Latin"),
    ]

    print("\nValidating common languages:")
    for code, name in common_languages:
        is_valid = is_valid_iso639_1_code(code)
        status = "✓" if is_valid else "✗"
        print(f"  {status} {code}: {name}")


if __name__ == "__main__":
    print("=" * 60)
    print("ISO 639-1 Language Code Validation Examples")
    print("=" * 60)

    example_basic_validation()
    example_case_insensitive()
    example_all_codes()
    example_validation_in_context()
    example_common_languages()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
