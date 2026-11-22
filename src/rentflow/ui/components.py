"""Piezas de interfaz reutilizables en varias pantallas (texto e insignias de personas y pisos)."""
from html import escape

import streamlit as st

from rentflow import db
from rentflow.ui.theme import ICON, ROOM_PLACEHOLDER, badge, stars_html


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


BIO_MAX = 300


def about_fields(user):
    """Campos «Sobre ti» para usar DENTRO de un st.form. Devuelve los valores para db.update_user.

    El nombre de un perfil verificado no se puede cambiar: anularía la verificación.
    """
    st.markdown("#### Sobre ti")
    c1, c2 = st.columns([3, 1])
    name = c1.text_input("Nombre", user["name"], max_chars=60, disabled=bool(user["verified"]),
                         help="Tu perfil está verificado: el nombre no se puede cambiar." if user["verified"] else None)
    age = c2.number_input("Edad", 18, 99, int(user["age"] or 24))
    c1, c2 = st.columns(2)
    is_tenant = user["role"] == "inquilino"
    occupation = c1.text_input("¿A qué te dedicas?" if is_tenant else "Ocupación", user["occupation"] or "",
                               max_chars=80, placeholder="Consultora, Erasmus en la UC3M…")
    origin = c2.text_input("¿De dónde eres?", user["origin"] or "", max_chars=60)
    bio = st.text_area(
        "Descripción", user["bio"] or "", max_chars=BIO_MAX, height=90,
        placeholder=("Cuéntales a tus futuros compañeros cómo eres: aficiones, rutina, qué buscas en un piso…"
                     if is_tenant else "Preséntate a los inquilinos: cómo gestionas el piso, cómo respondes…"),
    )
    return {"name": (name or "").strip() or user["name"], "age": int(age), "occupation": occupation.strip(),
            "origin": origin.strip(), "bio": bio.strip()}


def room_photo(room, key, caption=None):
    """Foto de la habitación (o la imagen de reserva) en un contenedor con `key` para el CSS.

    key = "thumb<algo>" -> miniatura 3:2 recortada; key = "roomphoto" -> foto grande 16:9 de la ficha.
    """
    with st.container(key=key):
        st.image(room["photo"] or str(ROOM_PLACEHOLDER), width="stretch",
                 caption=caption)


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
