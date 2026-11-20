"""Tests for ISO 639-1 language code validation"""

from sgb_validator.iso639 import is_valid_iso639_1_code


def test_valid_codes() -> None:
    """Test that common valid language codes are accepted"""
    print("\nTesting valid ISO 639-1 codes...")

    valid_codes = [
        "en",
        "de",
        "fr",
        "es",
        "it",
        "pt",
        "nl",
        "ru",
        "zh",
        "ja",
        "ar",
        "hi",
        "ko",
        "vi",
        "tr",
        "pl",
        "uk",
        "ro",
        "el",
        "cs",
    ]

    for code in valid_codes:
        assert is_valid_iso639_1_code(code), f"Code '{code}' should be valid"
        print(f"  ✓ '{code}' is valid")

    print(f"✓ All {len(valid_codes)} common language codes validated successfully")


def test_case_insensitive() -> None:
    """Test that validation is case-insensitive"""
    print("\nTesting case-insensitive validation...")

    test_cases = [
        ("en", True),
        ("EN", True),
        ("En", True),
        ("eN", True),
        ("de", True),
        ("DE", True),
        ("De", True),
    ]

    for code, expected in test_cases:
        result = is_valid_iso639_1_code(code)
        assert result == expected, f"Code '{code}' should be {expected}"
        print(f"  ✓ '{code}' correctly validated as {result}")

    print("✓ Case-insensitive validation working correctly")


def test_invalid_codes() -> None:
    """Test that invalid codes are rejected"""
    print("\nTesting invalid codes...")

    invalid_codes = [
        "xx",  # Non-existent code
        "zz",  # Non-existent code
        "xyz",  # Too long
        "e",  # Too short
        "eng",  # Three-letter code (ISO 639-2)
        "deu",  # Three-letter code (ISO 639-2)
        "123",  # Numbers
        "",  # Empty string
        "  ",  # Whitespace
        "en-US",  # Language tag (not just code)
        "de-DE",  # Language tag
    ]

    for code in invalid_codes:
        result = is_valid_iso639_1_code(code)
        assert not result, f"Code '{code}' should be invalid"
        print(f"  ✓ '{code}' correctly rejected")

    print(f"✓ All {len(invalid_codes)} invalid codes correctly rejected")


def test_edge_cases() -> None:
    """Test edge cases"""
    print("\nTesting edge cases...")

    # None input
    assert not is_valid_iso639_1_code(None), "None should be invalid"
    print("  ✓ None correctly rejected")

    # Non-string input
    assert not is_valid_iso639_1_code(123), "Integer should be invalid"
    print("  ✓ Integer correctly rejected")

    assert not is_valid_iso639_1_code([]), "List should be invalid"
    print("  ✓ List correctly rejected")

    print("✓ All edge cases handled correctly")


def test_specific_codes() -> None:
    """Test specific codes mentioned in the project"""
    print("\nTesting specific codes used in the project...")

    # These are the codes that were previously in the limited vocabulary
    project_codes = ["de", "fr", "nl", "la"]

    for code in project_codes:
        assert is_valid_iso639_1_code(code), f"Code '{code}' should be valid"
        print(f"  ✓ '{code}' is valid")

    print("✓ All project-specific codes are valid")
