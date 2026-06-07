"""
Тесты слоя интерфейса.

Запуск из корня проекта:
    pytest -v
"""

from ui.i18n import t, tooltip, STRINGS, TOOLTIPS, LANGUAGES, DEFAULT_LANG
from ui.theme import (
    PALETTE, REGIME_COLORS, FONTS, regime_color, build_css, _is_hex,
)


def test_all_strings_cover_all_languages():
    """Каждая строка переведена на все активные языки."""
    for key, entry in STRINGS.items():
        for lang in LANGUAGES:
            assert lang in entry and entry[lang], f"нет перевода {key} для {lang}"


def test_all_tooltips_cover_all_languages():
    """Каждая подсказка переведена на все активные языки."""
    for key, entry in TOOLTIPS.items():
        for lang in LANGUAGES:
            assert lang in entry and entry[lang], f"нет подсказки {key} для {lang}"


def test_translation_lookup():
    """Перевод возвращается на нужном языке."""
    assert t("tab_overview", "ru") == "Обзор"
    assert t("tab_overview", "en") == "Overview"


def test_translation_fallback_to_default():
    """Отсутствующий язык откатывается на язык по умолчанию."""
    assert t("tab_overview", "ja") == STRINGS["tab_overview"][DEFAULT_LANG]


def test_translation_fallback_to_key():
    """Неизвестный ключ возвращается как есть."""
    assert t("no_such_key", "ru") == "no_such_key"


def test_tooltip_lookup_and_empty():
    """Подсказка находится, отсутствующая даёт пустую строку."""
    assert tooltip("var_erosion", "ru")
    assert tooltip("no_such_tooltip") == ""


def test_regime_strings_present():
    """Все три режима имеют названия."""
    for code in ("S1", "S2", "S3"):
        assert t(f"regime_{code}", "ru")
        assert t(f"regime_{code}", "en")


def test_palette_is_valid_hex():
    """Все цвета палитры суть корректные шестнадцатеричные коды."""
    for name, value in PALETTE.items():
        assert _is_hex(value), f"{name} не цвет: {value}"


def test_regime_colors_cover_three_regimes():
    """Цвета заданы для всех трёх режимов, основной и свечение."""
    assert set(REGIME_COLORS) == {"S1", "S2", "S3"}
    for code in REGIME_COLORS:
        base, glow = REGIME_COLORS[code]
        assert _is_hex(base) and _is_hex(glow)


def test_regime_color_lookup():
    """Функция возвращает основной цвет и свечение."""
    assert regime_color("S1") == PALETTE["s1"]
    assert regime_color("S3", glow=True) == PALETTE["s3_glow"]


def test_regime_color_rejects_unknown():
    """Неизвестный режим отвергается."""
    try:
        regime_color("S9")
    except ValueError:
        return
    raise AssertionError("не отвергнут неизвестный режим")


def test_css_contains_variables_and_fonts():
    """CSS объявляет переменные палитры и подключает шрифты."""
    css = build_css()
    assert "--bg-base" in css and "--s1" in css and "--s3" in css
    assert "JetBrains+Mono" in css
    assert PALETTE["bg_base"] in css and PALETTE["s2"] in css


def test_fonts_declare_mono_and_sans():
    """Объявлены моноширинный и гротескный шрифты с кириллицей."""
    assert "JetBrains Mono" in FONTS["mono"]
    assert "Inter" in FONTS["sans"]
