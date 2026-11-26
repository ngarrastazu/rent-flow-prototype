"""Pantallas del casero: mis habitaciones (solicitudes, búsqueda inversa, chats), publicar y perfil."""
from datetime import date
from html import escape

import streamlit as st

from rentflow import db, matching, rentals
from rentflow.ui.components import (
    about_fields,
    room_badges,
    room_facts,
    room_photo,
    verified_badge,
    votes_text,
)
from rentflow.ui.navigation import PAGE_MESSAGES, PAGE_PUBLISH, flash, go, open_chat
from rentflow.ui.theme import ICON, badge, badges, empty_state, score_block, score_style


def page_my_rooms(user):
    st.title("Mis habitaciones")
    rooms = db.rooms_of_landlord(user["id"])
    if not rooms:
        empty_state("Todavía no has publicado ninguna habitación.",
                    lambda: st.button("Publicar habitación", icon=ICON["publish"], type="primary",
                                      on_click=go, args=(PAGE_PUBLISH,)))
        return

    rented = sum(1 for r in rooms if r["tenant_id"])
    pending = db.count_pending_requests_of_landlord(user["id"])
    st.caption(f"{len(rooms)} habitaciones · {rented} alquiladas · **{pending} solicitudes pendientes**. "
               "Para cada una: solicitudes, inquilinos más compatibles y chats.")
    for room in rooms:
        room_card(user, room)
    if (req_id := st.session_state.get("_accept_dialog")) is not None:
        accept_dialog(user, req_id)


def room_status(room):
    """Insignia del estado del anuncio."""
    if room["tenant_id"]:
        return badge("Alquilada", "verified")
    return badge("Publicada", "brand") if room["active"] else badge("Pausada", "muted")


def room_card(user, room):
    mates = db.roommates(room["id"])
    with st.container(border=True, key=f"cardroom{room['id']}"):
        photo_col, head_col, act_col = st.columns([1, 4.2, 1.2], vertical_alignment="center")
        with photo_col:
            room_photo(room, key=f"thumbll{room['id']}")
        with head_col:
            st.markdown(f"**{escape(room['title'])}** {room_status(room)}", unsafe_allow_html=True)
            st.caption(room_facts(room) + f" · {ICON['mates']} " + (", ".join(m["name"] for m in mates)
                                                                     or "sin compañeros"))
            badges(room_badges(room))
        with act_col:
            if not room["tenant_id"]:
                st.button("Reactivar" if not room["active"] else "Pausar anuncio",
                          icon=":material/play_arrow:" if not room["active"] else ":material/pause:",
                          key=f"pause{room['id']}", type="tertiary",
                          on_click=toggle_pause, args=(user["id"], room["id"], room["active"]))

        if room["tenant_id"]:
            occupant = db.get_user(room["tenant_id"])
            c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
            c1.caption(f"Alquilada a **{occupant['name']}**. Puedes escribirle o darle de baja desde "
                       "«Mis inquilinos».")
            c2.button("Escribir", icon=ICON["chat"], key=f"occ{room['id']}", type="tertiary",
                      on_click=open_chat, args=(room["id"], occupant["id"]))
            return

        pending = db.requests_for_room(room["id"])
        interested = db.interested_in(room["id"])
        tab_req, tab_cand, tab_chat = st.tabs([f"Solicitudes ({len(pending)})", "Más compatibles",
                                               f"Chats ({len(interested)})"])
        with tab_req:
            if not pending:
                st.caption("Aún no hay solicitudes. Cuando un inquilino la pida, la verás aquí con su "
                           "compatibilidad y la opinión de los compañeros.")
            mates_prefs = matching.mates_preferences(mates)
            for req in pending:
                request_row(room, req, mates_prefs)
        with tab_cand:
            lines = []
            for cand in matching.candidates_for(room["id"]):
                t = cand["tenant"]
                _, label = score_style(cand["score"])
                check = " ✓" if t["verified"] else ""
                lines.append(f"**{cand['score']} %** {label.lower()} · {t['name']}{check}, {t['age']} · "
                             f"{t['occupation']}")
            # un solo bloque con saltos de línea: lista compacta, sin hueco entre filas
            st.caption("  \n".join(lines) if lines else "Nadie que busque piso encaja ahora mismo.")
        with tab_chat:
            if not interested:
                st.caption("Aún nadie te ha escrito por esta habitación.")
            for conv in interested:
                st.button(f"Chat con {conv['tenant_name']}", icon=ICON["chat"], key=f"conv{conv['id']}",
                          type="tertiary", on_click=go, args=(PAGE_MESSAGES,),
                          kwargs={"conversation_id": conv["id"]})


