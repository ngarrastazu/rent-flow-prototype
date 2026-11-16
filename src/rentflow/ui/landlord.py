"""Pantallas del casero: mis habitaciones (con búsqueda inversa) y publicar habitación."""
from datetime import date

import streamlit as st

from rentflow import db, matching
from rentflow.ui.components import room_badges, room_facts
from rentflow.ui.navigation import PAGE_MESSAGES, PAGE_PUBLISH, go
from rentflow.ui.theme import ICON, badges, empty_state, score_style


def page_my_rooms(user):
    st.title("Mis habitaciones")
    rooms = db.rooms_of_landlord(user["id"])
    if not rooms:
        empty_state("Todavía no has publicado ninguna habitación.",
                    lambda: st.button("Publicar habitación", icon=ICON["publish"], type="primary",
                                      on_click=go, args=(PAGE_PUBLISH,)))
        return

    st.caption(f"{len(rooms)} {'habitación publicada' if len(rooms) == 1 else 'habitaciones publicadas'}. "
               "Para cada una, los inquilinos que más encajan y quién te ha escrito.")
    for room in rooms:
        room_card(room)


def room_card(room):
    mates = db.roommates(room["id"])
    interested = db.interested_in(room["id"])
    with st.container(border=True):
        st.markdown(f"**{room['title']}**")
        st.caption(room_facts(room) + f" · {ICON['mates']} " + (", ".join(m["name"] for m in mates)
                                                                 or "sin compañeros"))
        badges(room_badges(room))

        c1, c2 = st.columns([2, 1], gap="medium")
        with c1:
            st.markdown("###### Inquilinos más compatibles · búsqueda inversa")
            candidates = matching.candidates_for(room["id"])
            if not candidates:
                st.caption("Nadie que busque piso encaja ahora mismo.")
            for cand in candidates:
                t = cand["tenant"]
                _, label = score_style(cand["score"])
                check = " ✓" if t["verified"] else ""
                st.caption(f"**{cand['score']} %** {label.lower()} · {t['name']}{check}, {t['age']} · "
                           f"{t['occupation']}")
        with c2:
            st.markdown(f"###### Interesados que te han escrito · {len(interested)}")
            if not interested:
                st.caption("Aún nadie. Te avisaremos aquí.")
            for conv in interested:
                st.button(f"Chat con {conv['tenant_name']}", icon=ICON["chat"], key=f"conv{conv['id']}",
                          type="tertiary", on_click=go, args=(PAGE_MESSAGES,),
                          kwargs={"conversation_id": conv["id"]})


def page_publish(user):
    st.title("Publicar habitación")
    st.caption("En cuanto la publiques aparecerá en los matches de los inquilinos compatibles.")
    living = db.rooms_lived_in()
    available_mates = {u["id"]: f"{u['name']} ({u['age']})"
                       for u in db.list_users("inquilino") if u["id"] not in living}
    with st.container(key="narrow"), st.form("publish", clear_on_submit=True):
        st.markdown("#### La habitación")
        title = st.text_input("Título", placeholder="Habitación exterior en Malasaña")
        c1, c2, c3, c4 = st.columns(4)
        zone = c1.selectbox("Zona", db.ZONES)
        price = c2.number_input("Precio (€/mes)", 200, 2000, 550, step=10)
        size = c3.number_input("Tamaño (m²)", 5, 40, 12)
        available = c4.date_input("Disponible desde", date.today())
        description = st.text_area("Descripción", height=100)
        photo = st.file_uploader("Foto", type=["jpg", "jpeg", "png"])

        st.markdown("#### Normas y compañeros")
        c1, c2, c3 = st.columns(3)
        own_bathroom = c1.checkbox("Baño propio")
        smoking = c2.checkbox("Se puede fumar")
        pets = c3.checkbox("Se admiten mascotas")
        members = st.multiselect("Compañeros que ya viven en el piso (deben tener cuenta)",
                                 list(available_mates), format_func=available_mates.get, placeholder="Ninguno")
        if st.form_submit_button("Publicar", type="primary"):
            if not title.strip():
                st.error("Ponle un título.")
            else:
                db.create_room(user["id"], title.strip(), zone, int(price), int(size), own_bathroom,
                               available.isoformat(), smoking, pets, description,
                               photo.getvalue() if photo else None, members)
                st.success("¡Publicada! Ya aparece en los matches de los inquilinos compatibles.")
