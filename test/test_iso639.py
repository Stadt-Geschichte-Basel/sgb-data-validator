"""Tests for ISO 639-1 language code validation"""

from src.iso639 import get_all_codes, is_valid_iso639_1_code


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


def test_all_codes_count() -> None:
    """Test that we have the correct number of ISO 639-1 codes"""
    print("\nTesting ISO 639-1 code count...")

    all_codes = get_all_codes()

    # ISO 639-1 has 184 two-letter codes
    # Our list should have approximately this many
    assert len(all_codes) >= 180, f"Expected at least 180 codes, got {len(all_codes)}"
    assert len(all_codes) <= 200, f"Expected at most 200 codes, got {len(all_codes)}"

    print(f"  ✓ Found {len(all_codes)} ISO 639-1 codes")
    print("✓ Code count is in expected range")


def test_specific_codes() -> None:
    """Test specific codes mentioned in the project"""
    print("\nTesting specific codes used in the project...")

    # These are the codes that were previously in the limited vocabulary
    project_codes = ["de", "fr", "nl", "la"]

    for code in project_codes:
        assert is_valid_iso639_1_code(code), f"Code '{code}' should be valid"
        print(f"  ✓ '{code}' is valid")

    print("✓ All project-specific codes are valid")


def test_frozenset_immutability() -> None:
    """Test that the code set is immutable"""
    print("\nTesting immutability of code set...")

    codes = get_all_codes()
    assert isinstance(codes, frozenset), "Codes should be a frozenset"
    print("  ✓ Codes are stored in immutable frozenset")

    # Verify we can't modify it
    try:
        codes.add("test")
        raise AssertionError("Should not be able to add to frozenset")
    except AttributeError:
        print("  ✓ Frozenset correctly prevents modification")

    print("✓ Code set is properly immutable")


if __name__ == "__main__":
    print("=" * 70)
    print("ISO 639-1 Language Code Validation Tests")
    print("=" * 70)

    test_valid_codes()
    test_case_insensitive()
    test_invalid_codes()
    test_edge_cases()
    test_all_codes_count()
    test_specific_codes()
    test_frozenset_immutability()

    print("\n" + "=" * 70)
    print("✓ All ISO 639-1 validation tests passed successfully!")
    print("=" * 70)