def request_row(room, req, mates_prefs):
    """Una solicitud pendiente: quién es, cuánto encaja, qué opinan los compañeros y qué decide el casero."""
    cand = db.get_user(req["tenant_id"])
    prefs = db.get_preferences(cand["id"])
    scored = matching.score_room(prefs, room, mates_prefs) if prefs else None
    with st.container(border=True, key=f"cardrq{req['id']}"):
        c0, c1, c2 = st.columns([1, 4, 1.4], vertical_alignment="center")
        with c0:
            if scored:
                score_block(scored[0], size=26)
            else:
                st.caption("No cumple sus filtros")
        with c1:
            st.markdown(f"**{escape(cand['name'])}**, {cand['age']} {verified_badge(cand)}",
                        unsafe_allow_html=True)
            st.caption(f"{cand['occupation']} · de {cand['origin']} · entrada {req['move_in']} · "
                       f"{req['months']} meses · enviada el {req['created_at'][:10]}")
            if req["message"]:
                st.caption(f"«{req['message']}»")
            st.caption(f"{ICON['mates']} " + votes_text(req["id"]))
        with c2:
            st.button("Aceptar", icon=":material/check:", key=f"acc{req['id']}", width="stretch",
                      on_click=lambda: st.session_state.update(_accept_dialog=req["id"]))
            st.button("Rechazar", key=f"rej{req['id']}", type="tertiary",
                      on_click=reject, args=(room["landlord_id"], req["id"]))
            st.button("Chat", icon=ICON["chat"], key=f"rqchat{req['id']}", type="tertiary",
                      on_click=open_chat, args=(room["id"], cand["id"]))


@st.dialog("Aceptar solicitud", on_dismiss=lambda: st.session_state.pop("_accept_dialog", None))
def accept_dialog(user, request_id):
    # La marca _accept_dialog mantiene el diálogo abierto; se borra al confirmar, cancelar o cerrarlo
    req = db.get_request(request_id)
    if not req or req["status"] != "pendiente":
        st.session_state.pop("_accept_dialog", None)
        st.caption("Esta solicitud ya no está pendiente.")
        return
    others = len(db.requests_for_room(req["room_id"])) - 1
    st.markdown(f"¿Alquilar **{req['title']}** a **{req['tenant_name']}**?")
    st.caption(f"{ICON['mates']} {votes_text(request_id)}")
    st.caption("La habitación dejará de mostrarse en los matches"
               + (" y se cerrará la otra solicitud" if others == 1 else
                  f" y se cerrarán las otras {others} solicitudes" if others > 1 else "")
               + ". Todos reciben un aviso en el chat. Podrás darle de baja más adelante desde «Mis inquilinos».")
    c1, c2 = st.columns(2)
    if c1.button("Aceptar y alquilar", type="primary", width="stretch"):
        try:
            rentals.accept_request(request_id, user["id"])
        except rentals.RentalError as e:
            st.error(str(e))
        else:
            st.session_state.pop("_accept_dialog", None)
            flash(f"Habitación alquilada a {req['tenant_name']}")
            st.rerun()
    if c2.button("Cancelar", width="stretch"):
        st.session_state.pop("_accept_dialog", None)
        st.rerun()


def reject(landlord_id, request_id):
    try:
        rentals.reject_request(request_id, landlord_id)
        flash("Solicitud rechazada. El inquilino recibe un aviso en el chat.")
    except rentals.RentalError as e:
        flash(str(e))


def toggle_pause(landlord_id, room_id, active):
    try:
        rentals.set_paused(landlord_id, room_id, paused=bool(active))
        flash("Anuncio pausado: no sale en los matches" if active else "Anuncio publicado de nuevo")
    except rentals.RentalError as e:
        flash(str(e))


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


def page_landlord_profile(user):
    st.title("Mi perfil")
    st.caption("Es lo que ven los inquilinos en la ficha de tus habitaciones, junto a tus reseñas.")
    with st.container(key="narrow"), st.form("landlord_profile"):
        about = about_fields(user)
        if st.form_submit_button("Guardar perfil", type="primary"):
            db.update_user(user["id"], **about)
            flash("Perfil guardado")
            st.rerun()  # para que la barra lateral muestre los datos nuevos
