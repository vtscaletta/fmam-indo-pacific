"""Слой интерфейса. Словарь строк и визуальная тема."""

from ui.i18n import t, STRINGS, LANGUAGES
from ui.theme import PALETTE, FONTS, regime_color, build_css, REGIME_COLORS

__all__ = ["t", "STRINGS", "LANGUAGES", "PALETTE", "FONTS",
           "regime_color", "build_css", "REGIME_COLORS"]
