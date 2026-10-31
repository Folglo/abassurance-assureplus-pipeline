# AbAssurance x AssurePlus : consolidation des données et tableau de bord

Preuve de concept qui rassemble les données de deux assureurs fusionnés :

- **AbAssurance** : base Oracle (tables `AB_CLIENT`, `AB_CONTRAT`, `AB_SINISTRE`, `AB_PAIEMENT`) ;
- **AssurePlus** : base SQL Server (tables `AP_USERS`, `AP_CONTRACTS`, `AP_CLAIMS`, `AP_PAYMENTS`).

Le logiciel nettoie les données, les met dans un modèle commun, détecte les doublons clients et
affiche cinq indicateurs : répartition des clients, statistiques contrats, sinistres, finances et
matrice de doublons.

> Toutes les données sont **fictives** (générées par `abassurance/synthetic.py`)

## Application en ligne

https://abassurance-assureplus-pipeline.streamlit.app/

Comptes de démonstration : `admin` / `AbAssurance-Admin26` (données en clair) et `user` /
`AbAssurance-User26` (données pseudonymisées et masquées).

## Pipeline

```
CSV Oracle + CSV SQL Server -> nettoyage -> mapping -> contrôles d'intégrité -> doublons
                                                       -> statistiques -> tableau de bord
```

| Module | Rôle |
|---|---|
| `abassurance/extract.py` | lecture des exports CSV (colonnes des annexes) |
| `abassurance/clean.py` | nettoyage : dates, nombres, emails, téléphones, codes postaux, listes de valeurs |
| `abassurance/mapping.py` | transformation Oracle / SQL Server vers le modèle commun |
| `abassurance/quality.py` | journal des anomalies (aucune ligne ne disparaît sans trace) |
| `abassurance/duplicates.py` | détection des doublons et matrice de doublons |
| `abassurance/stats.py` | indicateurs du tableau de bord |
| `abassurance/privacy.py` | masquage et pseudonymisation (RGPD) |
| `abassurance/auth.py` | connexion `admin` / `user` |
| `streamlit_app.py` | tableau de bord |

## Installation et lancement

Python 3.12 -sous Windows

```bash
pip install -r requirements-dev.txt
python -m abassurance.synthetic        # regénère les données fictives (déjà fournies dans data/)
streamlit run streamlit_app.py         # lance le tableau de bord
```

## Tests et qualité du code

```bash
python -m pytest --cov=abassurance --cov-report=term-missing
ruff check .
ruff format --check .
```

La chaîne d'intégration continue (`.github/workflows/ci.yml`) lance Ruff, les tests et la
couverture (minimum 80 %) à chaque push et à chaque pull request.

Le script `python scripts/demo_silent_bug.py` illustre un bug évité : une date mal formatée
devenait `NaT` sans alerte. Elle est maintenant rejetée avec un motif.

## Règles de gestion retenues (à valider avec le client)

- **Détection de doublon** : noms proches (similarité >= 0,85, indépendante de l'ordre et des
  accents) Et au moins un identifiant identique parmi date de naissance, email, téléphone.
  Deux identifiants identiques ou plus = « certain », un seul = « à vérifier ».
- **Nom complet SQL Server** : les mots en majuscules forment le nom, le reste le prénom.
- **Prime** : la prime mensuelle d'AssurePlus est multipliée par 12.
- **Paiements Oracle** : pas de statut dans la base, ils sont considérés comme encaissés.
- **Listes de valeurs** (statuts, types, moyens de paiement) : à confirmer par un
  `SELECT DISTINCT` sur les vraies bases.
- **Dates** : formats acceptés AAAA-MM-JJ, AAAA-MM-JJ HH:MM:SS et JJ/MM/AAAA.
- **Clients particuliers / professionnels** : aucun champ ne les distingue dans les schémas.

## Architecture cible

Ce dépôt est la preuve de concept en Python. En production, les mêmes règles seraient portées par
des outils dédiés : Talend (ETL), Kafka (flux), Spark (traitement) et Hadoop (stockage), avec le
tableau de bord en sortie.

## Schéma de données et contributions

- Schéma conceptuel (MCD) : `docs/schema-mcd.png`
- Branches, commits et pull requests : voir [CONTRIBUTING.md](CONTRIBUTING.md)
