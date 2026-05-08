import pytest
from flux.plugins.quran.plugin import _smart_truncate, _truncate_for_x

def test_smart_truncate():
    # Less than max_len
    assert _smart_truncate("Hello world", 20) == "Hello world"
    
    # Truncate exactly at word boundary
    res = _smart_truncate("This is a long sentence that needs truncating", 25)
    assert res == "This is a long..."
    assert len(res) <= 28 # (25 + 3 for ellipsis, but function aims for max_len total. Wait, limit is max_len - 3)
    
def test_smart_truncate_length():
    text = "This is a very long sentence that keeps going and going and going."
    res = _smart_truncate(text, 30)
    assert len(res) <= 30
    assert res.endswith("...")
    assert res == "This is a very long..."

def test_truncate_for_x():
    # If short enough, leave as is
    short = "Hello X!"
    assert _truncate_for_x(short, 280) == short

    # If too long, drop Arabic first
    arabic = "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ\n" * 10
    english = "In the name of Allah, the entirely merciful, the especially merciful."
    combined = f"{arabic}\n{english}"
    
    # Normally this would be > 280 if it was longer, let's make it explicitly long
    long_combined = (arabic * 10) + "\n" + (english * 10)
    assert len(long_combined) > 280
    
    truncated = _truncate_for_x(long_combined, 280)
    assert len(truncated) <= 280
    # Should contain english but no arabic
    assert "Allah" in truncated
    assert "بِسْمِ" not in truncated

def test_truncate_for_x_all_english():
    # If it's all English but too long, smart truncate
    long_english = "word " * 100
    assert len(long_english) > 280
    
    truncated = _truncate_for_x(long_english, 280)
    assert len(truncated) <= 280
    assert truncated.endswith("...")
