"""Détection des doublons clients : noms proches ET au moins un identifiant identique."""

from difflib import SequenceMatcher
from itertools import combinations

import pandas as pd

from abassurance import config
from abassurance.clean import name_key

IDENTIFIERS = ("birth_date", "email", "phone")
PAIR_COLUMNS = [
    "customer_a",
    "customer_b",
    "source_a",
    "source_b",
    "name_a",
    "name_b",
    "email_a",
    "email_b",
    "matched_on",
    "similarity_score",
    "match_status",
]


def _candidate_pairs(customers, identifiers=IDENTIFIERS):
    """Regroupe les clients qui partagent une date de naissance, un email ou un téléphone.

    Les valeurs manquantes sont ignorées pour un identifiant, mais le client reste comparable
    via les deux autres : une date de naissance invalide ne fait plus sortir un client du calcul.
    """
    matches = {}
    for identifier in identifiers:
        valid = customers[customers[identifier].notna()]
        for _, group in valid.groupby(identifier):
            for a, b in combinations(group.index, 2):
                matches.setdefault((a, b), []).append(identifier)
    return matches


def find_duplicates(customers, threshold=config.NAME_SIMILARITY_THRESHOLD, identifiers=IDENTIFIERS):
    """Retourne les paires de clients probablement identiques."""
    customers = customers.reset_index(drop=True)
    keys = [
        name_key(f, last)
        for f, last in zip(customers["first_name"], customers["last_name"], strict=True)
    ]
    rows = []
    for (a, b), matched in _candidate_pairs(customers, identifiers).items():
        score = SequenceMatcher(None, keys[a], keys[b]).ratio()
        if score < threshold:
            continue
        first, second = customers.loc[a], customers.loc[b]
        rows.append(
            {
                "customer_a": first["customer_key"],
                "customer_b": second["customer_key"],
                "source_a": first["source"],
                "source_b": second["source"],
                "name_a": f"{first['first_name']} {first['last_name']}",
                "name_b": f"{second['first_name']} {second['last_name']}",
                "email_a": first["email"],
                "email_b": second["email"],
                "matched_on": ", ".join(matched),
                "similarity_score": round(score, 2),
                "match_status": "certain" if len(matched) >= 2 else "to_review",
            }
        )
    return pd.DataFrame(rows, columns=PAIR_COLUMNS)


def duplicate_matrix(pairs):
    """Matrice source x source : nombre de paires de doublons (diagonale = doublons internes)."""
    sources = [config.SOURCE_AB, config.SOURCE_AP]
    matrix = pd.DataFrame(0, index=sources, columns=sources)
    for source_a, source_b in zip(pairs["source_a"], pairs["source_b"], strict=True):
        matrix.loc[source_a, source_b] += 1
        if source_a != source_b:
            matrix.loc[source_b, source_a] += 1
    return matrix


def count_unique_customers(customers, pairs):
    """Nombre de clients distincts : chaque groupe de doublons compte pour un seul client."""
    parent = {key: key for key in customers["customer_key"]}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for a, b in zip(pairs["customer_a"], pairs["customer_b"], strict=True):
        parent[find(a)] = find(b)
    return len({find(key) for key in parent})
