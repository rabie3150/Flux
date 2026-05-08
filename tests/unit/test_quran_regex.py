import pytest
from flux.plugins.quran.identify import identify_from_title, _validate_verse

def test_validate_verse():
    assert _validate_verse(2, 255) is True
    assert _validate_verse(2, 286) is True
    assert _validate_verse(2, 287) is False  # Baqarah only has 286
    assert _validate_verse(115, 1) is False  # 114 surahs
    assert _validate_verse(1, None) is True  # No ayah specified

def test_identify_from_title_common_phrases():
    res = identify_from_title("Beautiful recitation of Ayatul Kursi")
    assert res is not None
    assert res["surah"] == 2
    assert res["ayah"] == 255
    assert res["verse_key"] == "2:255"
    assert res["method"] == "common_phrase"

    res_ar = identify_from_title("تلاوة آية الكرسي")
    assert res_ar is not None
    assert res_ar["surah"] == 2
    assert res_ar["ayah"] == 255

def test_identify_from_title_numeric_pattern():
    res = identify_from_title("Quran Recitation Surah 2:255 HD")
    assert res is not None
    assert res["surah"] == 2
    assert res["ayah"] == 255

    res2 = identify_from_title("Sura 114 : 6")
    assert res2 is not None
    assert res2["surah"] == 114
    assert res2["ayah"] == 6

def test_identify_from_title_named_pattern_english():
    res = identify_from_title("Surah Al-Baqarah verse 255")
    assert res is not None
    assert res["surah"] == 2
    assert res["ayah"] == 255

    # Optional ayah
    res2 = identify_from_title("Recitation of Surah Yasin")
    assert res2 is not None
    assert res2["surah"] == 36
    assert res2["ayah"] is None
    assert res2["needs_ai"] is True

def test_identify_from_title_named_pattern_arabic():
    res = identify_from_title("سورة البقرة آية 255")
    assert res is not None
    assert res["surah"] == 2
    assert res["ayah"] == 255
    
    # Needs to handle normalization automatically
    res2 = identify_from_title("سوره البقره 255")
    assert res2 is not None
    assert res2["surah"] == 2
    assert res2["ayah"] == 255

def test_identify_from_title_standalone():
    res = identify_from_title("Amazing recitation 2:255")
    assert res is not None
    assert res["surah"] == 2
    assert res["ayah"] == 255

def test_identify_from_title_invalid():
    assert identify_from_title("Just a random video") is None
    assert identify_from_title("") is None
    assert identify_from_title("Surah 2:287") is None  # Invalid verse
