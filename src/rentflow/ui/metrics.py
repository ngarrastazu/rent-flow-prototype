"""Pantalla de métricas para el equipo: eventos registrados frente a las Test Cards."""
import streamlit as st

from rentflow import db, seed
from rentflow.ui.navigation import logout
from rentflow.ui.theme import ICON


def page_metrics(_user=None):
    st.title("Métricas del prototipo")
    st.caption("Para el equipo: cada acción de los usuarios se registra y se compara con las Test Cards.")

    seen = db.users_with_event("ver_matches")
    reviews = db.users_with_event("ver_resenas")
    contacts = db.users_with_event("contactar")
    msgs = db.count_events("mensaje")

    def pct(n):
        return f"{round(100 * n / seen)} %" if seen else "—"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ven matches", seen, border=True, help="Usuarios que han visto sus matches: denominador de los %")
    c2.metric("Abren reseñas", pct(reviews), border=True, help="I12 · objetivo ≥ 60 %")
    c3.metric("Contactan", pct(contacts), border=True, help="I9 · objetivo ≥ 50 %")
    c4.metric("Mensajes", msgs, border=True, help="Chat en la app frente a WhatsApp · objetivo ≥ 60 %")
    st.caption("Objetivos: reseñas ≥ 60 % (I12) · contacto ≥ 50 % (I9) · conversaciones dentro de la app ≥ 60 %.")

    st.subheader("Últimas acciones")
    st.dataframe(
        db.recent_events(50), width="stretch", hide_index=True,
        column_config={"fecha": "Fecha (UTC)", "usuario": "Usuario", "accion": "Acción", "habitacion": "Habitación"},
    )

    st.button("Reiniciar datos de la demo", icon=ICON["reset"], on_click=reset_demo)


def reset_demo():
    seed.seed()
    logout()
