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
