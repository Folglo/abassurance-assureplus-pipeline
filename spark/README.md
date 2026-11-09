# Démonstration PySpark

Cette démonstration reprend l'étape de nettoyage du pipeline avec PySpark, sur les huit tables des deux bases. Elle a été exécutée sur Databricks Free Edition, en calcul serverless avec Spark 4.2.0.

## Règles appliquées

Ce sont les règles de `abassurance/clean.py` et `abassurance/mapping.py`, écrites avec les fonctions de `pyspark.sql.functions`. Chaque table est décrite dans le dictionnaire `TABLES` : colonne nettoyée, colonne source, type de règle et options.

| Type de règle | Contrôle | Motifs de rejet |
|---|---|---|
| text | espaces en trop supprimés | missing |
| email | minuscules, format vérifié | missing, invalid_format |
| phone | format national à 10 chiffres | missing, invalid_format |
| zip | 5 chiffres, zéro de tête conservé | missing, invalid_format |
| date | trois formats acceptés, bornes 1900 et aujourd'hui | missing, unparseable, out_of_range |
| number | nombre décimal, bornes facultatives | missing, not_a_number, out_of_range |
| mapping | valeur traduite vers la liste commune | missing, unmapped_value |

## Exécution sur Databricks

1. Téléverser les huit fichiers de `data/` dans un volume Unity Catalog, par exemple `/Volumes/workspace/default/donnees/`.
2. Coller le contenu de `clean_spark.py` dans une cellule de notebook et l'exécuter.
3. Lancer le nettoyage dans une seconde cellule :

```python
configure(spark)

nettoye = clean_all(spark, "/Volumes/workspace/default/donnees")

for table, df in nettoye.items():
    print(table, df.count())

resume = quality_summary(nettoye)
resume.filter("reason != 'ok'").orderBy("table", "column", "reason").show(100, truncate=False)
```

## Résultat

| Table | Lignes lues |
|---|---|
| ab_client | 819 |
| ap_users | 506 |
| ab_contrat | 1111 |
| ap_contracts | 540 |
| ab_sinistre | 188 |
| ap_claims | 99 |
| ab_paiement | 6655 |
| ap_payments | 3240 |

| Table | Colonne | Motif | Lignes |
|---|---|---|---|
| ab_client | email | invalid_format | 27 |
| ab_client | phone | missing | 27 |
| ap_users | birth_date | missing | 1 |
| ap_users | birth_date | out_of_range | 1 |
| ap_users | birth_date | unparseable | 4 |
| ap_users | phone | missing | 4 |

Les autres colonnes sont acceptées sans rejet.
