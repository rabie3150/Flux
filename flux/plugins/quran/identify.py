"""Quran verse identification from video metadata.

Extracts surah:ayah references from video titles using regex patterns.
Supports Arabic, English, and transliterated surah names.
"""

from __future__ import annotations

import json
import re
from typing import Any

from flux.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Surah name mappings
# ---------------------------------------------------------------------------

# fmt: off
_SURAHS: list[dict[str, Any]] = [
    {"n": 1, "en": "Al-Fatihah", "ar": "الفاتحة", "tr": ["alfatihah", "alfatiha", "al-fatiha", "fatiha", "fatihah", "the opener"]},
    {"n": 2, "en": "Al-Baqarah", "ar": "البقرة", "tr": ["albaqarah", "al-baqarah", "baqarah", "the cow"]},
    {"n": 3, "en": "Aal-E-Imran", "ar": "آل عمران", "tr": ["aalimran", "aal-e-imran", "al-imran", "aleimran", "family of imran"]},
    {"n": 4, "en": "An-Nisa", "ar": "النساء", "tr": ["annisa", "an-nisa", "nisa", "the women"]},
    {"n": 5, "en": "Al-Ma'idah", "ar": "المائدة", "tr": ["almaidah", "al-ma'idah", "almaida", "maidah", "the table spread"]},
    {"n": 6, "en": "Al-An'am", "ar": "الأنعام", "tr": ["alanam", "al-an'am", "anam", "the cattle"]},
    {"n": 7, "en": "Al-A'raf", "ar": "الأعراف", "tr": ["alaraf", "al-a'raf", "araf", "the heights"]},
    {"n": 8, "en": "Al-Anfal", "ar": "الأنفال", "tr": ["alanfal", "al-anfal", "anfal", "the spoils of war"]},
    {"n": 9, "en": "At-Tawbah", "ar": "التوبة", "tr": ["attawbah", "at-tawbah", "tawbah", "the repentance"]},
    {"n": 10, "en": "Yunus", "ar": "يونس", "tr": ["yunus", "jonah"]},
    {"n": 11, "en": "Hud", "ar": "هود", "tr": ["hud"]},
    {"n": 12, "en": "Yusuf", "ar": "يوسف", "tr": ["yusuf", "joseph"]},
    {"n": 13, "en": "Ar-Ra'd", "ar": "الرعد", "tr": ["arRad", "ar-ra'd", "rad", "the thunder"]},
    {"n": 14, "en": "Ibrahim", "ar": "إبراهيم", "tr": ["ibrahim", "abraham"]},
    {"n": 15, "en": "Al-Hijr", "ar": "الحجر", "tr": ["alhijr", "al-hijr", "hijr", "the rocky tract"]},
    {"n": 16, "en": "An-Nahl", "ar": "النحل", "tr": ["annahal", "an-nahl", "nahl", "the bee"]},
    {"n": 17, "en": "Al-Isra", "ar": "الإسراء", "tr": ["alisra", "al-isra", "isra", "the night journey"]},
    {"n": 18, "en": "Al-Kahf", "ar": "الكهف", "tr": ["alkahf", "al-kahf", "kahf", "the cave"]},
    {"n": 19, "en": "Maryam", "ar": "مريم", "tr": ["maryam", "mary"]},
    {"n": 20, "en": "Ta-Ha", "ar": "طه", "tr": ["taha", "ta-ha"]},
    {"n": 21, "en": "Al-Anbiya", "ar": "الأنبياء", "tr": ["alanbiya", "al-anbiya", "anbiya", "the prophets"]},
    {"n": 22, "en": "Al-Hajj", "ar": "الحج", "tr": ["alhajj", "al-hajj", "hajj", "the pilgrimage"]},
    {"n": 23, "en": "Al-Mu'minun", "ar": "المؤمنون", "tr": ["almuminun", "al-mu'minun", "muminun", "the believers"]},
    {"n": 24, "en": "An-Nur", "ar": "النور", "tr": ["annur", "an-nur", "nur", "the light"]},
    {"n": 25, "en": "Al-Furqan", "ar": "الفرقان", "tr": ["alfurqan", "al-furqan", "furqan", "the criterion"]},
    {"n": 26, "en": "Ash-Shu'ara", "ar": "الشعراء", "tr": ["ashshura", "ash-shu'ara", "shura", "the poets"]},
    {"n": 27, "en": "An-Naml", "ar": "النمل", "tr": ["annaml", "an-naml", "naml", "the ant"]},
    {"n": 28, "en": "Al-Qasas", "ar": "القصص", "tr": ["alqasas", "al-qasas", "qasas", "the stories"]},
    {"n": 29, "en": "Al-Ankabut", "ar": "العنكبوت", "tr": ["alankabut", "al-ankabut", "ankabut", "the spider"]},
    {"n": 30, "en": "Ar-Rum", "ar": "الروم", "tr": ["arrum", "ar-rum", "rum", "the romans"]},
    {"n": 31, "en": "Luqman", "ar": "لقمان", "tr": ["luqman"]},
    {"n": 32, "en": "As-Sajda", "ar": "السجدة", "tr": ["assajda", "as-sajda", "sajda", "the prostration"]},
    {"n": 33, "en": "Al-Ahzab", "ar": "الأحزاب", "tr": ["alahzab", "al-ahzab", "ahzab", "the combined forces"]},
    {"n": 34, "en": "Saba", "ar": "سبأ", "tr": ["saba", "sheba"]},
    {"n": 35, "en": "Fatir", "ar": "فاطر", "tr": ["fatir", "the originator"]},
    {"n": 36, "en": "Ya-Sin", "ar": "يس", "tr": ["yasin", "ya-sin", "yaseen"]},
    {"n": 37, "en": "As-Saffat", "ar": "الصافات", "tr": ["assaffat", "as-saffat", "saffat", "those who set the ranks"]},
    {"n": 38, "en": "Sad", "ar": "ص", "tr": ["sad"]},
    {"n": 39, "en": "Az-Zumar", "ar": "الزمر", "tr": ["azzumar", "az-zumar", "zumar", "the troops"]},
    {"n": 40, "en": "Ghafir", "ar": "غافر", "tr": ["ghafir", "the forgiver"]},
    {"n": 41, "en": "Fussilat", "ar": "فصلت", "tr": ["fussilat", "explained in detail"]},
    {"n": 42, "en": "Ash-Shura", "ar": "الشورى", "tr": ["ashshura", "ash-shura", "shura", "the consultation"]},
    {"n": 43, "en": "Az-Zukhruf", "ar": "الزخرف", "tr": ["azzukhruf", "az-zukhruf", "zukhruf", "the ornaments of gold"]},
    {"n": 44, "en": "Ad-Dukhan", "ar": "الدخان", "tr": ["addukhan", "ad-dukhan", "dukhan", "the smoke"]},
    {"n": 45, "en": "Al-Jathiyah", "ar": "الجاثية", "tr": ["aljathiyah", "al-jathiyah", "jathiyah", "the crouching"]},
    {"n": 46, "en": "Al-Ahqaf", "ar": "الأحقاف", "tr": ["alahqaf", "al-ahqaf", "ahqaf", "the wind-curved sandhills"]},
    {"n": 47, "en": "Muhammad", "ar": "محمد", "tr": ["muhammad"]},
    {"n": 48, "en": "Al-Fath", "ar": "الفتح", "tr": ["alfath", "al-fath", "fath", "the victory"]},
    {"n": 49, "en": "Al-Hujurat", "ar": "الحجرات", "tr": ["alhujurat", "al-hujurat", "hujurat", "the rooms"]},
    {"n": 50, "en": "Qaf", "ar": "ق", "tr": ["qaf"]},
    {"n": 51, "en": "Adh-Dhariyat", "ar": "الذاريات", "tr": ["adhdhariyat", "adh-dhariyat", "dhariyat", "the winnowing winds"]},
    {"n": 52, "en": "At-Tur", "ar": "الطور", "tr": ["attur", "at-tur", "tur", "the mount"]},
    {"n": 53, "en": "An-Najm", "ar": "النجم", "tr": ["annajm", "an-najm", "najm", "the star"]},
    {"n": 54, "en": "Al-Qamar", "ar": "القمر", "tr": ["alqamar", "al-qamar", "qamar", "the moon"]},
    {"n": 55, "en": "Ar-Rahman", "ar": "الرحمن", "tr": ["arraHman", "ar-rahman", "rahman", "the beneficent"]},
    {"n": 56, "en": "Al-Waqi'a", "ar": "الواقعة", "tr": ["alwaqia", "al-waqi'a", "waqia", "the inevitable"]},
    {"n": 57, "en": "Al-Hadid", "ar": "الحديد", "tr": ["alhadid", "al-hadid", "hadid", "the iron"]},
    {"n": 58, "en": "Al-Mujadila", "ar": "المجادلة", "tr": ["almujadila", "al-mujadila", "mujadila", "the pleading woman"]},
    {"n": 59, "en": "Al-Hashr", "ar": "الحشر", "tr": ["alhashr", "al-hashr", "hashr", "the exile"]},
    {"n": 60, "en": "Al-Mumtahanah", "ar": "الممتحنة", "tr": ["almumtahanah", "al-mumtahanah", "mumtahanah", "she that is to be examined"]},
    {"n": 61, "en": "As-Saff", "ar": "الصف", "tr": ["assaff", "as-saff", "saff", "the ranks"]},
    {"n": 62, "en": "Al-Jumu'ah", "ar": "الجمعة", "tr": ["aljumuah", "al-jumu'ah", "jumuah", "the congregation"]},
    {"n": 63, "en": "Al-Munafiqun", "ar": "المنافقون", "tr": ["almunafiqun", "al-munafiqun", "munafiqun", "the hypocrites"]},
    {"n": 64, "en": "At-Taghabun", "ar": "التغابن", "tr": ["attaghabun", "at-taghabun", "taghabun", "the mutual loss"]},
    {"n": 65, "en": "At-Talaq", "ar": "الطلاق", "tr": ["attalaq", "at-talaq", "talaq", "the divorce"]},
    {"n": 66, "en": "At-Tahrim", "ar": "التحريم", "tr": ["attahrim", "at-tahrim", "tahrim", "the prohibition"]},
    {"n": 67, "en": "Al-Mulk", "ar": "الملك", "tr": ["almulk", "al-mulk", "mulk", "the sovereignty"]},
    {"n": 68, "en": "Al-Qalam", "ar": "القلم", "tr": ["alqalam", "al-qalam", "qalam", "the pen"]},
    {"n": 69, "en": "Al-Haqqah", "ar": "الحاقة", "tr": ["alhaqqah", "al-haqqah", "haqqah", "the reality"]},
    {"n": 70, "en": "Al-Ma'arij", "ar": "المعارج", "tr": ["almaarij", "al-ma'arij", "maarij", "the ascending stairways"]},
    {"n": 71, "en": "Nuh", "ar": "نوح", "tr": ["nuh", "noah"]},
    {"n": 72, "en": "Al-Jinn", "ar": "الجن", "tr": ["aljinn", "al-jinn", "jinn"]},
    {"n": 73, "en": "Al-Muzzammil", "ar": "المزمل", "tr": ["almuzzammil", "al-muzzammil", "muzzammil", "the enshrouded one"]},
    {"n": 74, "en": "Al-Muddaththir", "ar": "المدثر", "tr": ["almuddaththir", "al-muddaththir", "muddaththir", "the cloaked one"]},
    {"n": 75, "en": "Al-Qiyamah", "ar": "القيامة", "tr": ["alqiyamah", "al-qiyamah", "qiyamah", "the resurrection"]},
    {"n": 76, "en": "Al-Insan", "ar": "الإنسان", "tr": ["alinsan", "al-insan", "insan", "man"]},
    {"n": 77, "en": "Al-Mursalat", "ar": "المرسلات", "tr": ["almursalat", "al-mursalat", "mursalat", "the emissaries"]},
    {"n": 78, "en": "An-Naba", "ar": "النبأ", "tr": ["annaba", "an-naba", "naba", "the tidings"]},
    {"n": 79, "en": "An-Nazi'at", "ar": "النازعات", "tr": ["annaziat", "an-nazi'at", "naziat", "those who drag forth"]},
    {"n": 80, "en": "'Abasa", "ar": "عبس", "tr": ["abasa", "he frowned"]},
    {"n": 81, "en": "At-Takwir", "ar": "التكوير", "tr": ["attakwir", "at-takwir", "takwir", "the overthrowing"]},
    {"n": 82, "en": "Al-Infitar", "ar": "الإنفطار", "tr": ["alinfitar", "al-infitar", "infitar", "the cleaving"]},
    {"n": 83, "en": "Al-Mutaffifin", "ar": "المطففين", "tr": ["almutaffifin", "al-mutaffifin", "mutaffifin", "the defrauding"]},
    {"n": 84, "en": "Al-Inshiqaq", "ar": "الإنشقاق", "tr": ["alinshiqaq", "al-inshiqaq", "inshiqaq", "the sundering"]},
    {"n": 85, "en": "Al-Buruj", "ar": "البروج", "tr": ["alburuj", "al-buruj", "buruj", "the mansions of the stars"]},
    {"n": 86, "en": "At-Tariq", "ar": "الطارق", "tr": ["attariq", "at-tariq", "tariq", "the nightcomer"]},
    {"n": 87, "en": "Al-A'la", "ar": "الأعلى", "tr": ["alala", "al-a'la", "ala", "the most high"]},
    {"n": 88, "en": "Al-Ghashiyah", "ar": "الغاشية", "tr": ["alghashiyah", "al-ghashiyah", "ghashiyah", "the overwhelming"]},
    {"n": 89, "en": "Al-Fajr", "ar": "الفجر", "tr": ["alfajr", "al-fajr", "fajr", "the dawn"]},
    {"n": 90, "en": "Al-Balad", "ar": "البلد", "tr": ["albalad", "al-balad", "balad", "the city"]},
    {"n": 91, "en": "Ash-Shams", "ar": "الشمس", "tr": ["ashshams", "ash-shams", "shams", "the sun"]},
    {"n": 92, "en": "Al-Layl", "ar": "الليل", "tr": ["allayl", "al-layl", "layl", "the night"]},
    {"n": 93, "en": "Ad-Duhaa", "ar": "الضحى", "tr": ["adduhaa", "ad-duhaa", "duhaa", "the morning hours"]},
    {"n": 94, "en": "Ash-Sharh", "ar": "الشرح", "tr": ["ashsharh", "ash-sharh", "sharh", "the relief"]},
    {"n": 95, "en": "At-Tin", "ar": "التين", "tr": ["attin", "at-tin", "tin", "the fig"]},
    {"n": 96, "en": "Al-'Alaq", "ar": "العلق", "tr": ["alalaq", "al-'alaq", "alaq", "the clot"]},
    {"n": 97, "en": "Al-Qadr", "ar": "القدر", "tr": ["alqadr", "al-qadr", "qadr", "the power"]},
    {"n": 98, "en": "Al-Bayyinah", "ar": "البينة", "tr": ["albayyinah", "al-bayyinah", "bayyinah", "the clear proof"]},
    {"n": 99, "en": "Az-Zalzalah", "ar": "الزلزلة", "tr": ["azzalzalah", "az-zalzalah", "zalzalah", "the earthquake"]},
    {"n": 100, "en": "Al-'Adiyat", "ar": "العاديات", "tr": ["aladiyat", "al-'adiyat", "adiyat", "the courser"]},
    {"n": 101, "en": "Al-Qari'ah", "ar": "القارعة", "tr": ["alqariah", "al-qari'ah", "qariah", "the calamity"]},
    {"n": 102, "en": "At-Takathur", "ar": "التكاثر", "tr": ["attakathur", "at-takathur", "takathur", "the rivalry in world increase"]},
    {"n": 103, "en": "Al-'Asr", "ar": "العصر", "tr": ["alasr", "al-'asr", "asr", "the declining day"]},
    {"n": 104, "en": "Al-Humazah", "ar": "الهمزة", "tr": ["alhumazah", "al-humazah", "humazah", "the traducer"]},
    {"n": 105, "en": "Al-Fil", "ar": "الفيل", "tr": ["alfil", "al-fil", "fil", "the elephant"]},
    {"n": 106, "en": "Quraysh", "ar": "قريش", "tr": ["quraysh", "quraish", "quraish"]},
    {"n": 107, "en": "Al-Ma'un", "ar": "الماعون", "tr": ["almaun", "al-ma'un", "maun", "the small kindnesses"]},
    {"n": 108, "en": "Al-Kawthar", "ar": "الكوثر", "tr": ["alkawthar", "al-kawthar", "kawthar", "the abundance"]},
    {"n": 109, "en": "Al-Kafirun", "ar": "الكافرون", "tr": ["alkafirun", "al-kafirun", "kafirun", "the disbelievers"]},
    {"n": 110, "en": "An-Nasr", "ar": "النصر", "tr": ["annasr", "an-nasr", "nasr", "the divine support"]},
    {"n": 111, "en": "Al-Masad", "ar": "المسد", "tr": ["almasad", "al-masad", "masad", "the palm fibre"]},
    {"n": 112, "en": "Al-Ikhlas", "ar": "الإخلاص", "tr": ["alikhlas", "al-ikhlas", "ikhlas", "the sincerity"]},
    {"n": 113, "en": "Al-Falaq", "ar": "الفلق", "tr": ["alfalaq", "al-falaq", "falaq", "the daybreak"]},
    {"n": 114, "en": "An-Nas", "ar": "الناس", "tr": ["annas", "an-nas", "nas", "mankind"]},
]
# fmt: on


