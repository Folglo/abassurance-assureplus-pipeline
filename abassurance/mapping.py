"""Mapping : transformation des schémas Oracle et SQL Server vers le modèle unifié."""

import pandas as pd

from abassurance import config
from abassurance.clean import (
    clean_email,
    clean_phone,
    clean_text,
    clean_zip,
    map_values,
    parse_dates,
    parse_numbers,
)

CUSTOMER_COLUMNS = [
    "customer_key",
    "source",
    "origin_id",
    "last_name",
    "first_name",
    "birth_date",
    "email",
    "phone",
    "address",
    "zip_code",
    "tax_number",
    "created_at",
    "status",
    "loyalty_score",
]
CONTRACT_COLUMNS = [
    "contract_key",
    "source",
    "contract_number",
    "customer_key",
    "insurance_type",
    "start_date",
    "end_date",
    "annual_premium",
    "status",
    "intermediary_code",
]
CLAIM_COLUMNS = [
    "claim_key",
    "source",
    "origin_number",
    "contract_key",
    "claim_date",
    "estimated_amount",
    "status",
    "description",
    "fraud_score",
]
PAYMENT_COLUMNS = [
    "payment_key",
    "source",
    "origin_reference",
    "contract_key",
    "payment_date",
    "amount",
    "method",
    "status",
]


def _clean(log, table, source, column, ids, raw_values, cleaner):
    """Nettoie une colonne et enregistre les anomalies dans le journal."""
    values, reasons = cleaner(raw_values)
    log.record(table, source, column, ids, raw_values, reasons)
    return values


def _key(source, values):
    """Clé unique inter-sources : « AB-12 » ou « AP-12 »."""
    return config.SOURCE_CODES[source] + "-" + values.astype(str).str.strip()


def split_full_name(full_name):
    """Sépare « Prénom NOM », « NOM Prénom » ou « NOM, Prénom » (règle à valider avec le client).

    Les mots en majuscules forment le nom ; sinon le dernier mot est le nom.
    """
    if pd.isna(full_name) or not str(full_name).strip():
        return None, None
    text = " ".join(str(full_name).split())
    if "," in text:
        last, first = (part.strip() for part in text.split(",", 1))
        return last.upper(), first.title()
    tokens = text.split(" ")
    upper = [t for t in tokens if t.isupper() and len(t) > 1]
    if upper and len(upper) < len(tokens):
        last = [t for t in tokens if t in upper]
        first = [t for t in tokens if t not in upper]
    else:
        last, first = tokens[-1:], tokens[:-1]
    return " ".join(last).upper(), " ".join(first).title() or None


def map_customers_oracle(raw, log, today):
    """AB_CLIENT vers le modèle unifié."""
    src, table, ids = config.SOURCE_AB, "customers", raw["AB_CLIENT_ID"]
    frame = pd.DataFrame({"origin_id": ids.astype(str).str.strip()})
    frame["customer_key"] = _key(src, ids)
    frame["source"] = src
    last = _clean(log, table, src, "last_name", ids, raw["AB_NOM"], clean_text)
    first = _clean(log, table, src, "first_name", ids, raw["AB_PRENOM"], clean_text)
    frame["last_name"] = last.str.upper()
    frame["first_name"] = first.str.title()
    frame["birth_date"] = _clean(
        log,
        table,
        src,
        "birth_date",
        ids,
        raw["AB_DATE_NAISSANCE"],
        lambda s: parse_dates(s, today),
    )
    frame["email"] = _clean(log, table, src, "email", ids, raw["AB_EMAIL"], clean_email)
    frame["phone"] = _clean(log, table, src, "phone", ids, raw["AB_TELEPHONE"], clean_phone)
    frame["address"] = _clean(log, table, src, "address", ids, raw["AB_ADRESSE"], clean_text)
    frame["zip_code"] = _clean(log, table, src, "zip_code", ids, raw["AB_CODE_POSTAL"], clean_zip)
    frame["tax_number"] = raw["AB_NUM_FISCAL"].str.strip()
    frame["created_at"] = _clean(
        log,
        table,
        src,
        "created_at",
        ids,
        raw["AB_DATE_CREATION"],
        lambda s: parse_dates(s, today),
    )
    frame["status"] = _clean(
        log,
        table,
        src,
        "status",
        ids,
        raw["AB_STATUT_CLIENT"],
        lambda s: map_values(s, config.CUSTOMER_STATUS),
    )
    frame["loyalty_score"] = pd.Series(float("nan"), index=frame.index)
    return frame[CUSTOMER_COLUMNS]


def map_customers_sqlserver(raw, log, today):
    """AP_USERS vers le modèle unifié (le nom complet est séparé en nom et prénom)."""
    src, table, ids = config.SOURCE_AP, "customers", raw["AP_USER_ID"]
    frame = pd.DataFrame({"origin_id": ids.astype(str).str.strip()})
    frame["customer_key"] = _key(src, ids)
    frame["source"] = src
    names = [split_full_name(value) for value in raw["AP_FULL_NAME"]]
    frame["last_name"] = pd.Series([n[0] for n in names], index=frame.index, dtype="object")
    frame["first_name"] = pd.Series([n[1] for n in names], index=frame.index, dtype="object")
    log.record(
        table,
        src,
        "full_name",
        ids,
        raw["AP_FULL_NAME"],
        pd.Series(["unsplittable" if n[0] is None else None for n in names], index=frame.index),
    )
    frame["birth_date"] = _clean(
        log,
        table,
        src,
        "birth_date",
        ids,
        raw["AP_BIRTH_DATE"],
        lambda s: parse_dates(s, today),
    )
    frame["email"] = _clean(log, table, src, "email", ids, raw["AP_MAIL_ADDRESS"], clean_email)
    frame["phone"] = _clean(log, table, src, "phone", ids, raw["AP_PHONE_NUMBER"], clean_phone)
    frame["address"] = _clean(log, table, src, "address", ids, raw["AP_STREET_ADDRESS"], clean_text)
    frame["zip_code"] = _clean(log, table, src, "zip_code", ids, raw["AP_ZIP_CODE"], clean_zip)
    frame["tax_number"] = pd.Series([None] * len(frame), index=frame.index, dtype="object")
    frame["created_at"] = _clean(
        log,
        table,
        src,
        "created_at",
        ids,
        raw["AP_CREATED_AT"],
        lambda s: parse_dates(s, today),
    )
    frame["status"] = _clean(
        log,
        table,
        src,
        "status",
        ids,
        raw["AP_CUSTOMER_STATUS"],
        lambda s: map_values(s, config.CUSTOMER_STATUS),
    )
    score = _clean(
        log,
        table,
        src,
        "loyalty_score",
        ids,
        raw["AP_LOYALTY_SCORE"],
        lambda s: parse_numbers(s, minimum=0),
    )
    frame["loyalty_score"] = score
    return frame[CUSTOMER_COLUMNS]
