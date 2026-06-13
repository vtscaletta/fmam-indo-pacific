"""
Визуальная тема. Светлый аналитический дашборд профессионального класса.

Эстетика делового интеллекта: светлый фон, белые карточки с мягкой тенью,
насыщенная сетка показателей, крупная типографика. Цвет кодирует состояние
по логике светофора и читается мгновенно. Палитра сине-циановая с тёплыми
акцентами, нейтральная и профессиональная.
"""

from __future__ import annotations

PALETTE = {
    # Фон и поверхности
    "bg_page": "#F4F6FA",
    "bg_panel": "#FFFFFF",
    "bg_subtle": "#F8FAFC",
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",

    # Текст
    "text_primary": "#0F1B2D",
    "text_secondary": "#475569",
    "text_muted": "#94A3B8",

    # Акценты интерфейса
    "accent": "#2563EB",
    "accent_soft": "#DBEAFE",
    "accent2": "#0891B2",
    "accent2_soft": "#CFFAFE",

    # Режимы системы, логика светофора
    "s1": "#16A34A", "s1_soft": "#DCFCE7",
    "s2": "#D97706", "s2_soft": "#FEF3C7",
    "s3": "#DC2626", "s3_soft": "#FEE2E2",
}

REGIME_COLORS = {
    "S1": (PALETTE["s1"], PALETTE["s1_soft"]),
    "S2": (PALETTE["s2"], PALETTE["s2_soft"]),
    "S3": (PALETTE["s3"], PALETTE["s3_soft"]),
}

# Уровни вердикта в цветах светофора.
VERDICT_COLORS = {
    "green": (PALETTE["s1"], PALETTE["s1_soft"]),
    "amber": (PALETTE["s2"], PALETTE["s2_soft"]),
    "red": (PALETTE["s3"], PALETTE["s3_soft"]),
}

FONTS = {
    "sans": "'Manrope', 'Helvetica Neue', system-ui, sans-serif",
    "serif": "'Spectral', Georgia, 'Times New Roman', serif",
    "mono": "'JetBrains Mono', 'SFMono-Regular', Consolas, monospace",
    "import_url": "https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Spectral:wght@500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap",
}


def regime_color(code: str, soft: bool = False) -> str:
    if code not in REGIME_COLORS:
        raise ValueError(f"неизвестный режим: {code}")
    strong, light = REGIME_COLORS[code]
    return light if soft else strong


def verdict_color(level: str, soft: bool = False) -> str:
    if level not in VERDICT_COLORS:
        raise ValueError(f"неизвестный уровень: {level}")
    strong, light = VERDICT_COLORS[level]
    return light if soft else strong


def _is_hex(value: str) -> bool:
    if not isinstance(value, str) or not value.startswith("#"):
        return False
    body = value[1:]
    return len(body) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in body)


def plotly_layout() -> dict:
    """Общие настройки оформления фигур plotly в светлой теме."""
    return dict(
        paper_bgcolor=PALETTE["bg_panel"],
        plot_bgcolor=PALETTE["bg_panel"],
        font=dict(family="Manrope, sans-serif", color=PALETTE["text_secondary"], size=13),
        margin=dict(l=48, r=20, t=30, b=40),
        colorway=[PALETTE["accent"], PALETTE["accent2"], PALETTE["s2"], PALETTE["s3"]],
    )


