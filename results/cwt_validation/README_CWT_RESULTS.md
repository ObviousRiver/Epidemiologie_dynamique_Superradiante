# Résultats de Validation CWT (Continuous Wavelet Transform)

**Date** : 13 décembre 2025
**Objectif** : Validation non-paramétrique du modèle Super-Radiant via ondelettes
**Statut** : ✅ Améliorations implémentées, limitations identifiées

---

## 📊 Résumé Exécutif

L'approche CWT a été développée pour **valider de manière non-paramétrique** si les modes sech² du modèle SR correspondent à des structures réelles dans les données. Contrairement au modèle SR qui ajuste simultanément tous les paramètres via `curve_fit`, le CWT "découvre" les modes directement depuis le signal via l'analyse temps-échelle.

### Résultats Globaux

| Dataset | SR R² | SIR R² | CWT R² | CWT vs SR | Interprétation |
|---------|-------|--------|--------|-----------|----------------|
| **France** | 0.49 | 0.22 | **0.21** | Comparable à SIR | ⚠️ CWT acceptable mais inférieur à SR |
| **UK** | 0.95 | 0.93 | **-0.77** | Très inférieur | ❌ CWT inadapté (structure monocentrique) |
| **Norway** | 0.82 | 0.80 | **-8.56** | Très inférieur | ❌ CWT inadapté (petite population) |
| **Sweden** | 0.74 | 0.60 | **-17.96** | Très inférieur | ❌ CWT inadapté |

---

## 🔬 Améliorations Algorithmiques Implémentées

### Version 1 (Initiale)

**Paramètres** :
- `threshold_factor = 2.0` (seuil élevé)
- Pas de séparation temporelle minimale
- Échelles : 3-80 jours (100 points)
- Détection par pics individuels dans chaque échelle

**Résultat France** :
- ❌ RMS = 8,197
- ❌ R² = -1.99
- ❌ 3 modes détectés tous au même temps (j=57)

### Version 2 (Améliorée)

**Améliorations** :
1. ✅ **Réduction threshold** : `threshold_factor = 1.2` (détecte plus de modes)
2. ✅ **Séparation temporelle** : `min_time_separation = 8 jours` (force modes distincts)
3. ✅ **Échelles calibrées** : 2-60 jours (120 points, résolution fine)
4. ✅ **Profil d'énergie** : Somme sur échelles + détection par énergie totale
5. ✅ **Amplitude robuste** : Moyenne locale (fenêtre ±2 jours)
6. ✅ **Calibration T** : `T = période/4` (Morlet → sech²)

**Résultat France** :
- ✅ RMS = 4,219 (**amélioration de 48%**)
- ✅ R² = 0.21 (**vs -1.99**, énorme progrès)
- ✅ 2 modes détectés séparés (j=57, j=110)

---

## 📈 Résultats Détaillés par Pays

### France (Population 67M)

| Modèle | RMS | R² | N modes | Performance |
|--------|-----|-----|---------|-------------|
| **SR** | **3,404** | **0.49** | 3 | ✅ Meilleur |
| SIR | 4,199 | 0.22 | 1 | Moyen |
| CWT | 4,219 | 0.21 | 2 | Comparable SIR |

**Convergence SR-CWT** :
- ⚠️ Mode 1 : Δτ=14j, ΔT=2j (convergence modérée)
- ❌ Mode 2 : Δτ=53j, ΔT=11j (divergence)

**Interprétation** :
CWT détecte des modes réels mais avec des paramètres différents de SR. L'approche CWT est **viable mais sous-optimale** comparée au fit SR global.

---

### UK (Population 67M, Monocentrique)

| Modèle | RMS | R² | N modes | Performance |
|--------|-----|-----|---------|-------------|
| **SR** | **405** | **0.95** | 3 | ✅ Excellent |
| SIR | 482 | 0.93 | 1 | ✅ Très bon |
| CWT | 2,350 | **-0.77** | 3 | ❌ Échec |

**Interprétation** :
UK a une **structure monocentrique** (Londres domine). Le CWT force la détection de 3 modes alors qu'un seul mode dominant existe. Cela crée du **sur-ajustement** avec reconstruction très mauvaise (R² négatif).

---

### Norway (Population 5.4M, Dispersée)

| Modèle | RMS | R² | N modes | Performance |
|--------|-----|-----|---------|-------------|
| **SR** | **35** | **0.82** | 3 | ✅ Meilleur |
| SIR | 37 | 0.80 | 1 | Bon |
| CWT | 257 | **-8.56** | 3 | ❌ Échec majeur |

**Interprétation** :
**Petite population** (5.4M) → Amplitudes faibles → Seuil de détection CWT inadapté → Modes fantômes → Reconstruction catastrophique.

---

### Sweden (Population 10.3M, Multi-centres)

