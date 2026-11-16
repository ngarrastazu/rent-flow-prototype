"""Pantallas del inquilino: mis matches, ficha de la habitación y perfil de hábitos."""
from datetime import date
from html import escape

import streamlit as st

from rentflow import db, matching
from rentflow.ui.components import (
    habit_line,
    person_header,
    rating_line,
    room_badges,
    room_facts,
    verified_badge,
)
from rentflow.ui.navigation import PAGE_MATCHES, PAGE_MESSAGES, PAGE_PROFILE, go
from rentflow.ui.theme import ICON, badges, empty_state, review_html, score_block


def page_matches(user):
    prefs = db.get_preferences(user["id"])
    if not prefs:
        st.title("Tus matches")
        empty_state("Primero cuéntanos qué buscas y cómo vives para calcular tu compatibilidad.",
                    lambda: st.button("Rellenar mi perfil", type="primary", on_click=go, args=(PAGE_PROFILE,)))
        return

    if st.session_state.get("selected_room"):
        room_detail(user, prefs, st.session_state.selected_room)
        return

    st.title("Tus matches")
    st.caption(f"{ICON['zone']} {', '.join(prefs['zones']) or 'Cualquier zona'} · "
               f"{prefs['budget_min']}–{prefs['budget_max']} €/mes · entrada {prefs['move_in']}"
               f"{' · baño propio' if prefs['own_bathroom'] else ''}")
    if not st.session_state.get("logged_matches"):
        db.log_event(user["id"], "ver_matches")
        st.session_state.logged_matches = True

    results = matching.matches_for(user["id"])
    if not results:
        empty_state("No hay habitaciones que encajen. Prueba a ampliar zonas o presupuesto en tu perfil.",
                    lambda: st.button("Editar mi perfil", on_click=go, args=(PAGE_PROFILE,)))
        return

    for r in results:
        match_card(r)


def match_card(r):
    room = r["room"]
    landlord = db.get_user(room["landlord_id"])
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 4, 1.4], vertical_alignment="center")
        with c1:
            score_block(r["score"], size=32)
        with c2:
            st.markdown(f"**{room['title']}**")
            st.caption(room_facts(room))
            mates = ", ".join(f"{m['name'].split()[0]} ({m['age']})" for m in r["mates"]) or "sin compañeros todavía"
            # Línea con insignia de verificado del casero (por eso HTML y no st.caption)
            st.markdown(
                f'<span class="rf-meta">{ICON["mates"]} {escape(mates)} · {ICON["landlord"]} '
                f'{escape(landlord["name"])}</span> '
                f"{verified_badge(landlord)}",
                unsafe_allow_html=True,
            )
        with c3:
            st.button("Ver detalles", key=f"det{room['id']}", width="stretch",
                      on_click=go, args=(PAGE_MATCHES,), kwargs={"selected_room": room["id"]})


def room_detail(user, prefs, room_id):
    room = db.get_room(room_id)
    landlord = db.get_user(room["landlord_id"])
    mates = db.roommates(room_id)
    mates_prefs = [db.get_preferences(m["id"]) for m in mates]  # alineado con `mates` (puede haber None)
    scored = matching.score_room(prefs, room, [p for p in mates_prefs if p])

    if st.session_state.get("logged_detail") != room_id:
        db.log_event(user["id"], "ver_detalle", room_id)
        st.session_state.logged_detail = room_id

    st.button("Volver a mis matches", icon=ICON["back"], type="tertiary", on_click=go, args=(PAGE_MATCHES,),
              kwargs={"selected_room": None})
    st.title(room["title"])
    st.caption(room_facts(room, with_bathroom=True))

    left, right = st.columns([3, 2], gap="large")
    with left:
        if room["photo"]:
            st.image(room["photo"], width="stretch", caption=room["title"])
        st.write(room["description"])
        rules = [
            "se puede fumar" if room["smoking_allowed"] else "no se fuma",
            "se admiten mascotas" if room["pets_allowed"] else "sin mascotas",
        ]
        st.caption("Normas: " + " · ".join(rules))
        badges(room_badges(room))

        st.subheader("Tus compañeros")
        if not mates:
            st.caption("Todavía no vive nadie más: serías el primero.")
        cols = st.columns(2) if len(mates) > 1 else [st.container()]
        for i, (m, p) in enumerate(zip(mates, mates_prefs, strict=True)):
            with cols[i % len(cols)], st.container(border=True):
                person_header(m, f", {m['age']}")
                st.caption(f"{m['occupation']} · de {m['origin']}")
                if m["bio"]:
                    st.caption(f"_{m['bio']}_")
                if p:
                    st.caption(habit_line(p))
                rating_line(m["id"])

        st.subheader("Casero")
        with st.container(border=True):
            person_header(landlord)
            if landlord["bio"]:
                st.caption(landlord["bio"])
            rating_line(landlord["id"])

        show = st.toggle("Ver reseñas del casero y de los compañeros", key=f"rev{room_id}",
                         on_change=log_reviews_opened, args=(user["id"], room_id))
        if show:
            for person in [landlord] + mates:
                revs = db.reviews_of(person["id"])
                if revs:
                    st.markdown(f"**{person['name']}**")
                    st.markdown("".join(review_html(rv["rating"], rv["comment"], rv["author_name"]) for rv in revs),
                                unsafe_allow_html=True)

    with right, st.container(border=True, key="sticky"):
        if scored:
            score_block(scored[0], size=56)
            st.markdown("**Por qué este match**")
            for factor, value in scored[1].items():
                st.progress(value, text=f"{factor} ({int(matching.WEIGHTS[factor] * 100)} %): {round(value * 100)} %")
        else:
            st.caption("Esta habitación no cumple alguno de tus requisitos.")
        st.button("Contactar con el casero y los compañeros", icon=ICON["chat"], type="primary", width="stretch",
                  on_click=contact, args=(user, room))


