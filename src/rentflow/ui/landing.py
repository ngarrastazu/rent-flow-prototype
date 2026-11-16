"""Pantalla de entrada: banda de marca, probar como Mario, entrar como otro usuario o crear cuenta."""
import streamlit as st

from rentflow import db
from rentflow.ui.navigation import DEMO_USER, PAGE_PROFILE, login
from rentflow.ui.theme import ICON, LOGO_ON_VIOLET


def landing():
    with st.container(key="hero"):
        st.image(str(LOGO_ON_VIOLET), width=260)
        st.markdown(
            '<p class="rf-claim">Dinos qué buscas. Te encontramos habitación y compañeros compatibles.</p>'
            '<p class="rf-sub">Búsqueda inversa, matching por hábitos, perfiles verificados, '
            "reseñas de caseros y compañeros, y chat dentro de la app.</p>",
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2, gap="medium")
    with col1, st.container(border=True):
        st.subheader("Entrar")
        mario = db.find_user_by_name(DEMO_USER)
        if mario:
            st.caption("La demo sigue a Mario, 27 años, recién llegado a Madrid por trabajo.")
            st.button("Probar como Mario (demo)", icon=ICON["play"], type="primary", width="stretch",
                      on_click=login, args=(mario["id"],))
        st.divider()
        labels = {u["id"]: f"{u['name']} · {u['role']}" for u in db.list_users()}
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        c1.selectbox("O entra como otro usuario", list(labels), format_func=labels.get, key="login_choice")
        # Se lee del estado al pulsar (no se captura el valor de la ejecución anterior)
        c2.button("Entrar", on_click=lambda: login(st.session_state.login_choice), width="stretch")

    with col2, st.container(border=True):
        st.subheader("Crear cuenta")
        with st.form("signup", border=False):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("Nombre")
            age = c2.number_input("Edad", 18, 99, 24)
            role = st.radio("Soy…", ["inquilino", "casero"], horizontal=True,
                            format_func=lambda r: "Busco habitación" if r == "inquilino" else "Alquilo una habitación")
            c1, c2 = st.columns(2)
            occupation = c1.text_input("¿A qué te dedicas?", placeholder="Erasmus en la UC3M, consultora…")
            origin = c2.text_input("¿De dónde eres?")
            # Secundario: el único botón violeta de la portada es la demo de Mario
            if st.form_submit_button("Crear cuenta", width="stretch"):
                if not name.strip():
                    st.error("Escribe tu nombre.")
                else:
                    uid = db.create_user(name.strip(), int(age), role, occupation, origin)
                    login(uid)
                    if role == "inquilino":
                        st.session_state.page = PAGE_PROFILE
                    st.rerun()
