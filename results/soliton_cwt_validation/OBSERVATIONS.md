# Observations sur l'Ondelette Soliton (sech²) vs Morlet

**Date**: 2025-12-13
**Objectif**: Tester si une ondelette personnalisée basée sur sech² améliore la détection de modes par rapport à Morlet

## Hypothèse Initiale

L'ondelette de Morlet (sinusoïdale × gaussienne) est intrinsèquement mal adaptée aux structures sech² car:
- Morlet est oscillante, sech² est non-périodique
- La corrélation entre formes très différentes est faible
- Solution proposée: utiliser **sech² - mean(sech²)** comme ondelette personnalisée

## Implémentation

### Ondelette Testées

1. **Dérivée de sech** (première tentative):
   - `ψ(x) = sech(x) × tanh(x)`
   - Moyenne nulle naturellement
   - Structure bipolaire (lobe positif + lobe négatif)

2. **sech² centré** (deuxième tentative):
   - `ψ(x) = sech²(x) - mean(sech²(x))`
   - Moyenne nulle par soustraction
   - Pic central positif + ailes négatives

### Résultats Expérimentaux

#### Test 1: Dérivée de sech
- **Scalogramme**: Maximum au jour 31 (signal=1032 cas), PAS au pic principal (jour 57, signal=50747 cas)
- **Profil d'énergie**: VALLÉE au jour 57 où se trouve le pic principal!
- **Conclusion**: ❌ La structure bipolaire crée des annulations destructives avec les pics sech²

#### Test 2: sech² centré
- **Scalogramme**: Maximum correct au jour 57 (pic principal)
- **Amplitude**: Bien calibrée après normalisation L2 (facteur /20)
- **Structure**: Large zone diffuse jaune/orange autour du pic
- **Profil d'énergie**: Large bosse lisse centrée sur jour 57
- **Modes détectés**: 1 seul (vs 2 pour Morlet, 3 pour SR)
- **Conclusion**: ⚠️ Corrélation forte mais trop diffuse, masque les modes secondaires

## Comparaison Scalogrammes

### Morlet CWT
- Structure multi-échelle fine avec bandes diagonales distinctes
- Profil d'énergie: pic étroit et net
- **2 modes détectés** (τ=57j, τ=110j)
- RMS=4219, R²=0.209

### Soliton CWT (sech²)
- Large zone uniforme sans structure d'échelle claire
- Profil d'énergie: large bosse diffuse
- **1 mode détecté** (τ=57j)
- RMS=4810, R²=-0.028

## Analyse Théorique

### Force de Corrélation
Test sur signal sech²(x-2):
- **Soliton wavelet**: corrélation max = 22.62
- **Morlet wavelet**: corrélation max = 0.57
- **Ratio**: Soliton 40× plus forte!

### Paradoxe
L'ondelette sech² corrèle **trop bien** avec les pics sech²:
- La corrélation est très forte MAIS très diffuse spatialement
- S'étale sur une grande région du plan (temps, échelle)
- Perd la sélectivité en échelle nécessaire pour distinguer les modes

Morlet, bien que moins corrélée en absolu, a une **meilleure sélectivité**:
- Structure oscillante crée des interférences constructives/destructives
- Localisation temps-fréquence plus nette
- Permet de séparer les contributions de différentes échelles

## Tentatives d'Optimisation

1. **Détection multi-bandes**: Diviser le scalogramme en bandes d'échelle
   - Résultat: Toutes les bandes ont leur maximum au même endroit (jour 56-57)
   - ❌ Ne résout pas le problème de diffusion

2. **Détection 2D avec maximum_filter**: Chercher maxima locaux dans scalogramme 2D
   - Résultat: Un seul maximum global détecté
   - ❌ Pas de pics secondaires significatifs

3. **Ajustement des seuils**: prominence, percentiles, etc.
   - Résultat: Ne change pas la structure fondamentalement diffuse
   - ❌ Le problème est dans l'ondelette elle-même

## Conclusion

### Résultat Principal
**L'ondelette sech² personnalisée est MOINS efficace que Morlet** pour la détection multi-modale dans les signaux épidémiques, malgré une corrélation intrinsèquement plus forte avec les structures sech².

### Explication
La **sélectivité temps-fréquence** est plus importante que la **force de corrélation absolue** pour la séparation de modes. L'ondelette Morlet, grâce à sa structure oscillante, offre une meilleure localisation même si elle est moins "similaire" aux sech².

### Validation de l'Approche SR
Ce résultat **renforce indirectement la validité du modèle SuperRadiant**:
- L'approche non-paramétrique (CWT Morlet) détecte 2 modes
- L'approche paramétrique (SR) détecte 3 modes avec bon fit (R²=0.485)
- Une ondelette "trop adaptée" (sech²) détecte seulement 1 mode

→ Le SR n'est pas en train d'overfitter avec une base sech² arbitraire: si les structures sech² étaient artificielles, l'ondelette sech² devrait les détecter facilement, ce qui n'est PAS le cas.

### Recommandation
**Continuer avec Morlet CWT** comme validation non-paramétrique du modèle SR. L'approche soliton CWT, bien qu'élégante théoriquement, ne présente pas d'avantage pratique pour cette application.

## Métrique de Performance

| Modèle        | RMS   | R²      | N_modes | Note                          |
|---------------|-------|---------|---------|-------------------------------|
| SR            | 3404  | 0.485   | 3       | ✅ Meilleur fit               |
| SIR           | 4199  | 0.217   | 1       | Baseline classique            |
| Morlet CWT    | 4219  | 0.209   | 2       | ✅ Détection robuste          |
| Soliton CWT   | 4810  | -0.028  | 1       | ❌ Trop diffus                |

## Fichiers Générés

- `models/soliton_cwt_model.py`: Implémentation complète
- `scripts/compare_soliton_morlet_cwt.py`: Script de comparaison
- `results/soliton_cwt_validation/soliton_vs_morlet_comparison.png`: Figure comparative
- `results/soliton_cwt_validation/comparison_summary.csv`: Résultats numériques

---

*Cette expérience démontre l'importance de la sélectivité temps-fréquence en CWT et valide le choix de Morlet pour la validation non-paramétrique du modèle SuperRadiant.*
