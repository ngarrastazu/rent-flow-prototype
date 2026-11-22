"""Páginas, sesión y cambios de página. Sin dibujar nada: lo usan todas las pantallas."""
import streamlit as st

from rentflow import db

DEMO_USER = "Mario Rossi"

# Nombres de página (son también las opciones del menú lateral)
PAGE_MATCHES = "Mis matches"
PAGE_PROFILE = "Mi perfil y hábitos"
PAGE_MY_ROOMS = "Mis habitaciones"
PAGE_PUBLISH = "Publicar habitación"
PAGE_MESSAGES = "Mensajes"
PAGE_METRICS = "Métricas (equipo)"

# Icono Material de cada página en el menú (sin emojis: DESIGN.md §9)
PAGE_ICONS = {
    PAGE_MATCHES: ":material/favorite:",
    PAGE_PROFILE: ":material/tune:",
    PAGE_MY_ROOMS: ":material/home_work:",
    PAGE_PUBLISH: ":material/add_home:",
    PAGE_MESSAGES: ":material/chat:",
    PAGE_METRICS: ":material/insights:",
}

# Estado de widgets que debe sobrevivir al salir y volver a la página (filtros de "Mis matches").
# Streamlit borra el estado de un widget que no se dibuja; router.main() lo re-asigna en cada ejecución.
PERSISTENT_KEYS = ("f_price", "f_zones", "f_bath", "f_sort", "f_view")

TENANT_PAGES = [PAGE_MATCHES, PAGE_PROFILE, PAGE_MESSAGES, PAGE_METRICS]
LANDLORD_PAGES = [PAGE_MY_ROOMS, PAGE_PUBLISH, PAGE_MESSAGES, PAGE_METRICS]


def go(page, **state):
    """Callback de botón: cambia de página y guarda estado extra."""
    st.session_state.page = page
    for k, v in state.items():
        st.session_state[k] = v


def login(user_id):
    st.session_state.user_id = user_id
    user = db.get_user(user_id)
    st.session_state.page = TENANT_PAGES[0] if user["role"] == "inquilino" else LANDLORD_PAGES[0]
    st.session_state.pop("selected_room", None)


def keep_widget_state():
    """Re-asigna el estado de PERSISTENT_KEYS para que Streamlit no lo borre entre páginas."""
    for k in PERSISTENT_KEYS:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]


def logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
