"""Base de datos SQLite de RentFlow: esquema y funciones de acceso."""
import os
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

Row = dict[str, Any]

# src/rentflow/db.py -> raíz del proyecto -> data/rentflow.db (se puede cambiar con RENTFLOW_DB_PATH)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("RENTFLOW_DB_PATH", PROJECT_ROOT / "data" / "rentflow.db"))

ZONES = [
    "Chamberí", "Malasaña", "Chueca", "Salamanca", "Retiro", "Lavapiés",
    "La Latina", "Argüelles", "Moncloa", "Tetuán", "Arganzuela", "Usera",
]
SCHEDULES = ["Mañanas (me levanto temprano)", "Horario normal", "Noches / turnos"]

# Centro aproximado de cada barrio (lat, lon) para el mapa. Es orientativo: no hay direcciones reales.
ZONE_COORDS = {
    "Chamberí": (40.4340, -3.7036), "Malasaña": (40.4262, -3.7046), "Chueca": (40.4228, -3.6976),
    "Salamanca": (40.4300, -3.6780), "Retiro": (40.4115, -3.6770), "Lavapiés": (40.4087, -3.7008),
    "La Latina": (40.4108, -3.7106), "Argüelles": (40.4302, -3.7160), "Moncloa": (40.4390, -3.7240),
    "Tetuán": (40.4600, -3.6985), "Arganzuela": (40.3985, -3.6955), "Usera": (40.3875, -3.7070),
}
MADRID_CENTER = (40.4210, -3.7030)