| Modèle | RMS | R² | N modes | Performance |
|--------|-----|-----|---------|-------------|
| **SR** | **198** | **0.74** | 3 | ✅ Meilleur |
| SIR | 244 | 0.60 | 1 | Moyen |
| CWT | 1,678 | **-17.96** | 3 | ❌ Échec catastrophique |

**Interprétation** :
Malgré une structure multi-centres (Stockholm, Göteborg, Malmö), le CWT échoue. Les modes SR ne sont probablement **pas séparables dans le domaine temps-échelle** avec l'ondelette de Morlet.

---

## 🔍 Limitations Fondamentales Identifiées

### 1. **Non-Orthogonalité des Modes SR**

Les modes SR sont des fonctions **sech² non-orthogonales** :
```
y_SR(t) = Σ A_i × sech²((t - τ_i)/(2T_i))
```

La CWT décompose sur une base d'**ondelettes orthogonales** (Morlet = sinusoïde modulée par gaussienne). Les modes SR ne correspondent pas directement aux modes CWT.

### 2. **Sensibilité aux Paramètres**

Les paramètres optimaux pour France (`threshold_factor=1.2`, `min_time_separation=8`) **ne sont pas universels** :
- UK monocentrique → Besoin d'un seuil plus élevé pour éviter sur-détection
- Norway petite pop → Besoin d'un seuil plus bas pour détecter signaux faibles
- Pas de paramètres "universels" trouvés

### 3. **Over-fitting pour Structures Simples**

Sur UK (monocentrique), forcer 3 modes CWT crée un **sur-ajustement** :
- Le signal a un mode dominant
- CWT détecte 3 modes artificiels
- Reconstruction pire que modèle nul (R² < 0)

### 4. **Calibration Morlet ↔ sech²**

La correspondance `T = période/4` est **empirique** et probablement inexacte :
- Morlet : sinusoïde modulée (forme périodique)
- sech² : forme non-périodique, décroissance exponentielle
- Pas de transformation analytique exacte

---

## ✅ Conclusions Scientifiques

### Ce que le CWT Valide

1. ✅ **Existence de modes multiples** : Le CWT détecte effectivement plusieurs pics temporels distincts sur France
2. ✅ **Séparation temporelle** : Les modes sont séparés dans le temps (57j, 110j) conformément à l'intuition SR
3. ✅ **Amélioration algorithmique** : Les optimisations (profil d'énergie, séparation forcée) améliorent drastiquement la performance

### Ce que le CWT Ne Valide Pas

1. ❌ **Forme sech² exacte** : Les modes CWT ne convergent pas vers les paramètres SR
2. ❌ **Nombre de modes** : CWT détecte 2 modes vs 3 pour SR (France)
3. ❌ **Universalité** : CWT échoue sur UK/Norway/Sweden → **Pas une validation croisée générale**

### Verdict Final

Le CWT est un **outil de validation partielle** mais **pas une alternative** au modèle SR :

- ✅ **Preuve de concept** : Détection non-paramétrique de modes multiples est possible
- ⚠️ **Limites sévères** : Sensible aux paramètres, non-universel, calibration inexacte
- 🎯 **Utilité** : Exploration initiale, validation qualitative, mais SR reste supérieur pour modélisation

---

## 🔬 Recommandations

### Pour la Modélisation

1. **Utiliser SR comme méthode principale** : Le fit global reste supérieur
2. **CWT comme outil exploratoire** : Identifier approximativement le nombre de modes avant fit SR
3. **Ne pas forcer n_modes dans CWT** : Détecter automatiquement (prendre tous modes > seuil)

### Pour Futures Améliorations

1. **Ondelette customisée** : Créer une ondelette basée sur sech² (au lieu de Morlet)
2. **Optimisation bayésienne** : Calibrer automatiquement threshold/scales par pays
3. **Analyse multi-résolution** : Combiner plusieurs échelles de granularité

### Pour Publications

**Message** : *"La validation CWT démontre que des structures multi-modes existent dans les données épidémiologiques, mais la décomposition optimale reste celle du modèle SR paramétrique. Les ondelettes standard (Morlet) ne capturent pas fidèlement les modes sech² non-orthogonaux."*

---

## 📁 Fichiers Générés

### France

- `fig8_cwt_decomposition.png` : Décomposition modes + comparaison SR/SIR/CWT
- `fig9_cwt_scalogram.png` : Scalogramme temps-échelle
- `comparison_sr_cwt_sir.csv` : Métriques comparatives

### Multi-Pays (UK, Norway, Sweden)

- `cwt_multi_country_summary.csv` : Tableau comparatif 3 pays
- `cwt_multi_country_comparison.png` : Visualisation comparative

---

**Auteur** : Analyse CWT automatisée
**Version CWT** : 2.0 (Améliorée)
**Branche Git** : `claude/uk-norway-sweden-01AVvUaUTsBW1fQFBZMhowhA`
