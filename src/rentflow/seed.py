"""Carga datos de ejemplo de Madrid para la demo (siempre los mismos, semilla fija).

Uso:  uv run rentflow-seed     -> borra la base de datos y la vuelve a crear
      (equivale a: uv run python -m rentflow.seed)
"""
import random
from datetime import date, timedelta

from rentflow import db

SEED = 42  # semilla fija: los datos son siempre los mismos

ZONE_PRICE = {  # precio base orientativo de una habitación (€/mes)
    "Chamberí": 640, "Malasaña": 620, "Chueca": 630, "Salamanca": 680, "Retiro": 600,
    "Lavapiés": 540, "La Latina": 570, "Argüelles": 580, "Moncloa": 560, "Tetuán": 500,
    "Arganzuela": 520, "Usera": 450,
}
FIRST_NAMES = [
    "Lucía", "Pablo", "Sofía", "Hugo", "Martina", "Daniel", "Paula", "Álvaro", "Carla", "Javier",
    "Elena", "Marcos", "Irene", "Sergio", "Claudia", "Adrián", "Nerea", "Diego", "Laura", "Iván",
    "Chiara", "Luca", "Emma", "Jonas", "Chloé", "Lukas", "Anna", "Mateo", "Inés", "Tomás",
    "Julia", "Noah", "Valeria", "Leo", "Alba", "Bruno", "Marta", "Félix", "Sara", "Nico",
    "Giulia", "Thomas", "Camille", "Oliver", "Lena", "Rafael", "Aitana", "Óscar", "Noa", "Gabriel",
]
ORIGINS = ["Valencia", "Sevilla", "Bilbao", "Zaragoza", "A Coruña", "Murcia", "Valladolid",
           "Roma", "París", "Berlín", "Lisboa", "Múnich", "Milán", "Ámsterdam", "Bogotá"]
OCCUPATIONS = {
    "Erasmus": ["Erasmus en la UCM", "Erasmus en la UC3M", "Erasmus en la UPM", "Erasmus en Comillas ICAI"],
    "Estudiante": ["Estudiante de Ingeniería", "Estudiante de Derecho", "Estudiante de Medicina",
                   "Estudiante de máster", "Estudiante de ADE"],
    "Primer trabajo": ["Consultor junior", "Ingeniera de software", "Analista financiero",
                       "Enfermera", "Diseñador UX", "Profesora de inglés", "Auditor junior"],
}
LANDLORDS = [
    ("Carmen Ruiz", 58, "Jubilada, alquila dos pisos heredados"),
    ("Antonio Gil", 52, "Funcionario, alquila un piso por habitaciones"),
    ("Pilar Navarro", 64, "Jubilada, vive en la sierra"),
    ("Javier Ortega", 45, "Médico a turnos"),
    ("Rosa Medina", 61, "Profesora jubilada"),
    ("Fernando Castro", 49, "Pequeño empresario"),
    ("Isabel Moreno", 55, "Gestiona el piso de sus padres"),
    ("Luis Herrera", 67, "Jubilado"),
]
LANDLORD_COMMENTS = [
    (5, "Muy atento, arregló la caldera en un día."),
    (5, "Contrato claro y devolvió la fianza sin problemas."),
    (4, "Buen trato, aunque tarda un poco en contestar."),
    (5, "El piso era exactamente como en las fotos."),
    (4, "Correcto en todo, muy recomendable."),
    (3, "Bien en general, pero las reparaciones iban lentas."),
]
MATE_COMMENTS = [
    (5, "Ordenada y muy maja, compartimos cenas los domingos."),
    (5, "Respeta los horarios y siempre paga a tiempo."),
    (4, "Buen compañero, a veces algo ruidoso los fines de semana."),
    (5, "Convivencia fácil, se nota que tenemos rutinas parecidas."),
    (4, "Limpio y tranquilo, muy recomendable."),
]
DESCRIPTIONS = [
    "Habitación exterior y luminosa en piso reformado, cerca del metro.",
    "Piso tranquilo con salón amplio y cocina equipada. Gastos aparte (unos 50 €).",
    "Habitación con escritorio y armario empotrado, ideal para estudiar o teletrabajar.",
    "Piso con terraza comunitaria, a 5 minutos de la parada de metro.",
    "Habitación amplia en edificio con ascensor. Wifi de fibra incluido.",
]


def rand_date(start, end):
    return (start + timedelta(days=random.randint(0, (end - start).days))).isoformat()


def random_prefs(uid, segment):
    budget_max = random.choice([450, 500, 550, 600, 650, 700, 750])
    if segment == "Erasmus":
        budget_max = random.choice([450, 500, 550, 600])
    db.save_preferences(
        uid,
        budget_min=budget_max - 200,
        budget_max=budget_max,
        zones=random.sample(db.ZONES, k=random.randint(2, 4)),
        move_in=rand_date(date(2026, 12, 15), date(2027, 2, 1)),
        schedule=random.choice(db.SCHEDULES),
        cleanliness=random.randint(2, 5),
        noise=random.randint(1, 4),
        smokes=random.random() < 0.15,
        pets=random.random() < 0.1,
        own_bathroom=random.random() < 0.2,
    )


