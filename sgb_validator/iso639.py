"""ISO 639-1 language code validation

This module provides validation for ISO 639-1 two-letter language codes
used in metadata fields like dcterms:language.
"""

# Complete list of ISO 639-1 two-letter language codes
# Source: https://www.loc.gov/standards/iso639-2/php/code_list.php
ISO_639_1_CODES = frozenset(
    [
        "aa",
        "ab",
        "ae",
        "af",
        "ak",
        "am",
        "an",
        "ar",
        "as",
        "av",
        "ay",
        "az",
        "ba",
        "be",
        "bg",
        "bh",
        "bi",
        "bm",
        "bn",
        "bo",
        "br",
        "bs",
        "ca",
        "ce",
        "ch",
        "co",
        "cr",
        "cs",
        "cu",
        "cv",
        "cy",
        "da",
        "de",
        "dv",
        "dz",
        "ee",
        "el",
        "en",
        "eo",
        "es",
        "et",
        "eu",
        "fa",
        "ff",
        "fi",
        "fj",
        "fo",
        "fr",
        "fy",
        "ga",
        "gd",
        "gl",
        "gn",
        "gu",
        "gv",
        "ha",
        "he",
        "hi",
        "ho",
        "hr",
        "ht",
        "hu",
        "hy",
        "hz",
        "ia",
        "id",
        "ie",
        "ig",
        "ii",
        "ik",
        "io",
        "is",
        "it",
        "iu",
        "ja",
        "jv",
        "ka",
        "kg",
        "ki",
        "kj",
        "kk",
        "kl",
        "km",
        "kn",
        "ko",
        "kr",
        "ks",
        "ku",
        "kv",
        "kw",
        "ky",
        "la",
        "lb",
        "lg",
        "li",
        "ln",
        "lo",
        "lt",
        "lu",
        "lv",
        "mg",
        "mh",
        "mi",
        "mk",
        "ml",
        "mn",
        "mr",
        "ms",
        "mt",
        "my",
        "na",
        "nb",
        "nd",
        "ne",
        "ng",
        "nl",
        "nn",
        "no",
        "nr",
        "nv",
        "ny",
        "oc",
        "oj",
        "om",
        "or",
        "os",
        "pa",
        "pi",
        "pl",
        "ps",
        "pt",
        "qu",
        "rm",
        "rn",
        "ro",
        "ru",
        "rw",
        "sa",
        "sc",
        "sd",
        "se",
        "sg",
        "si",
        "sk",
        "sl",
        "sm",
        "sn",
        "so",
        "sq",
        "sr",
        "ss",
        "st",
        "su",
        "sv",
        "sw",
        "ta",
        "te",
        "tg",
        "th",
        "ti",
        "tk",
        "tl",
        "tn",
        "to",
        "tr",
        "ts",
        "tt",
        "tw",
        "ty",
        "ug",
        "uk",
        "ur",
        "uz",
        "ve",
        "vi",
        "vo",
        "wa",
        "wo",
        "xh",
        "yi",
        "yo",
        "za",
        "zh",
        "zu",
    ]
)


def is_valid_iso639_1_code(code: str) -> bool:
    """Check if a string is a valid ISO 639-1 two-letter language code.

    Args:
        code: The language code to validate (case-insensitive)

    Returns:
        True if the code is a valid ISO 639-1 code, False otherwise

    Examples:
        >>> is_valid_iso639_1_code("en")
        True
        >>> is_valid_iso639_1_code("EN")
        True
        >>> is_valid_iso639_1_code("de")
        True
        >>> is_valid_iso639_1_code("invalid")
        False
        >>> is_valid_iso639_1_code("xyz")
        False
    """
    if not code or not isinstance(code, str):
        return False

    return code.lower() in ISO_639_1_CODES


def get_all_codes() -> frozenset[str]:
    """Get all valid ISO 639-1 language codes.

    Returns:
        Frozenset of all valid two-letter ISO 639-1 codes
    """
    return ISO_639_1_CODES
