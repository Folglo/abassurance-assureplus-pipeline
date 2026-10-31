"""Fonctions de nettoyage. Chaque fonction renvoie les valeurs nettoyées ET les motifs de rejet."""

import re
import unicodedata

import pandas as pd

MIN_DATE = pd.Timestamp("1900-01-01")
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def to_ascii(text):
    """Supprime les accents : « Hélène » devient « Helene »."""
    return unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii")


def normalize_name(text):
    """Met un nom sous forme comparable : minuscules, sans accents ni ponctuation."""
    if pd.isna(text):
        return ""
    lowered = to_ascii(text).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", lowered).split())


def name_key(first_name, last_name):
    """Clé de comparaison indépendante de l'ordre des mots (« Jean DUPONT » = « DUPONT Jean »)."""
    tokens = f"{normalize_name(first_name)} {normalize_name(last_name)}".split()
    return " ".join(sorted(tokens))


def _apply(series, func):
    """Applique `func(valeur) -> (valeur nettoyée, motif)` sur toute une colonne."""
    results = [func(value) for value in series]
    values = pd.Series([r[0] for r in results], index=series.index, dtype="object")
    reasons = pd.Series([r[1] for r in results], index=series.index, dtype="object")
    return values, reasons


def clean_text(series):
    """Supprime les espaces en trop ; une valeur vide devient manquante."""

    def clean(value):
        if pd.isna(value) or not str(value).strip():
            return None, "missing"
        return " ".join(str(value).split()), None

    return _apply(series, clean)


def clean_email(series):
    """Met l'email en minuscules et vérifie son format."""

    def clean(value):
        if pd.isna(value) or not str(value).strip():
            return None, "missing"
        email = str(value).strip().lower()
        if not EMAIL_PATTERN.match(email):
            return None, "invalid_format"
        return email, None

    return _apply(series, clean)


def clean_phone(series):
    """Ramène un numéro français au format national à 10 chiffres (06XXXXXXXX)."""

    def clean(value):
        if pd.isna(value) or not str(value).strip():
            return None, "missing"
        digits = re.sub(r"[^\d+]", "", str(value))
        if digits.startswith("+33"):
            digits = "0" + digits[3:]
        elif digits.startswith("0033"):
            digits = "0" + digits[4:]
        if not (digits.isdigit() and len(digits) == 10 and digits.startswith("0")):
            return None, "invalid_format"
        return digits, None

    return _apply(series, clean)


def clean_zip(series):
    """Garde le code postal en texte (le zéro de tête est conservé : « 6000 » devient « 06000 »)."""

    def clean(value):
        if pd.isna(value) or not str(value).strip():
            return None, "missing"
        zip_code = str(value).strip()
        if zip_code.isdigit() and len(zip_code) == 4:
            zip_code = zip_code.zfill(5)
        if not (zip_code.isdigit() and len(zip_code) == 5):
            return None, "invalid_format"
        return zip_code, None

    return _apply(series, clean)


def parse_dates(series, today=None, allow_future=False):
    """Convertit en dates et explique chaque rejet (jamais de NaT silencieux).

    Formats acceptés : AAAA-MM-JJ [HH:MM:SS] et JJ/MM/AAAA. Motifs : missing,
    unparseable, out_of_range.
    """
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    text = series.astype("string").str.strip()
    parsed = None
    for date_format in DATE_FORMATS:
        attempt = pd.to_datetime(text, format=date_format, errors="coerce")
        parsed = attempt if parsed is None else parsed.fillna(attempt)

    missing = (text.isna() | (text == "")).to_numpy(dtype=bool)
    unparseable = (~missing) & parsed.isna().to_numpy(dtype=bool)
    out_of_range = parsed.notna().to_numpy(dtype=bool) & (parsed < MIN_DATE).to_numpy(dtype=bool)
    if not allow_future:
        end_of_today = today.normalize() + pd.Timedelta(days=1)
        out_of_range |= parsed.notna().to_numpy(dtype=bool) & (parsed >= end_of_today).to_numpy(
            dtype=bool
        )

    reasons = pd.Series([None] * len(series), index=series.index, dtype="object")
    reasons[missing] = "missing"
    reasons[unparseable] = "unparseable"
    reasons[out_of_range] = "out_of_range"
    parsed = parsed.mask(pd.Series(out_of_range, index=series.index))
    return parsed, reasons


def parse_numbers(series, minimum=None, maximum=None):
    """Convertit en nombres décimaux et explique chaque rejet."""
    text = series.astype("string").str.strip().str.replace(",", ".", regex=False)
    values = pd.to_numeric(text, errors="coerce").astype("float64")

    missing = (text.isna() | (text == "")).to_numpy(dtype=bool)
    not_a_number = (~missing) & values.isna().to_numpy(dtype=bool)
    out_of_range = pd.Series(False, index=series.index).to_numpy(dtype=bool)
    if minimum is not None:
        out_of_range = out_of_range | (values < minimum).to_numpy(dtype=bool)
    if maximum is not None:
        out_of_range = out_of_range | (values > maximum).to_numpy(dtype=bool)

    reasons = pd.Series([None] * len(series), index=series.index, dtype="object")
    reasons[missing] = "missing"
    reasons[not_a_number] = "not_a_number"
    reasons[out_of_range] = "out_of_range"
    return values.mask(pd.Series(out_of_range, index=series.index)), reasons


def map_values(series, mapping):
    """Traduit les valeurs d'une source vers la liste commune ; inconnu = « unknown » + motif."""
    keys = series.astype("string").str.strip().str.upper()
    mapped = keys.map(mapping).astype("object")
    reasons = pd.Series([None] * len(series), index=series.index, dtype="object")
    missing = keys.isna().to_numpy(dtype=bool)
    unmapped = (~missing) & mapped.isna().to_numpy(dtype=bool)
    reasons[missing] = "missing"
    reasons[unmapped] = "unmapped_value"
    return mapped.fillna("unknown"), reasons
    
