from flux_lang.config import AppConfig, LANG_NAMES, load_config, save_config

def test_default_config_values():
    cfg = AppConfig()
    assert cfg.source_lang == "en"
    assert cfg.target_lang == "it"
    assert cfg.words_per_video == 5
    assert cfg.difficulty == "beginner"
    assert len(cfg.themes) > 0
    assert cfg.tts.provider == "edge_tts"
    assert cfg.style.progress_dots is True

def test_sentence_display_secs_default():
    cfg = AppConfig()
    assert cfg.timing.sentence_display_secs == 2.5

def test_lang_names():
    cfg = AppConfig(source_lang="en", target_lang="it")
    assert cfg.source_lang_name == "English"
    assert cfg.target_lang_name == "Italian"
    
    cfg2 = AppConfig(source_lang="xx", target_lang="yy")
    assert cfg2.source_lang_name == "XX"
    assert cfg2.target_lang_name == "YY"