def make_tenant(name):
    segment = random.choice(list(OCCUPATIONS))
    age = {"Erasmus": random.randint(20, 24), "Estudiante": random.randint(19, 25),
           "Primer trabajo": random.randint(23, 30)}[segment]
    surname = random.choice("ABCDEFGHIJLMNOPRSTV")
    uid = db.create_user(f"{name} {surname}.", age, "inquilino", random.choice(OCCUPATIONS[segment]),
                         random.choice(ORIGINS), verified=int(random.random() < 0.7))
    random_prefs(uid, segment)
    return uid


def seed():
    """Borra la base de datos y la vuelve a llenar. Idempotente: siempre genera los mismos datos."""
    random.seed(SEED)  # aquí y no al importar: "Reiniciar datos" debe dar lo mismo que la primera vez
    if db.DB_PATH.exists():
        db.DB_PATH.unlink()
    db.init_db()

    # --- Mario, el protagonista de la demo ---
    mario = db.create_user("Mario Rossi", 27, "inquilino", "Analista en banca de inversión", "Milán",
                           "Recién llegado a Madrid por trabajo. Gimnasio y running entre semana.", verified=1)
    db.save_preferences(mario, 500, 700, ["Chamberí", "Malasaña", "Argüelles"], "2027-01-10",
                        db.SCHEDULES[0], cleanliness=4, noise=2, smokes=False, pets=False, own_bathroom=True)

    # --- Caseros ---
    landlords = [db.create_user(n, a, "casero", "Propietario particular", "Madrid", bio, verified=1)
                 for n, a, bio in LANDLORDS]

    # --- Inquilinos: unos buscan piso y otros ya viven en uno (compañeros) ---
    names = FIRST_NAMES[:]
    random.shuffle(names)
    seekers = [make_tenant(n) for n in names[:20]]
    pool = [make_tenant(n) for n in names[20:48]]

    # --- El piso de Mario: Chamberí, con Lucía y Tom ---
    lucia = db.create_user("Lucía Martín", 26, "inquilino", "Fisioterapeuta, corre maratones", "Valencia",
                           "Me encanta correr por el Retiro y cocinar los domingos.", verified=1)
    db.save_preferences(lucia, 500, 700, ["Chamberí"], "2026-09-01", db.SCHEDULES[0], 3, 2, False, False, True)
    tom = db.create_user("Tom Becker", 28, "inquilino", "Consultor de estrategia", "Berlín",
                         "Trabajo mucho entre semana; los viernes, cerveza en la terraza.", verified=1)
    db.save_preferences(tom, 550, 750, ["Chamberí"], "2026-09-01", db.SCHEDULES[0], 2, 3, False, False, True)
    db.create_room(landlords[0], "Habitación con baño propio en Chamberí", "Chamberí", 650, 14, True,
                   "2027-01-01", False, False,
                   "Piso exterior de 3 habitaciones junto a la plaza de Olavide. Mucha luz, salón amplio "
                   "y cocina reformada. Metro Iglesia a 3 minutos.", members=[lucia, tom])

    # --- Resto de habitaciones ---
    for _ in range(29):
        zone = random.choice(db.ZONES)
        own_bath = random.random() < 0.4
        price = ZONE_PRICE[zone] + random.randint(-60, 80) + (60 if own_bath else 0)
        price = round(price / 10) * 10
        n_mates = min(random.choice([0, 1, 1, 2, 2, 3]), len(pool))
        members = [pool.pop() for _ in range(n_mates)]
        db.create_room(
            landlord_id=random.choice(landlords),
            title=f"Habitación {'con baño propio ' if own_bath else ''}en {zone}",
            zone=zone, price=price, size_m2=random.randint(9, 18), own_bathroom=own_bath,
            available_from=rand_date(date(2026, 12, 1), date(2027, 2, 15)),
            smoking_allowed=random.random() < 0.2, pets_allowed=random.random() < 0.3,
            description=random.choice(DESCRIPTIONS), members=members,
        )

    # --- Reseñas de caseros y de compañeros ---
    authors = seekers + [lucia, tom]
    for ll in landlords:
        for rating, text in random.sample(LANDLORD_COMMENTS, k=random.randint(2, 5)):
            db.add_review(random.choice(authors), ll, rating, text)
    for mate in [lucia, tom] + [r["user_id"] for r in db.query("SELECT user_id FROM room_members")]:
        for rating, text in random.sample(MATE_COMMENTS, k=random.randint(1, 3)):
            db.add_review(random.choice(seekers), mate, rating, text)

    # --- Un par de conversaciones para que el casero tenga interesados ---
    other_rooms = [r for r in db.rooms_of_landlord(landlords[0]) if r["id"] > 1]
    if other_rooms:
        room = min(other_rooms, key=lambda r: r["id"])
        for tenant in seekers[:2]:
            conv, _ = db.get_or_create_conversation(room["id"], tenant)
            db.send_message(conv, tenant, "¡Hola! Me interesa la habitación. ¿Se puede visitar esta semana?")

    print(f"Base de datos creada en {db.DB_PATH}")
    print(f"  {len(db.list_users('inquilino'))} inquilinos, {len(landlords)} caseros, "
          f"{len(db.active_rooms())} habitaciones")


def main() -> None:
    seed()


if __name__ == "__main__":
    main()
