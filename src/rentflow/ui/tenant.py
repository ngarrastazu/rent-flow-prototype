"""Pantallas del inquilino: mis matches, ficha de la habitación y perfil de hábitos."""
from datetime import date
from html import escape

import streamlit as st

from rentflow import db, matching
from rentflow.ui.components import (
    about_fields,
    habit_line,
    person_header,
    rating_line,
    room_badges,
    room_facts,
    room_photo,
    verified_badge,
)
from rentflow.ui.maps import LAYER_ID, rooms_deck
from rentflow.ui.navigation import PAGE_MATCHES, PAGE_MESSAGES, PAGE_PROFILE, flash, go
from rentflow.ui.theme import ICON, badges, empty_state, review_html, score_block

PAGE_SIZE = 10  # tarjetas por tanda en la vista de lista ("Ver más" añade otras tantas)
VIEWS = {"Lista": ICON["list"], "Mapa": ICON["map"]}


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

    all_results = matching.matches_for(user["id"], limit=None)
    if not all_results:
        empty_state("No hay habitaciones que encajen. Prueba a ampliar zonas o presupuesto en tu perfil.",
                    lambda: st.button("Editar mi perfil", on_click=go, args=(PAGE_PROFILE,)))
        return

    results = filter_bar(user, all_results)
    if not results:
        empty_state("Ninguna habitación cumple estos filtros.",
                    lambda: st.button("Quitar filtros", icon=ICON["filter"], on_click=clear_filters,
                                      args=(all_results,)))
        return

    if (st.session_state.get("f_view") or "Lista") == "Mapa":
        if not st.session_state.get("logged_map"):
            db.log_event(user["id"], "ver_mapa")
            st.session_state.logged_map = True
        matches_map(results)
    else:
        shown = st.session_state.get("matches_shown", PAGE_SIZE)
        for r in results[:shown]:
            match_card(r)
        if len(results) > shown:
            st.button(f"Ver más ({len(results) - shown})", icon=ICON["more"], width="stretch",
                      on_click=show_more, args=(shown,))


def show_more(shown):
    st.session_state.matches_shown = shown + PAGE_SIZE


# ---------------------------------------------------------------- filtros (sin recalcular el perfil)

def _price_bounds(results):
    prices = [r["room"]["price"] for r in results]
    lo, hi = min(prices) // 10 * 10, -(-max(prices) // 10) * 10
    return lo, max(hi, lo + 10)  # el slider necesita un rango no vacío


def clear_filters(results):
    st.session_state.f_price = _price_bounds(results)[1]
    st.session_state.f_zones = []
    st.session_state.f_bath = False
    st.session_state.matches_shown = PAGE_SIZE


def filter_bar(user, all_results):
    """Barra de filtros y vista. Devuelve los resultados filtrados y ordenados (la puntuación no cambia)."""
    lo, hi = _price_bounds(all_results)
    zone_options = sorted({r["room"]["zone"] for r in all_results})
    ss = st.session_state
    # Valores por defecto y saneado si el perfil cambió (sin pasar `value=` para no chocar con session_state)
    if "f_price" not in ss or not lo <= ss.f_price <= hi:
        ss.f_price = hi  # por defecto sin límite de precio
    ss.f_zones = [z for z in ss.get("f_zones", []) if z in zone_options]
    ss.setdefault("f_bath", False)
    ss.setdefault("f_sort", "Compatibilidad")
    ss.setdefault("f_view", "Lista")

    with st.container(key="filters"):
        c1, c2, c3, c4 = st.columns([2, 2.8, 1.3, 1.9], vertical_alignment="bottom", gap="small")
        c1.slider("Precio máximo (€/mes)", lo, hi, step=10, key="f_price")
        c2.multiselect("Zonas", zone_options, key="f_zones", placeholder="Todas las zonas")
        c3.toggle("Baño propio", key="f_bath")
        c4.selectbox("Ordenar por", list(matching.SORTS), key="f_sort")

    active = ss.f_price < hi or bool(ss.f_zones) or ss.f_bath
    results = matching.filter_matches(all_results, ss.f_price, ss.f_zones, ss.f_bath, ss.f_sort)
    if active and not ss.get("logged_filter"):
        db.log_event(user["id"], "filtrar")  # I11: ¿exploran la oferta más allá del top?
        ss.logged_filter = True

    c1, c2, c3 = st.columns([3.2, 1.3, 1.5], vertical_alignment="center")
    c1.markdown(f"**{len(results)}** de {len(all_results)} habitaciones compatibles"
                + (" · con filtros" if active else ""))
    if active:
        c2.button("Quitar filtros", icon=ICON["filter"], type="tertiary", on_click=clear_filters,
                  args=(all_results,))
    c3.segmented_control("Vista", list(VIEWS), key="f_view", format_func=lambda v: f"{VIEWS[v]} {v}",
                         label_visibility="collapsed", width="stretch")
    return results


