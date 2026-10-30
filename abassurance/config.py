"""Constantes du projet : chemins, sources et tables de correspondance des valeurs."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SOURCE_AB = "AbAssurance"
SOURCE_AP = "AssurePlus"
SOURCE_CODES = {SOURCE_AB: "AB", SOURCE_AP: "AP"}

# Seuil de similarité des noms et seuil d'alerte fraude (hypothèses à valider avec le client).
NAME_SIMILARITY_THRESHOLD = 0.85
FRAUD_ALERT_THRESHOLD = 80

# Les valeurs réelles devront être confirmées par un SELECT DISTINCT sur chaque base.
CUSTOMER_STATUS = {
    "ACTIF": "active",
    "INACTIF": "inactive",
    "SUSPENDU": "suspended",
    "RESILIE": "terminated",
    "ACTIVE": "active",
    "INACTIVE": "inactive",
    "SUSPENDED": "suspended",
    "TERMINATED": "terminated",
}

CONTRACT_STATUS = {
    "ACTIF": "active",
    "EXPIRE": "expired",
    "RESILIE": "cancelled",
    "ACTIVE": "active",
    "EXPIRED": "expired",
    "CANCELLED": "cancelled",
}

INSURANCE_TYPE = {
    "SANTE": "health",
    "HABITATION": "home",
    "AUTO": "auto",
    "PROFESSIONNEL": "professional",
    "AUTO_BASIC": "auto",
    "AUTO_PREMIUM": "auto",
    "ASSISTANCE_PREMIUM": "assistance",
}

CLAIM_STATUS = {
    "OUVERT": "open",
    "EN_COURS": "in_progress",
    "CLOS": "closed",
    "REFUSE": "rejected",
    "OPEN": "open",
    "IN_PROGRESS": "in_progress",
    "CLOSED": "closed",
    "REJECTED": "rejected",
}

PAYMENT_METHOD = {
    "CB": "card",
    "VIREMENT": "transfer",
    "PRELEVEMENT": "direct_debit",
    "CHEQUE": "cheque",
    "CARD": "card",
    "WIRE": "transfer",
    "DIRECT_DEBIT": "direct_debit",
    "CHECK": "cheque",
}

PAYMENT_STATUS = {
    "SUCCESS": "paid",
    "FAILED": "failed",
    "PENDING": "pending",
}
