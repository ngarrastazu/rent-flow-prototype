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