# ---------------------------------------------------------------- lista y mapa

def match_card(r):
    room = r["room"]
    landlord = db.get_user(room["landlord_id"])
    with st.container(border=True, key=f"card{room['id']}"):
        c0, c1, c2, c3 = st.columns([1.2, 1.2, 3.5, 1.1], vertical_alignment="center")
        with c0:
            score_block(r["score"], size=32)
        with c1:
            room_photo(room, key=f"thumb{room['id']}")
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


def matches_map(results):
    """Mapa con las habitaciones filtradas; al pulsar un punto se muestra su resumen a la derecha."""
    left, right = st.columns([3, 1.6], gap="medium")
    with left:
        event = st.pydeck_chart(rooms_deck(results), height=470, key="matches_map",
                                on_select="rerun", selection_mode="single-object")
    picked = (event.selection.get("objects", {}) or {}).get(LAYER_ID, []) if event else []
    chosen = next((r for r in results if picked and r["room"]["id"] == picked[0]["id"]), None)
    with right:
        if not chosen:
            with st.container(border=True, key="cardmaphint"):
                st.markdown("**Pulsa un punto del mapa** para ver la habitación.")
                st.caption("El número es la compatibilidad. Ubicación aproximada por barrio.")
            return
        room = chosen["room"]
        with st.container(border=True, key="cardmapsel"):
            room_photo(room, key=f"thumbmap{room['id']}")
            score_block(chosen["score"], size=32)
            st.markdown(f"**{room['title']}**")
            st.caption(room_facts(room))
            badges(room_badges(room))
            st.button("Ver detalles", key=f"mapdet{room['id']}", width="stretch",
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
        room_photo(room, key="roomphoto")
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
            with cols[i % len(cols)], st.container(border=True, key=f"cardmate{m['id']}"):
                person_header(m, f", {m['age']}")
                st.caption(f"{m['occupation']} · de {m['origin']}")
                if m["bio"]:
                    st.caption(f"_{m['bio']}_")
                if p:
                    st.caption(habit_line(p))
                rating_line(m["id"])

        st.subheader("Casero")
        with st.container(border=True, key="cardlandlord"):
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
        st.caption(f"{ICON['zone']} Ubicación aproximada · {room['zone']}")
        st.pydeck_chart(rooms_deck([{"room": room, "score": scored[0] if scored else None}],
                                   zoom=14, show_scores=False), height=170, key=f"minimap{room_id}")


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
    st.caption("Tu presentación la ven caseros y compañeros; tus hábitos sirven para calcular la compatibilidad.")
    p = db.get_preferences(user["id"]) or {
        "budget_min": 400, "budget_max": 600, "zones": [], "move_in": date.today().isoformat(),
        "schedule": db.SCHEDULES[1], "cleanliness": 3, "noise": 2, "smokes": 0, "pets": 0, "own_bathroom": 0}

    with st.container(key="narrow"), st.form("prefs"):
        about = about_fields(user)

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
            db.update_user(user["id"], **about)
            db.save_preferences(user["id"], budget[0], budget[1], zones, move_in.isoformat(), schedule,
                                cleanliness, noise, smokes, pets, own_bathroom)
            flash("Perfil guardado")
            st.session_state._goto = PAGE_MATCHES  # el menú ya está dibujado: se cambia en la siguiente ejecución
            st.rerun()
