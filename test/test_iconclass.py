"""Tests for Iconclass notation validation"""

from pydantic import ValidationError

from src.iconclass import IconclassNotation, validate_iconclass_notation


def test_basic_notation() -> None:
    """Test basic Iconclass notation codes"""
    print("Testing basic notation...")

    # Simple numeric notation
    notation = IconclassNotation(notation="11H")
    assert notation.notation == "11H"
    assert "1" in notation.parts
    assert "11" in notation.parts
    assert "11H" in notation.parts
    print("✓ Basic notation '11H' validated")

    # Longer notation
    notation = IconclassNotation(notation="25F23")
    assert notation.notation == "25F23"
    assert "2" in notation.parts
    assert "25" in notation.parts
    assert "25F" in notation.parts
    assert "25F2" in notation.parts
    assert "25F23" in notation.parts
    print("✓ Longer notation '25F23' validated")


def test_notation_with_parentheses() -> None:
    """Test notation with parenthetical qualifiers"""
    print("\nTesting notation with parentheses...")

    notation = IconclassNotation(notation="25F23(DOG)")
    assert notation.notation == "25F23(DOG)"
    assert "25F23" in notation.parts
    assert "25F23(...)" in notation.parts
    assert "25F23(DOG)" in notation.parts
    print("✓ Notation with parentheses '25F23(DOG)' validated")


def test_notation_with_plus_additions() -> None:
    """Test notation with (+X) style additions"""
    print("\nTesting notation with plus additions...")

    notation = IconclassNotation(notation="11H(+3)")
    assert notation.notation == "11H(+3)"
    assert "11H" in notation.parts
    assert "11H(+3)" in notation.parts
    print("✓ Notation with plus addition '11H(+3)' validated")

    # Multiple characters after plus
    notation = IconclassNotation(notation="11H(+31)")
    assert "11H(+3)" in notation.parts
    assert "11H(+31)" in notation.parts
    print("✓ Notation with multi-char plus '11H(+31)' validated")


def test_complex_notation() -> None:
    """Test complex notation with multiple qualifiers"""
    print("\nTesting complex notation...")

    notation = IconclassNotation(notation="11H(JEROME)(+3)")
    assert "11H" in notation.parts
    assert "11H(...)" in notation.parts
    assert "11H(JEROME)" in notation.parts
    assert "11H(JEROME)(+3)" in notation.parts
    print("✓ Complex notation '11H(JEROME)(+3)' validated")


def test_invalid_notation() -> None:
    """Test that invalid notation is rejected"""
    print("\nTesting invalid notation...")

    # Empty notation
    try:
        IconclassNotation(notation="")
        print("✗ Should have rejected empty notation")
    except ValidationError:
        print("✓ Correctly rejected empty notation")

    # Invalid characters
    try:
        IconclassNotation(notation="11H@INVALID")
        print("✗ Should have rejected notation with @ symbol")
    except ValidationError:
        print("✓ Correctly rejected notation with invalid character '@'")

    # Invalid characters
    try:
        IconclassNotation(notation="11H$")
        print("✗ Should have rejected notation with $ symbol")
    except ValidationError:
        print("✓ Correctly rejected notation with invalid character '$'")


def test_edge_cases() -> None:
    """Test edge cases in notation"""
    print("\nTesting edge cases...")

    # Notation with spaces (might be valid in some contexts)
    notation = IconclassNotation(notation="11 H")
    assert notation.notation == "11 H"
    print("✓ Notation with space '11 H' validated")

    # Notation with dots
    notation = IconclassNotation(notation="11.H")
    assert notation.notation == "11.H"
    print("✓ Notation with dot '11.H' validated")

    # Notation with 'q' qualifier
    notation = IconclassNotation(notation="11Hq")
    assert notation.notation == "11Hq"
    assert "11H" in notation.parts
    assert "11Hq" in notation.parts
    print("✓ Notation with 'q' qualifier '11Hq' validated")


def test_validate_function() -> None:
    """Test the standalone validation function"""
    print("\nTesting validation function...")

    result = validate_iconclass_notation("11H")
    assert result.notation == "11H"
    assert isinstance(result, IconclassNotation)
    print("✓ Validation function works correctly")


def test_real_world_examples() -> None:
    """Test with real-world Iconclass codes from the vocabulary"""
    print("\nTesting real-world examples...")

    # Examples from the vocabularies.json file
    examples = [
        "11A",  # Gottheit, Gott
        "11B",  # Heilige Dreifaltigkeit
        "11C",  # Gottvater
        "11D",  # Christus
        "11E",  # der Heilige Geist
        "11F",  # die Jungfrau Maria
        "11G",  # Engel
        "11H",  # Heilige
        "11I",  # Propheten, Sibyllen
        "25F23",  # Example complex code
    ]

    for example in examples:
        notation = IconclassNotation(notation=example)
        assert notation.notation == example
        print(f"✓ Real-world example '{example}' validated")


def test_parts_generation() -> None:
    """Test that parts are correctly generated"""
    print("\nTesting parts generation...")

    notation = IconclassNotation(notation="11H")
    expected_parts = ["1", "11", "11H"]
    assert notation.parts == expected_parts, (
        f"Expected {expected_parts}, got {notation.parts}"
    )
    print(f"✓ Parts for '11H': {notation.parts}")

    notation = IconclassNotation(notation="25F")
    assert "2" in notation.parts
    assert "25" in notation.parts
    assert "25F" in notation.parts
    print(f"✓ Parts for '25F': {notation.parts}")

    notation = IconclassNotation(notation="11H(JEROME)")
    assert "11H" in notation.parts
    assert "11H(...)" in notation.parts
    assert "11H(JEROME)" in notation.parts
    print(f"✓ Parts for '11H(JEROME)': {notation.parts}")


if __name__ == "__main__":
    test_basic_notation()
    test_notation_with_parentheses()
    test_notation_with_plus_additions()
    test_complex_notation()
    test_invalid_notation()
    test_edge_cases()
    test_validate_function()
    test_real_world_examples()
    test_parts_generation()
    print("\n✓ All Iconclass tests completed successfully")
