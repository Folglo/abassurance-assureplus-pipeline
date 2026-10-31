"""Pipeline complet : extraction, nettoyage, mapping, contrôles d'intégrité, doublons."""

from dataclasses import dataclass

import pandas as pd

from abassurance import config, mapping
from abassurance.duplicates import find_duplicates
from abassurance.extract import load_raw
from abassurance.quality import QualityLog


@dataclass
class PipelineResult:
    """Tables unifiées, doublons détectés et journal de qualité."""

    customers: pd.DataFrame
    contracts: pd.DataFrame
    claims: pd.DataFrame
    payments: pd.DataFrame
    duplicates: pd.DataFrame
    quality: QualityLog
    row_counts: pd.DataFrame


def _row_counts(raw, tables):
    """Lignes lues puis conservées, par table et par source : permet de vérifier qu'aucune ligne
    ne disparaît sans explication."""
    sources = {
        "customers": ("ab_client", "ap_users"),
        "contracts": ("ab_contrat", "ap_contracts"),
        "claims": ("ab_sinistre", "ap_claims"),
        "payments": ("ab_paiement", "ap_payments"),
    }
    rows = []
    for table, (ab_name, ap_name) in sources.items():
        for source, raw_name in ((config.SOURCE_AB, ab_name), (config.SOURCE_AP, ap_name)):
            kept = int((tables[table]["source"] == source).sum())
            rows.append(
                {
                    "table": table,
                    "source": source,
                    "rows_read": len(raw[raw_name]),
                    "rows_kept": kept,
                }
            )
    return pd.DataFrame(rows)


def run_pipeline(data_dir=config.DATA_DIR, today=None):
    """Exécute toutes les étapes et retourne un PipelineResult."""
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    raw = load_raw(data_dir)
    log = QualityLog()

    customers = pd.concat(
        [
            mapping.map_customers_oracle(raw["ab_client"], log, today),
            mapping.map_customers_sqlserver(raw["ap_users"], log, today),
        ],
        ignore_index=True,
    )
    customers = mapping.drop_duplicate_keys(customers, "customer_key", "customers", log)

    contracts = pd.concat(
        [
            mapping.map_contracts_oracle(raw["ab_contrat"], log, today),
            mapping.map_contracts_sqlserver(raw["ap_contracts"], log, today),
        ],
        ignore_index=True,
    )
    contracts = mapping.drop_duplicate_keys(contracts, "contract_key", "contracts", log)
    contracts = mapping.drop_orphans(
        contracts, set(customers["customer_key"]), "customer_key", "contracts", log
    )

    claims = pd.concat(
        [
            mapping.map_claims_oracle(raw["ab_sinistre"], log, today),
            mapping.map_claims_sqlserver(raw["ap_claims"], log, today),
        ],
        ignore_index=True,
    )
    claims = mapping.drop_duplicate_keys(claims, "claim_key", "claims", log)
    claims = mapping.drop_orphans(
        claims, set(contracts["contract_key"]), "contract_key", "claims", log
    )

    payments = pd.concat(
        [
            mapping.map_payments_oracle(raw["ab_paiement"], log, today),
            mapping.map_payments_sqlserver(raw["ap_payments"], log, today),
        ],
        ignore_index=True,
    )
    payments = mapping.drop_duplicate_keys(payments, "payment_key", "payments", log)
    payments = mapping.drop_orphans(
        payments, set(contracts["contract_key"]), "contract_key", "payments", log
    )

    tables = {
        "customers": customers,
        "contracts": contracts,
        "claims": claims,
        "payments": payments,
    }
    return PipelineResult(
        customers=customers,
        contracts=contracts,
        claims=claims,
        payments=payments,
        duplicates=find_duplicates(customers),
        quality=log,
        row_counts=_row_counts(raw, tables),
    )
