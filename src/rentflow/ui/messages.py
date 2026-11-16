"""Pantalla de mensajes (común a inquilino y casero): chat y valoraciones."""
import streamlit as st

from rentflow import db
from rentflow.ui.navigation import PAGE_MATCHES, PAGE_MY_ROOMS, go
from rentflow.ui.theme import ICON, empty_state

# Avatares (DESIGN.md §7) con iconos Material, sin emojis.
# Si se añaden mensajes automáticos de RentFlow, usar theme.APP_ICON como avatar.
AVATAR_ME = ":material/sentiment_satisfied:"
AVATAR_LANDLORD = ":material/home:"
AVATAR_MATE = ":material/person:"


def page_messages(user):
    st.title("Mensajes")
    convs = db.conversations_of(user["id"])
    if not convs:
        is_tenant = user["role"] == "inquilino"
        empty_state(
            "Todavía no tienes conversaciones. "
            + ("Contacta con una habitación desde tus matches." if is_tenant
               else "Cuando un inquilino te escriba, aparecerá aquí."),
            lambda: st.button("Ver mis matches" if is_tenant else "Ver mis habitaciones",
                              on_click=go, args=(PAGE_MATCHES if is_tenant else PAGE_MY_ROOMS,)),
        )
        return

    labels = {c["id"]: f"{c['title']} · {c['tenant_name']}" for c in convs}
    ids = list(labels)
    current = st.session_state.get("conversation_id")
    index = ids.index(current) if current in ids else 0
    conv_id = st.selectbox("Conversación", ids, index=index, format_func=labels.get, label_visibility="collapsed")
    st.session_state.conversation_id = conv_id
    conv = next(c for c in convs if c["id"] == conv_id)

    room = db.get_room(conv["room_id"])
    landlord = db.get_user(room["landlord_id"])
    mates = db.roommates(room["id"])
    tenant = db.get_user(conv["tenant_id"])
    people = ([f"{tenant['name']} (interesado)", f"{landlord['name']} (casero)"]
              + [f"{m['name']} (compañero)" for m in mates])
    st.caption(f"{ICON['mates']} En esta conversación: " + ", ".join(people))

    msgs = db.messages_of(conv_id)
    # Altura fija con scroll solo cuando hay muchos mensajes; si no, la caja se ajusta (más compacto)
    with st.container(border=True, height=440 if len(msgs) > 5 else "content"):
        for msg in msgs:
            mine = msg["author_id"] == user["id"]
            if mine:
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
        db.log_event(user["id"], "mensaje", room["id"])
        st.rerun()

    with st.expander("Valorar a alguien de esta conversación", icon=ICON["star"]):
        others = {p["id"]: p["name"] for p in [tenant, landlord] + mates if p["id"] != user["id"]}
        with st.form(f"review{conv_id}", clear_on_submit=True, border=False):
            c1, c2 = st.columns([2, 1])
            target_id = c1.selectbox("¿A quién?", list(others), format_func=others.get)
            rating = c2.slider("Nota", 1, 5, 5)
            comment = st.text_input("Comentario")
            if st.form_submit_button("Enviar valoración"):
                db.add_review(user["id"], target_id, rating, comment)
                db.log_event(user["id"], "resena", room["id"])
                st.success("¡Gracias por tu valoración!")
