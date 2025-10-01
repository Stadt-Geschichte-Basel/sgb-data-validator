"""
SGB Data Validator - Main entry point

This script demonstrates the validator with sample data.
For actual validation, use validate.py
"""


def main() -> None:
    """Main entry point"""
    print("SGB Data Validator")
    print("==================")
    print()
    print("This package validates Omeka S data for the Stadt.Geschichte.Basel project.")
    print()
    print("To validate data from the Omeka S API, run:")
    print("  uv run python validate.py --help")
    print()
    print("Example usage:")
    print("  uv run python validate.py --item-set-id 10780 --output report.txt")
    print()


if __name__ == "__main__":
    main()
