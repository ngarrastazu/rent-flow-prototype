"""Solicitudes y alquiler de habitaciones (sin Streamlit).

Ciclo de una habitación:

    publicada --solicitudes--> (los compañeros opinan) --el casero acepta--> alquilada
        ^                                                                       |
        +----------------------- el casero da de baja al ocupante -------------+

Reglas:
- Solo un inquilino que no vive ya en esa habitación puede solicitarla, y una sola vez a la vez.
- Los compañeros del piso dan su opinión ("doble aceptación"); decide el casero.
- Al aceptar: la habitación deja de publicarse, se cierran las demás solicitudes de la habitación
  y las demás del inquilino, y este deja de aparecer como candidato en la búsqueda inversa.
- Cada paso deja un mensaje automático de RentFlow en el chat de esa habitación con ese inquilino.

Todas las funciones lanzan `RentalError` (con un texto para mostrar) si la acción no está permitida.
"""
from datetime import date

from rentflow import db

MONTHS = (3, 6, 9, 12)  # estancias que se pueden pedir


class RentalError(ValueError):
    """Acción no permitida; el mensaje se puede mostrar tal cual al usuario."""


def _first_name(user):
    return (user["name"] or "").split()[0]


def _notify(room_id, tenant_id, text):
    conv, _ = db.get_or_create_conversation(room_id, tenant_id)
    db.send_system_message(conv, text)
    return conv


def _own_room(landlord_id, room_id):
    room = db.get_room(room_id)
    if not room or room["landlord_id"] != landlord_id:
        raise RentalError("Esta habitación no es tuya.")
    return room


def _pending(request_id):
    req = db.get_request(request_id)
    if not req:
        raise RentalError("La solicitud no existe.")
    if req["status"] != "pendiente":
        raise RentalError("Esta solicitud ya no está pendiente.")
    return req


# ---------------------------------------------------------------- inquilino

def can_request(tenant_id, room):
    """None si el inquilino puede solicitar la habitación; si no, el motivo."""
    if room["tenant_id"] == tenant_id:
        return "Ya vives en esta habitación."
    if not room["active"] or room["tenant_id"]:
        return "Esta habitación ya no está disponible."
    if any(m["id"] == tenant_id for m in db.roommates(room["id"])):
        return "Ya vives en este piso."
    req = db.latest_request(room["id"], tenant_id)
    if req and req["status"] == "pendiente":
        return "Ya tienes una solicitud pendiente para esta habitación."
    return None


def send_request(tenant_id, room_id, message="", move_in=None, months=12):
    tenant = db.get_user(tenant_id)
    room = db.get_room(room_id)
    if not tenant or tenant["role"] != "inquilino":
        raise RentalError("Solo los inquilinos pueden solicitar habitaciones.")
    if not room:
        raise RentalError("La habitación no existe.")
    if reason := can_request(tenant_id, room):
        raise RentalError(reason)
    if months not in MONTHS:
        raise RentalError("Elige una estancia de 3, 6, 9 o 12 meses.")
    move_in = move_in or date.today()
    if isinstance(move_in, date):
        move_in = move_in.isoformat()
    message = (message or "").strip()

    request_id = db.create_request(room_id, tenant_id, message, move_in, months)
    conv = _notify(room_id, tenant_id, f"{tenant['name']} ha solicitado esta habitación: entrada el {move_in}, "
                                       f"estancia de {months} meses. Los compañeros pueden dar su opinión.")
    if message:
        db.send_message(conv, tenant_id, message)
    db.log_event(tenant_id, "solicitar", room_id)
    return request_id


def withdraw_request(request_id, tenant_id):
    req = _pending(request_id)
    if req["tenant_id"] != tenant_id:
        raise RentalError("Esta solicitud no es tuya.")
    db.set_request_status(request_id, "retirada")
    _notify(req["room_id"], tenant_id, f"{req['tenant_name']} ha retirado su solicitud.")
    db.log_event(tenant_id, "retirar_solicitud", req["room_id"])


