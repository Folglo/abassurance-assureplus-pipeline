"""Tableau de bord AbAssurance x AssurePlus (Streamlit).

Lancement local : streamlit run streamlit_app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from abassurance import stats
from abassurance.auth import authenticate
from abassurance.duplicates import count_unique_customers, duplicate_matrix
from abassurance.formatting import format_euro, format_number, format_percent
from abassurance.pipeline import run_pipeline
from abassurance.privacy import anonymise_pairs
from abassurance.stats import AGE_LABELS

BASE_LABEL = {"source": "Base"}


@st.cache_data
def load_result():
    """Exécute le pipeline une seule fois par session serveur."""
    return run_pipeline(today=pd.Timestamp.today().normalize())


def show_login():
    """Formulaire de connexion : enregistre le rôle dans la session."""
    st.title("AbAssurance x AssurePlus")
    st.subheader("Connexion")
    with st.form("login"):
        username = st.text_input("Identifiant")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")
    if submitted:
        role = authenticate(username, password)
        if role is None:
            st.error("Identifiant ou mot de passe incorrect.")
        else:
            st.session_state["role"] = role
            st.session_state["username"] = username
            st.rerun()


def show_customers(result):
    data = stats.customer_stats(result.customers)
    unique = count_unique_customers(result.customers, result.duplicates)
    c1, c2, c3 = st.columns(3)
    c1.metric("Clients dans les deux bases", format_number(data["total"]))
    c2.metric("Clients distincts estimés", format_number(unique))
    c3.metric("Paires de doublons", format_number(len(result.duplicates)))
    left, right = st.columns(2)
    left.plotly_chart(
        px.pie(data["by_source"], names="source", values="customers", title="Clients par base"),
        key="customers_by_source",
    )
    right.plotly_chart(
        px.bar(
            data["by_status"],
            x="status",
            y="customers",
            color="source",
            barmode="group",
            labels={"status": "Statut", "customers": "Clients", **BASE_LABEL},
            title="Clients par statut",
        ),
        key="customers_by_status",
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            data["by_age_group"],
            x="age_group",
            y="customers",
            color="source",
            barmode="group",
            category_orders={"age_group": [*AGE_LABELS, "unknown"]},
            labels={"age_group": "Tranche d'âge", "customers": "Clients", **BASE_LABEL},
            title="Clients par tranche d'âge",
        ),
        key="customers_by_age",
    )
    departments = px.bar(
        data["by_department"],
        x="department",
        y="customers",
        labels={"department": "Département", "customers": "Clients"},
        title="10 premiers départements",
    )
    departments.update_xaxes(type="category")  # sinon « 01 » et « 75 » sont lus comme des nombres
    right.plotly_chart(departments, key="customers_by_department")


def show_contracts(result):
    data = stats.contract_stats(result.contracts)
    c1, c2, c3 = st.columns(3)
    c1.metric("Contrats", format_number(data["total"]))
    c2.metric("Contrats actifs", format_number(data["active"]))
    c3.metric("Primes annuelles", format_euro(data["total_premium"]))
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            data["by_type"],
            x="insurance_type",
            y="contracts",
            color="source",
            barmode="group",
            labels={"insurance_type": "Type d'assurance", "contracts": "Contrats", **BASE_LABEL},
            title="Contrats par type d'assurance",
        ),
        key="contracts_by_type",
    )
    right.plotly_chart(
        px.bar(
            data["by_type"],
            x="insurance_type",
            y="average_premium",
            color="source",
            barmode="group",
            labels={
                "insurance_type": "Type d'assurance",
                "average_premium": "Prime annuelle moyenne (€)",
                **BASE_LABEL,
            },
            title="Prime annuelle moyenne",
        ),
        key="contracts_premium",
    )
    st.plotly_chart(
        px.bar(
            data["by_status"],
            x="status",
            y="contracts",
            color="source",
            barmode="group",
            labels={"status": "Statut", "contracts": "Contrats", **BASE_LABEL},
            title="Contrats par statut",
        ),
        key="contracts_by_status",
    )


def show_claims(result):
    data = stats.claim_stats(result.claims, result.contracts)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sinistres", format_number(data["total"]))
    c2.metric("Montant estimé total", format_euro(data["total_amount"]))
    c3.metric("Sinistres pour 100 contrats", format_number(data["claims_per_100_contracts"], 1))
    c4.metric("Alertes fraude (AssurePlus)", format_number(data["fraud_alerts"]))
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            data["by_status"],
            x="status",
            y="claims",
            color="source",
            barmode="group",
            labels={"status": "Statut", "claims": "Sinistres", **BASE_LABEL},
            title="Sinistres par statut",
        ),
        key="claims_by_status",
    )
    right.plotly_chart(
        px.bar(
            data["by_type"],
            x="insurance_type",
            y="total_amount",
            color="source",
            barmode="group",
            labels={
                "insurance_type": "Type d'assurance",
                "total_amount": "Montant estimé (€)",
                **BASE_LABEL,
            },
            title="Montant estimé par type de contrat",
        ),
        key="claims_by_type",
    )


def show_finance(result):
    data = stats.finance_stats(result.payments, result.contracts)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Encaissé", format_euro(data["total_paid"]))
    c2.metric("Primes annuelles", format_euro(data["annual_premiums"]))
    c3.metric("Paiements échoués", format_number(data["failed_payments"]))
    c4.metric("Taux d'échec", format_percent(data["failure_rate"]))
    st.plotly_chart(
        px.line(
            data["by_month"],
            x="month",
            y="amount",
            color="source",
            markers=True,
            labels={"month": "Mois", "amount": "Montant encaissé (€)", **BASE_LABEL},
            title="Encaissements par mois",
        ),
        key="finance_by_month",
    )
    st.plotly_chart(
        px.bar(
            data["by_method"],
            x="method",
            y="amount",
            color="source",
            barmode="group",
            labels={"method": "Moyen de paiement", "amount": "Montant (€)", **BASE_LABEL},
            title="Encaissements par moyen de paiement",
        ),
        key="finance_by_method",
    )


def show_duplicates(result, role):
    matrix = duplicate_matrix(result.duplicates)
    st.plotly_chart(
        px.imshow(
            matrix,
            text_auto=True,
            labels={"x": "Base", "y": "Base", "color": "Paires de doublons"},
            title="Matrice de doublons (paires de clients)",
        ),
        key="duplicate_matrix",
    )
    pairs = result.duplicates
    status = st.selectbox("Niveau de certitude", ["Tous", "certain", "to_review"])
    if status != "Tous":
        pairs = pairs[pairs["match_status"] == status]
    if role != "admin":
        st.info("Profil « user » : identités masquées et identifiants pseudonymisés (RGPD).")
        pairs = anonymise_pairs(pairs)
    st.dataframe(pairs, hide_index=True)


def show_quality(result):
    st.subheader("Lignes lues et conservées")
    st.dataframe(result.row_counts, hide_index=True)
    st.subheader("Anomalies détectées (rien n'est supprimé sans trace)")
    st.dataframe(result.quality.summary(), hide_index=True)
    st.download_button(
        "Télécharger le détail des anomalies (CSV)",
        data=result.quality.to_frame().to_csv(index=False).encode("utf-8"),
        file_name="anomalies.csv",
        mime="text/csv",
    )


def main():
    st.set_page_config(page_title="AbAssurance x AssurePlus", layout="wide")
    role = st.session_state.get("role")
    if role is None:
        show_login()
        return

    st.sidebar.write(f"Connecté : {st.session_state.get('username')} ({role})")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

    result = load_result()
    st.title("Tableau de bord AbAssurance x AssurePlus")
    names = ["Clients", "Contrats", "Sinistres", "Finances", "Doublons"]
    if role == "admin":
        names.append("Qualité des données")
    tabs = st.tabs(names)
    with tabs[0]:
        show_customers(result)
    with tabs[1]:
        show_contracts(result)
    with tabs[2]:
        show_claims(result)
    with tabs[3]:
        show_finance(result)
    with tabs[4]:
        show_duplicates(result, role)
    if role == "admin":
        with tabs[5]:
            show_quality(result)


if __name__ == "__main__":
    main()
