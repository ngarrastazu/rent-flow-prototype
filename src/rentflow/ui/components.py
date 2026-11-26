"""Piezas de interfaz reutilizables en varias pantallas (texto e insignias de personas y pisos)."""
from html import escape

import streamlit as st

from rentflow import db
from rentflow.ui.theme import ICON, ROOM_PLACEHOLDER, badge, stars_html

# Estado de una solicitud -> (texto de la insignia, tipo de insignia)
REQUEST_STATUS = {
    "pendiente": ("Pendiente", "brand"),
    "aceptada": ("Aceptada", "verified"),
    "rechazada": ("Rechazada", "muted"),
    "retirada": ("Retirada", "muted"),
    "cerrada": ("Cerrada", "muted"),
}


def request_badge(status):
    text, kind = REQUEST_STATUS[status]
    return badge(text, kind)


def votes_text(request_id, names=True):
    """Opinión de los compañeros sobre una solicitud, en una línea.

    names=True (casero): «Lucía: le encaja · Tom: no le encaja · Ana: sin opinar».
    names=False (candidato): «1 de 2 compañeros te han dado el visto bueno».
    """
    votes = db.votes_for(request_id)
    if not votes:
        return "Piso sin compañeros: decide solo el casero."
    if not names:
        yes = sum(v["vote"] == 1 for v in votes)
        return f"{yes} de {len(votes)} compañeros te han dado el visto bueno."
    label = {1: "le encaja", -1: "no le encaja", None: "sin opinar"}
    return " · ".join(f"{v['name'].split()[0]}: {label[v['vote']]}" for v in votes)


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


def photo_source(photo):
    """Lo que necesita st.image: los bytes subidos o la ruta absoluta de una foto de ejemplo de assets/."""
    if photo is None:
        return str(ROOM_PLACEHOLDER)
    return photo["image"] if photo["image"] is not None else str(db.PROJECT_ROOT / "assets" / photo["path"])


def room_photo(room, key, caption=None):
    """Foto principal del anuncio (o la imagen de reserva) en un contenedor con `key` para el CSS.

    key = "thumb<algo>" -> miniatura 3:2 recortada; key = "roomphoto" -> foto grande 16:9 de la ficha.
    """
    with st.container(key=key):
        st.image(photo_source(db.main_photo(room["id"])), width="stretch", caption=caption)


def space_labels(photos):
    """Etiqueta de cada foto según su espacio, numerando las repetidas: «Salón», «Salón 2»…"""
    seen, labels = {}, []
    for ph in photos:
        space = ph["space"] or "Otra"
        seen[space] = seen.get(space, 0) + 1
        labels.append(space if seen[space] == 1 else f"{space} {seen[space]}")
    return labels


def room_gallery(room):
    """Galería de la ficha: foto grande y, debajo, un selector por espacio (habitación, salón, cocina…)."""
    photos = db.room_photos(room["id"])
    if len(photos) <= 1:
        room_photo(room, key="roomphoto")
        return
    labels = space_labels(photos)
    key = f"gal{room['id']}"
    if not isinstance(st.session_state.get(key), int) or st.session_state[key] >= len(photos):
        st.session_state[key] = 0  # la principal
    with st.container(key="roomphoto"):
        st.image(photo_source(photos[st.session_state[key]]), width="stretch")
    # Solo texto (sin iconos) y a todo el ancho: con 5 espacios los iconos no caben en la columna
    st.segmented_control("Fotos del piso", list(range(len(photos))), key=key, label_visibility="collapsed",
                         format_func=lambda i: labels[i], width="stretch")
    shown = st.session_state.get(key) or 0
    st.caption(f"Foto {shown + 1} de {len(photos)} · {labels[shown]}")


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