def build_css() -> str:
    p = PALETTE
    return f"""
@import url('{FONTS["import_url"]}');

/* База rem поднята, оттого весь интерфейс крупнее и читаемее. */
html {{ font-size: 17px; }}

/* Шрифт применяется ко всему агрессивно, иначе Streamlit перебивает тело и
   виджеты своим дефолтом, и смена выглядит частичной. Кириллица берётся из тех
   же Manrope и Spectral, оба несут полные кириллические начертания. */
html, body, .stApp, .stMarkdown, .stMarkdown p, p, li, label, span,
button, input, select, textarea, [data-baseweb], [class*="st-"] {{
    font-family: {FONTS["sans"]}; }}

.stApp {{ background: {p["bg_page"]}; color: {p["text_primary"]}; font-size: 1rem; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1320px; }}

/* Размер текста поднят на самих текстовых элементах, не только на контейнере. */
.stMarkdown, .stMarkdown p, .stApp p, .stApp li {{ font-size: 1.05rem; color: {p["text_primary"]}; }}
.stApp label {{ font-size: 1rem; }}

/* Вторая линия против тёмной темы. */
.stApp, .stApp p, .stApp li, .stApp label,
.stMarkdown, .stMarkdown p {{ color: {p["text_primary"]}; }}
.stTabs [data-baseweb="tab"] {{ color: {p["text_secondary"]}; font-weight: 600; font-size: 1rem; }}
.stTabs [aria-selected="true"] {{ color: {p["accent"]}; }}
.stRadio label, .stRadio div, .stSelectbox label, .stSlider label {{ color: {p["text_primary"]}; }}
section[data-testid="stSidebar"] {{ background: {p["bg_panel"]}; }}
section[data-testid="stSidebar"] * {{ color: {p["text_primary"]}; }}

h1, h2, h3 {{ font-family: {FONTS["serif"]}; color: {p["text_primary"]}; letter-spacing: -0.01em; }}
h1 {{ font-size: 40px; font-weight: 800; }}
h2 {{ font-size: 27px; font-weight: 700; }}
h3 {{ font-size: 21px; font-weight: 700; }}

#MainMenu, header, footer {{ visibility: hidden; }}

.dash-eyebrow {{ font-size: 13px; letter-spacing: 2px; font-weight: 600; color: {p["text_muted"]}; text-transform: uppercase; }}
.dash-sub {{ font-size: 17px; color: {p["text_secondary"]}; margin-bottom: 4px; }}

.kpi {{ background: {p["bg_panel"]}; border: 1px solid {p["border"]}; border-radius: 16px;
        padding: 14px 20px; box-shadow: 0 1px 3px rgba(15,27,45,.06); }}
.kpi-label {{ font-size: 13px; letter-spacing: 1px; font-weight: 600; color: {p["text_muted"]}; text-transform: uppercase; }}
.kpi-value {{ font-size: 44px; font-weight: 800; line-height: 1.05; font-variant-numeric: tabular-nums; color: {p["text_primary"]}; font-family: {FONTS["serif"]}; }}
.kpi-delta {{ font-size: 14px; font-weight: 600; }}

.verdict {{ border-radius: 18px; padding: 22px 26px; box-shadow: 0 2px 10px rgba(15,27,45,.08); }}
.verdict-title {{ font-size: 26px; font-weight: 800; display: flex; align-items: center; gap: 12px; font-family: {FONTS["serif"]}; }}
.verdict-text {{ font-size: 17px; line-height: 1.55; margin-top: 8px; }}
.verdict-dot {{ width: 16px; height: 16px; border-radius: 50%; }}

.panel {{ background: {p["bg_panel"]}; border: 1px solid {p["border"]}; border-radius: 16px;
          padding: 12px 18px; box-shadow: 0 1px 3px rgba(15,27,45,.06); }}
.panel-title {{ font-size: 18px; font-weight: 700; color: {p["text_primary"]}; margin-bottom: 6px; font-family: {FONTS["serif"]}; }}

.agentcard {{ background: {p["bg_panel"]}; border: 1px solid {p["border"]}; border-radius: 14px;
             padding: 16px; box-shadow: 0 1px 3px rgba(15,27,45,.06); }}
.agentcard-name {{ font-size: 17px; font-weight: 700; color: {p["text_primary"]}; }}
.agentcard-adv {{ font-size: 13px; color: {p["text_muted"]}; margin-bottom: 10px; }}

.barrow {{ display:flex; justify-content:space-between; font-size:14px; color:{p["text_secondary"]}; margin-top:8px; }}
.bartrack {{ background:{p["bg_page"]}; border-radius:6px; height:8px; margin-top:4px; }}
.barfill {{ height:8px; border-radius:6px; }}

.pill {{ display:inline-block; padding:6px 14px; border-radius:999px; font-weight:700; font-size:14px; }}

.stButton > button, .stDownloadButton > button {{
    padding: 0.3rem 0.9rem !important; min-height: 0 !important;
    line-height: 1.3 !important; font-size: 0.95rem !important; }}

/* Анти-воздух, широким фронтом по разным версиям селекторов Streamlit. Плашки
   перестают зиять пустотой, промежутки между блоками ужаты. */
[data-testid="stVerticalBlock"] {{ gap: 0.4rem; }}
[data-testid="stElementContainer"] {{ margin: 0 !important; }}
[data-testid="stElementContainer"]:empty {{ display: none; }}
.stMarkdown {{ margin-bottom: 0; }}
.element-container {{ margin-bottom: 0 !important; }}
.panel p {{ margin: 0.3rem 0; }}
.panel p:first-child {{ margin-top: 0; }}
.panel p:last-child {{ margin-bottom: 0; }}
"""
