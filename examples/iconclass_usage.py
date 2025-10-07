"""Example usage of Iconclass validator

This example demonstrates how to use the Iconclass validator in the
sgb-data-validator package.
"""

from pathlib import Path

from pydantic import ValidationError

from src.iconclass import IconclassNotation, validate_iconclass_notation
from src.vocabularies import VocabularyLoader


def example_basic_validation() -> None:
    """Example: Basic format validation"""
    print("=" * 60)
    print("Example 1: Basic Format Validation")
    print("=" * 60)

    # Validate notation format
    try:
        notation = IconclassNotation(notation="11H")
        print(f"✓ Notation '{notation.notation}' is valid")
        print(f"  Parts: {notation.parts}")
    except ValidationError as e:
        print(f"✗ Validation error: {e}")

    # Try invalid notation
    try:
        notation = IconclassNotation(notation="11H@INVALID")
        print(f"✗ Should have failed: {notation.notation}")
    except ValidationError:
        print("✓ Correctly rejected invalid notation '11H@INVALID'")


def example_complex_notation() -> None:
    """Example: Complex notation with qualifiers"""
    print("\n" + "=" * 60)
    print("Example 2: Complex Notation with Qualifiers")
    print("=" * 60)

    complex_codes = [
        "11H(JEROME)",  # Parenthetical qualifier
        "11H(+3)",  # Plus addition
        "25F23(DOG)",  # Animal qualifier
        "11H(JEROME)(+3)",  # Multiple qualifiers
    ]

    for code in complex_codes:
        notation = IconclassNotation(notation=code)
        print(f"\nNotation: {notation.notation}")
        print(f"Parts: {notation.parts}")


def example_vocabulary_validation() -> None:
    """Example: Validation against vocabulary"""
    print("\n" + "=" * 60)
    print("Example 3: Validation Against Vocabulary")
    print("=" * 60)

    vocab_file = Path("data/raw/vocabularies.json")
    loader = VocabularyLoader(vocab_file)

    test_codes = [
        ("11H", "Heilige (Saints)"),
        ("11A", "Gottheit, Gott"),
        ("11H(JEROME)", "Saint Jerome"),
        ("ZZZ999", "Non-existent code"),
    ]

    for code, description in test_codes:
        is_valid = loader.is_valid_iconclass(code)
        status = "✓ VALID" if is_valid else "✗ INVALID"
        print(f"{status}: {code} - {description}")


def example_helper_function() -> None:
    """Example: Using the helper function"""
    print("\n" + "=" * 60)
    print("Example 4: Using Helper Function")
    print("=" * 60)

    code = "11H"
    result = validate_iconclass_notation(code)
    print(f"Validated: {result.notation}")
    print(f"Parts: {result.parts}")


def example_parts_splitting() -> None:
    """Example: Understanding hierarchical parts"""
    print("\n" + "=" * 60)
    print("Example 5: Hierarchical Parts Splitting")
    print("=" * 60)

    notation = IconclassNotation(notation="25F23")
    print(f"Notation: {notation.notation}")
    print(f"Hierarchical structure:")
    for i, part in enumerate(notation.parts, 1):
        indent = "  " * (i - 1)
        print(f"{indent}Level {i}: {part}")

    print("\nWith qualifiers:")
    notation = IconclassNotation(notation="11H(JEROME)")
    print(f"Notation: {notation.notation}")
    for part in notation.parts:
        print(f"  - {part}")


if __name__ == "__main__":
    example_basic_validation()
    example_complex_notation()
    example_vocabulary_validation()
    example_helper_function()
    example_parts_splitting()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