# Build lookup indexes
_SURAH_BY_EN: dict[str, int] = {}
_SURAH_BY_AR: dict[str, int] = {}
_SURAH_BY_TR: dict[str, int] = {}
_SURAH_NAMES: dict[int, dict[str, Any]] = {}

for s in _SURAHS:
    num = s["n"]
    _SURAH_NAMES[num] = s
    _SURAH_BY_EN[s["en"].lower()] = num
    _SURAH_BY_AR[s["ar"]] = num
    for t in s["tr"]:
        _SURAH_BY_TR[t.lower()] = num


def _normalize_arabic(text: str) -> str:
    """Remove tashkeel and normalize Arabic chars."""
    # Remove common diacritics
    tashkeel = "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652\u0653\u0670"
    for ch in tashkeel:
        text = text.replace(ch, "")
    # Normalize alef variants
    text = text.replace("\u0623", "\u0627").replace("\u0625", "\u0627").replace("\u0622", "\u0627")
    return text


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Numeric pattern: "2:255", "Surah 2 Verse 255", "Chapter 2 : 255", etc.
_NUMERIC_RE = re.compile(
    r"(?:surah|chapter|sura|سورة)?\s*"  # optional surah prefix
    r"(\d{1,3})\s*[:\-\.،]\s*(\d{1,3})",  # surah:ayah
    re.IGNORECASE | re.UNICODE,
)

