"""Pruebas de humo de la interfaz con streamlit.testing (sin navegador)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from rentflow import db, seed

APP = Path(__file__).parent.parent / "app.py"


def _app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    seed.seed()
    return AppTest.from_file(str(APP), default_timeout=30)


def test_landing_renders(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    assert not at.exception
    assert any("Dinos qué buscas" in m.value for m in at.markdown)


def test_demo_flow_as_mario(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    at.button[0].click().run()  # ▶ Probar como Mario (demo)
    assert not at.exception
    assert at.title[0].value == "Tus matches"
    first_score = next(m.value for m in at.markdown if "class=\"rf-score\"" in m.value)
    assert "94 %" in first_score and "Match excelente" in first_score

    at.button(key="det1").click().run()  # Ver detalles de la habitación de Chamberí
    assert not at.exception
    assert at.title[0].value == "Habitación con baño propio en Chamberí"

    for page in ["Mi perfil y hábitos", "Mensajes", "Métricas (equipo)"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page


def test_filters_and_map_view(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    at.button[0].click().run()  # Mario
    total = next(m.value for m in at.markdown if "habitaciones compatibles" in m.value)
    at.toggle(key="f_bath").set_value(True).run()
    assert not at.exception
    filtered = next(m.value for m in at.markdown if "habitaciones compatibles" in m.value)
    assert "con filtros" in filtered and filtered != total
    at.session_state["f_view"] = "Mapa"
    at.run()
    assert not at.exception
    from rentflow import db as _db
    assert _db.users_with_event("filtrar") == 1 and _db.users_with_event("ver_mapa") == 1


def test_tenant_edits_occupation_and_bio(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    at.button[0].click().run()  # Mario
    at.sidebar.radio[0].set_value("Mi perfil y hábitos").run()
    assert not at.exception
    name = next(t for t in at.text_input if t.label == "Nombre")
    assert name.disabled  # verificado: el nombre no se cambia
    next(t for t in at.text_input if t.label == "¿A qué te dedicas?").set_value("Analista de riesgos")
    at.text_area[0].set_value("Me gusta cocinar y correr por el Retiro.")
    next(b for b in at.button if b.label == "Guardar y ver mis matches").click().run()
    assert not at.exception
    from rentflow import db as _db
    mario = _db.get_user(1)
    assert mario["occupation"] == "Analista de riesgos"
    assert mario["bio"] == "Me gusta cocinar y correr por el Retiro."
    assert mario["name"] == "Mario Rossi"


def test_landlord_profile_page(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import db as _db
    carmen = _db.find_user_by_name("Carmen Ruiz")
    at.session_state["login_choice"] = carmen["id"]
    next(b for b in at.button if b.label == "Entrar").click().run()
    at.sidebar.radio[0].set_value("Mi perfil").run()
    assert not at.exception
    at.text_area[0].set_value("Respondo en el día. Las averías, en menos de 48 h.")
    next(b for b in at.button if b.label == "Guardar perfil").click().run()
    assert not at.exception
    assert _db.get_user(carmen["id"])["bio"] == "Respondo en el día. Las averías, en menos de 48 h."


def _login(at, name):
    from rentflow import db as _db
    at.session_state["login_choice"] = _db.find_user_by_name(name)["id"]
    next(b for b in at.button if b.label == "Entrar").click().run()
    assert not at.exception


def test_landlord_accepts_request_from_dialog(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import db as _db
    from rentflow import rentals
    rentals.send_request(1, 1, "Hola, soy Mario", "2027-01-10", 12)  # Mario pide la de Chamberí
    _login(at, "Carmen Ruiz")
    assert any("Solicitudes (2)" in t.label for t in at.tabs)  # Mario y el rival
    mario_req = _db.latest_request(1, 1)["id"]
    at.button(key=f"acc{mario_req}").click().run()
    next(b for b in at.button if b.label == "Aceptar y alquilar").click().run()
    assert not at.exception
    assert _db.get_room(1)["tenant_id"] == 1

    at.sidebar.radio[0].set_value("Mis inquilinos").run()
    assert not at.exception
    assert any("Mario Rossi" in m.value for m in at.markdown)


def test_tenant_request_pages(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import rentals
    at.button[0].click().run()  # Mario
    for page in ["Mis solicitudes", "Mi piso"]:
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
    rentals.send_request(1, 1, "", "2027-01-10", 12)
    at.sidebar.radio[0].set_value("Mis solicitudes").run()
    assert not at.exception
    assert any("Pendiente" in m.value for m in at.markdown)


def test_roommate_votes_in_my_flat(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import db as _db
    _login(at, "Tom Becker")
    at.sidebar.radio[0].set_value("Mi piso").run()
    assert not at.exception
    rival = _db.requests_for_room(1)[0]["id"]
    at.button(key=f"up{rival}").click().run()  # Tom cambia de opinión: ahora sí le encaja
    assert not at.exception
    assert [v["vote"] for v in _db.votes_for(rival)] == [1, 1]


def test_tenant_sends_request_from_dialog(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import db as _db
    at.button[0].click().run()  # Mario
    at.button(key="det1").click().run()
    next(b for b in at.button if b.label == "Solicitar esta habitación").click().run()
    next(b for b in at.button if b.label == "Enviar solicitud").click().run()
    assert not at.exception
    req = _db.latest_request(1, 1)
    assert req and req["status"] == "pendiente" and req["months"] == 12
    assert any("Solicitud enviada" in m.value for m in at.markdown)


def test_gallery_and_photo_manager(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import db as _db
    at.button[0].click().run()  # Mario
    at.button(key="det1").click().run()
    assert not at.exception
    at.session_state["gal1"] = 3  # cocina
    at.run()
    assert not at.exception
    assert any("Foto 4 de 5 · Cocina" in c.value for c in at.caption)

    next(b for b in at.sidebar.button if b.label == "Cerrar sesión").click().run()
    _login(at, "Carmen Ruiz")
    at.button(key="photos1").click().run()
    assert not at.exception
    kitchen = next(p for p in _db.room_photos(1) if p["space"] == "Cocina")
    at.button(key=f"mn{kitchen['id']}").click().run()
    assert not at.exception
    assert _db.main_photo(1)["id"] == kitchen["id"]


def test_publish_page_renders(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    _login(at, "Carmen Ruiz")
    at.sidebar.radio[0].set_value("Publicar habitación").run()
    assert not at.exception


def test_private_message_to_landlord(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch).run()
    from rentflow import db as _db
    at.button[0].click().run()  # Mario
    at.button(key="det1").click().run()
    at.button(key="dmlandlord").click().run()  # «Enviar mensaje al casero»
    assert not at.exception
    assert at.selectbox[0].format_func(at.selectbox[0].value) == "Privado · Carmen Ruiz"
    at.chat_input[0].set_value("Hola Carmen, ¿la habitación tiene calefacción?").run()
    assert not at.exception
    carmen = _db.find_user_by_name("Carmen Ruiz")["id"]
    conv = _db.direct_conversations_of(carmen)[0]
    assert [m["text"] for m in _db.messages_of(conv["id"])] == ["Hola Carmen, ¿la habitación tiene calefacción?"]
    assert _db.count_events("mensaje_privado") == 1
