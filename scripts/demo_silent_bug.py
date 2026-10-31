"""Démonstration du bug « erreur silencieuse » (D3-Q3).

Une date de naissance mal écrite devient NaT (« vide ») sans aucun message. Le client
perd alors un identifiant de comparaison et peut échapper à la détection des doublons.
"""

import pandas as pd

from abassurance.clean import parse_dates

dates = pd.Series(["1985-03-12", "12-03-85", "pas une date", None])

print("=== Version naïve : pd.to_datetime(errors='coerce') ===")
naive = pd.to_datetime(dates, errors="coerce")
print(naive.to_string())
print(f"Dates perdues sans explication : {int(naive.isna().sum())} sur {len(dates)}")

print()
print("=== Version corrigée : parse_dates() ===")
parsed, reasons = parse_dates(dates)
print(pd.DataFrame({"date": parsed, "motif_de_rejet": reasons}).to_string())
print(f"Dates rejetées AVEC un motif : {int(reasons.notna().sum())} sur {len(dates)}")
