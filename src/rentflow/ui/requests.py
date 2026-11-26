"""Pantallas del inquilino sobre alquiler: «Mis solicitudes» y «Mi piso» (donde vive y a quién opinar)."""
from html import escape

import streamlit as st

from rentflow import db, matching, rentals
from rentflow.ui.components import (
    habit_line,
    person_header,
    rating_line,
    request_badge,
    room_facts,
    room_photo,
    verified_badge,
    votes_text,
)
from rentflow.ui.navigation import PAGE_MATCHES, PAGE_MY_FLAT, flash, go, open_chat
from rentflow.ui.theme import ICON, badge, badges, empty_state

# ---------------------------------------------------------------- Mis solicitudes


def page_my_requests(user):
    st.title("Mis solicitudes")
    reqs = db.requests_of_tenant(user["id"])
    if not reqs:
        empty_state("Todavía no has solicitado ninguna habitación. Ábrela desde tus matches y pulsa «Solicitar».",
                    lambda: st.button("Ver mis matches", on_click=go, args=(PAGE_MATCHES,)))
        return

    pending = sum(r["status"] == "pendiente" for r in reqs)
    st.caption(f"{len(reqs)} solicitudes · {pending} pendientes. El casero decide; los compañeros del piso "
               "dan su opinión antes.")
    for req in reqs:
        request_card(user, req)


def request_card(user, req):
    room = db.get_room(req["room_id"])
    with st.container(border=True, key=f"cardreq{req['id']}"):
        c0, c1, c2 = st.columns([1.1, 4, 1.4], vertical_alignment="center")
        with c0:
            room_photo(room, key=f"thumbreq{req['id']}")
        with c1:
            st.markdown(f"**{escape(room['title'])}** {request_badge(req['status'])}", unsafe_allow_html=True)
            st.caption(room_facts(room))
            detail = f"Enviada el {req['created_at'][:10]} · entrada {req['move_in']} · {req['months']} meses"
            if req["status"] == "pendiente":
                detail += " · " + votes_text(req["id"], names=False)
            st.caption(detail)
            if req["note"]:
                st.caption(f"_{req['note']}_")
        with c2:
            if req["status"] == "aceptada" and room["tenant_id"] == user["id"]:
                st.button("Ir a mi piso", key=f"flat{req['id']}", width="stretch",
                          on_click=go, args=(PAGE_MY_FLAT,))
            elif room["active"]:
                st.button("Ver habitación", key=f"see{req['id']}", width="stretch",
                          on_click=go, args=(PAGE_MATCHES,), kwargs={"selected_room": room["id"]})
            st.button("Chat", icon=ICON["chat"], key=f"chatreq{req['id']}", type="tertiary",
                      on_click=open_chat, args=(room["id"], user["id"]))
            if req["status"] == "pendiente":
                st.button("Retirar", key=f"wd{req['id']}", type="tertiary",
                          on_click=withdraw, args=(req["id"], user["id"]))


def withdraw(request_id, tenant_id):
    try:
        rentals.withdraw_request(request_id, tenant_id)
        flash("Solicitud retirada")
    except rentals.RentalError as e:
        flash(str(e))


# ---------------------------------------------------------------- Mi piso


def page_my_flat(user):
    st.title("Mi piso")
    room = db.occupied_room(user["id"])
    member_of = db.member_rooms(user["id"])
    if not room and not member_of:
        empty_state("Todavía no vives en ningún piso de RentFlow. Cuando un casero acepte tu solicitud, "
                    "lo verás aquí.",
                    lambda: st.button("Ver mis matches", on_click=go, args=(PAGE_MATCHES,)))
        return

    if room:
        st.caption("Tu habitación, tu casero y con quién vives.")
        home_card(user, room)
    for flat_room in member_of:
        st.subheader(f"Buscáis compañero · {flat_room['title']}")
        st.caption("Vives en este piso. Opina sobre quien quiere entrar: el casero ve vuestra opinión antes de "
                   "decidir.")
        reqs = [r for r in db.pending_requests_for_member(user["id"]) if r["room_id"] == flat_room["id"]]
        if not reqs:
            st.caption("No hay solicitudes pendientes ahora mismo.")
        for req in reqs:
            candidate_card(user, req)


def home_card(user, room):
    landlord = db.get_user(room["landlord_id"])
    mates = db.roommates(room["id"])
    my_prefs = db.get_preferences(user["id"])
    with st.container(border=True, key="cardhome"):
        c0, c1 = st.columns([1.3, 4], vertical_alignment="top")
        with c0:
            room_photo(room, key="thumbhome")
        with c1:
            st.markdown(f"**{escape(room['title'])}** {badge('Es tu habitación', 'verified')}",
                        unsafe_allow_html=True)
            st.caption(room_facts(room, with_bathroom=True))
            person_header(landlord, " · casero")
            rating_line(landlord["id"])
            st.button("Escribir al casero y a los compañeros", icon=ICON["chat"], key="chathome",
                      on_click=open_chat, args=(room["id"], user["id"]))
    if mates:
        st.markdown("#### Tus compañeros")
        cols = st.columns(min(len(mates), 3))
        for i, m in enumerate(mates):
            p = db.get_preferences(m["id"])
            with cols[i % len(cols)], st.container(border=True, key=f"cardhm{m['id']}"):
                person_header(m, f", {m['age']}")
                st.caption(f"{m['occupation']} · de {m['origin']}")
                if p and my_prefs:
                    st.caption(f"Afinidad de hábitos contigo: **{matching.pair_affinity(my_prefs, p)} %**")
                rating_line(m["id"])


def candidate_card(user, req):
    cand = db.get_user(req["tenant_id"])
    cp, mp = db.get_preferences(cand["id"]), db.get_preferences(user["id"])
    my_vote = next((v["vote"] for v in db.votes_for(req["id"]) if v["user_id"] == user["id"]), None)
    with st.container(border=True, key=f"cardcand{req['id']}"):
        c1, c2 = st.columns([4, 1.5], vertical_alignment="center")
        with c1:
            st.markdown(f"**{escape(cand['name'])}**, {cand['age']} {verified_badge(cand)}",
                        unsafe_allow_html=True)
            st.caption(f"{cand['occupation']} · de {cand['origin']} · entrada {req['move_in']} · "
                       f"{req['months']} meses")
            if cand["bio"]:
                st.caption(f"_{cand['bio']}_")
            if req["message"]:
                st.caption(f"«{req['message']}»")
            if cp and mp:
                st.caption(f"Afinidad de hábitos contigo: **{matching.pair_affinity(mp, cp)} %** · "
                           + habit_line(cp))
            rating_line(cand["id"])
        with c2:
            if my_vote:
                badges([badge("Te encaja" if my_vote == 1 else "No te encaja",
                              "verified" if my_vote == 1 else "muted")])
            st.button("Me encaja", icon=":material/thumb_up:", key=f"up{req['id']}", width="stretch",
                      disabled=my_vote == 1, on_click=cast_vote, args=(req["id"], user["id"], 1))
            st.button("No me encaja", icon=":material/thumb_down:", key=f"down{req['id']}", type="tertiary",
                      disabled=my_vote == -1, on_click=cast_vote, args=(req["id"], user["id"], -1))


def cast_vote(request_id, user_id, value):
    try:
        rentals.vote(request_id, user_id, value)
        flash("Opinión guardada. El casero la verá al decidir.")
    except rentals.RentalError as e:
        flash(str(e))
