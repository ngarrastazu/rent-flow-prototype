"""Solicitudes, opiniones de compañeros, aceptación y bajas (rentflow.rentals)."""
import pytest

from rentflow import db, matching, rentals
from rentflow.rentals import RentalError

MARIO = 1
CHAMBERI = 1


def landlord_of(room_id):
    return db.get_room(room_id)["landlord_id"]


def mate_ids(room_id):
    return [m["id"] for m in db.roommates(room_id)]


def other_room_for_mario():
    """Otra habitación compatible con Mario, distinta de la de Chamberí."""
    return next(r["room"]["id"] for r in matching.matches_for(MARIO, None) if r["room"]["id"] != CHAMBERI)


def test_seed_has_pending_requests_and_keeps_94(seeded_db):
    assert matching.matches_for(MARIO)[0]["score"] == 94
    rival = db.requests_for_room(CHAMBERI)
    assert len(rival) == 1 and rival[0]["tenant_id"] != MARIO
    assert rentals.vote_summary(rival[0]["id"]) == (1, 1, 2)  # Lucía sí, Tom no
    assert db.count_events("solicitar") == 0  # el seed no ensucia las métricas


def test_send_request_and_duplicate(seeded_db):
    rid = rentals.send_request(MARIO, CHAMBERI, "Hola", "2027-01-10", 12)
    req = db.get_request(rid)
    assert req["status"] == "pendiente" and req["months"] == 12
    with pytest.raises(RentalError, match="pendiente"):
        rentals.send_request(MARIO, CHAMBERI)
    assert db.users_with_event("solicitar") == 1
    texts = [m["text"] for m in db.messages_of(db.get_or_create_conversation(CHAMBERI, MARIO)[0])]
    assert any("ha solicitado" in t for t in texts) and "Hola" in texts


def test_cannot_request_as_landlord_or_own_flat(seeded_db):
    with pytest.raises(RentalError, match="inquilinos"):
        rentals.send_request(landlord_of(CHAMBERI), CHAMBERI)
    with pytest.raises(RentalError, match="Ya vives en este piso"):
        rentals.send_request(mate_ids(CHAMBERI)[0], CHAMBERI)
    with pytest.raises(RentalError, match="meses"):
        rentals.send_request(MARIO, CHAMBERI, months=5)


def test_withdraw_only_by_owner(seeded_db):
    rid = rentals.send_request(MARIO, CHAMBERI)
    with pytest.raises(RentalError, match="no es tuya"):
        rentals.withdraw_request(rid, 2)
    rentals.withdraw_request(rid, MARIO)
    assert db.get_request(rid)["status"] == "retirada"
    rentals.send_request(MARIO, CHAMBERI)  # se puede volver a pedir


def test_only_roommates_can_vote(seeded_db):
    rid = rentals.send_request(MARIO, CHAMBERI)
    lucia, tom = mate_ids(CHAMBERI)
    rentals.vote(rid, lucia, 1)
    rentals.vote(rid, tom, 1)
    rentals.vote(rid, tom, -1)  # cambiar de opinión sustituye la anterior
    assert rentals.vote_summary(rid) == (1, 1, 2)
    with pytest.raises(RentalError, match="compañeros"):
        rentals.vote(rid, MARIO, 1)


def test_accept_rents_room_and_closes_other_requests(seeded_db):
    carmen = landlord_of(CHAMBERI)
    rival = db.requests_for_room(CHAMBERI)[0]
    other_room = other_room_for_mario()
    mine = rentals.send_request(MARIO, CHAMBERI)
    elsewhere = rentals.send_request(MARIO, other_room)

    with pytest.raises(RentalError, match="no es tuya"):
        rentals.accept_request(mine, carmen + 1)  # otro casero
    closed = rentals.accept_request(mine, carmen)

    room = db.get_room(CHAMBERI)
    assert room["tenant_id"] == MARIO and not room["active"]
    assert closed == {"room": [rival["id"]], "tenant": [elsewhere]}
    assert db.get_request(rival["id"])["status"] == "cerrada"
    assert db.get_request(elsewhere)["status"] == "cerrada"
    assert MARIO in db.rooms_lived_in()
    assert all(r["room"]["id"] != CHAMBERI for r in matching.matches_for(MARIO, None))
    assert all(c["tenant"]["id"] != MARIO for c in matching.candidates_for(other_room))
    assert db.occupied_room(MARIO)["id"] == CHAMBERI
    with pytest.raises(RentalError, match="pendiente"):
        rentals.accept_request(mine, carmen)


def test_reject_with_reason(seeded_db):
    rid = rentals.send_request(MARIO, CHAMBERI)
    rentals.reject_request(rid, landlord_of(CHAMBERI), "Ya tengo a alguien")
    req = db.get_request(rid)
    assert req["status"] == "rechazada" and req["note"] == "Ya tengo a alguien"
    assert db.get_room(CHAMBERI)["active"]


def test_remove_occupant_republishes_room(seeded_db):
    carmen = landlord_of(CHAMBERI)
    rentals.accept_request(rentals.send_request(MARIO, CHAMBERI), carmen)
    kinds = {(r["name"], r["kind"]) for r in db.residents_of_landlord(carmen)}
    assert ("Mario Rossi", "ocupante") in kinds and ("Lucía Martín", "compañero") in kinds
    rentals.remove_resident(carmen, CHAMBERI, MARIO, "Fin del contrato")
    room = db.get_room(CHAMBERI)
    assert room["tenant_id"] is None and room["active"]
    assert matching.matches_for(MARIO)[0]["score"] == 94  # vuelve a buscar y el match sigue igual


