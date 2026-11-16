"""Identidad visual de RentFlow (ver docs/DESIGN.md): logos, colores, CSS global y piezas HTML.

Es el único módulo que usa `unsafe_allow_html`, y solo para lo que permite la guía:
el CSS global, las insignias, la puntuación de compatibilidad y las estrellas.
"""
from html import escape

import streamlit as st

from rentflow.db import PROJECT_ROOT

# ---------------------------------------------------------------- logos

ASSETS = PROJECT_ROOT / "assets"
LOGO_HORIZONTAL = ASSETS / "png" / "horizontal" / "rentflow-horizontal-02-color-fondo-claro.png"
LOGO_ON_VIOLET = ASSETS / "png" / "horizontal" / "rentflow-horizontal-07-blanco-sobre-violeta.png"
ISOTYPE = ASSETS / "png" / "isotipo" / "rentflow-isotipo-02-color-fondo-claro.png"
ISOTYPE_MONO = ASSETS / "png" / "isotipo" / "rentflow-isotipo-04-monocromo-violeta.png"
APP_ICON = ASSETS / "png" / "icono-app" / "rentflow-icono-app-violeta.png"

# ---------------------------------------------------------------- color (tokens de DESIGN.md §3)

VIOLET = "#4B02F2"
VIOLET_DARK = "#3A01BE"
VIOLET_SOFT = "#EFEAFE"
BLUE = "#2C78EE"
BLUE_DEEP = "#1C4FBA"
NIGHT = "#0D0638"
INK = "#14102B"
INK_MUTED = "#5A5670"
LINE = "#E6E3F0"
SURFACE = "#F7F6FB"
SUCCESS = "#1F9D55"

# Iconos Material de Streamlit (DESIGN.md §9: nada de emojis)
ICON = {
    "zone": ":material/location_on:",
    "price": ":material/euro:",
    "size": ":material/square_foot:",
    "date": ":material/event:",
    "mates": ":material/group:",
    "landlord": ":material/home:",
    "chat": ":material/chat:",
    "user": ":material/person:",
    "play": ":material/play_arrow:",
    "back": ":material/arrow_back:",
    "logout": ":material/logout:",
    "reset": ":material/restart_alt:",
    "star": ":material/star:",
    "publish": ":material/add_home:",
}


def setup_page():
    """Configuración de página, logo de la barra lateral y CSS. Una vez por ejecución, al principio."""
    st.set_page_config(page_title="RentFlow", page_icon=str(ISOTYPE), layout="wide")
    st.logo(str(LOGO_HORIZONTAL), icon_image=str(ISOTYPE), size="large")
    inject_css()


