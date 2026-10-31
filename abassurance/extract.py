"""Extraction : lecture des exports CSV des deux bases (colonnes des schémas en annexe)."""

from pathlib import Path

import pandas as pd

from abassurance.config import DATA_DIR

RAW_FILES = {
    "ab_client": "ab_client.csv",
    "ab_contrat": "ab_contrat.csv",
    "ab_sinistre": "ab_sinistre.csv",
    "ab_paiement": "ab_paiement.csv",
    "ap_users": "ap_users.csv",
    "ap_contracts": "ap_contracts.csv",
    "ap_claims": "ap_claims.csv",
    "ap_payments": "ap_payments.csv",
}


def load_raw(data_dir=DATA_DIR):
    """Lit les 8 tables en texte brut. Une table absente arrête immédiatement le traitement."""
    data_dir = Path(data_dir)
    return {name: pd.read_csv(data_dir / file, dtype=str) for name, file in RAW_FILES.items()}
