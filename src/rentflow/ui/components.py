"""Piezas de interfaz reutilizables en varias pantallas (texto e insignias de personas y pisos)."""
from html import escape

import streamlit as st

from rentflow import db
from rentflow.ui.theme import ICON, badge, stars_html


def verified_badge(user):
    """HTML de la insignia de verificado, o cadena vacía."""
    return badge("✓ Verificado", "verified") if user["verified"] else ""


def habit_line(p):
    extras = (" · fuma" if p["smokes"] else "") + (" · tiene mascota" if p["pets"] else "")
    return f"{p['schedule']} · limpieza {p['cleanliness']}/5 · ruido {p['noise']}/5{extras}"


def room_facts(room, with_bathroom=False):
    """Línea con los datos del piso: zona, precio, tamaño, (baño) y fecha de entrada."""
    parts = [
        f"{ICON['zone']} {room['zone']}",
        f"{room['price']} €/mes",
        f"{room['size_m2']} m²",
    ]
    if with_bathroom:
        parts.append("baño propio" if room["own_bathroom"] else "baño compartido")
    parts.append(f"entrada {room['available_from']}")
    return " · ".join(parts)


def room_badges(room):
    """Insignias de la habitación (máximo 3)."""
    items = []
    if room["own_bathroom"]:
        items.append(badge("Baño propio"))
    if room["pets_allowed"]:
        items.append(badge("Admite mascotas"))
    if room["smoking_allowed"]:
        items.append(badge("Se puede fumar"))
    return items


def person_header(person, extra=""):
    """Nombre en negrita + insignia de verificado (+ texto opcional) en una sola línea."""
    st.markdown(f"**{escape(person['name'])}**{escape(extra)} {verified_badge(person)}", unsafe_allow_html=True)


def rating_line(user_id):
    avg, n = db.rating_of(user_id)
    st.markdown(stars_html(avg, n), unsafe_allow_html=True)
