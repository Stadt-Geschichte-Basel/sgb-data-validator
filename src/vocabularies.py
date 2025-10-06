"""Vocabulary loader for controlled vocabularies"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.iconclass import IconclassNotation


class VocabularyLoader:
    """Loads and manages controlled vocabularies"""

    def __init__(self, vocab_file: Path) -> None:
        with open(vocab_file, encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)

        self.eras: set[str] = set()
        self.mime_types: set[str] = set()
        self.licenses: set[str] = set()
        self.iconclass: set[str] = set()
        self.types: set[str] = set()
        self.languages: set[str] = set()

        for vocab in data:
            label = vocab.get("label", "")
            terms = vocab.get("terms", [])

            if "Epoche" in label:
                self.eras.update(terms)
            elif "Media Type" in label:
                self.mime_types.update(terms)
            elif "Licenses" in label:
                self.licenses.update(terms)
            elif "Iconclass" in label:
                # Extract just the code part before the pipe
                self.iconclass.update(term.split("|")[0] for term in terms)
            elif "Dublin Core Types" in label:
                self.types.update(terms)
            elif "Languages" in label:
                self.languages.update(terms)

    def is_valid_era(self, value: str) -> bool:
        """Check if value is a valid era"""
        return value in self.eras

    def is_valid_mime_type(self, value: str) -> bool:
        """Check if value is a valid MIME type"""
        return value in self.mime_types

    def is_valid_license(self, value: str) -> bool:
        """Check if value is a valid license URI"""
        return value in self.licenses

    def is_valid_iconclass(self, value: str) -> bool:
        """Check if value is a valid Iconclass code
        
        This method validates both the format and the content of the
        Iconclass notation. It first validates the notation format using
        the IconclassNotation pydantic model, then checks if any of the
        hierarchical parts match entries in the vocabulary.
        
        Args:
            value: The Iconclass code to validate
            
        Returns:
            True if the code is valid, False otherwise
        """
        # First validate the notation format
        try:
            notation = IconclassNotation(notation=value)
        except ValidationError:
            return False
        
        # Check if any part of the notation matches a valid code
        for part in notation.parts:
            if part in self.iconclass:
                return True
        
        # Also check if it starts with a valid code (for codes not in parts)
        for code in self.iconclass:
            if value.startswith(code):
                return True
        
        return False

    def is_valid_type(self, value: str) -> bool:
        """Check if value is a valid Dublin Core type URI"""
        return value in self.types

    def is_valid_language(self, value: str) -> bool:
        """Check if value is a valid language code"""
        return value in self.languages
