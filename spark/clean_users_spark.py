"""Démonstration PySpark : nettoyage des clients AssurePlus (ap_users.csv) avec motifs de rejet.

Les règles sont celles de abassurance/clean.py (pandas) : mêmes formats, mêmes motifs de rejet
(missing, invalid_format, unparseable, out_of_range). Ce script est exécuté sur Databricks ;
il n'est pas utilisé par l'application Streamlit.
"""

from datetime import date, timedelta

from pyspark.sql import functions as sf

# Format Spark et forme attendue du texte, pour chacun des trois formats de date acceptés
DATE_FORMATS = (
    ("yyyy-MM-dd HH:mm:ss", r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"),
    ("yyyy-MM-dd", r"^\d{4}-\d{2}-\d{2}$"),
    ("dd/MM/yyyy", r"^\d{2}/\d{2}/\d{4}$"),
)
EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
MIN_DATE = "1900-01-01"

# Nom de la colonne nettoyée -> colonne source
COLUMNS = {
    "email": "AP_MAIL_ADDRESS",
    "phone": "AP_PHONE_NUMBER",
    "zip_code": "AP_ZIP_CODE",
    "birth_date": "AP_BIRTH_DATE",
    "created_at": "AP_CREATED_AT",
}


def _blank(column):
    """Vrai si la valeur est absente ou ne contient que des espaces."""
    return column.isNull() | (sf.trim(column) == "")


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


def clean_date(column, today):
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
    end_of_today = sf.lit((today + timedelta(days=1)).isoformat()).cast("timestamp")
    reason = (
        sf.when(_blank(raw), "missing")
        .when(parsed.isNull(), "unparseable")
        .when(parsed < sf.lit(MIN_DATE).cast("timestamp"), "out_of_range")
        .when(parsed >= end_of_today, "out_of_range")
    )
    return sf.when(reason.isNull(), sf.to_date(parsed)), reason


def configure(spark):
    """Lecture stricte des dates : une date invalide devient NULL au lieu de lever une erreur."""
    spark.conf.set("spark.sql.legacy.timeParserPolicy", "CORRECTED")


def clean_users(df, today=None):
    """Ajoute, pour chaque colonne, la valeur nettoyée et son motif de rejet (``<nom>_reason``)."""
    today = today or date.today()
    rules = {
        "email": clean_email,
        "phone": clean_phone,
        "zip_code": clean_zip,
        "birth_date": lambda column: clean_date(column, today),
        "created_at": lambda column: clean_date(column, today),
    }
    for name, rule in rules.items():
        value, reason = rule(COLUMNS[name])
        df = df.withColumn(name, value).withColumn(f"{name}_reason", reason)
    return df


def reason_counts(df):
    """Nombre de lignes par motif (« ok » = valeur acceptée), pour chaque colonne nettoyée."""
    counts = {}
    for name in COLUMNS:
        reason = sf.coalesce(sf.col(f"{name}_reason"), sf.lit("ok")).alias("reason")
        rows = df.groupBy(reason).count().collect()
        counts[name] = {row["reason"]: row["count"] for row in rows}
    return counts
