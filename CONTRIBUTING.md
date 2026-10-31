# Contribuer au projet

Ce document définit la convention de nommage des branches et les règles de travail.
Il s'appuie sur les bonnes pratiques Git et GitHub.

## Branches principales
| Branche | Rôle | Règle |
|---|---|---|
| `main` | version stable, mise en production | contient uniquement du code testé et validé |
| `develop` | développement principal | reçoit les fonctionnalités terminées |

## Branches de travail
| Type | Créée depuis | Fusionnée dans | Usage | Exemple |
|---|---|---|---|---|
| `feature/` | `develop` | `develop` | nouvelle fonctionnalité | `feature/data-cleaning` |
| `bugfix/` | `develop` | `develop` | correction d'un bug non urgent | `bugfix/birth-date-format` |
| `release/` | `develop` | `main`, puis `develop` | préparation d'une version | `release/1.0.0` |
| `hotfix/` | `main` | `main` et `develop` | correction rapide d'un bug critique | `hotfix/total-clients-count` |

## Règles de nommage
- Format : `type/description-courte`.
- Noms explicites, en anglais, en minuscules, séparés par des tirets, sans accents ni espaces.
- Jamais de noms génériques comme `feature1` ou `test`.
- Le type placé devant le nom indique d'un coup d'œil la nature du travail (nouvelle fonction, correction, version) et où la branche sera fusionnée.

## Commits
- Un commit = un seul changement (commit atomique).
- Message clair et concis, en anglais : `type: short description`.
- Types : `feat`, `fix`, `test`, `docs`, `refactor`.
- Exemple : `feat: add phone number cleaning`

## Avant de fusionner
1. Les tests unitaires passent.
2. Une pull request est ouverte vers `develop`, avec une description.
3. `develop` n'est fusionnée dans `main` que lorsque la version est testée et validée.