def room_coords(room) -> tuple[float, float]:
    """Posición aproximada de la habitación: centro del barrio + desplazamiento fijo según su id.

    Determinista (no usa random) para que cada piso salga siempre en el mismo punto y no se solapen.
    """
    lat, lon = ZONE_COORDS.get(room["zone"], MADRID_CENTER)
    k = room["id"] * 2654435761 % 2**32  # hash multiplicativo de Knuth
    return lat + ((k % 1000) / 1000 - 0.5) * 0.008, lon + ((k // 1000 % 1000) / 1000 - 0.5) * 0.010

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    age         INTEGER,
    role        TEXT NOT NULL CHECK (role IN ('inquilino', 'casero')),
    occupation  TEXT,
    origin      TEXT,
    bio         TEXT,
    verified    INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Hábitos y lo que busca cada inquilino (también los compañeros que ya viven en un piso)
CREATE TABLE IF NOT EXISTS preferences (
    user_id       INTEGER PRIMARY KEY REFERENCES users(id),
    budget_min    INTEGER,
    budget_max    INTEGER,
    zones         TEXT,              -- zonas separadas por "|"
    move_in       TEXT,              -- fecha ISO AAAA-MM-DD
    schedule      TEXT,
    cleanliness   INTEGER,           -- 1 (relajado) a 5 (muy ordenado)
    noise         INTEGER,           -- 1 (silencio) a 5 (fiestas en casa)
    smokes        INTEGER DEFAULT 0,
    pets          INTEGER DEFAULT 0,
    own_bathroom  INTEGER DEFAULT 0  -- 1 = necesita baño propio
);

CREATE TABLE IF NOT EXISTS rooms (
    id               INTEGER PRIMARY KEY,
    landlord_id      INTEGER NOT NULL REFERENCES users(id),
    title            TEXT,
    zone             TEXT,
    price            INTEGER,
    size_m2          INTEGER,
    own_bathroom     INTEGER DEFAULT 0,
    available_from   TEXT,
    smoking_allowed  INTEGER DEFAULT 0,
    pets_allowed     INTEGER DEFAULT 0,
    description      TEXT,
    photo            BLOB,
    active           INTEGER DEFAULT 1
);

-- Compañeros que ya viven en el piso
CREATE TABLE IF NOT EXISTS room_members (
    room_id  INTEGER REFERENCES rooms(id),
    user_id  INTEGER REFERENCES users(id),
    PRIMARY KEY (room_id, user_id)
);

-- Reseñas de caseros y de compañeros
CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY,
    author_id   INTEGER REFERENCES users(id),
    target_id   INTEGER REFERENCES users(id),
    rating      INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Una conversación por inquilino interesado y habitación (casero + compañeros incluidos)
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY,
    room_id     INTEGER REFERENCES rooms(id),
    tenant_id   INTEGER REFERENCES users(id),
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (room_id, tenant_id)
);

CREATE TABLE IF NOT EXISTS messages (
    id               INTEGER PRIMARY KEY,
    conversation_id  INTEGER REFERENCES conversations(id),
    author_id        INTEGER REFERENCES users(id),
    text             TEXT,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Registro de acciones para medir las hipótesis (ver la página "Métricas")
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER,
    kind        TEXT,     -- ver_matches, ver_detalle, ver_resenas, contactar, mensaje, resena
    room_id     INTEGER,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Abre una conexión, hace commit (o rollback si hay error) y la cierra siempre.

    `with sqlite3.connect(...)` por sí solo no cierra la conexión; en Windows eso
    puede impedir borrar `rentflow.db` al reiniciar la demo.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:  # transacción: commit o rollback
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


def query(sql: str, params: Sequence[Any] = ()) -> list[Row]:
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def query_one(sql: str, params: Sequence[Any] = ()) -> Row | None:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: Sequence[Any] = ()) -> int | None:
    with connect() as conn:
        return conn.execute(sql, params).lastrowid


def is_empty() -> bool:
    return query_one("SELECT COUNT(*) AS n FROM users")["n"] == 0


# ---------- Usuarios y preferencias ----------

def get_user(user_id: int) -> Row | None:
    return query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def find_user_by_name(name: str) -> Row | None:
    return query_one("SELECT * FROM users WHERE name = ? ORDER BY id LIMIT 1", (name,))


def list_users(role=None):
    if role:
        return query("SELECT * FROM users WHERE role = ? ORDER BY name", (role,))
    return query("SELECT * FROM users ORDER BY role, name")


def create_user(name, age, role, occupation, origin, bio="", verified=0):
    return execute(
        "INSERT INTO users (name, age, role, occupation, origin, bio, verified) VALUES (?,?,?,?,?,?,?)",
        (name, age, role, occupation, origin, bio, verified),
    )


def update_user(user_id, name, age, occupation, origin, bio):
    """Actualiza los datos personales del perfil (no cambia el rol ni la verificación)."""
    execute("UPDATE users SET name = ?, age = ?, occupation = ?, origin = ?, bio = ? WHERE id = ?",
            (name, age, occupation, origin, bio, user_id))


def get_preferences(user_id):
    p = query_one("SELECT * FROM preferences WHERE user_id = ?", (user_id,))
    if p:
        p["zones"] = [z for z in (p["zones"] or "").split("|") if z]
    return p


def save_preferences(user_id, budget_min, budget_max, zones, move_in, schedule,
                     cleanliness, noise, smokes, pets, own_bathroom):
    execute(
        """INSERT INTO preferences (user_id, budget_min, budget_max, zones, move_in, schedule,
                                    cleanliness, noise, smokes, pets, own_bathroom)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             budget_min=excluded.budget_min, budget_max=excluded.budget_max, zones=excluded.zones,
             move_in=excluded.move_in, schedule=excluded.schedule, cleanliness=excluded.cleanliness,
             noise=excluded.noise, smokes=excluded.smokes, pets=excluded.pets,
             own_bathroom=excluded.own_bathroom""",
        (user_id, budget_min, budget_max, "|".join(zones), move_in, schedule,
         cleanliness, noise, int(smokes), int(pets), int(own_bathroom)),
    )


# ---------- Habitaciones ----------

def create_room(landlord_id, title, zone, price, size_m2, own_bathroom, available_from,
                smoking_allowed, pets_allowed, description, photo=None, members=()) -> int:
    """Crea la habitación y sus compañeros en una sola transacción."""
    with connect() as conn:
        room_id = conn.execute(
            """INSERT INTO rooms (landlord_id, title, zone, price, size_m2, own_bathroom, available_from,
                                  smoking_allowed, pets_allowed, description, photo)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (landlord_id, title, zone, price, size_m2, int(own_bathroom), available_from,
             int(smoking_allowed), int(pets_allowed), description, photo),
        ).lastrowid
        conn.executemany("INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
                         [(room_id, uid) for uid in members])
    return room_id


def get_room(room_id):
    return query_one("SELECT * FROM rooms WHERE id = ?", (room_id,))


def active_rooms():
    return query("SELECT * FROM rooms WHERE active = 1")


def rooms_of_landlord(landlord_id):
    return query("SELECT * FROM rooms WHERE landlord_id = ? ORDER BY id DESC", (landlord_id,))


def roommates(room_id):
    return query(
        """SELECT u.* FROM users u JOIN room_members m ON m.user_id = u.id
           WHERE m.room_id = ? ORDER BY u.name""",
        (room_id,),
    )


def rooms_lived_in():
    """IDs de inquilinos que ya viven en algún piso (no buscan habitación)."""
    return {r["user_id"] for r in query("SELECT user_id FROM room_members")}


# ---------- Reseñas ----------

def reviews_of(user_id):
    return query(
        """SELECT r.*, a.name AS author_name FROM reviews r JOIN users a ON a.id = r.author_id
           WHERE r.target_id = ? ORDER BY r.created_at DESC""",
        (user_id,),
    )


def rating_of(user_id):
    r = query_one("SELECT AVG(rating) AS avg, COUNT(*) AS n FROM reviews WHERE target_id = ?", (user_id,))
    return (round(r["avg"], 1) if r["avg"] else None), r["n"]


def add_review(author_id, target_id, rating, comment):
    execute("INSERT INTO reviews (author_id, target_id, rating, comment) VALUES (?,?,?,?)",
            (author_id, target_id, rating, comment))


# ---------- Conversaciones y mensajes ----------

def get_or_create_conversation(room_id, tenant_id):
    conv = query_one("SELECT * FROM conversations WHERE room_id = ? AND tenant_id = ?", (room_id, tenant_id))
    if conv:
        return conv["id"], False
    return execute("INSERT INTO conversations (room_id, tenant_id) VALUES (?, ?)", (room_id, tenant_id)), True


def conversations_of(user_id):
    """Conversaciones en las que participa el usuario: como inquilino, casero o compañero."""
    return query(
        """SELECT DISTINCT c.*, r.title, r.zone, r.landlord_id, t.name AS tenant_name
           FROM conversations c
           JOIN rooms r ON r.id = c.room_id
           JOIN users t ON t.id = c.tenant_id
           LEFT JOIN room_members m ON m.room_id = c.room_id
           WHERE c.tenant_id = ? OR r.landlord_id = ? OR m.user_id = ?
           ORDER BY c.created_at DESC""",
        (user_id, user_id, user_id),
    )


def messages_of(conversation_id):
    return query(
        """SELECT m.*, u.name AS author_name, u.role AS author_role FROM messages m
           JOIN users u ON u.id = m.author_id
           WHERE m.conversation_id = ? ORDER BY m.id""",
        (conversation_id,),
    )


def send_message(conversation_id, author_id, text):
    execute("INSERT INTO messages (conversation_id, author_id, text) VALUES (?,?,?)",
            (conversation_id, author_id, text))


def interested_in(room_id):
    return query(
        """SELECT c.*, u.name AS tenant_name FROM conversations c JOIN users u ON u.id = c.tenant_id
           WHERE c.room_id = ? ORDER BY c.created_at DESC""",
        (room_id,),
    )


# ---------- Eventos (métricas) ----------

def log_event(user_id, kind, room_id=None):
    execute("INSERT INTO events (user_id, kind, room_id) VALUES (?,?,?)", (user_id, kind, room_id))


def users_with_event(kind: str) -> int:
    """Usuarios distintos que han hecho la acción al menos una vez."""
    return query_one("SELECT COUNT(DISTINCT user_id) AS n FROM events WHERE kind = ?", (kind,))["n"]


def count_events(kind: str) -> int:
    """Número total de eventos de un tipo (p. ej. mensajes enviados)."""
    return query_one("SELECT COUNT(*) AS n FROM events WHERE kind = ?", (kind,))["n"]


def recent_events(limit: int = 50) -> list[Row]:
    """Últimas acciones con nombre de usuario y habitación, para la página de métricas."""
    return query(
        """SELECT e.created_at AS fecha, u.name AS usuario, e.kind AS accion,
                  COALESCE(r.title, '—') AS habitacion
           FROM events e
           LEFT JOIN users u ON u.id = e.user_id
           LEFT JOIN rooms r ON r.id = e.room_id
           ORDER BY e.id DESC LIMIT ?""",
        (limit,),
    )
