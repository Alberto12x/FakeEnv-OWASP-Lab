"""Populate the FakeEnv database with realistic mock data.

Usage:
    python seed.py

This drops and recreates every table, then inserts an administrator, several
client accounts, six months of invoices each, and 30 days of daily telemetry
(water, electricity, temperature) per client.
"""

import random
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import Invoice, Property, Telemetry, User
from app.security import hash_password

random.seed(2026)  # reproducible data set

# username, email, password, name, surname, role, address, city, question, answer
ACCOUNTS = [
    ("admin", "admin@fakenv.com", "admin123", "Admin", "FakEnv", "admin",
     "Calle Mayor 1", "Madrid", "¿Cuál es el nombre de tu padre?", "Manuel"),
    ("ana.torres", "ana.torres@example.com", "password1", "Ana", "Torres", "user",
     "Av. del Sol 22", "Sevilla", "¿Cuál es el nombre de tu padre?", "Antonio"),
    ("carlos.ruiz", "carlos.ruiz@example.com", "qwerty", "Carlos", "Ruiz", "user",
     "Calle Luna 5", "Valencia", "¿Cuál es el nombre de tu padre?", "Jose"),
    ("lucia.mendez", "lucia.mendez@example.com", "lucia2024", "Lucía", "Méndez", "user",
     "Plaza Verde 8", "Bilbao", "¿Cuál es el nombre de tu primera mascota?", "Toby"),
    ("javier.gil", "javier.gil@example.com", "futbol10", "Javier", "Gil", "user",
     "Camino Real 14", "Zaragoza", "¿En qué ciudad naciste?", "Huesca"),
    ("marta.sanz", "marta.sanz@example.com", "girasol", "Marta", "Sanz", "user",
     "Calle Olivo 3", "Granada", "¿Cuál es el nombre de tu padre?", "Pedro"),
]


# Inmuebles por usuario: alias, dirección, ciudad, tipo, m2
PROPERTIES = {
    "ana.torres": [
        ("Vivienda habitual", "Av. del Sol 22", "Sevilla", "Vivienda", 95),
        ("Apartamento de playa", "Paseo Marítimo 8", "Cádiz", "Vivienda", 60),
    ],
    "carlos.ruiz": [
        ("Vivienda habitual", "Calle Luna 5", "Valencia", "Vivienda", 110),
    ],
    "lucia.mendez": [
        ("Vivienda habitual", "Plaza Verde 8", "Bilbao", "Vivienda", 80),
        ("Oficina", "Gran Vía 30", "Bilbao", "Oficina", 45),
    ],
    "javier.gil": [
        ("Chalet familiar", "Camino Real 14", "Zaragoza", "Vivienda", 140),
    ],
    "marta.sanz": [
        ("Vivienda habitual", "Calle Olivo 3", "Granada", "Vivienda", 70),
    ],
}


def build_users():
    users = []
    for (username, email, password, name, surname, role,
         address, city, question, answer) in ACCOUNTS:
        users.append(
            User(
                username=username,
                email=email,
                password=hash_password(password),
                name=name,
                surname=surname,
                role=role,
                address=address,
                city=city,
                security_question=question,
                security_answer=answer,
            )
        )
    return users


def build_invoices(user, start_counter):
    """Six monthly invoices for the last six months."""
    invoices = []
    today = date.today()
    for i in range(6):
        # Month window ending roughly i months ago.
        period_end = today.replace(day=1) - timedelta(days=1 + i * 30)
        period_start = period_end - timedelta(days=29)
        electricity = round(random.uniform(180, 420), 1)  # kWh / month
        water = round(random.uniform(4.0, 12.0), 2)       # m3 / month
        amount = round(electricity * 0.15 + water * 2.10 + 8.50, 2)
        number = f"FAK-{period_end.year}-{start_counter + i:04d}"
        invoices.append(
            Invoice(
                user=user,
                invoice_number=number,
                concept="Consumo de agua y electricidad",
                period_start=period_start,
                period_end=period_end,
                issue_date=period_end + timedelta(days=2),
                due_date=period_end + timedelta(days=22),
                electricity_kwh=electricity,
                water_m3=water,
                amount=amount,
                status="paid" if i > 0 else "pending",
            )
        )
    return invoices


def build_telemetry(prop, user, days=60, drift_sign=1):
    """`days` of daily readings per metric for one property.

    Each property gets its own baseline plus a gentle drift (`drift_sign` = +1
    rising consumption, -1 falling), so the charts show a recognisable trend
    instead of pure noise.
    """
    readings = []
    today = date.today()

    base_water = random.uniform(0.20, 0.40)   # m³/day
    base_elec = random.uniform(6.0, 12.0)     # kWh/day
    # Daily fractional drift applied over the whole window (e.g. +0.4%/day).
    drift = drift_sign * random.uniform(0.002, 0.006)

    for d in range(days):
        day = today - timedelta(days=d)
        age = days - 1 - d            # 0 = oldest day, days-1 = today
        factor = 1 + drift * age
        water = max(0.05, base_water * factor * random.uniform(0.85, 1.15))
        elec = max(1.0, base_elec * factor * random.uniform(0.85, 1.15))
        temp = random.uniform(18.5, 24.5)
        readings.append(Telemetry(
            user=user, property=prop, reading_date=day, metric="water",
            value=round(water, 3), unit="m³"))
        readings.append(Telemetry(
            user=user, property=prop, reading_date=day, metric="electricity",
            value=round(elec, 2), unit="kWh"))
        readings.append(Telemetry(
            user=user, property=prop, reading_date=day, metric="temperature",
            value=round(temp, 1), unit="°C"))
    return readings


def run():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        users = build_users()
        db.session.add_all(users)
        db.session.flush()  # assign ids

        counter = 1
        prop_index = 0
        for user in users:
            if user.is_admin:
                continue

            # Create this client's inmuebles and their per-property telemetry.
            # Alternate the trend direction so the demo shows both rising and
            # falling consumption.
            for alias, address, city, ptype, size in PROPERTIES.get(user.username, []):
                prop = Property(
                    owner=user, alias=alias, address=address,
                    city=city, property_type=ptype, size_m2=size,
                )
                db.session.add(prop)
                db.session.flush()
                drift_sign = 1 if prop_index % 2 == 0 else -1
                db.session.add_all(build_telemetry(prop, user, drift_sign=drift_sign))
                prop_index += 1

            db.session.add_all(build_invoices(user, counter))
            counter += 6

        db.session.commit()

        print("✓ Base de datos poblada con éxito.")
        print("\nCuentas creadas (usuario / contraseña):")
        for acc in ACCOUNTS:
            print(f"  - {acc[0]:<14} / {acc[2]:<12} ({acc[5]})")


if __name__ == "__main__":
    run()
