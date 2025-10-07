"""Integration test for Iconclass validation in the data validator"""

from pathlib import Path

from src.vocabularies import VocabularyLoader


def test_iconclass_integration() -> None:
    """Test Iconclass validation integration with VocabularyLoader"""
    print("Testing Iconclass integration with VocabularyLoader...")

    vocab_file = Path("data/raw/vocabularies.json")
    loader = VocabularyLoader(vocab_file)

    # Test valid codes from the vocabulary
    valid_codes = [
        "11A",  # Gottheit, Gott
        "11B",  # die Heilige Dreifaltigkeit
        "11H",  # Heilige
        "25F23",  # More complex example
    ]

    for code in valid_codes:
        assert loader.is_valid_iconclass(code), f"Code {code} should be valid"
        print(f"✓ Valid code: {code}")

    # Test codes with qualifiers
    qualified_codes = [
        "11H(JEROME)",
        "11H(+3)",
        "25F23(DOG)",
    ]

    for code in qualified_codes:
        assert loader.is_valid_iconclass(code), f"Code {code} should be valid"
        print(f"✓ Valid qualified code: {code}")

    # Test invalid codes
    invalid_codes = [
        "",  # Empty
        "@@INVALID",  # Invalid characters
        "11H@",  # Invalid character in code
        "ZZZ999",  # Nonexistent base code
    ]

    for code in invalid_codes:
        assert not loader.is_valid_iconclass(code), f"Code {code} should be invalid"
        print(f"✓ Invalid code correctly rejected: {code}")


def test_iconclass_format_validation() -> None:
    """Test that format validation works independently"""
    print("\nTesting format validation...")

    from src.iconclass import IconclassNotation
    from pydantic import ValidationError

    # Valid formats
    valid_formats = [
        "11H",
        "25F23",
        "11H(JEROME)",
        "11H(+3)",
        "11 H",  # Space allowed
        "11.H",  # Dot allowed
        "11Hq",  # 'q' allowed
    ]

    for notation in valid_formats:
        try:
            IconclassNotation(notation=notation)
            print(f"✓ Valid format: {notation}")
        except ValidationError as e:
            print(f"✗ Should have accepted: {notation} - {e}")
            raise

    # Invalid formats
    invalid_formats = [
        "",  # Empty
        "11H@",  # @ not allowed
        "11H$",  # $ not allowed
        "11H!",  # ! not allowed
    ]

    for notation in invalid_formats:
        try:
            IconclassNotation(notation=notation)
            print(f"✗ Should have rejected: {notation}")
            raise AssertionError(f"Should have rejected: {notation}")
        except ValidationError:
            print(f"✓ Invalid format correctly rejected: {notation}")


if __name__ == "__main__":
    test_iconclass_integration()
    test_iconclass_format_validation()
    print("\n✓ All integration tests passed")
