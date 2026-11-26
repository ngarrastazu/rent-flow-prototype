"""Pantalla del casero «Mis inquilinos»: quién vive en sus pisos, escribirles y darles de baja."""
from html import escape

import streamlit as st

from rentflow import db, rentals
from rentflow.ui.components import person_header, rating_line, room_facts, room_photo
from rentflow.ui.navigation import PAGE_MY_ROOMS, flash, go, open_chat
from rentflow.ui.theme import ICON, badge, empty_state

KIND_LABEL = {
    "ocupante": ("Vive en esta habitación", "verified"),
    "compañero": ("Compañero del piso", "brand"),
}


def page_residents(user):
    st.title("Mis inquilinos")
    residents = db.residents_of_landlord(user["id"])
    if not residents:
        empty_state("Todavía no vive nadie en tus pisos. Cuando aceptes una solicitud, lo verás aquí.",
                    lambda: st.button("Ver mis habitaciones", on_click=go, args=(PAGE_MY_ROOMS,)))
        return

    people = {r["id"] for r in residents}
    st.caption(f"{len(people)} personas viven en tus pisos. Escríbeles o dales de baja cuando dejen la "
               "habitación: la habitación vuelve a publicarse.")
    by_room = {}
    for r in residents:
        by_room.setdefault(r["room_id"], []).append(r)
    for room_id, people_in_room in by_room.items():
        room = db.get_room(room_id)
        with st.container(border=True, key=f"cardres{room_id}"):
            c0, c1 = st.columns([1, 6], vertical_alignment="center")
            with c0:
                room_photo(room, key=f"thumbres{room_id}")
            with c1:
                st.markdown(f"**{escape(room['title'])}**")
                st.caption(room_facts(room))
            for person in people_in_room:
                resident_row(user, room, person)
    if pending := st.session_state.get("_remove_dialog"):
        remove_dialog(user, *pending)


def resident_row(user, room, person):
    label, kind = KIND_LABEL[person["kind"]]
    with st.container(border=True, key=f"cardrp{room['id']}_{person['id']}"):
        c1, c2 = st.columns([4, 2.2], vertical_alignment="center")
        with c1:
            st.markdown(f"**{escape(person['name'])}**, {person['age']} {badge(label, kind)}",
                        unsafe_allow_html=True)
            info = f"{person['occupation']} · de {person['origin']}"
            if person["since"]:
                info += f" · desde el {person['since'][:10]}"
            st.caption(info)
            if person["bio"]:
                st.caption(f"_{person['bio']}_")
            rating_line(person["id"])
        with c2:
            b1, b2 = st.columns(2)
            b1.button("Escribir", icon=ICON["chat"], key=f"wr{room['id']}_{person['id']}", width="stretch",
                      on_click=open_chat, args=(room["id"], person["id"]))
            b2.button("Dar de baja", icon=":material/person_remove:", key=f"rm{room['id']}_{person['id']}",
                      type="tertiary", width="stretch",
                      on_click=lambda: st.session_state.update(_remove_dialog=(room["id"], person["id"])))


@st.dialog("Dar de baja", on_dismiss=lambda: st.session_state.pop("_remove_dialog", None))
def remove_dialog(user, room_id, person_id):
    # La marca _remove_dialog mantiene el diálogo abierto; se borra al confirmar, cancelar o cerrarlo
    room, person = db.get_room(room_id), db.get_user(person_id)
    occupant = room["tenant_id"] == person_id
    person_header(person)
    st.caption(
        f"Dejará de figurar en «{room['title']}». "
        + ("La habitación volverá a publicarse y a recibir solicitudes." if occupant else
           "Cambia la compatibilidad de esa habitación con todos los inquilinos, porque se compara con los "
           "compañeros que viven en el piso.")
        + " Recibirá un aviso en el chat.")
    note = st.text_input("Motivo (opcional)", placeholder="Fin del contrato, se muda…")
    c1, c2 = st.columns(2)
    if c1.button("Dar de baja", type="primary", width="stretch"):
        try:
            rentals.remove_resident(user["id"], room_id, person_id, note)
        except rentals.RentalError as e:
            st.error(str(e))
        else:
            st.session_state.pop("_remove_dialog", None)
            flash(f"{person['name']} ya no vive en «{room['title']}»")
            st.rerun()
    if c2.button("Cancelar", width="stretch"):
        st.session_state.pop("_remove_dialog", None)
        st.rerun()
