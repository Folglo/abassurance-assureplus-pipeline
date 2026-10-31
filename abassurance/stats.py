"""Indicateurs du tableau de bord : fonctions pures (tableaux et chiffres clés)."""

import pandas as pd

from abassurance import config

AGE_BINS = [0, 25, 35, 45, 55, 65, 200]
AGE_LABELS = ["< 25", "25-34", "35-44", "45-54", "55-64", "65+"]


def customer_stats(customers, today=None):
    """Répartition des clients par source, statut, tranche d'âge et département."""
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    age = (today - customers["birth_date"]).dt.days // 365
    age_group = pd.cut(age, bins=AGE_BINS, labels=AGE_LABELS, right=False)
    age_group = age_group.astype("object").fillna("unknown")
    department = customers["zip_code"].str[:2].fillna("unknown")
    by_age = (
        pd.DataFrame({"source": customers["source"], "age_group": age_group})
        .groupby(["source", "age_group"])
        .size()
        .reset_index(name="customers")
    )
    order = {label: position for position, label in enumerate(AGE_LABELS + ["unknown"])}
    by_age["position"] = by_age["age_group"].map(order)
    by_age = by_age.sort_values(["source", "position"], ignore_index=True).drop(columns="position")
    return {
        "total": len(customers),
        "by_source": customers.groupby("source").size().reset_index(name="customers"),
        "by_status": customers.groupby(["source", "status"]).size().reset_index(name="customers"),
        "by_age_group": by_age,
        "by_department": department.value_counts()
        .head(10)
        .rename_axis("department")
        .reset_index(name="customers"),
    }


def contract_stats(contracts):
    """Nombre et primes des contrats par type d'assurance et par statut."""
    by_type = (
        contracts.groupby(["source", "insurance_type"])
        .agg(
            contracts=("contract_key", "count"),
            average_premium=("annual_premium", "mean"),
            total_premium=("annual_premium", "sum"),
        )
        .round(2)
        .reset_index()
    )
    return {
        "total": len(contracts),
        "active": int((contracts["status"] == "active").sum()),
        "total_premium": round(float(contracts["annual_premium"].sum()), 2),
        "by_type": by_type,
        "by_status": contracts.groupby(["source", "status"]).size().reset_index(name="contracts"),
    }


def claim_stats(claims, contracts):
    """Sinistres par statut et par type de contrat, montant estimé, alertes fraude."""
    with_type = claims.merge(
        contracts[["contract_key", "insurance_type"]], on="contract_key", how="left"
    )
    flagged = claims["fraud_score"] >= config.FRAUD_ALERT_THRESHOLD
    return {
        "total": len(claims),
        "total_amount": round(float(claims["estimated_amount"].sum()), 2),
        "average_amount": round(float(claims["estimated_amount"].mean()), 2),
        "claims_per_100_contracts": round(100 * len(claims) / max(len(contracts), 1), 1),
        "fraud_alerts": int(flagged.sum()),
        "by_status": claims.groupby(["source", "status"]).size().reset_index(name="claims"),
        "by_type": with_type.groupby(["source", "insurance_type"])
        .agg(claims=("claim_key", "count"), total_amount=("estimated_amount", "sum"))
        .round(2)
        .reset_index(),
    }


def finance_stats(payments, contracts):
    """Encaissements par mois et par moyen de paiement, taux d'échec, primes annuelles."""
    paid = payments[payments["status"] == "paid"]
    known = payments[payments["status"].isin(["paid", "failed"])]
    failed = int((payments["status"] == "failed").sum())
    monthly = (
        paid.assign(month=paid["payment_date"].dt.strftime("%Y-%m"))
        .groupby(["month", "source"])["amount"]
        .sum()
        .round(2)
        .reset_index()
    )
    return {
        "total_paid": round(float(paid["amount"].sum()), 2),
        "failed_payments": failed,
        "failure_rate": round(100 * failed / max(len(known), 1), 1),
        "annual_premiums": round(float(contracts["annual_premium"].sum()), 2),
        "by_month": monthly,
        "by_method": paid.groupby(["source", "method"])["amount"].sum().round(2).reset_index(),
    }
