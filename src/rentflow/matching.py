"""Algoritmo de matching de RentFlow.

Para cada habitación calcula una compatibilidad de 0 a 100 con el inquilino:

1. Filtros duros: descartan la habitación (precio muy por encima del presupuesto,
   fecha de entrada incompatible, tabaco, mascotas o baño propio).
2. Puntuación ponderada (cada factor vale de 0 a 1):

   Compatibilidad = 30 % presupuesto + 20 % zona + 20 % horarios
                    + 15 % limpieza + 15 % estilo de vida (ruido, tabaco, mascotas)

   Horarios, limpieza y estilo de vida se comparan con los compañeros que ya viven
   en el piso (media de todos ellos).
"""
from datetime import date, timedelta

from rentflow import db
from rentflow.db import Row

WEIGHTS = {
    "Presupuesto": 0.30,
    "Zona": 0.20,
    "Horarios": 0.20,
    "Limpieza": 0.15,
    "Estilo de vida": 0.15,
}
PRICE_TOLERANCE = 1.10      # se aceptan pisos hasta un 10 % por encima del presupuesto
MOVE_IN_MARGIN_DAYS = 30    # el piso puede quedar libre hasta 30 días después de la fecha deseada
NO_ROOMMATES_SCORE = 0.8    # piso sin compañeros todavía: puntuación neutra

assert abs(sum(WEIGHTS.values()) - 1) < 1e-9, "Los pesos de WEIGHTS deben sumar 1"


def _similarity(a: int, b: int, scale: int = 4) -> float:
    """1 si son iguales, 0 si están en extremos opuestos de una escala de 1 a 5."""
    return 1 - abs(a - b) / scale


def mates_preferences(mates: list[Row]) -> list[Row]:
    """Preferencias de los compañeros de un piso (se omiten los que no tienen perfil)."""
    return [p for p in (db.get_preferences(m["id"]) for m in mates) if p]


def _habits_vs(tenant: Row, mate: Row) -> tuple[float, float, float]:
    """Compara los hábitos del inquilino con los de un compañero."""
    schedule = 1.0 if tenant["schedule"] == mate["schedule"] else 0.4
    clean = _similarity(tenant["cleanliness"], mate["cleanliness"])
    noise = _similarity(tenant["noise"], mate["noise"])
    smoke = 1.0 if tenant["smokes"] == mate["smokes"] else 0.3
    pets = 1.0 if tenant["pets"] == mate["pets"] else 0.6
    lifestyle = (noise + smoke + pets) / 3
    return schedule, clean, lifestyle


def score_room(prefs: Row, room: Row, mates_prefs: list[Row]) -> tuple[int, dict[str, float]] | None:
    """Devuelve (puntuación 0-100, desglose por factor) o None si un filtro duro descarta el piso."""
    # 1. Filtros duros
    if room["price"] > prefs["budget_max"] * PRICE_TOLERANCE:
        return None
    if prefs["smokes"] and not room["smoking_allowed"]:
        return None
    if prefs["pets"] and not room["pets_allowed"]:
        return None
    if prefs["own_bathroom"] and not room["own_bathroom"]:
        return None
    if prefs.get("move_in") and room.get("available_from"):
        latest = date.fromisoformat(prefs["move_in"]) + timedelta(days=MOVE_IN_MARGIN_DAYS)
        if date.fromisoformat(room["available_from"]) > latest:
            return None

    # 2. Factores
    if room["price"] <= prefs["budget_max"]:
        budget = 1.0
    else:  # entre el presupuesto y +10 %: baja de 1 a 0,4
        over = (room["price"] - prefs["budget_max"]) / (prefs["budget_max"] * (PRICE_TOLERANCE - 1))
        budget = 1 - 0.6 * over

    zone = 1.0 if not prefs["zones"] or room["zone"] in prefs["zones"] else 0.3

    if mates_prefs:
        parts = [_habits_vs(prefs, m) for m in mates_prefs]
        schedule = sum(p[0] for p in parts) / len(parts)
        clean = sum(p[1] for p in parts) / len(parts)
        lifestyle = sum(p[2] for p in parts) / len(parts)
    else:
        schedule = clean = lifestyle = NO_ROOMMATES_SCORE

    breakdown = {
        "Presupuesto": budget,
        "Zona": zone,
        "Horarios": schedule,
        "Limpieza": clean,
        "Estilo de vida": lifestyle,
    }
    total = sum(WEIGHTS[k] * v for k, v in breakdown.items())
    return round(total * 100), breakdown


def matches_for(tenant_id: int, limit: int | None = 10) -> list[dict]:
    """Habitaciones ordenadas por compatibilidad para un inquilino.

    Cada resultado: {"room", "score" (0-100), "breakdown" (factor -> 0..1), "mates"}.
    `limit=None` devuelve todas las compatibles (para filtrar y paginar en la interfaz).
    """
    prefs = db.get_preferences(tenant_id)
    if not prefs:
        return []
    results = []
    for room in db.active_rooms():
        mates = db.roommates(room["id"])
        if any(m["id"] == tenant_id for m in mates):
            continue  # ya vive ahí
        scored = score_room(prefs, room, mates_preferences(mates))
        if scored:
            score, breakdown = scored
            results.append({"room": room, "score": score, "breakdown": breakdown, "mates": mates})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


SORTS = {
    "Compatibilidad": lambda r: (-r["score"], r["room"]["price"]),
    "Precio más bajo": lambda r: (r["room"]["price"], -r["score"]),
    "Entrada más pronto": lambda r: (r["room"]["available_from"] or "", -r["score"]),
}


def filter_matches(results: list[dict], max_price: int | None = None, zones=None,
                   own_bathroom: bool = False, sort: str = "Compatibilidad") -> list[dict]:
    """Filtra y ordena resultados ya puntuados. No recalcula nada: la compatibilidad no cambia."""
    out = [
        r for r in results
        if (max_price is None or r["room"]["price"] <= max_price)
        and (not zones or r["room"]["zone"] in zones)
        and (not own_bathroom or r["room"]["own_bathroom"])
    ]
    return sorted(out, key=SORTS[sort])


def candidates_for(room_id: int, limit: int = 5) -> list[dict]:
    """Búsqueda inversa para el casero: inquilinos que buscan piso, ordenados por compatibilidad.

    Cada resultado: {"tenant", "score" (0-100)}.
    """
    room = db.get_room(room_id)
    mates_prefs = mates_preferences(db.roommates(room_id))
    living = db.rooms_lived_in()
    results = []
    for tenant in db.list_users("inquilino"):
        if tenant["id"] in living:
            continue
        prefs = db.get_preferences(tenant["id"])
        if not prefs:
            continue
        scored = score_room(prefs, room, mates_prefs)
        if scored:
            results.append({"tenant": tenant, "score": scored[0]})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