def log_reviews_opened(user_id, room_id):
    """Callback del interruptor de reseñas: registra el evento solo al activarlo (I12)."""
    if st.session_state.get(f"rev{room_id}"):
        db.log_event(user_id, "ver_resenas", room_id)


def contact(user, room):
    conv, created = db.get_or_create_conversation(room["id"], user["id"])
    if created:
        db.send_message(conv, user["id"], f"¡Hola! Soy {user['name'].split()[0]}. RentFlow me ha sugerido "
                                          f"esta habitación y me encantaría conoceros. ¿Cuándo podría visitarla?")
        db.log_event(user["id"], "contactar", room["id"])
    go(PAGE_MESSAGES, conversation_id=conv, selected_room=None)


def page_profile(user):
    st.title("Mi perfil y hábitos")
    st.caption("Con esto calculamos tu compatibilidad con cada piso y sus compañeros.")
    p = db.get_preferences(user["id"]) or {
        "budget_min": 400, "budget_max": 600, "zones": [], "move_in": date.today().isoformat(),
        "schedule": db.SCHEDULES[1], "cleanliness": 3, "noise": 2, "smokes": 0, "pets": 0, "own_bathroom": 0}

    with st.container(key="narrow"), st.form("prefs"):
        st.markdown("#### Qué buscas")
        budget = st.slider("Presupuesto (€/mes)", 300, 1200, (p["budget_min"], p["budget_max"]), step=25)
        zones = st.multiselect("Zonas", db.ZONES, default=p["zones"], placeholder="Cualquier zona")
        c1, c2 = st.columns(2, vertical_alignment="bottom")
        move_in = c1.date_input("Fecha de entrada", date.fromisoformat(p["move_in"]))
        own_bathroom = c2.checkbox("Necesito baño propio", bool(p["own_bathroom"]))

        st.markdown("#### Cómo vives")
        schedule = st.radio("Horario", db.SCHEDULES, index=db.SCHEDULES.index(p["schedule"]), horizontal=True)
        c1, c2 = st.columns(2)
        cleanliness = c1.slider("Orden y limpieza (1 = relajado, 5 = muy ordenado)", 1, 5, p["cleanliness"])
        noise = c2.slider("Ruido en casa (1 = silencio, 5 = fiestas en casa)", 1, 5, p["noise"])
        c1, c2 = st.columns(2)
        smokes = c1.checkbox("Fumo", bool(p["smokes"]))
        pets = c2.checkbox("Tengo mascota", bool(p["pets"]))

        if st.form_submit_button("Guardar y ver mis matches", type="primary"):
            db.save_preferences(user["id"], budget[0], budget[1], zones, move_in.isoformat(), schedule,
                                cleanliness, noise, smokes, pets, own_bathroom)
            st.session_state._goto = PAGE_MATCHES  # el menú ya está dibujado: se cambia en la siguiente ejecución
            st.rerun()
