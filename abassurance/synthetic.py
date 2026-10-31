"""Génération de données fictives (aucune donnée réelle) avec les colonnes exactes des annexes.

Les jeux de données contiennent volontairement des défauts réalistes : doublons entre les deux
bases, dates de naissance mal formatées, emails invalides, clés répétées, lignes orphelines.

Lancement : python -m abassurance.synthetic
"""

import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from abassurance.clean import to_ascii
from abassurance.config import DATA_DIR

REFERENCE_DATE = date(2026, 10, 30)

FIRST_NAMES = [
    "Jean",
    "Marie",
    "Pierre",
    "Sophie",
    "Lucas",
    "Camille",
    "Thomas",
    "Julie",
    "Nicolas",
    "Emma",
    "Antoine",
    "Léa",
    "Hugo",
    "Chloé",
    "Mathieu",
    "Manon",
    "Julien",
    "Sarah",
    "Maxime",
    "Inès",
    "Alexandre",
    "Hélène",
    "François",
    "Élodie",
    "Romain",
    "Anaïs",
    "Kévin",
    "Fatima",
    "Mohamed",
    "Aïcha",
    "Yann",
    "Claire",
    "Olivier",
    "Céline",
    "Sébastien",
    "Laura",
    "Benoît",
    "Amélie",
]
LAST_NAMES = [
    "Martin",
    "Bernard",
    "Dubois",
    "Thomas",
    "Robert",
    "Richard",
    "Petit",
    "Durand",
    "Leroy",
    "Moreau",
    "Simon",
    "Laurent",
    "Lefebvre",
    "Michel",
    "Garcia",
    "David",
    "Bertrand",
    "Roux",
    "Vincent",
    "Fournier",
    "Morel",
    "Girard",
    "André",
    "Mercier",
    "Dupont",
    "Lambert",
    "Bonnet",
    "François",
    "Martinez",
    "Legrand",
    "Garnier",
    "Faure",
    "Rousseau",
    "Blanc",
    "Guérin",
    "Muller",
    "Henry",
    "Roussel",
    "Nicolas",
    "Perrin",
    "Morin",
    "Mathieu",
    "Clément",
    "Gauthier",
    "Dumont",
    "Lopez",
    "Fontaine",
    "Chevalier",
    "Robin",
    "Masson",
    "Traoré",
    "Diallo",
    "Touré",
]
CITIES = [
    ("Paris", "75011"),
    ("Lyon", "69003"),
    ("Marseille", "13006"),
    ("Toulouse", "31000"),
    ("Nice", "06000"),
    ("Nantes", "44000"),
    ("Bordeaux", "33000"),
    ("Lille", "59000"),
    ("Strasbourg", "67000"),
    ("Rennes", "35000"),
    ("Bourg-en-Bresse", "01000"),
    ("Dijon", "21000"),
]
DOMAINS = ["mail.fr", "exemple.com", "courriel.org", "webmail.fr"]
CLAIM_TEXTS = [
    "Dégât des eaux dans la cuisine",
    "Collision arrière sur un parking",
    "Bris de glace",
    "Vol de vélo",
    "Incendie de la remise",
    "Hospitalisation suite à une chute",
    "Grêle sur toiture",
]
AB_TYPES = ["SANTE", "HABITATION", "AUTO", "PROFESSIONNEL"]
AP_PRODUCTS = ["AUTO_BASIC", "AUTO_PREMIUM", "ASSISTANCE_PREMIUM"]
AB_METHODS = ["CB", "VIREMENT", "PRELEVEMENT", "CHEQUE"]
AP_CHANNELS = ["CARD", "WIRE", "DIRECT_DEBIT", "CHECK"]


@dataclass
class Person:
    """Une personne fictive, source commune des lignes Oracle et SQL Server."""

    first: str
    last: str
    birth: date
    email: str
    phone: str
    street: str
    zip_code: str
    tax_number: str


def _person(rng):
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    city, zip_code = rng.choice(CITIES)
    birth = date(1945, 1, 1) + timedelta(days=rng.randrange(0, 365 * 61))
    email = f"{to_ascii(first).lower()}.{to_ascii(last).lower()}{rng.randrange(1, 99)}"
    phone = "0" + rng.choice("67") + "".join(rng.choice("0123456789") for _ in range(8))
    return Person(
        first,
        last,
        birth,
        f"{email}@{rng.choice(DOMAINS)}",
        phone,
        f"{rng.randrange(1, 120)} rue {rng.choice(LAST_NAMES)}, {city}",
        zip_code,
        "".join(rng.choice("0123456789") for _ in range(13)),
    )


def _ab_phone(rng, phone):
    return " ".join(phone[i : i + 2] for i in range(0, 10, 2)) if rng.random() < 0.5 else phone


