"""Démonstration PySpark : nettoyage des huit tables des deux bases, avec motifs de rejet.

Les règles sont celles de abassurance/clean.py et abassurance/mapping.py (pandas) : mêmes formats,
mêmes bornes, mêmes motifs de rejet (missing, invalid_format, unparseable, not_a_number,
out_of_range, unmapped_value). Chaque table est décrite dans TABLES : colonne nettoyée, colonne
source, type de règle et options.
"""

from datetime import date, timedelta
from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as sf

# Format Spark et forme attendue du texte, pour chacun des trois formats de date acceptés
DATE_FORMATS = (
    ("yyyy-MM-dd HH:mm:ss", r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"),
    ("yyyy-MM-dd", r"^\d{4}-\d{2}-\d{2}$"),
    ("dd/MM/yyyy", r"^\d{2}/\d{2}/\d{4}$"),
)
EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
NUMBER_REGEX = r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$"
MIN_DATE = "1900-01-01"

# Tables de correspondance des valeurs (copie de abassurance/config.py)
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

# Pour chaque fichier : colonne nettoyée -> (colonne source, type de règle, options)
TABLES = {
    "ab_client": {
        "last_name": ("AB_NOM", "text", {}),
        "first_name": ("AB_PRENOM", "text", {}),
        "birth_date": ("AB_DATE_NAISSANCE", "date", {}),
        "email": ("AB_EMAIL", "email", {}),
        "phone": ("AB_TELEPHONE", "phone", {}),
        "address": ("AB_ADRESSE", "text", {}),
        "zip_code": ("AB_CODE_POSTAL", "zip", {}),
        "created_at": ("AB_DATE_CREATION", "date", {}),
        "status": ("AB_STATUT_CLIENT", "mapping", {"mapping": CUSTOMER_STATUS}),
    },
    "ap_users": {
        "birth_date": ("AP_BIRTH_DATE", "date", {}),
        "email": ("AP_MAIL_ADDRESS", "email", {}),
        "phone": ("AP_PHONE_NUMBER", "phone", {}),
        "address": ("AP_STREET_ADDRESS", "text", {}),
        "zip_code": ("AP_ZIP_CODE", "zip", {}),
        "created_at": ("AP_CREATED_AT", "date", {}),
        "status": ("AP_CUSTOMER_STATUS", "mapping", {"mapping": CUSTOMER_STATUS}),
        "loyalty_score": ("AP_LOYALTY_SCORE", "number", {"minimum": 0}),
    },
    "ab_contrat": {
        "insurance_type": ("AB_TYPE_ASSURANCE", "mapping", {"mapping": INSURANCE_TYPE}),
        "start_date": ("AB_DATE_DEBUT", "date", {}),
        "end_date": ("AB_DATE_FIN", "date", {"allow_future": True}),
        "annual_premium": ("AB_PRIME_ANNUELLE", "number", {"minimum": 0}),
        "status": ("AB_STATUT_CONTRAT", "mapping", {"mapping": CONTRACT_STATUS}),
    },
    "ap_contracts": {
        "insurance_type": ("AP_PRODUCT_CODE", "mapping", {"mapping": INSURANCE_TYPE}),
        "start_date": ("AP_START_DATE", "date", {}),
        "end_date": ("AP_END_DATE", "date", {"allow_future": True}),
        "monthly_premium": ("AP_MONTHLY_PREMIUM", "number", {"minimum": 0}),
        "status": ("AP_CONTRACT_STATE", "mapping", {"mapping": CONTRACT_STATUS}),
    },
    "ab_sinistre": {
        "claim_date": ("AB_DATE_SINISTRE", "date", {}),
        "estimated_amount": ("AB_MONTANT_ESTIME", "number", {"minimum": 0}),
        "status": ("AB_STATUT_SINISTRE", "mapping", {"mapping": CLAIM_STATUS}),
    },
    "ap_claims": {
        "claim_date": ("AP_INCIDENT_DATE", "date", {}),
        "estimated_amount": ("AP_ESTIMATED_AMOUNT", "number", {"minimum": 0}),
        "status": ("AP_CLAIM_STATUS", "mapping", {"mapping": CLAIM_STATUS}),
        "fraud_score": ("AP_FRAUD_SCORE", "number", {"minimum": 0, "maximum": 100}),
    },
    "ab_paiement": {
        "payment_date": ("AB_DATE_PAIEMENT", "date", {}),
        "amount": ("AB_MONTANT", "number", {"minimum": 0}),
        "method": ("AB_MODE_PAIEMENT", "mapping", {"mapping": PAYMENT_METHOD}),
    },
    "ap_payments": {
        "payment_date": ("AP_PAYMENT_DATETIME", "date", {}),
        "amount": ("AP_AMOUNT_PAID", "number", {"minimum": 0}),
        "method": ("AP_PAYMENT_CHANNEL", "mapping", {"mapping": PAYMENT_METHOD}),
        "status": ("AP_TRANSACTION_STATUS", "mapping", {"mapping": PAYMENT_STATUS}),
    },
}


def _blank(column):
    """Vrai si la valeur est absente ou ne contient que des espaces."""
    return column.isNull() | (sf.trim(column) == "")


def clean_text(column):
    """Supprime les espaces en trop ; une valeur vide devient manquante."""
    raw = sf.col(column)
    reason = sf.when(_blank(raw), "missing")
    return sf.when(reason.isNull(), sf.regexp_replace(sf.trim(raw), r"\s+", " ")), reason


def clean_email(column):
    """Email en minuscules, format vérifié. Renvoie (valeur nettoyée, motif de rejet)."""
    raw = sf.col(column)
    email = sf.lower(sf.trim(raw))
    reason = sf.when(_blank(raw), "missing").when(~email.rlike(EMAIL_REGEX), "invalid_format")
    return sf.when(reason.isNull(), email), reason


def clean_phone(column):
    """Numéro français ramené au format national à 10 chiffres (06XXXXXXXX)."""
    raw = sf.col(column)
    digits = sf.regexp_replace(raw, r"[^\d+]", "")
    national = (
        sf.when(digits.startswith("+33"), sf.concat(sf.lit("0"), sf.substring(digits, 4, 20)))
        .when(digits.startswith("0033"), sf.concat(sf.lit("0"), sf.substring(digits, 5, 20)))
        .otherwise(digits)
    )
    reason = sf.when(_blank(raw), "missing").when(~national.rlike(r"^0\d{9}$"), "invalid_format")
    return sf.when(reason.isNull(), national), reason


def clean_zip(column):
    """Code postal en texte sur 5 chiffres (« 6000 » devient « 06000 »)."""
    raw = sf.col(column)
    zip_code = sf.trim(raw)
    padded = sf.when(zip_code.rlike(r"^\d{4}$"), sf.lpad(zip_code, 5, "0")).otherwise(zip_code)
    reason = sf.when(_blank(raw), "missing").when(~padded.rlike(r"^\d{5}$"), "invalid_format")
    return sf.when(reason.isNull(), padded), reason


def clean_date(column, today, allow_future=False):
    """Date lue dans l'un des trois formats acceptés, avec un motif pour chaque rejet.

    Une date n'est acceptée que si elle se reformate à l'identique : « 31/02/1990 » est refusée.
    """
    raw = sf.col(column)
    text = sf.trim(raw)
    attempts = []
    for pattern, shape in DATE_FORMATS:
        parsed = sf.expr(f"try_to_timestamp(trim(`{column}`), '{pattern}')")
        valid = sf.when(sf.date_format(parsed, pattern) == text, parsed)
        attempts.append(sf.when(text.rlike(shape), valid))
    parsed = sf.coalesce(*attempts)
    reason = (
        sf.when(_blank(raw), "missing")
        .when(parsed.isNull(), "unparseable")
        .when(parsed < sf.lit(MIN_DATE).cast("timestamp"), "out_of_range")
    )
    if not allow_future:
        end_of_today = sf.lit((today + timedelta(days=1)).isoformat()).cast("timestamp")
        reason = reason.when(parsed >= end_of_today, "out_of_range")
    return sf.when(reason.isNull(), sf.to_date(parsed)), reason


def clean_number(column, minimum=None, maximum=None):
    """Nombre décimal (la virgule est acceptée), avec bornes facultatives."""
    raw = sf.col(column)
    text = sf.regexp_replace(sf.trim(raw), ",", ".")
    number = sf.when(text.rlike(NUMBER_REGEX), text.cast("double"))
    reason = sf.when(_blank(raw), "missing").when(number.isNull(), "not_a_number")
    if minimum is not None:
        reason = reason.when(number < minimum, "out_of_range")
    if maximum is not None:
        reason = reason.when(number > maximum, "out_of_range")
    return sf.when(reason.isNull(), number), reason


def clean_mapping(column, mapping):
    """Traduit une valeur vers la liste commune ; inconnue = « unknown » et motif unmapped_value."""
    raw = sf.col(column)
    pairs = [sf.lit(item) for pair in mapping.items() for item in pair]
    mapped = sf.try_element_at(sf.create_map(*pairs), sf.upper(sf.trim(raw)))
    reason = sf.when(_blank(raw), "missing").when(mapped.isNull(), "unmapped_value")
    return sf.coalesce(mapped, sf.lit("unknown")), reason


RULES = {
    "text": clean_text,
    "email": clean_email,
    "phone": clean_phone,
    "zip": clean_zip,
    "number": clean_number,
    "mapping": clean_mapping,
}


def clean_table(df, spec, today):
    """Ajoute, pour chaque colonne, la valeur nettoyée et son motif de rejet (``<nom>_reason``)."""
    for name, (column, kind, options) in spec.items():
        if kind == "date":
            value, reason = clean_date(column, today, **options)
        else:
            value, reason = RULES[kind](column, **options)
        df = df.withColumn(name, value).withColumn(f"{name}_reason", reason)
    return df


def configure(spark):
    """Lecture stricte des dates : une date invalide devient NULL au lieu de lever une erreur."""
    spark.conf.set("spark.sql.legacy.timeParserPolicy", "CORRECTED")


def clean_all(spark, folder, today=None):
    """Lit et nettoie les huit fichiers CSV d'un dossier. Retourne un dictionnaire par table."""
    today = today or date.today()
    return {
        table: clean_table(spark.read.csv(f"{folder}/{table}.csv", header=True), spec, today)
        for table, spec in TABLES.items()
    }


def _reasons_of(df, table):
    """Nombre de lignes par colonne et par motif pour une table (« ok » = valeur acceptée)."""
    entries = [
        sf.struct(
            sf.lit(name).alias("column"),
            sf.coalesce(sf.col(f"{name}_reason"), sf.lit("ok")).alias("reason"),
        )
        for name in TABLES[table]
    ]
    return (
        df.select(sf.explode(sf.array(*entries)).alias("entry"))
        .select(sf.lit(table).alias("table"), "entry.column", "entry.reason")
        .groupBy("table", "column", "reason")
        .count()
        .withColumnRenamed("count", "rows")
    )


def quality_summary(cleaned):
    """Tableau unique : table, colonne, motif, nombre de lignes, pour toutes les tables."""
    frames = [_reasons_of(df, table) for table, df in cleaned.items()]
    return reduce(DataFrame.unionByName, frames)


def save_all(cleaned, schema="workspace.default"):
    """Enregistre les tables nettoyées et le journal des rejets dans le catalogue (Silver)."""
    for table, df in cleaned.items():
        sources = [column for column, _, _ in TABLES[table].values()]
        df.drop(*sources).write.mode("overwrite").saveAsTable(f"{schema}.silver_{table}")
    summary = quality_summary(cleaned)
    summary.write.mode("overwrite").saveAsTable(f"{schema}.silver_quality_log")
