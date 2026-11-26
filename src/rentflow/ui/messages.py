"""Pantalla de mensajes (común a inquilino y casero): chats de piso, chats privados y valoraciones.

- Chat de piso (grupo): una habitación + el interesado, con el casero y los compañeros. Aquí llegan las
  solicitudes y los avisos automáticos de RentFlow.
- Chat privado: solo dos personas (p. ej. un inquilino y el casero, o el casero y uno de sus inquilinos).
"""
import streamlit as st

from rentflow import db
from rentflow.ui.components import person_header
from rentflow.ui.navigation import PAGE_MATCHES, PAGE_MY_ROOMS, go
from rentflow.ui.theme import APP_ICON, ICON, empty_state

# Avatares (DESIGN.md §7) con iconos Material, sin emojis; los mensajes automáticos llevan el icono de la app.
AVATAR_ME = ":material/sentiment_satisfied:"
AVATAR_LANDLORD = ":material/home:"
AVATAR_MATE = ":material/person:"

ROLE_LABEL = {"casero": "casero", "inquilino": "inquilino"}


def page_messages(user):
    st.title("Mensajes")
    groups = db.conversations_of(user["id"])
    directs = db.direct_conversations_of(user["id"])
    if not groups and not directs:
        is_tenant = user["role"] == "inquilino"
        empty_state(
            "Todavía no tienes conversaciones. "
            + ("Contacta con una habitación desde tus matches o envía un mensaje a su casero."
               if is_tenant else "Cuando un inquilino te escriba, aparecerá aquí."),
            lambda: st.button("Ver mis matches" if is_tenant else "Ver mis habitaciones",
                              on_click=go, args=(PAGE_MATCHES if is_tenant else PAGE_MY_ROOMS,)),
        )
        return

    # Todas juntas, la de mensaje más reciente primero
    convs = sorted(groups + directs, key=lambda c: (c["last_msg"], c["id"]), reverse=True)
    labels = {c["id"]: (f"Privado · {c['other_name']}" if c["kind"] == "privado"
                        else f"{c['title']} · {c['tenant_name']}") for c in convs}
    ids = list(labels)
    current = st.session_state.get("conversation_id")
    index = ids.index(current) if current in ids else 0
    conv_id = st.selectbox("Conversación", ids, index=index, format_func=labels.get, label_visibility="collapsed")
    st.session_state.conversation_id = conv_id
    conv = next(c for c in convs if c["id"] == conv_id)

    if conv["kind"] == "privado":
        other = db.get_user(conv["other_id"])
        st.caption(f"{ICON['user']} Conversación privada: solo tú y {other['name']} "
                   f"({ROLE_LABEL.get(other['role'], other['role'])}) veis estos mensajes.")
        room_id, others = None, [other]
    else:
        room = db.get_room(conv["room_id"])
        landlord = db.get_user(room["landlord_id"])
        mates = db.roommates(room["id"])
        tenant = db.get_user(conv["tenant_id"])
        tenant_role = "vive aquí" if room["tenant_id"] == tenant["id"] else (
            "compañero" if any(m["id"] == tenant["id"] for m in mates) else "interesado")
        people = ([f"{tenant['name']} ({tenant_role})", f"{landlord['name']} (casero)"]
                  + [f"{m['name']} (compañero)" for m in mates if m["id"] != tenant["id"]])
        st.caption(f"{ICON['mates']} Chat del piso: " + ", ".join(people))
        room_id = room["id"]
        others = [p for p in [tenant, landlord] + mates if p["id"] != user["id"]]

    chat(user, conv_id, room_id)
    review_box(user, conv_id, room_id, others)


def chat(user, conv_id, room_id):
    msgs = db.messages_of(conv_id)
    if not msgs:
        st.caption("Aún no hay mensajes. Escribe el primero.")
    else:
        # Altura fija con scroll solo cuando hay muchos mensajes; si no, la caja se ajusta (más compacto)
        with st.container(border=True, height=440 if len(msgs) > 5 else "content"):
            for msg in msgs:
                mine = msg["author_id"] == user["id"]
                if msg["author_role"] == "sistema":
                    avatar = str(APP_ICON)
                elif mine:
                    avatar = AVATAR_ME
                elif msg["author_role"] == "casero":
                    avatar = AVATAR_LANDLORD
                else:
                    avatar = AVATAR_MATE
                with st.chat_message("user" if mine else "assistant", avatar=avatar):
                    st.markdown(f"**{msg['author_name']}** :gray[· {msg['created_at'][11:16]}]")
                    st.write(msg["text"])

    text = st.chat_input("Escribe un mensaje…")
    if text:
        db.send_message(conv_id, user["id"], text)
        db.log_event(user["id"], "mensaje" if room_id else "mensaje_privado", room_id)
        st.rerun()


def review_box(user, conv_id, room_id, others):
    with st.expander("Valorar a alguien de esta conversación" if len(others) > 1 else
                     f"Valorar a {others[0]['name']}" if others else "Valorar", icon=ICON["star"]):
        if not others:
            st.caption("No hay nadie más en esta conversación.")
            return
        names = {p["id"]: p["name"] for p in others}
        with st.form(f"review{conv_id}", clear_on_submit=True, border=False):
            c1, c2 = st.columns([2, 1])
            if len(others) > 1:
                target_id = c1.selectbox("¿A quién?", list(names), format_func=names.get)
            else:
                target_id = others[0]["id"]
                with c1:
                    person_header(others[0])
            rating = c2.slider("Nota", 1, 5, 5)
            comment = st.text_input("Comentario")
            if st.form_submit_button("Enviar valoración"):
                db.add_review(user["id"], target_id, rating, comment)
                db.log_event(user["id"], "resena", room_id)
                st.success("¡Gracias por tu valoración!")
