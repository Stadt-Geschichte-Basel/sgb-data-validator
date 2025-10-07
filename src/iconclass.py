"""Pydantic model and validators for Iconclass notation

This module provides validation for Iconclass notation codes used in cultural
heritage metadata. Iconclass is a hierarchical classification system for art
and iconography.
"""

import re
from typing import Any

from pydantic import BaseModel, field_validator


class IconclassNotation(BaseModel):
    """Model for validating Iconclass notation codes

    Iconclass notation uses a hierarchical structure with special characters:
    - Base notation: digits (0-9)
    - Extensions: uppercase letters (A-Z)
    - Special keys: parentheses for subdivisions like (+...)
    - Qualifiers: q for special qualifiers

    Examples:
        - "11H" - Valid base notation
        - "25F23(DOG)" - Valid with parenthetical qualifier
        - "11H(JEROME)(+3)" - Valid with multiple qualifiers
    """

    notation: str
    parts: list[str] = []

    @field_validator("notation")
    @classmethod
    def validate_notation_format(cls, v: str) -> str:
        """Validate that notation contains only allowed characters

        Args:
            v: The notation string to validate

        Returns:
            The validated notation string

        Raises:
            ValueError: If notation contains invalid characters
        """
        if not v or v.strip() == "":
            raise ValueError("Notation cannot be empty")

        # Allow digits, uppercase letters, 'q', parentheses, plus signs, spaces, and dots
        if not re.match(r"^[0-9A-Zq\(\)\+\s\.]*$", v):
            raise ValueError("Invalid characters in Iconclass notation")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Initialize parts after model validation

        This method is called after all field validators have run,
        ensuring the notation field is available.
        """
        if not self.notation:
            return

        # Pattern to split on parenthetical expressions
        splitter = re.compile(r"(\(.+?\))")
        parts = []
        last_part = ""

        for part in splitter.split(self.notation):
            if not part:
                continue

            # Handle (+X) style additions - each character after + is added incrementally
            if part.startswith("(+"):
                temp_last_part = last_part + "(+"
                for char in part[2:]:
                    if char and char != ")":
                        new_part = temp_last_part + char + ")"
                        parts.append(new_part)
                        temp_last_part += char
                if parts:
                    last_part = parts[-1]

            # Handle other parenthetical expressions
            elif part.startswith("(") and part.endswith(")"):
                # Add (...) placeholder if not already present
                if part != "(...)":
                    parts.append(last_part + "(...)")
                parts.append(last_part + part)
                last_part = parts[-1]

            # Handle base notation characters
            else:
                for i in range(len(part)):
                    new_part = last_part + part[i]
                    parts.append(new_part)
                    if parts:
                        last_part = parts[-1]

        self.parts = parts


def validate_iconclass_notation(notation: str) -> IconclassNotation:
    """Validate an Iconclass notation string

    Args:
        notation: The Iconclass notation to validate

    Returns:
        Validated IconclassNotation instance

    Raises:
        ValidationError: If notation is invalid
    """
    return IconclassNotation(notation=notation)