def test_remove_roommate_and_permissions(seeded_db):
    carmen = landlord_of(CHAMBERI)
    lucia = mate_ids(CHAMBERI)[0]
    with pytest.raises(RentalError, match="no es tuya"):
        rentals.remove_resident(carmen + 1, CHAMBERI, lucia)
    with pytest.raises(RentalError, match="no vive"):
        rentals.remove_resident(carmen, CHAMBERI, MARIO)
    rentals.remove_resident(carmen, CHAMBERI, lucia)
    assert lucia not in mate_ids(CHAMBERI) and lucia not in db.rooms_lived_in()


def test_pause_and_resume(seeded_db):
    carmen = landlord_of(CHAMBERI)
    rentals.set_paused(carmen, CHAMBERI, True)
    assert all(r["room"]["id"] != CHAMBERI for r in matching.matches_for(MARIO, None))
    with pytest.raises(RentalError, match="disponible"):
        rentals.send_request(MARIO, CHAMBERI)
    rentals.set_paused(carmen, CHAMBERI, False)
    assert matching.matches_for(MARIO)[0]["room"]["id"] == CHAMBERI


def test_pair_affinity():
    a = {"schedule": "x", "cleanliness": 4, "noise": 2, "smokes": 0, "pets": 0}
    b = {"schedule": "y", "cleanliness": 1, "noise": 5, "smokes": 1, "pets": 1}
    assert matching.pair_affinity(a, a) == 100
    assert matching.pair_affinity(a, b) == matching.pair_affinity(b, a) < 50


def test_migration_adds_tenant_column(tmp_path, monkeypatch):
    """Una base de datos de antes de las solicitudes se actualiza sola al arrancar."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "old.db")
    with db.connect() as conn:
        conn.execute("CREATE TABLE rooms (id INTEGER PRIMARY KEY, landlord_id INTEGER, active INTEGER DEFAULT 1)")
        conn.execute("INSERT INTO rooms (landlord_id) VALUES (1)")
    db.init_db()
    assert db.get_room(1)["tenant_id"] is None


# ---------- Fotos del anuncio ----------

def test_photos_main_and_order(temp_db):
    landlord = db.create_user("Casera", 50, "casero", "", "")
    room = db.create_room(landlord, "t", "Usera", 400, 10, False, "2027-01-01", False, False, "",
                          photos=[{"path": "rooms/habitacion-02.jpg", "space": "Habitación"},
                                  {"image": b"x", "space": "Cocina"}])
    photos = db.room_photos(room)
    assert [p["space"] for p in photos] == ["Habitación", "Cocina"] and photos[0]["is_main"]
    db.add_room_photos(room, [{"image": b"y"}])
    assert db.count_photos(room) == 3 and db.room_photos(room)[2]["space"] == "Otra"
    db.set_main_photo(room, photos[1]["id"])
    assert db.main_photo(room)["space"] == "Cocina"
    assert sum(p["is_main"] for p in db.room_photos(room)) == 1
    db.delete_room_photo(room, photos[1]["id"])  # borrar la principal: pasa a serlo la primera que queda
    assert db.main_photo(room)["id"] == photos[0]["id"]
    db.set_photo_space(room, photos[0]["id"], "Salón")
    assert db.main_photo(room)["space"] == "Salón"


def test_legacy_single_photo_is_migrated(temp_db):
    """Un anuncio con la foto antigua en rooms.photo la conserva como principal tras arrancar."""
    landlord = db.create_user("Casera", 50, "casero", "", "")
    room = db.create_room(landlord, "t", "Usera", 400, 10, False, "2027-01-01", False, False, "")
    db.execute("UPDATE rooms SET photo = ? WHERE id = ?", (b"legacy", room))
    db.init_db()
    main = db.main_photo(room)
    assert main["image"] == b"legacy" and main["is_main"] == 1
    assert db.get_room(room)["photo"] is None
    db.init_db()  # idempotente
    assert db.count_photos(room) == 1


# ---------- Chats privados ----------

def test_direct_chat_is_unique_per_pair_and_private(seeded_db):
    carmen = landlord_of(CHAMBERI)
    lucia = mate_ids(CHAMBERI)[0]
    conv, created = db.get_or_create_direct(MARIO, carmen)
    assert created and db.get_or_create_direct(carmen, MARIO) == (conv, False)
    with pytest.raises(ValueError):
        db.get_or_create_direct(MARIO, MARIO)
    db.send_message(conv, MARIO, "Hola Carmen, solo para ti")

    assert [c["other_name"] for c in db.direct_conversations_of(MARIO)] == ["Carmen Ruiz"]
    assert [c["other_name"] for c in db.direct_conversations_of(carmen)] == ["Mario Rossi"]
    assert db.direct_conversations_of(lucia) == []  # vive en el piso, pero no ve el chat privado
    assert all(c["id"] != conv for c in db.conversations_of(lucia))
    assert all(c["id"] != conv for c in db.conversations_of(carmen))  # no se mezcla con los chats de piso
    assert all(c["kind"] == "grupo" for c in db.interested_in(CHAMBERI))


def test_conversations_sorted_by_last_message(seeded_db):
    carmen = landlord_of(CHAMBERI)
    first, _ = db.get_or_create_direct(carmen, mate_ids(CHAMBERI)[0])
    second, _ = db.get_or_create_direct(carmen, mate_ids(CHAMBERI)[1])
    db.send_message(second, carmen, "Hola")
    db.send_message(first, carmen, "Hola otra vez")  # el último mensaje es en `first`
    assert [c["id"] for c in db.direct_conversations_of(carmen)][:2] == [first, second]