def inject_css():
    st.markdown(f"""
<style>
/* Las fuentes (Inter / Inter Tight) se cargan desde .streamlit/config.toml */
h1, h2, h3, h4, h5 {{ letter-spacing: -0.02em; color: {INK}; }}

/* ---------- Compacto: menos aire alrededor del contenido ---------- */
[data-testid="stMainBlockContainer"], .block-container {{
  padding-top: 2.25rem; padding-bottom: 2rem; max-width: 1280px;
}}
[data-testid="stVerticalBlock"] {{ gap: 0.75rem; }}
h1 {{ font-size: 32px !important; padding: 0 0 0.15rem !important; line-height: 1.15; }}
h2 {{ font-size: 22px !important; padding: 0.5rem 0 0.1rem !important; }}
h3, h4 {{ font-size: 18px !important; padding: 0.25rem 0 0.35rem !important; }}
h5 {{ font-size: 15px !important; padding: 0.25rem 0 0 !important; color: {INK_MUTED}; text-transform: none; }}
[data-testid="stHeaderActionElements"] {{ display: none; }}       /* sin enlaces de ancla en títulos */
[data-testid="stCaptionContainer"] {{ color: {INK_MUTED}; font-size: 14px; opacity: 1; }}  /* contraste 4,5:1 */
[data-testid="stCaptionContainer"] p {{ margin-bottom: 0; }}
hr {{ margin: 0.75rem 0 !important; border-color: {LINE} !important; }}
[data-testid="stAppDeployButton"], footer {{ display: none; }}

/* ---------- Tarjetas: st.container(border=True) ---------- */
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stVerticalBlock"][class*="border"] {{
  border-radius: 16px; border-color: {LINE}; background: #FFFFFF;
}}

/* ---------- Botones ---------- */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
  border-radius: 10px; font-weight: 600; min-height: 2.4rem;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
  background: {VIOLET}; border-color: {VIOLET}; color: #FFFFFF;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
  background: {VIOLET_DARK}; border-color: {VIOLET_DARK};
}}
.stButton > button[kind="secondary"]:hover {{ border-color: {VIOLET}; color: {VIOLET}; }}

/* ---------- Campos ---------- */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {{ border-radius: 10px; }}

/* ---------- Barra lateral y menú ---------- */
[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {LINE}; }}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding-top: 0.5rem; }}
[data-testid="stSidebar"] [role="radiogroup"] {{ gap: 2px; width: 100%; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {{
  width: 100%; padding: 8px 12px; margin: 0; border-radius: 10px; cursor: pointer;
}}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {{ display: none; }}  /* círculo */
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {{ background: {VIOLET_SOFT}; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{ background: {VIOLET_SOFT}; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {{ color: {VIOLET}; font-weight: 600; }}
[data-testid="stSidebarHeader"] img {{ height: 2.25rem !important; max-width: 100%; }}

/* ---------- Desglose del match y métricas ---------- */
[data-testid="stProgressBarTrack"] > div {{ background-color: {BLUE}; }}
[data-testid="stProgress"] p {{ font-size: 14px; }}
[data-testid="stMetric"] {{ padding: 0.75rem 1rem; }}
[data-testid="stMetricValue"] {{ font-weight: 700; color: {VIOLET}; font-size: 28px; }}
[data-testid="stMetricLabel"] p {{ color: {INK_MUTED}; font-size: 14px; }}

/* ---------- Fotos ---------- */
[data-testid="stImage"] img {{ border-radius: 16px; }}
[data-testid="stSidebar"] [data-testid="stImage"] img,
.st-key-hero [data-testid="stImage"] img,
.st-key-empty [data-testid="stImage"] img {{ border-radius: 0; }}

/* ---------- Portada: banda violeta ---------- */
.st-key-hero {{
  background: {VIOLET}; border-radius: 16px; padding: 28px 32px 24px; margin-bottom: 8px; gap: 0.25rem;
}}
.st-key-hero p {{ color: #FFFFFF; }}
.st-key-hero .rf-claim {{ font-size: 26px; font-weight: 700; line-height: 1.2; letter-spacing: -0.01em; margin: 0; }}
.st-key-hero .rf-sub {{ font-size: 16px; opacity: 0.85; margin: 6px 0 0; }}

/* ---------- Contenedores de ancho limitado y columna fija ---------- */
.st-key-narrow {{ max-width: 760px; }}
.st-key-sticky {{ position: sticky; top: 3.5rem; }}
.st-key-empty {{ align-items: flex-start; padding: 8px 0; }}

/* ---------- Piezas propias ---------- */
.rf-badge {{
  display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 13px; font-weight: 600;
  margin-right: 4px; white-space: nowrap; line-height: 1.6;
}}
.rf-badge.verified {{ background: #E6F5EC; color: {SUCCESS}; }}
.rf-badge.brand {{ background: {VIOLET_SOFT}; color: {VIOLET}; }}
.rf-badge.muted {{ background: {SURFACE}; color: {INK_MUTED}; border: 1px solid {LINE}; }}
.rf-score {{
  font-family: 'Inter Tight', 'Inter', sans-serif; font-weight: 700; line-height: 1; letter-spacing: -0.02em;
}}
.rf-score-label {{ font-size: 13px; font-weight: 600; margin: 4px 0 6px; }}
.rf-stars {{ letter-spacing: 1px; }}
.rf-stars .on {{ color: {VIOLET}; }}
.rf-stars .off {{ color: {LINE}; }}
.rf-stars .txt {{ color: {INK_MUTED}; font-size: 14px; letter-spacing: 0; margin-left: 4px; }}
.rf-meta {{ font-size: 14px; color: {INK_MUTED}; }}
.rf-review {{ margin: 0 0 6px; font-size: 14px; }}
.rf-review em {{ color: {INK}; }}
.rf-review .who {{ color: {INK_MUTED}; }}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- compatibilidad (DESIGN.md §3)

def score_style(score):
    """(color, etiqueta) según el rango de compatibilidad."""
    if score >= 85:
        return VIOLET, "Match excelente"
    if score >= 70:
        return BLUE, "Buen match"
    return INK_MUTED, "Match posible"


def score_block(score, size=32):
    """Porcentaje grande con su etiqueta: el color nunca va solo (accesibilidad)."""
    color, label = score_style(score)
    st.markdown(
        f'<div class="rf-score" style="font-size:{size}px;color:{color}">{score} %</div>'
        f'<div class="rf-score-label" style="color:{color}">{label}</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- insignias y estrellas

def badge(text, kind="brand"):
    """HTML de una insignia. kind: verified | brand | muted."""
    return f'<span class="rf-badge {kind}">{escape(text)}</span>'


def badges(items):
    """Pinta una fila de insignias (máximo 3 según la guía)."""
    if items:
        st.markdown("".join(items[:3]), unsafe_allow_html=True)


def stars_html(avg, n):
    """★★★★☆ 4,2 (5 reseñas): llenas en violeta, vacías en gris de línea, coma decimal."""
    if not avg:
        return '<span class="rf-stars"><span class="txt">Sin reseñas todavía</span></span>'
    full = round(avg)
    word = "reseña" if n == 1 else "reseñas"
    return (f'<span class="rf-stars"><span class="on">{"★" * full}</span><span class="off">{"★" * (5 - full)}</span>'
            f'<span class="txt">{str(avg).replace(".", ",")} ({n} {word})</span></span>')


def review_html(rating, comment, author):
    return (f'<p class="rf-review"><span class="rf-stars"><span class="on">{"★" * rating}</span>'
            f'<span class="off">{"★" * (5 - rating)}</span></span> '
            f'<em>“{escape(comment or "")}”</em> <span class="who">— {escape(author)}</span></p>')


def empty_state(message, action=None):
    """Estado vacío: isotipo, frase que explica qué pasa y (opcional) botón para resolverlo."""
    with st.container(key="empty"):
        st.image(str(ISOTYPE_MONO), width=56)
        st.markdown(message)
        if action:
            action()
