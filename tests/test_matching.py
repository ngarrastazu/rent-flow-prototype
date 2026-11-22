"""Tests del algoritmo de matching y de la historia de la demo."""
import pytest

from rentflow import db, matching

TENANT = {
    "budget_min": 400, "budget_max": 600, "zones": ["Chamberí"], "move_in": "2027-01-10",
    "schedule": db.SCHEDULES[0], "cleanliness": 4, "noise": 2, "smokes": 0, "pets": 0, "own_bathroom": 0,
}
ROOM = {
    "price": 600, "zone": "Chamberí", "own_bathroom": 0, "available_from": "2027-01-01",
    "smoking_allowed": 0, "pets_allowed": 0,
}


def test_weights_sum_to_one():
    assert sum(matching.WEIGHTS.values()) == pytest.approx(1)


def test_perfect_match_without_roommates():
    score, breakdown = matching.score_room(TENANT, ROOM, [])
    assert breakdown["Presupuesto"] == 1
    assert breakdown["Zona"] == 1
    assert breakdown["Horarios"] == matching.NO_ROOMMATES_SCORE
    assert set(breakdown) == set(matching.WEIGHTS)
    assert 0 <= score <= 100


def test_identical_roommate_scores_100():
    score, _ = matching.score_room(TENANT, ROOM, [TENANT])
    assert score == 100


@pytest.mark.parametrize("tenant_change, room_change", [
    ({}, {"price": 661}),                              # > presupuesto + 10 %
    ({"smokes": 1}, {}),                               # fuma y no se permite
    ({"pets": 1}, {}),                                 # mascota y no se admiten
    ({"own_bathroom": 1}, {}),                         # necesita baño propio
    ({}, {"available_from": "2027-02-15"}),            # libre > 30 días después
])
def test_hard_filters_discard_room(tenant_change, room_change):
    assert matching.score_room({**TENANT, **tenant_change}, {**ROOM, **room_change}, []) is None


def test_over_budget_penalised_but_kept():
    _, breakdown = matching.score_room(TENANT, {**ROOM, "price": 660}, [])
    assert breakdown["Presupuesto"] == pytest.approx(0.4)


def test_zone_outside_preferences():
    _, breakdown = matching.score_room(TENANT, {**ROOM, "zone": "Usera"}, [])
    assert breakdown["Zona"] == 0.3


# ---------- La historia de la demo (no romper) ----------

def test_mario_first_match_is_chamberi_94(seeded_db):
    mario = db.find_user_by_name("Mario Rossi")
    assert mario["id"] == 1
    top = matching.matches_for(mario["id"])[0]
    assert top["room"]["id"] == 1
    assert top["room"]["title"] == "Habitación con baño propio en Chamberí"
    assert top["score"] == 94
    assert {m["name"] for m in top["mates"]} == {"Lucía Martín", "Tom Becker"}


def test_seed_counts(seeded_db):
    assert len(db.list_users("inquilino")) == 51
    assert len(db.list_users("casero")) == 8
    assert len(db.active_rooms()) == 30


def test_reverse_search_excludes_people_already_living_in_a_flat(seeded_db):
    living = db.rooms_lived_in()
    candidates = matching.candidates_for(1)
    assert candidates
    assert all(c["tenant"]["id"] not in living for c in candidates)
    assert [c["score"] for c in candidates] == sorted((c["score"] for c in candidates), reverse=True)


def test_seed_is_repeatable(seeded_db):
    """'Reiniciar datos de la demo' vuelve a llamar a seed() en el mismo proceso: debe dar lo mismo."""
    from rentflow import seed

    before = db.query("SELECT * FROM preferences ORDER BY user_id")
    seed.seed()
    assert db.query("SELECT * FROM preferences ORDER BY user_id") == before


# ---------- Filtros, mapa y fotos ----------

def test_filters_do_not_change_scores(seeded_db):
    allr = matching.matches_for(1, limit=None)
    assert len(allr) >= 10 and allr[0]["score"] == 94
    cheap = matching.filter_matches(allr, max_price=600)
    assert cheap and all(r["room"]["price"] <= 600 for r in cheap)
    by_id = {r["room"]["id"]: r["score"] for r in allr}
    assert all(by_id[r["room"]["id"]] == r["score"] for r in cheap)


def test_filters_zones_bathroom_and_sort(seeded_db):
    allr = matching.matches_for(1, limit=None)
    only = matching.filter_matches(allr, zones=["Chamberí"], own_bathroom=True)
    assert only[0]["room"]["id"] == 1
    assert all(r["room"]["zone"] == "Chamberí" and r["room"]["own_bathroom"] for r in only)
    by_price = matching.filter_matches(allr, sort="Precio más bajo")
    assert [r["room"]["price"] for r in by_price] == sorted(r["room"]["price"] for r in allr)
    assert matching.filter_matches(allr, max_price=1) == []


def test_room_coords_are_deterministic_and_near_zone():
    room = {"id": 7, "zone": "Usera"}
    assert db.room_coords(room) == db.room_coords(room)
    lat, lon = db.room_coords(room)
    zlat, zlon = db.ZONE_COORDS["Usera"]
    assert abs(lat - zlat) < 0.005 and abs(lon - zlon) < 0.006
    assert set(db.ZONE_COORDS) == set(db.ZONES)


def test_seed_rooms_have_photos(seeded_db):
    assert all(r["photo"] for r in db.active_rooms())


def test_update_user_keeps_role_and_verification(seeded_db):
    db.update_user(1, "Mario Rossi", 28, "Analista de riesgos", "Milán", "Nueva bio")
    u = db.get_user(1)
    assert (u["age"], u["occupation"], u["bio"]) == (28, "Analista de riesgos", "Nueva bio")
    assert u["role"] == "inquilino" and u["verified"] == 1
    assert matching.matches_for(1)[0]["score"] == 94  # editar el perfil no toca los hábitos
