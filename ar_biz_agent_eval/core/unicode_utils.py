import re
import unicodedata
from typing import Any

# Arabic Diacritics (Tashkeel) Unicode range
ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED]")

# Arabic Tatweel / Kashida
ARABIC_TATWEEL = re.compile(r"\u0640")

# Unicode Bidirectional Control Characters (LRM, RLM, LRE, RLE, PDF, LRO, RLO, LRI, RLI, FSI, PDI)
BIDI_CONTROLS = re.compile(r"[\u200E\u200F\u202A-\u202E\u2066-\u2069]")

# Eastern Arabic-Indic Digits to ASCII Western Digits mapping
EASTERN_TO_WESTERN_DIGITS = {
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9",
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
}

# Western Digits to Eastern Arabic-Indic Digits mapping
WESTERN_TO_EASTERN_DIGITS = {
    "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤",
    "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩",
}


def strip_tashkeel(text: str) -> str:
    """Strips all Arabic diacritical marks (Tashkeel / Harakat)."""
    if not text:
        return ""
    return ARABIC_DIACRITICS.sub("", text)


def strip_tatweel(text: str) -> str:
    """Strips Arabic Tatweel (Kashida) character used for typographic justification."""
    if not text:
        return ""
    return ARABIC_TATWEEL.sub("", text)


def strip_bidi_controls(text: str) -> str:
    """Strips invisible Unicode bidirectional formatting markers."""
    if not text:
        return ""
    return BIDI_CONTROLS.sub("", text)


def convert_arabic_digits(text: str) -> str:
    """Converts Eastern Arabic-Indic digits (٠-٩) and Persian digits (۰-۹) to ASCII digits (0-9)."""
    if not text:
        return ""
    return "".join(EASTERN_TO_WESTERN_DIGITS.get(ch, ch) for ch in text)


def convert_to_eastern_digits(text: str) -> str:
    """Converts standard ASCII digits (0-9) to Eastern Arabic-Indic digits (٠-٩)."""
    if not text:
        return ""
    return "".join(WESTERN_TO_EASTERN_DIGITS.get(ch, ch) for ch in text)


def normalize_arabic(
    text: str,
    strip_diacritics: bool = True,
    normalize_alef: bool = True,
    normalize_taa_marbuta: bool = True,
    normalize_yaa: bool = True,
    convert_digits: bool = True,
    strip_kashida: bool = True,
    strip_bidi: bool = True,
) -> str:
    """Comprehensive Arabic orthographic normalization.
    
    Standardizes:
      - Alef variants (أ, إ, آ, ٱ -> ا)
      - Taa Marbuta (ة -> ه)
      - Yaa / Alef Maqsura (ى -> ي)
      - Tashkeel removal
      - Tatweel removal
      - Digit normalization
      - Bidi controls removal
      - Unicode NFKC decomposition
    """
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)

    if strip_bidi:
        normalized = strip_bidi_controls(normalized)

    if strip_kashida:
        normalized = strip_tatweel(normalized)

    if strip_diacritics:
        normalized = strip_tashkeel(normalized)

    if normalize_alef:
        normalized = re.sub(r"[إأآٱ]", "ا", normalized)

    if normalize_taa_marbuta:
        normalized = re.sub(r"ة", "ه", normalized)

    if normalize_yaa:
        normalized = re.sub(r"ى", "ي", normalized)

    if convert_digits:
        normalized = convert_arabic_digits(normalized)

    # Normalize multiple whitespace characters
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def clean_for_comparison(text: str) -> str:
    """Deep canonicalization for linguistic evaluation and exact/fuzzy parameter matching."""
    if not isinstance(text, str):
        text = str(text)
    normalized = normalize_arabic(
        text,
        strip_diacritics=True,
        normalize_alef=True,
        normalize_taa_marbuta=True,
        normalize_yaa=True,
        convert_digits=True,
        strip_kashida=True,
        strip_bidi=True,
    )
    return normalized.lower().strip()


def contains_arabic(text: str) -> bool:
    """Checks whether the string contains any Arabic characters."""
    if not text:
        return False
    return bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", text))


def is_code_switched(text: str) -> bool:
    """Determines if the text contains code-switching between Arabic and Latin/English."""
    if not text:
        return False
    has_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
    has_latin = bool(re.search(r"[A-Za-z]", text))
    return has_arabic and has_latin