# Named pattern: "Al-Baqarah 255", "Surah Al-Baqarah Ayah 255", etc.
# We build this dynamically from surah names since the list is long.
_EN_NAME_PATTERN = "|".join(
    re.escape(name) for name in sorted(_SURAH_BY_EN.keys(), key=len, reverse=True)
)
_AR_NAME_PATTERN = "|".join(
    re.escape(name) for name in sorted(_SURAH_BY_AR.keys(), key=len, reverse=True)
)

_NAMED_RE = re.compile(
    r"(?:surah|chapter|sura|سورة)?\s*"
    r"(?:(" + _EN_NAME_PATTERN + r")|(" + _AR_NAME_PATTERN + r"))"
    r"\s*(?:verse|ayah|آية)?\s*[:\-\.\s]*"
    r"(\d{1,3})",
    re.IGNORECASE | re.UNICODE,
)

# Standalone numeric: just "2:255" at word boundary
_STANDALONE_RE = re.compile(
    r"\b(\d{1,3})\s*[:\-\.]\s*(\d{1,3})\b",
    re.UNICODE,
)


def _resolve_surah_number(name: str | None) -> int | None:
    """Resolve a surah name (English, Arabic, or transliterated) to its number."""
    if not name:
        return None
    key = name.strip().lower()
    # Direct English match
    if key in _SURAH_BY_EN:
        return _SURAH_BY_EN[key]
    # Transliterated match
    if key in _SURAH_BY_TR:
        return _SURAH_BY_TR[key]
    # Arabic match (normalized)
    normalized = _normalize_arabic(key)
    if normalized in _SURAH_BY_AR:
        return _SURAH_BY_AR[normalized]
    return None


