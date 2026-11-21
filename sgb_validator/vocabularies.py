"""Vocabulary loader for controlled vocabularies"""

import json
from pathlib import Path
from typing import Any

DEFAULT_VOCABULARIES = Path(__file__).with_name("vocabularies.json")


class VocabularyLoader:
    """Loads and manages controlled vocabularies"""

    def __init__(self, vocab_file: Path = DEFAULT_VOCABULARIES) -> None:
        with open(vocab_file, encoding="utf-8") as f:
            data: list[dict[str, Any]] = json.load(f)

        self.eras: set[str] = set()
        self.mime_types: set[str] = set()
        self.licenses: set[str] = set()
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
            elif "Dublin Core Types" in label:
                self.types.update(terms)
            elif "Languages" in label:
                self.languages.update(t.casefold() for t in terms)

    def is_valid_era(self, value: str) -> bool:
        """Check if value is a valid era"""
        return value in self.eras

    def is_valid_mime_type(self, value: str) -> bool:
        """Check if value is a valid MIME type"""
        return value in self.mime_types

    def is_valid_license(self, value: str) -> bool:
        """Check if value is a valid license URI"""
        return value in self.licenses

    def is_valid_type(self, value: str) -> bool:
        """Check if value is a valid Dublin Core type URI"""
        return value in self.types

    def is_valid_language(self, value: str) -> bool:
        """Check if value is in the DSP language list (case-insensitive)"""
        return value.casefold() in self.languages
