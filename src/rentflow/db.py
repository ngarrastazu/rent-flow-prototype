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
# Espacios que puede mostrar una foto del anuncio (la habitación y el resto del piso)
SPACES = ["Habitación", "Salón", "Comedor", "Cocina", "Baño", "Terraza", "Edificio", "Otra"]
MAX_PHOTOS = 12  # fotos por anuncio

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
    photo            BLOB,                -- obsoleto: las fotos están en room_photos (se migra solo)
    active           INTEGER DEFAULT 1,   -- 0 = no aparece en los matches (alquilada o pausada)
    tenant_id        INTEGER REFERENCES users(id)  -- inquilino que la ocupa (NULL = libre)
);

-- Fotos del anuncio: la habitación y el resto del piso. Una es la principal (portada del anuncio).
-- `image` = foto subida por el casero; `path` = foto de ejemplo dentro de assets/ (el seed no duplica bytes).
CREATE TABLE IF NOT EXISTS room_photos (
    id          INTEGER PRIMARY KEY,
    room_id     INTEGER NOT NULL REFERENCES rooms(id),
    image       BLOB,
    path        TEXT,
    space       TEXT,                 -- uno de SPACES
    is_main     INTEGER DEFAULT 0,
    position    INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    CHECK (image IS NOT NULL OR path IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_main_photo ON room_photos(room_id) WHERE is_main = 1;

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
-- Dos tipos de conversación:
--   'grupo'   = chat del piso: room_id + tenant_id (el interesado), con el casero y los compañeros.
--   'privado' = solo dos personas: tenant_id < peer_id (pareja ordenada), sin habitación (room_id NULL).
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY,
    room_id     INTEGER REFERENCES rooms(id),
    tenant_id   INTEGER REFERENCES users(id),
    kind        TEXT NOT NULL DEFAULT 'grupo' CHECK (kind IN ('grupo', 'privado')),
    peer_id     INTEGER REFERENCES users(id),
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (room_id, tenant_id)
);
-- Un único chat privado por pareja de personas
CREATE UNIQUE INDEX IF NOT EXISTS one_direct_chat ON conversations(tenant_id, peer_id) WHERE kind = 'privado';

CREATE TABLE IF NOT EXISTS messages (
    id               INTEGER PRIMARY KEY,
    conversation_id  INTEGER REFERENCES conversations(id),
    author_id        INTEGER REFERENCES users(id),
    text             TEXT,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Solicitudes de un inquilino para quedarse una habitación.
-- Estados: pendiente -> aceptada | rechazada | retirada (por el inquilino) | cerrada (por el sistema:
-- la habitación se alquiló a otra persona o el inquilino encontró otra).
CREATE TABLE IF NOT EXISTS requests (
    id           INTEGER PRIMARY KEY,
    room_id      INTEGER NOT NULL REFERENCES rooms(id),
    tenant_id    INTEGER NOT NULL REFERENCES users(id),
    message      TEXT,
    move_in      TEXT,                -- fecha ISO deseada de entrada
    months       INTEGER,             -- estancia prevista
    status       TEXT NOT NULL DEFAULT 'pendiente'
                 CHECK (status IN ('pendiente', 'aceptada', 'rechazada', 'retirada', 'cerrada')),
    note         TEXT,                -- motivo del rechazo o del cierre
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    decided_at   TEXT
);
-- Como mucho una solicitud pendiente por inquilino y habitación
CREATE UNIQUE INDEX IF NOT EXISTS one_pending_request ON requests(room_id, tenant_id) WHERE status = 'pendiente';

-- Opinión de los compañeros del piso sobre un candidato ("doble aceptación")
CREATE TABLE IF NOT EXISTS request_votes (
    request_id  INTEGER NOT NULL REFERENCES requests(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    vote        INTEGER NOT NULL CHECK (vote IN (-1, 1)),
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (request_id, user_id)
);

-- Registro de acciones para medir las hipótesis (ver la página "Métricas")
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER,
    kind        TEXT,     -- ver_matches, ver_detalle, solicitar, aceptar_solicitud... (ver CLAUDE.md)
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
        # Bases de datos creadas antes de las solicitudes: añade la columna que falta (no se pierden datos)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(rooms)")}
        if cols and "tenant_id" not in cols:
            conn.execute("ALTER TABLE rooms ADD COLUMN tenant_id INTEGER REFERENCES users(id)")
        # ... y antes de los chats privados: tipo de conversación y segunda persona
        conv_cols = {r["name"] for r in conn.execute("PRAGMA table_info(conversations)")}
        if conv_cols and "kind" not in conv_cols:
            conn.execute("ALTER TABLE conversations ADD COLUMN kind TEXT NOT NULL DEFAULT 'grupo'")
            conn.execute("ALTER TABLE conversations ADD COLUMN peer_id INTEGER REFERENCES users(id)")
        conn.executescript(SCHEMA)
        # Anuncios con la foto única antigua (rooms.photo): pasa a ser su foto principal en room_photos
        if "photo" not in {r["name"] for r in conn.execute("PRAGMA table_info(rooms)")}:
            return
        conn.execute("""INSERT INTO room_photos (room_id, image, space, is_main)
                        SELECT id, photo, 'Habitación', 1 FROM rooms r
                        WHERE photo IS NOT NULL
                          AND NOT EXISTS (SELECT 1 FROM room_photos p WHERE p.room_id = r.id)""")
        conn.execute("UPDATE rooms SET photo = NULL WHERE photo IS NOT NULL")


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
                smoking_allowed, pets_allowed, description, photo=None, members=(), photos=()) -> int:
    """Crea la habitación, sus compañeros y sus fotos en una sola transacción.

    `photos`: lista de dicts {"image": bytes} o {"path": "rooms/x.jpg"}, con "space" opcional; la primera
    es la principal. `photo` (bytes) se mantiene por compatibilidad: equivale a una sola foto de la habitación.
    """
    photos = list(photos) or ([{"image": photo, "space": "Habitación"}] if photo else [])
    with connect() as conn:
        room_id = conn.execute(
            """INSERT INTO rooms (landlord_id, title, zone, price, size_m2, own_bathroom, available_from,
                                  smoking_allowed, pets_allowed, description)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (landlord_id, title, zone, price, size_m2, int(own_bathroom), available_from,
             int(smoking_allowed), int(pets_allowed), description),
        ).lastrowid
        conn.executemany("INSERT INTO room_members (room_id, user_id) VALUES (?, ?)",
                         [(room_id, uid) for uid in members])
        _insert_photos(conn, room_id, photos)
    return room_id


# ---------- Fotos del anuncio ----------

def _insert_photos(conn, room_id, photos):
    """Añade fotos al final; si el anuncio no tenía principal, la primera nueva pasa a serlo."""
    row = conn.execute("SELECT COALESCE(MAX(position), -1) AS pos, COALESCE(MAX(is_main), 0) AS has_main "
                       "FROM room_photos WHERE room_id = ?", (room_id,)).fetchone()
    pos, has_main = row["pos"], row["has_main"]
    for i, ph in enumerate(photos):
        conn.execute(
            "INSERT INTO room_photos (room_id, image, path, space, is_main, position) VALUES (?,?,?,?,?,?)",
            (room_id, ph.get("image"), ph.get("path"), ph.get("space") or "Otra",
             int(not has_main and i == 0), pos + 1 + i),
        )


def add_room_photos(room_id, photos):
    with connect() as conn:
        _insert_photos(conn, room_id, photos)


def room_photos(room_id):
    """Fotos del anuncio: la principal primero y luego en el orden en que se subieron."""
    return query("SELECT * FROM room_photos WHERE room_id = ? ORDER BY is_main DESC, position, id", (room_id,))


def main_photo(room_id):
    """Foto principal (portada) del anuncio, o None si no tiene fotos."""
    return query_one("SELECT * FROM room_photos WHERE room_id = ? ORDER BY is_main DESC, position, id LIMIT 1",
                     (room_id,))


def count_photos(room_id):
    return query_one("SELECT COUNT(*) AS n FROM room_photos WHERE room_id = ?", (room_id,))["n"]


def set_main_photo(room_id, photo_id):
    with connect() as conn:
        conn.execute("UPDATE room_photos SET is_main = 0 WHERE room_id = ?", (room_id,))
        conn.execute("UPDATE room_photos SET is_main = 1 WHERE room_id = ? AND id = ?", (room_id, photo_id))


def set_photo_space(room_id, photo_id, space):
    execute("UPDATE room_photos SET space = ? WHERE room_id = ? AND id = ?", (space, room_id, photo_id))


def delete_room_photo(room_id, photo_id):
    """Borra una foto; si era la principal, la siguiente pasa a serlo."""
    with connect() as conn:
        conn.execute("DELETE FROM room_photos WHERE room_id = ? AND id = ?", (room_id, photo_id))
        has_main = conn.execute("SELECT 1 FROM room_photos WHERE room_id = ? AND is_main = 1", (room_id,)).fetchone()
        if not has_main:
            conn.execute("""UPDATE room_photos SET is_main = 1 WHERE id = (
                                SELECT id FROM room_photos WHERE room_id = ? ORDER BY position, id LIMIT 1)""",
                         (room_id,))


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
    """IDs de inquilinos que ya viven en algún piso (no buscan habitación): compañeros y ocupantes."""
    return {r["user_id"] for r in query(
        "SELECT user_id FROM room_members UNION SELECT tenant_id FROM rooms WHERE tenant_id IS NOT NULL")}


def occupied_room(user_id):
    """Habitación que ocupa el inquilino (tras aceptarse su solicitud), o None."""
    return query_one("SELECT * FROM rooms WHERE tenant_id = ? ORDER BY id LIMIT 1", (user_id,))


def member_rooms(user_id):
    """Habitaciones de pisos donde el usuario ya vive como compañero."""
    return query(
        """SELECT r.* FROM rooms r JOIN room_members m ON m.room_id = r.id
           WHERE m.user_id = ? ORDER BY r.id""",
        (user_id,),
    )


def residents_of_landlord(landlord_id):
    """Quién vive en los pisos del casero: el ocupante de cada habitación y los compañeros del piso.

    kind = 'ocupante' | 'compañero'; since = fecha en que se aceptó la solicitud (solo ocupantes).
    """
    return query(
        """SELECT r.id AS room_id, u.*, 'ocupante' AS kind,
                  (SELECT MAX(q.decided_at) FROM requests q
                   WHERE q.room_id = r.id AND q.tenant_id = u.id AND q.status = 'aceptada') AS since
           FROM rooms r JOIN users u ON u.id = r.tenant_id
           WHERE r.landlord_id = ?
           UNION ALL
           SELECT r.id AS room_id, u.*, 'compañero' AS kind, NULL AS since
           FROM rooms r JOIN room_members m ON m.room_id = r.id JOIN users u ON u.id = m.user_id
           WHERE r.landlord_id = ?
           ORDER BY room_id DESC, kind DESC, name""",
        (landlord_id, landlord_id),
    )


def set_room_active(room_id, active):
    execute("UPDATE rooms SET active = ? WHERE id = ?", (int(active), room_id))


def release_room(room_id):
    """El ocupante deja la habitación: queda libre y se vuelve a publicar."""
    execute("UPDATE rooms SET tenant_id = NULL, active = 1 WHERE id = ?", (room_id,))


def remove_member(room_id, user_id):
    execute("DELETE FROM room_members WHERE room_id = ? AND user_id = ?", (room_id, user_id))


# ---------- Solicitudes ----------

REQUEST_SELECT = """SELECT q.*, r.title, r.zone, r.price, r.landlord_id, r.active AS room_active,
                           r.tenant_id AS room_tenant_id, t.name AS tenant_name
                    FROM requests q JOIN rooms r ON r.id = q.room_id JOIN users t ON t.id = q.tenant_id"""


def create_request(room_id, tenant_id, message, move_in, months):
    return execute(
        "INSERT INTO requests (room_id, tenant_id, message, move_in, months) VALUES (?,?,?,?,?)",
        (room_id, tenant_id, message, move_in, months),
    )


def get_request(request_id):
    return query_one(REQUEST_SELECT + " WHERE q.id = ?", (request_id,))


def latest_request(room_id, tenant_id):
    """Última solicitud de un inquilino para una habitación (cualquier estado), o None."""
    return query_one(REQUEST_SELECT + " WHERE q.room_id = ? AND q.tenant_id = ? ORDER BY q.id DESC LIMIT 1",
                     (room_id, tenant_id))


def requests_for_room(room_id, status="pendiente"):
    return query(REQUEST_SELECT + " WHERE q.room_id = ? AND q.status = ? ORDER BY q.id", (room_id, status))


def count_requests_for_room(room_id):
    """{estado: número} de las solicitudes de una habitación."""
    rows = query("SELECT status, COUNT(*) AS n FROM requests WHERE room_id = ? GROUP BY status", (room_id,))
    return {r["status"]: r["n"] for r in rows}


def requests_of_tenant(tenant_id):
    return query(REQUEST_SELECT + " WHERE q.tenant_id = ? ORDER BY q.id DESC", (tenant_id,))


def pending_requests_for_member(user_id):
    """Solicitudes pendientes para entrar en pisos donde vive el usuario (para que opine)."""
    return query(
        REQUEST_SELECT + """ JOIN room_members m ON m.room_id = q.room_id
                             WHERE m.user_id = ? AND q.status = 'pendiente' ORDER BY q.id""",
        (user_id,),
    )


def count_pending_requests_of_landlord(landlord_id):
    return query_one(
        """SELECT COUNT(*) AS n FROM requests q JOIN rooms r ON r.id = q.room_id
           WHERE r.landlord_id = ? AND q.status = 'pendiente'""",
        (landlord_id,),
    )["n"]


def set_request_status(request_id, status, note=None):
    execute("UPDATE requests SET status = ?, note = ?, decided_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, note, request_id))


def accept_request_tx(request_id):
    """Acepta la solicitud en una sola transacción. Devuelve los ids de las solicitudes cerradas.

    - la solicitud pasa a 'aceptada'; la habitación queda ocupada por el inquilino y deja de publicarse;
    - si el inquilino ya ocupaba otra habitación, esa queda libre y se vuelve a publicar (mudanza);
    - deja de figurar como compañero en otros pisos;
    - se cierran las demás solicitudes pendientes de esa habitación y las del inquilino.
    """
    with connect() as conn:
        q = conn.execute("SELECT room_id, tenant_id FROM requests WHERE id = ?", (request_id,)).fetchone()
        room_id, tenant_id = q["room_id"], q["tenant_id"]
        conn.execute("UPDATE requests SET status = 'aceptada', note = NULL, decided_at = CURRENT_TIMESTAMP "
                     "WHERE id = ?", (request_id,))
        conn.execute("UPDATE rooms SET tenant_id = NULL, active = 1 WHERE tenant_id = ? AND id <> ?",
                     (tenant_id, room_id))
        conn.execute("UPDATE rooms SET tenant_id = ?, active = 0 WHERE id = ?", (tenant_id, room_id))
        conn.execute("DELETE FROM room_members WHERE user_id = ?", (tenant_id,))
        closed_room = [r["id"] for r in conn.execute(
            "SELECT id FROM requests WHERE room_id = ? AND status = 'pendiente' AND id <> ?",
            (room_id, request_id))]
        closed_tenant = [r["id"] for r in conn.execute(
            "SELECT id FROM requests WHERE tenant_id = ? AND status = 'pendiente' AND id <> ?",
            (tenant_id, request_id))]
        conn.executemany(
            "UPDATE requests SET status = 'cerrada', note = ?, decided_at = CURRENT_TIMESTAMP WHERE id = ?",
            [("La habitación se ha alquilado a otra persona.", i) for i in closed_room]
            + [("Encontraste otra habitación en RentFlow.", i) for i in closed_tenant],
        )
    return {"room": closed_room, "tenant": closed_tenant}


def set_vote(request_id, user_id, vote):
    execute(
        """INSERT INTO request_votes (request_id, user_id, vote) VALUES (?,?,?)
           ON CONFLICT(request_id, user_id) DO UPDATE SET vote = excluded.vote, created_at = CURRENT_TIMESTAMP""",
        (request_id, user_id, vote),
    )


def votes_for(request_id):
    """Opinión de cada compañero actual del piso sobre la solicitud (vote = 1, -1 o None si no ha opinado)."""
    return query(
        """SELECT u.id AS user_id, u.name, v.vote
           FROM requests q
           JOIN room_members m ON m.room_id = q.room_id
           JOIN users u ON u.id = m.user_id
           LEFT JOIN request_votes v ON v.request_id = q.id AND v.user_id = u.id
           WHERE q.id = ? ORDER BY u.name""",
        (request_id,),
    )


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


LAST_AT = "COALESCE((SELECT MAX(x.id) FROM messages x WHERE x.conversation_id = c.id), 0)"


def conversations_of(user_id):
    """Chats de piso (grupo) en los que participa el usuario: como interesado, casero o compañero.

    Ordenados por el último mensaje (last_msg = id del último mensaje, 0 si no hay).
    """
    return query(
        f"""SELECT DISTINCT c.*, r.title, r.zone, r.landlord_id, t.name AS tenant_name, {LAST_AT} AS last_msg
            FROM conversations c
            JOIN rooms r ON r.id = c.room_id
            JOIN users t ON t.id = c.tenant_id
            LEFT JOIN room_members m ON m.room_id = c.room_id
            WHERE c.kind = 'grupo' AND (c.tenant_id = ? OR r.landlord_id = ? OR m.user_id = ?)
            ORDER BY last_msg DESC, c.id DESC""",
        (user_id, user_id, user_id),
    )


def get_or_create_direct(user_a, user_b):
    """Chat privado entre dos personas (uno por pareja). Devuelve (id, creado)."""
    if user_a == user_b:
        raise ValueError("No puedes escribirte a ti mismo.")
    lo, hi = sorted((user_a, user_b))
    conv = query_one("SELECT id FROM conversations WHERE kind = 'privado' AND tenant_id = ? AND peer_id = ?",
                     (lo, hi))
    if conv:
        return conv["id"], False
    return execute("INSERT INTO conversations (kind, tenant_id, peer_id) VALUES ('privado', ?, ?)", (lo, hi)), True


def direct_conversations_of(user_id):
    """Chats privados del usuario, con los datos de la otra persona (other_*), por último mensaje."""
    return query(
        f"""SELECT c.*, o.id AS other_id, o.name AS other_name, o.role AS other_role, {LAST_AT} AS last_msg
            FROM conversations c
            JOIN users o ON o.id = CASE WHEN c.tenant_id = ? THEN c.peer_id ELSE c.tenant_id END
            WHERE c.kind = 'privado' AND (c.tenant_id = ? OR c.peer_id = ?)
            ORDER BY last_msg DESC, c.id DESC""",
        (user_id, user_id, user_id),
    )


def get_conversation(conversation_id):
    return query_one("SELECT * FROM conversations WHERE id = ?", (conversation_id,))


def messages_of(conversation_id):
    """Mensajes de una conversación. Los automáticos de RentFlow no tienen autor (author_role = 'sistema')."""
    return query(
        """SELECT m.*, COALESCE(u.name, 'RentFlow') AS author_name, COALESCE(u.role, 'sistema') AS author_role
           FROM messages m LEFT JOIN users u ON u.id = m.author_id
           WHERE m.conversation_id = ? ORDER BY m.id""",
        (conversation_id,),
    )


def send_message(conversation_id, author_id, text):
    execute("INSERT INTO messages (conversation_id, author_id, text) VALUES (?,?,?)",
            (conversation_id, author_id, text))


def send_system_message(conversation_id, text):
    """Mensaje automático de RentFlow (sin autor): solicitudes, aceptaciones, bajas…"""
    send_message(conversation_id, None, text)


def interested_in(room_id):
    return query(
        """SELECT c.*, u.name AS tenant_name FROM conversations c JOIN users u ON u.id = c.tenant_id
           WHERE c.room_id = ? AND c.kind = 'grupo' ORDER BY c.created_at DESC""",
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
