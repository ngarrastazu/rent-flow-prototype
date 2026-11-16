"""Enrutado: tema, barra lateral, menú por rol y qué función dibuja cada página."""
import streamlit as st

from rentflow import db, seed
from rentflow.ui.components import person_header
from rentflow.ui.landing import landing
from rentflow.ui.landlord import page_my_rooms, page_publish
from rentflow.ui.messages import page_messages
from rentflow.ui.metrics import page_metrics
from rentflow.ui.navigation import (
    LANDLORD_PAGES,
    PAGE_ICONS,
    PAGE_MATCHES,
    PAGE_MESSAGES,
    PAGE_METRICS,
    PAGE_MY_ROOMS,
    PAGE_PROFILE,
    PAGE_PUBLISH,
    TENANT_PAGES,
    logout,
)
from rentflow.ui.tenant import page_matches, page_profile
from rentflow.ui.theme import ICON, setup_page

ROUTES = {
    PAGE_MATCHES: page_matches,
    PAGE_PROFILE: page_profile,
    PAGE_MY_ROOMS: page_my_rooms,
    PAGE_PUBLISH: page_publish,
    PAGE_MESSAGES: page_messages,
    PAGE_METRICS: page_metrics,
}


def ensure_data():
    """Crea la base de datos y la llena con los datos de la demo si está vacía."""
    db.init_db()
    if db.is_empty():
        seed.seed()


def sidebar(user, pages):
    with st.sidebar:
        with st.container(border=True):
            person_header(user)
            st.caption(f"{user['occupation']} · {'Busca habitación' if user['role'] == 'inquilino' else 'Casero'}")
        st.radio("Menú", pages, key="page", label_visibility="collapsed",
                 format_func=lambda p: f"{PAGE_ICONS[p]} {p}",
                 on_change=lambda: st.session_state.update(selected_room=None))
        st.divider()
        st.button("Cerrar sesión", icon=ICON["logout"], type="tertiary", on_click=logout)


def main():
    setup_page()
    ensure_data()

    if "user_id" not in st.session_state:
        landing()
        return

    user = db.get_user(st.session_state.user_id)
    if not user:
        logout()
        st.rerun()

    pages = TENANT_PAGES if user["role"] == "inquilino" else LANDLORD_PAGES
    if "_goto" in st.session_state:
        st.session_state.page = st.session_state.pop("_goto")
        st.session_state.selected_room = None
    if st.session_state.get("page") not in pages:
        st.session_state.page = pages[0]

    sidebar(user, pages)
    ROUTES[st.session_state.page](user)