# ---------------------------------------------------------------- compañeros

def vote(request_id, user_id, value):
    """Un compañero del piso opina sobre el candidato: value = 1 (me encaja) o -1 (no me encaja)."""
    req = _pending(request_id)
    if value not in (1, -1):
        raise RentalError("Opinión no válida.")
    if not any(m["id"] == user_id for m in db.roommates(req["room_id"])):
        raise RentalError("Solo los compañeros del piso pueden opinar.")
    db.set_vote(request_id, user_id, value)
    db.log_event(user_id, "votar", req["room_id"])


def vote_summary(request_id):
    """(a favor, en contra, total de compañeros) de una solicitud."""
    votes = db.votes_for(request_id)
    return (sum(v["vote"] == 1 for v in votes), sum(v["vote"] == -1 for v in votes), len(votes))


# ---------------------------------------------------------------- casero

def accept_request(request_id, landlord_id):
    req = _pending(request_id)
    room = _own_room(landlord_id, req["room_id"])
    if room["tenant_id"]:
        raise RentalError("La habitación ya está alquilada. Da de baja al inquilino actual antes.")
    tenant = db.get_user(req["tenant_id"])
    closed = db.accept_request_tx(request_id)

    _notify(room["id"], tenant["id"], f"¡Solicitud aceptada! {_first_name(tenant)} se queda la habitación "
                                      f"desde el {req['move_in']}. Bienvenido al piso.")
    for rid in closed["room"]:
        other = db.get_request(rid)
        _notify(other["room_id"], other["tenant_id"],
                "Esta habitación se ha alquilado a otra persona. Tu solicitud se ha cerrado.")
    for rid in closed["tenant"]:
        other = db.get_request(rid)
        _notify(other["room_id"], other["tenant_id"],
                f"{tenant['name']} ha encontrado otra habitación y su solicitud se ha cerrado.")
    db.log_event(landlord_id, "aceptar_solicitud", room["id"])
    return closed


def reject_request(request_id, landlord_id, note=""):
    req = _pending(request_id)
    _own_room(landlord_id, req["room_id"])
    note = (note or "").strip() or None
    db.set_request_status(request_id, "rechazada", note)
    _notify(req["room_id"], req["tenant_id"],
            "El casero ha rechazado la solicitud." + (f" Motivo: {note}" if note else ""))
    db.log_event(landlord_id, "rechazar_solicitud", req["room_id"])


def set_paused(landlord_id, room_id, paused):
    """Pausa o reactiva un anuncio libre (pausado = no sale en los matches; las solicitudes se mantienen)."""
    room = _own_room(landlord_id, room_id)
    if room["tenant_id"]:
        raise RentalError("La habitación está alquilada: no se puede pausar ni reactivar.")
    db.set_room_active(room_id, not paused)
    db.log_event(landlord_id, "pausar_anuncio" if paused else "reactivar_anuncio", room_id)


def remove_resident(landlord_id, room_id, user_id, note=""):
    """Da de baja a quien vive en un piso del casero.

    - Ocupante de la habitación: la habitación queda libre y se vuelve a publicar.
    - Compañero del piso: deja de figurar en el piso (y vuelve a poder buscar habitación).
    Ojo: quitar compañeros cambia la compatibilidad de esa habitación con todos los inquilinos.
    """
    room = _own_room(landlord_id, room_id)
    user = db.get_user(user_id)
    if room["tenant_id"] == user_id:
        db.release_room(room_id)
        text = f"{user['name']} ya no vive en esta habitación. La habitación vuelve a estar publicada."
    elif any(m["id"] == user_id for m in db.roommates(room_id)):
        db.remove_member(room_id, user_id)
        text = f"{user['name']} ya no figura como compañero de este piso."
    else:
        raise RentalError(f"{user['name']} no vive en esta habitación.")
    note = (note or "").strip()
    _notify(room_id, user_id, text + (f" Motivo: {note}" if note else ""))
    db.log_event(landlord_id, "quitar_inquilino", room_id)
