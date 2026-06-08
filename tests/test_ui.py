"""Тесты слоя интерфейса. Запуск: pytest -v"""

from ui.i18n import t, tooltip, STRINGS, TOOLTIPS, LANGUAGES, DEFAULT_LANG
from ui.theme import (PALETTE, REGIME_COLORS, VERDICT_COLORS, FONTS,
                      regime_color, verdict_color, build_css, plotly_layout, _is_hex)


def test_all_strings_cover_all_languages():
    for key, entry in STRINGS.items():
        for lang in LANGUAGES:
            assert lang in entry and entry[lang], f"нет перевода {key} для {lang}"


def test_all_tooltips_cover_all_languages():
    for key, entry in TOOLTIPS.items():
        for lang in LANGUAGES:
            assert lang in entry and entry[lang], f"нет подсказки {key} для {lang}"


def test_translation_fallback():
    assert t("tab_overview", "ja") == STRINGS["tab_overview"][DEFAULT_LANG]
    assert t("no_such_key", "ru") == "no_such_key"


def test_palette_valid_hex():
    for name, value in PALETTE.items():
        assert _is_hex(value), f"{name} не цвет: {value}"


def test_regime_colors():
    assert set(REGIME_COLORS) == {"S1", "S2", "S3"}
    assert regime_color("S1") == PALETTE["s1"]
    assert regime_color("S3", soft=True) == PALETTE["s3_soft"]


def test_verdict_colors():
    assert set(VERDICT_COLORS) == {"green", "amber", "red"}
    assert verdict_color("red") == PALETTE["s3"]
    assert verdict_color("green", soft=True) == PALETTE["s1_soft"]


def test_regime_color_rejects_unknown():
    try:
        regime_color("S9")
    except ValueError:
        return
    raise AssertionError("не отвергнут неизвестный режим")


def test_css_light_theme():
    css = build_css()
    assert PALETTE["bg_page"] in css and PALETTE["text_primary"] in css
    assert "Inter" in css and "JetBrains+Mono" in css


def test_plotly_layout_light():
    lay = plotly_layout()
    assert lay["paper_bgcolor"] == PALETTE["bg_panel"]
    assert "colorway" in lay