def _ap_phone(rng, phone):
    if rng.random() < 0.5:
        return "+33 " + phone[1] + " " + " ".join(phone[i : i + 2] for i in range(2, 10, 2))
    return ".".join(phone[i : i + 2] for i in range(0, 10, 2))


def _timestamp(rng, start=date(2012, 1, 1), end=REFERENCE_DATE):
    day = start + timedelta(days=rng.randrange(0, (end - start).days))
    return datetime(day.year, day.month, day.day, rng.randrange(8, 19), rng.randrange(60))


def _ab_client(rng, client_id, person):
    zip_code = person.zip_code
    if zip_code.startswith("0") and rng.random() < 0.5:
        zip_code = zip_code.lstrip("0")  # le zéro de tête a été perdu dans l'ancien système
    email = person.email if rng.random() > 0.03 else person.email.replace("@", "#")
    return {
        "AB_CLIENT_ID": client_id,
        "AB_NOM": person.last.upper() if rng.random() < 0.5 else person.last,
        "AB_PRENOM": person.first,
        "AB_DATE_NAISSANCE": person.birth.isoformat(),
        "AB_EMAIL": email,
        "AB_TELEPHONE": _ab_phone(rng, person.phone) if rng.random() > 0.02 else "",
        "AB_ADRESSE": person.street,
        "AB_CODE_POSTAL": zip_code,
        "AB_NUM_FISCAL": person.tax_number,
        "AB_DATE_CREATION": _timestamp(rng).strftime("%Y-%m-%d %H:%M:%S"),
        "AB_STATUT_CLIENT": rng.choices(
            ["ACTIF", "INACTIF", "SUSPENDU", "RESILIE"], [80, 10, 3, 7]
        )[0],
    }


def _ap_name(rng, person):
    first, last = person.first, person.last.upper()
    if rng.random() < 0.2:
        first, last = to_ascii(first), to_ascii(last)
    style = rng.random()
    if style < 0.8:
        return f"{first} {last}"
    if style < 0.9:
        return f"{last} {first}"
    return f"{last}, {first}"


def _ap_user(rng, user_id, person, birth_text=None, keep_email=True):
    email = person.email.upper() if rng.random() < 0.2 else person.email
    if not keep_email and rng.random() < 0.5:
        email = person.email.split("@")[0] + "@autre-" + person.email.split("@")[1]
    return {
        "AP_USER_ID": user_id,
        "AP_FULL_NAME": _ap_name(rng, person),
        "AP_BIRTH_DATE": birth_text if birth_text is not None else person.birth.isoformat(),
        "AP_MAIL_ADDRESS": email,
        "AP_PHONE_NUMBER": _ap_phone(rng, person.phone),
        "AP_STREET_ADDRESS": person.street,
        "AP_ZIP_CODE": person.zip_code,
        "AP_CREATED_AT": _timestamp(rng).strftime("%Y-%m-%d %H:%M:%S"),
        "AP_CUSTOMER_STATUS": rng.choices(
            ["ACTIVE", "INACTIVE", "SUSPENDED", "TERMINATED"], [80, 10, 3, 7]
        )[0],
        "AP_LOYALTY_SCORE": rng.randrange(0, 101),
    }


def _fraud_score(rng):
    """Score de fraude de 0 à 100 : la plupart sont faibles, quelques-uns dépassent le seuil."""
    if rng.random() < 0.06:
        return round(rng.uniform(80, 99), 2)
    return round(rng.betavariate(1.2, 6) * 100, 2)


def _contract_dates(rng):
    start = date(2018, 1, 1) + timedelta(days=rng.randrange(0, 365 * 8 + 150))
    end = start + timedelta(days=365 * rng.choice([1, 2, 3, 5]))
    return start, end


def _contract_status(rng, end, active, expired, cancelled):
    if rng.random() < 0.08:
        return cancelled
    return active if end >= REFERENCE_DATE else expired


def _extras(rng, contract_number, start, end, annual, ab):
    """Sinistres et paiements d'un contrat. `ab` : True pour Oracle, False pour SQL Server."""
    claims, payments = [], []
    last_day = min(end, REFERENCE_DATE)
    if rng.random() < 0.18 and last_day > start:
        day = start + timedelta(days=rng.randrange(0, (last_day - start).days + 1))
        amount = round(rng.lognormvariate(7.2, 0.9), 2)
        stamp = datetime(day.year, day.month, day.day, rng.randrange(0, 24), rng.randrange(60))
        claims.append((stamp, min(amount, 90000.0), rng.choice(CLAIM_TEXTS)))
    span = (last_day - start).days
    for _ in range(6 if span > 0 else 0):
        day = start + timedelta(days=rng.randrange(0, span + 1))
        payments.append(
            (
                datetime(day.year, day.month, day.day, rng.randrange(8, 20), rng.randrange(60)),
                round(annual / 12, 2),
            )
        )
    return claims, payments
