"""Fixtures comunes: cada test usa una base de datos temporal, nunca rentflow.db."""
import pytest

from rentflow import db, seed


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Base de datos vacía en un directorio temporal."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    return db.DB_PATH


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    """Base de datos temporal con los datos de la demo (misma semilla que seed.py)."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    seed.seed()
    return db.DB_PATH
