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


def generate(seed=42, n_oracle=800, n_sqlserver=500, n_cross=60, n_internal=10):
    """Construit les 8 tables sous forme de DataFrames (colonnes identiques aux annexes)."""
    rng = random.Random(seed)
    ab_clients, ap_users = [], []
    ab_people, ap_people = [], []  # personne rattachée à chaque ligne, pour créer les contrats

    for i in range(n_oracle):
        person = _person(rng)
        ab_clients.append(_ab_client(rng, 1000 + i, person))
        ab_people.append(1000 + i)

    # Doublons entre les deux bases : même personne, saisie différente côté SQL Server.
    # Les 8 premiers ont une date de naissance au format JJ/MM/AAAA (le défaut silencieux).
    for i in range(n_cross):
        row = ab_clients[(i * 7) % n_oracle]
        person = Person(
            row["AB_PRENOM"],
            row["AB_NOM"].title(),
            date.fromisoformat(row["AB_DATE_NAISSANCE"]),
            row["AB_EMAIL"].replace("#", "@"),
            row["AB_TELEPHONE"].replace(" ", "") or "0612345678",
            row["AB_ADRESSE"],
            row["AB_CODE_POSTAL"].zfill(5),
            row["AB_NUM_FISCAL"],
        )
        french = person.birth.strftime("%d/%m/%Y") if i < 8 else None
        ap_users.append(
            _ap_user(
                rng, 5000 + len(ap_users), person, french, keep_email=i < 8 or rng.random() < 0.88
            )
        )
        ap_people.append(5000 + len(ap_users) - 1)

    for _ in range(n_sqlserver - n_cross):
        ap_users.append(_ap_user(rng, 5000 + len(ap_users), _person(rng)))
        ap_people.append(5000 + len(ap_users) - 1)

    # Doublons internes : le même client saisi deux fois dans Oracle.
    for i in range(n_internal):
        original = ab_clients[(100 + i * 11) % n_oracle]
        twin = dict(original, AB_CLIENT_ID=9000 + i, AB_NOM=original["AB_NOM"].lower().title())
        twin["AB_TELEPHONE"] = "" if i % 2 else original["AB_TELEPHONE"]
        ab_clients.append(twin)
        ab_people.append(9000 + i)

    # Doublons internes côté SQL Server : même personne, deux identifiants.
    for i in range(4):
        original = ap_users[(200 + i * 13) % n_sqlserver]
        twin = dict(
            original,
            AP_USER_ID=7000 + i,
            AP_PHONE_NUMBER="",
            AP_FULL_NAME=original["AP_FULL_NAME"].upper(),
        )
        ap_users.append(twin)
        ap_people.append(7000 + i)

    # Pièges : familles qui partagent email et téléphone (ne sont PAS des doublons).
    for i in range(6):
        base = ab_clients[(300 + i * 13) % n_oracle]
        ab_clients.append(
            dict(
                base,
                AB_CLIENT_ID=9500 + i,
                AB_PRENOM=rng.choice(["Paul", "Jade", "Noé"]),
                AB_DATE_NAISSANCE=(date(2001, 1, 1) + timedelta(days=i * 97)).isoformat(),
            )
        )
        ab_people.append(9500 + i)

    # Défauts supplémentaires dans SQL Server : dates invalides et clés répétées.
    bad_dates = ("1985-13-45", "00/00/0000", "31/02/1990", "", "demain", "1850-01-01")
    for index, bad in enumerate(bad_dates, start=60):
        ap_users[index % n_sqlserver]["AP_BIRTH_DATE"] = bad
    ap_users.append(dict(ap_users[10]))
    ap_users.append(dict(ap_users[11]))
    ab_clients.append(dict(ab_clients[5]))
    ab_clients.append(dict(ab_clients[6]))
    ab_clients.append(dict(ab_clients[7]))

    # Contrats, sinistres, paiements.
    ab_contracts, ab_claims, ab_payments = [], [], []
    ap_contracts, ap_claims, ap_payments = [], [], []
    counter = {"claim": 1, "payment": 1, "number": 1}

    for client_id in ab_people:
        for _ in range(rng.choices([0, 1, 2, 3], [10, 50, 30, 10])[0]):
            number = f"AB-POL-{counter['number']:06d}"
            counter["number"] += 1
            start, end = _contract_dates(rng)
            kind = rng.choice(AB_TYPES)
            annual = round(
                rng.uniform(
                    *{
                        "SANTE": (600, 2400),
                        "HABITATION": (200, 900),
                        "AUTO": (400, 1500),
                        "PROFESSIONNEL": (800, 5000),
                    }[kind]
                ),
                2,
            )
            ab_contracts.append(
                {
                    "AB_POLICY_NUMBER": number,
                    "AB_CLIENT_ID": client_id,
                    "AB_TYPE_ASSURANCE": kind,
                    "AB_DATE_DEBUT": start.isoformat(),
                    "AB_DATE_FIN": end.isoformat(),
                    "AB_PRIME_ANNUELLE": annual,
                    "AB_STATUT_CONTRAT": _contract_status(rng, end, "ACTIF", "EXPIRE", "RESILIE"),
                    "AB_AGENCE_ID": rng.randrange(1, 60),
                }
            )
            claims, payments = _extras(rng, number, start, end, annual, ab=True)
            for stamp, amount, text in claims:
                ab_claims.append(
                    {
                        "AB_CLAIM_ID": counter["claim"],
                        "AB_POLICY_NUMBER": number,
                        "AB_DATE_SINISTRE": stamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "AB_MONTANT_ESTIME": amount,
                        "AB_STATUT_SINISTRE": rng.choice(["OUVERT", "EN_COURS", "CLOS", "REFUSE"]),
                        "AB_DESCRIPTION": text,
                    }
                )
                counter["claim"] += 1
            for stamp, amount in payments:
                ab_payments.append(
                    {
                        "AB_PAYMENT_ID": counter["payment"],
                        "AB_POLICY_NUMBER": number,
                        "AB_DATE_PAIEMENT": stamp.date().isoformat(),
                        "AB_MONTANT": amount,
                        "AB_MODE_PAIEMENT": rng.choice(AB_METHODS),
                    }
                )
                counter["payment"] += 1

    for user_id in ap_people:
        for _ in range(rng.choices([0, 1, 2], [15, 60, 25])[0]):
            number = f"AP-C-{counter['number']:06d}"
            counter["number"] += 1
            start, end = _contract_dates(rng)
            product = rng.choice(AP_PRODUCTS)
            monthly = round(
                rng.uniform(
                    *{
                        "AUTO_BASIC": (25, 70),
                        "AUTO_PREMIUM": (60, 140),
                        "ASSISTANCE_PREMIUM": (8, 30),
                    }[product]
                ),
                2,
            )
            ap_contracts.append(
                {
                    "AP_CONTRACT_REF": number,
                    "AP_USER_ID": user_id,
                    "AP_PRODUCT_CODE": product,
                    "AP_START_DATE": f"{start.isoformat()} 00:00:00",
                    "AP_END_DATE": f"{end.isoformat()} 00:00:00",
                    "AP_MONTHLY_PREMIUM": monthly,
                    "AP_CONTRACT_STATE": _contract_status(
                        rng, end, "ACTIVE", "EXPIRED", "CANCELLED"
                    ),
                    "AP_BROKER_CODE": f"BRK{rng.randrange(1, 40):03d}",
                }
            )
            claims, payments = _extras(rng, number, start, end, monthly * 12, ab=False)
            for stamp, amount, text in claims:
                ap_claims.append(
                    {
                        "AP_SINISTRE_NUM": counter["claim"],
                        "AP_CONTRACT_REF": number,
                        "AP_INCIDENT_DATE": stamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "AP_ESTIMATED_AMOUNT": amount,
                        "AP_CLAIM_STATUS": rng.choice(
                            ["OPEN", "IN_PROGRESS", "CLOSED", "REJECTED"]
                        ),
                        "AP_CLAIM_COMMENT": text,
                        "AP_FRAUD_SCORE": _fraud_score(rng),
                    }
                )
                counter["claim"] += 1
            for stamp, amount in payments:
                ap_payments.append(
                    {
                        "AP_PAYMENT_REF": str(
                            uuid.UUID(int=rng.getrandbits(128), version=4)
                        ).upper(),
                        "AP_CONTRACT_REF": number,
                        "AP_PAYMENT_DATETIME": stamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "AP_AMOUNT_PAID": amount,
                        "AP_PAYMENT_CHANNEL": rng.choice(AP_CHANNELS),
                        "AP_TRANSACTION_STATUS": rng.choices(
                            ["SUCCESS", "FAILED", "PENDING"], [92, 5, 3]
                        )[0],
                    }
                )

    # Lignes orphelines : contrat sans client, sinistre sans contrat.
    ab_contracts.append(
        dict(ab_contracts[0], AB_POLICY_NUMBER="AB-POL-ORPHAN", AB_CLIENT_ID=999999)
    )
    ab_contracts.append(
        dict(ab_contracts[1], AB_POLICY_NUMBER="AB-POL-ORPHAN2", AB_CLIENT_ID=999998)
    )
    ap_claims.append(dict(ap_claims[0], AP_SINISTRE_NUM=99999, AP_CONTRACT_REF="AP-C-UNKNOWN"))
    ab_payments.append(dict(ab_payments[0], AB_PAYMENT_ID=99999, AB_POLICY_NUMBER="AB-POL-UNKNOWN"))

    rng.shuffle(ap_users)  # l'ordre des lignes ne doit rien révéler
    return {
        "ab_client": pd.DataFrame(ab_clients),
        "ab_contrat": pd.DataFrame(ab_contracts),
        "ab_sinistre": pd.DataFrame(ab_claims),
        "ab_paiement": pd.DataFrame(ab_payments),
        "ap_users": pd.DataFrame(ap_users),
        "ap_contracts": pd.DataFrame(ap_contracts),
        "ap_claims": pd.DataFrame(ap_claims),
        "ap_payments": pd.DataFrame(ap_payments),
    }


def write_csv(output_dir=DATA_DIR, **options):
    """Écrit les 8 fichiers CSV (UTF-8) dans le dossier demandé."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = generate(**options)
    for name, frame in tables.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8")
    return {name: len(frame) for name, frame in tables.items()}


if __name__ == "__main__":
    for table_name, count in write_csv().items():
        print(f"{table_name}: {count} lignes")
