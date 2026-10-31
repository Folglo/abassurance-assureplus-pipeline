"""Protection des données personnelles (RGPD) : masquage et pseudonymisation."""

import hashlib

import pandas as pd


def mask_email(email):
    """« jean.dupont@mail.fr » devient « j***@mail.fr »."""
    if pd.isna(email) or "@" not in str(email):
        return email
    local, domain = str(email).split("@", 1)
    return f"{local[:1]}***@{domain}"


def mask_name(name):
    """« Jean DUPONT » devient « J*** D*** »."""
    if pd.isna(name):
        return name
    return " ".join(f"{word[:1]}***" for word in str(name).split())


def pseudonymise(value, salt="abassurance"):
    """Remplace un identifiant par une empreinte non réversible (10 caractères)."""
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:10]


def anonymise_pairs(pairs):
    """Tableau de doublons pour le profil « user » : aucune donnée directement lisible."""
    result = pairs.copy()
    for column in ("customer_a", "customer_b"):
        result[column] = result[column].map(pseudonymise)
    for column in ("name_a", "name_b"):
        result[column] = result[column].map(mask_name)
    for column in ("email_a", "email_b"):
        result[column] = result[column].map(mask_email)
    return result