def _validate_verse(surah: int, ayah: int) -> bool:
    """Validate that surah:ayah exists.

    Uses known verse counts per surah (simplified full list).
    """
    # Verse counts for all 114 surahs
    verse_counts = [
        7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99,
        128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34,
        30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29,
        18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12,
        12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19,
        36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
        11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
    ]
    if 1 <= surah <= 114:
        return 1 <= ayah <= verse_counts[surah - 1]
    return False


def identify_from_title(title: str) -> dict[str, Any] | None:
    """Extract surah:ayah from a video title.

    Returns {"surah": int, "ayah": int, "verse_key": str, "method": str}
    or None if no match found.
    """
    if not title or not title.strip():
        return None

    text = title.strip()

    # Try named pattern first (higher confidence)
    for match in _NAMED_RE.finditer(text):
        en_name = match.group(1)
        ar_name = match.group(2)
        ayah_str = match.group(3)
        surah = _resolve_surah_number(en_name or ar_name)
        if surah and ayah_str:
            ayah = int(ayah_str)
            if _validate_verse(surah, ayah):
                return {
                    "surah": surah,
                    "ayah": ayah,
                    "verse_key": f"{surah}:{ayah}",
                    "method": "named_pattern",
                    "matched_text": match.group(0),
                }

    # Try numeric pattern with optional surah prefix
    for match in _NUMERIC_RE.finditer(text):
        surah = int(match.group(1))
        ayah = int(match.group(2))
        if _validate_verse(surah, ayah):
            return {
                "surah": surah,
                "ayah": ayah,
                "verse_key": f"{surah}:{ayah}",
                "method": "numeric_pattern",
                "matched_text": match.group(0),
            }

    # Try standalone numeric (word boundary)
    for match in _STANDALONE_RE.finditer(text):
        surah = int(match.group(1))
        ayah = int(match.group(2))
        if _validate_verse(surah, ayah):
            return {
                "surah": surah,
                "ayah": ayah,
                "verse_key": f"{surah}:{ayah}",
                "method": "standalone_numeric",
                "matched_text": match.group(0),
            }

    return None


def identify_from_metadata(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Try to identify verse from ingredient metadata.

    Checks title, description, and any other text fields.
    """
    # Primary source: title
    title = metadata.get("title", "")
    result = identify_from_title(title)
    if result:
        return result

    # Fallback: description if present
    description = metadata.get("description", "")
    if description:
        result = identify_from_title(description)
        if result:
            return result

    return None
