"""
Визуальная тема. Тёмная инженерная база и японская палитра 和色.

Замысел. Фон есть тёплый почти чёрный цвета туши суми, на котором данные
светятся, как на терминале аналитика. Смысловые цвета взяты из палитры
традиционных японских тонов, что связывает оформление с предметом
исследования и держит сдержанность, приглушённые тона вместо кричащих.

Цвет несёт состояние, а не украшает. Три режима системы кодируются цветом,
который считывается мгновенно, ещё до прочтения подписи. Зелёный вечнозелёный
для устойчивого баланса, янтарь для холодной конфронтации, багряный для
дестабилизации. Это логика светофора, опертая на доинтеллектуальное
восприятие.

Числа набраны моноширинным шрифтом с поддержкой кириллицы, цифры стоят строго
друг под другом, что даёт вид точного прибора. Текст набран гротеском.
Пустота между элементами намеренна, это значимый воздух ма, панель дышит.
"""

from __future__ import annotations


# Палитра. Ключи семантические, значения из японских традиционных тонов.
PALETTE = {
    # Фон и поверхности, тёплый сумрак туши
    "bg_base": "#14110F",       # 墨 суми, основа
    "bg_panel": "#1E1A17",      # карточки
    "bg_elevated": "#2B2522",   # приподнятые поверхности
    "border": "#3A332E",        # тонкие границы

    # Текст, небелёное полотно
    "text_primary": "#F6F1D3",  # 生成り кинари
    "text_secondary": "#B0B0B0",
    "text_muted": "#6D6D6D",

    # Режимы системы, 和色
    "s1": "#316745",            # 常磐 токива, вечнозелёный, баланс
    "s1_glow": "#7BA05B",       # 若竹 вакатакэ, свечение
    "s2": "#FFB11B",            # 山吹 ямабуки, янтарь, конфронтация
    "s2_glow": "#FFC800",       # 黄金 коганэ
    "s3": "#C3272B",            # 猩々緋 сёдзёхи, багряный, дестабилизация
    "s3_glow": "#9D2933",       # 蘇芳 суо, тёмное свечение

    # Акценты интерактива
    "accent": "#1F4788",        # 縹 ханада, синий
    "accent_glow": "#4A78C0",   # светлее для тёмного фона
    "accent_alt": "#77428D",    # 江戸紫 эдомурасаки, фиолетовый выделения
}


# Цвета по коду режима, основной и свечение.
REGIME_COLORS = {
    "S1": (PALETTE["s1"], PALETTE["s1_glow"]),
    "S2": (PALETTE["s2"], PALETTE["s2_glow"]),
    "S3": (PALETTE["s3"], PALETTE["s3_glow"]),
}


FONTS = {
    "mono": "'JetBrains Mono', 'SFMono-Regular', Consolas, monospace",
    "sans": "'Inter', 'Helvetica Neue', system-ui, sans-serif",
    "import_url": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap",
}


def regime_color(code: str, glow: bool = False) -> str:
    """Возвращает цвет режима по коду S1, S2 или S3."""
    if code not in REGIME_COLORS:
        raise ValueError(f"неизвестный режим: {code}")
    base, glw = REGIME_COLORS[code]
    return glw if glow else base


def _is_hex(value: str) -> bool:
    if not isinstance(value, str) or not value.startswith("#"):
        return False
    body = value[1:]
    return len(body) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in body)


def build_css() -> str:
    """
    Собирает таблицу стилей для применения в интерфейсе. Объявляет переменные
    палитры, шрифты и базовое оформление поверхностей и заголовков.
    """
    p = PALETTE
    return f"""
@import url('{FONTS["import_url"]}');

:root {{
  --bg-base: {p["bg_base"]};
  --bg-panel: {p["bg_panel"]};
  --bg-elevated: {p["bg_elevated"]};
  --border: {p["border"]};
  --text-primary: {p["text_primary"]};
  --text-secondary: {p["text_secondary"]};
  --text-muted: {p["text_muted"]};
  --s1: {p["s1"]}; --s1-glow: {p["s1_glow"]};
  --s2: {p["s2"]}; --s2-glow: {p["s2_glow"]};
  --s3: {p["s3"]}; --s3-glow: {p["s3_glow"]};
  --accent: {p["accent"]}; --accent-glow: {p["accent_glow"]};
  --accent-alt: {p["accent_alt"]};
  --font-mono: {FONTS["mono"]};
  --font-sans: {FONTS["sans"]};
}}

.stApp {{
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-sans);
}}

h1, h2, h3, h4 {{
  font-family: var(--font-sans);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}}

.fmam-mono, .fmam-metric {{
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}}

.fmam-panel {{
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 18px 20px;
}}

.fmam-card {{
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
}}

.fmam-metric {{
  font-size: 30px;
  font-weight: 700;
  color: var(--text-primary);
}}

.fmam-label {{
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}}

.fmam-badge {{
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-weight: 500;
  font-size: 13px;
}}
.fmam-s1 {{ color: var(--s1-glow); border: 1px solid var(--s1); }}
.fmam-s2 {{ color: var(--s2-glow); border: 1px solid var(--s2); }}
.fmam-s3 {{ color: var(--s3-glow); border: 1px solid var(--s3); }}

.fmam-tooltip {{
  border-bottom: 1px dotted var(--text-muted);
  cursor: help;
}}
"""
