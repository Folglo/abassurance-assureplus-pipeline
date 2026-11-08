# Démonstration PySpark

Cette démonstration reprend l'étape de nettoyage du pipeline avec PySpark, sur la table des clients d'AssurePlus (`data/ap_users.csv`). Elle a été exécutée sur Databricks Free Edition, en calcul serverless avec Spark 4.2.0.

## Règles appliquées

| Colonne | Règle | Motifs de rejet |
|---|---|---|
| email | minuscules, format vérifié | missing, invalid_format |
| phone | format national à 10 chiffres | missing, invalid_format |
| zip_code | 5 chiffres, zéro de tête conservé | missing, invalid_format |
| birth_date, created_at | trois formats de date acceptés | missing, unparseable, out_of_range |

Ce sont les règles de `abassurance/clean.py`, écrites avec les fonctions de `pyspark.sql.functions`.

## Exécution sur Databricks

1. Téléverser `ap_users.csv` dans un volume Unity Catalog, par exemple `/Volumes/workspace/default/donnees/`.
2. Coller le contenu de `clean_users_spark.py` dans une cellule de notebook et l'exécuter.
3. Lancer le nettoyage dans une seconde cellule :

```python
configure(spark)

df = spark.read.csv("/Volumes/workspace/default/donnees/ap_users.csv", header=True)
propre = clean_users(df)

for nom, comptes in reason_counts(propre).items():
    print(nom, comptes)
```

## Résultat

| Colonne | Valeurs acceptées | Valeurs rejetées |
|---|---|---|
| email | 506 | 0 |
| phone | 502 | 4 (missing) |
| zip_code | 506 | 0 |
| birth_date | 500 | 6 (4 unparseable, 1 missing, 1 out_of_range) |
| created_at | 506 | 0 |
