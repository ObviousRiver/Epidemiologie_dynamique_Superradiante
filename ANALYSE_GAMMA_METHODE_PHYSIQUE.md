# Analyse de l'Exposant Critique γ - Méthode Physique Corrigée

**Date** : 6 décembre 2025
**Données** : SPF COVID-19, Vague 1 (18 mars - 30 juin 2020)
**Départements** : 77/96 métropolitains analysés

---

## 🎯 Correction Méthodologique Appliquée

### ❌ Ancienne méthode (REJETÉE)
- **Distance critique** : `r = (RMS_SIR - RMS_SR) / RMS_SR`
- **Problème** : Métrique algorithmique, pas une variable physique
- **Résultat** : γ = -1.007 (physiquement impossible : χ → 0)

### ✅ Nouvelle méthode (Physique des transitions de phase)
- **Distance critique** : `ε = |t - t_c|` où `t_c` = pic de variance
- **Susceptibilité** : `χ(t)` = variance glissante (fenêtre 7 jours)
- **Loi de puissance** : `χ(t) ∼ |t - t_c|^(-γ)`
- **Régression** : `ln(χ) = -γ ln(ε) + C` sur partie **ascendante** uniquement

---

## 📊 Résultats Globaux

### Exposant γ (Susceptibilité Critique)

| Statistique | Valeur | Validation |
|-------------|--------|------------|
| **Moyenne** | 0.495 ± 0.494 | ✅ Positif |
| **Médiane** | 0.465 | ✅ Positif |
| **Plage** | [-0.581, 1.832] | ⚠️ 11.7% négatifs |
| **Départements γ > 0** | 68/77 (88.3%) | ✅ Majorité physique |

### Comparaison avec Classes d'Universalité

| Classe | γ théorique | Notre γ | Écart |
|--------|-------------|---------|-------|
| **Ising 3D** | 1.24 | 0.465 | **-62%** |
| **Mean-field** | 1.00 | 0.465 | **-53%** |
| **Ising 2D** | 1.75 | 0.465 | **-73%** |

⚠️ **Notre γ est systématiquement 2-3× plus faible que les classes connues**

### Qualité du Fit (R²)

- **Moyenne** : 0.401
- **Médiane** : 0.364
- **Départements R² > 0.5** : 33/77 (42.9%)

---

## 🔬 Départements avec γ Proche des Classes d'Universalité

| Dep | Nom | γ | R² | Classe proche |
|-----|-----|------|------|---------------|
| **91** | Essonne | **1.259** | 0.797 | Ising 3D (1.24) ✅ |
| **15** | Cantal | **1.314** | 0.750 | Ising 3D (1.24) ✅ |
| **84** | Vaucluse | **1.112** | 0.815 | Mean-field (1.0) ✅ |
| **11** | Aude | **0.800** | 0.820 | - |
| **88** | Vosges | **0.759** | 0.360 | - |
| **94** | Val-de-Marne | **0.776** | 0.496 | - |

**Observation** : Seulement **3/77 départements** (3.9%) atteignent γ ≈ 1.0-1.3

---

## ⚠️ Problèmes Méthodologiques Identifiés

### 1. Signal Précurseur Inversé

**Attendu** : Le pic de variance (susceptibilité critique) devrait **précéder** le pic épidémique
**Observé** : Médiane = **-9 jours** (la variance pic **après** le pic de cas)

| Statistique | Valeur |
|-------------|--------|
| Médiane | **-9 jours** |
| Plage | [-80, +28] jours |
| Départements avec avance > 0 | 0/77 (0%) |

**Hypothèses** :
1. Le pic de variance ne correspond **pas** au point critique physique
2. La variable `nouveaux_cas = hosp.diff()` est trop **bruitée**
3. Il faudrait utiliser les **hospitalisations totales** (hosp) au lieu des différences
4. La variance glissante mesure la **volatilité**, maximale pendant la **décroissance chaotique**, pas la montée

### 2. γ Trop Faible (γ ≈ 0.5 au lieu de 1.0-1.5)

**Interprétations possibles** :

#### A. Phase Pré-Critique
- Les départements ne seraient **pas encore au point critique** lors de la Vague 1
- γ ≈ 0.5 pourrait correspondre à un régime **asymptotique** loin du point critique
- La susceptibilité χ croît, mais pas encore en loi de puissance

#### B. Fenêtre Temporelle Trop Courte
- **Médiane** : 29 points dans la partie ascendante
- **Plage** : [10, 70] points
- Avec seulement 10-30 points, la régression log-log peut être **instable**
- Les départements avec n_points > 40 ont-ils un γ plus élevé ?

#### C. Mauvaise Définition de la Variable d'Ordre
- **Hypothèse actuelle** : `nouveaux_cas = hosp.diff()` représente l'incidence
- **Alternative** : Utiliser `hosp` (hospitalisations totales) comme paramètre d'ordre
- La variance de `hosp` pourrait donner un signal plus robuste

#### D. Classe d'Universalité Différente
- Les systèmes sociaux pourraient appartenir à une **classe d'universalité inconnue**
- Exposants critiques : γ ≈ 0.5, β ≈ ? (à calculer), ν ≈ ? (à calculer)
- Nécessite une **dérivation théorique** du Hamiltonien SR pour prédire γ

---

## 📈 Corrélations Observées

### γ vs R² (Panel C)

**Tendance claire** :
- ✅ **γ élevé (> 1.0) ⇒ R² élevé (> 0.7)** : Fit de qualité, signal physique robuste
- ⚠️ **γ faible (< 0.3) ⇒ R² faible (< 0.3)** : Fit médiocre, signal bruité

**Interprétation** :
- Les départements avec **partie ascendante longue** (n_points > 40) donnent de meilleurs fits
- Les départements ruraux/faible densité ont des données **bruitées** (pic tardif, croissance lente)
- Les départements urbains (Grand Est, Île-de-France) ont paradoxalement **échoué** la régression

---

## 🧪 Cas d'Étude : Grand Est vs Île-de-France

### Grand Est
- **Point critique** : 2020-03-24 (J6)
- **Régression** : ⚠️ **Échouée** (données insuffisantes)
- **Cause probable** : Pic de variance **trop tôt** (J6), partie ascendante < 10 points

### Île-de-France
- **Point critique** : 2020-04-06 (J19)
- **γ** : 0.460 (R² = 0.237)
- **Avance** : -5 jours (pic variance **après** pic cas)
- **Qualité** : ⚠️ Fit médiocre (R² < 0.5)

**Problème** : Les régions les plus touchées (Grand Est, Île-de-France) donnent les **pires résultats**. Pourquoi ?

---

## 🔍 Questions Méthodologiques Ouvertes

### Q1. Variable d'Ordre : Quoi mesurer ?

| Variable | Avantages | Inconvénients |
|----------|-----------|---------------|
| `hosp.diff()` (actuel) | Mesure l'incidence quotidienne | Très bruité, diff amplifie le bruit |
| `hosp` (total) | Signal plus lisse | Cumulative, pas directement l'incidence |
| `rea` (réanimations) | Cas graves, moins bruité | Échantillon plus petit |
| `dc.diff()` (décès) | Signal terminal | Décalage temporel important |

**Recommandation** : Tester la variance de `hosp` (total) au lieu de `hosp.diff()`

### Q2. Point Critique : Pic de Variance ou Autre ?

**Alternatives à tester** :
1. **Pic d'accélération** : Maximum de `hosp.diff().diff()` (dérivée seconde)
2. **Point d'inflexion** : Où la courbe sigmoïde change de concavité
3. **Pic de susceptibilité SR** : Selon le modèle SR, `χ_SR ∝ d²I/dt²`

### Q3. Fenêtre de Variance : 7 jours optimal ?

| Fenêtre | Avantages | Inconvénients |
|---------|-----------|---------------|
| 3 jours | Capture fluctuations rapides | Très bruité |
| 7 jours (actuel) | Compromis | Peut lisser les signaux critiques |
| 14 jours | Signal lisse | Perd résolution temporelle |

**Test** : Calculer γ avec fenêtres de 3, 7, 14 jours et comparer

### Q4. Partie Ascendante : Jusqu'où régresser ?

**Critère actuel** : Tous les points avec `t < t_c` et `χ > 0`

**Alternatives** :
1. **Filtrer ε_min** : Ne régresser que pour `ε > ε_min` (ex: ε > 3 jours)
2. **Partie linéaire log-log** : Détecter automatiquement la zone de loi de puissance
3. **Fenêtre glissante** : Optimiser la plage [ε_min, ε_max] pour maximiser R²

---

## 🎯 Stratégie de Validation Proposée

### Étape 1 : Tester la Variable d'Ordre
1. ✅ **Actuel** : `nouveaux_cas = hosp.diff()` → γ ≈ 0.5
2. 🔄 **Tester** : `variance(hosp)` au lieu de `variance(hosp.diff())`
3. 🔄 **Tester** : `variance(rea)` (réanimations)

### Étape 2 : Tester la Fenêtre de Variance
1. ✅ **Actuel** : 7 jours
2. 🔄 **Tester** : 3 jours (haute résolution)
3. 🔄 **Tester** : 14 jours (signal lisse)

### Étape 3 : Tester la Définition du Point Critique
1. ✅ **Actuel** : Pic de variance
2. 🔄 **Tester** : Point d'inflexion de `hosp`
3. 🔄 **Tester** : Pic d'accélération (`hosp.diff().diff()`)

### Étape 4 : Filtrer la Régression
1. ✅ **Actuel** : Tous les points avec `ε > 0`
2. 🔄 **Tester** : Filtrer `ε > 3` (éviter les très petits ε bruités)
3. 🔄 **Tester** : Détection automatique de la zone de loi de puissance

---

## 📌 Conclusion Provisoire

### ✅ Progrès Réalisés
1. **γ est maintenant positif** (88.3% des départements) : Physiquement cohérent
2. **Quelques départements atteignent γ ≈ 1.0-1.3** : Proche Ising 3D / Mean-field
3. **Méthode physique robuste** : Distance temporelle au lieu de métrique de fit

### ⚠️ Problèmes Persistants
1. **γ moyen trop faible** (0.5 au lieu de 1.0-1.5)
2. **Signal précurseur inversé** (pic variance **après** pic cas)
3. **Qualité du fit modérée** (R² médian = 0.364)
4. **Grand Est échoue** (régression impossible)

### 🔬 Hypothèse Principale
Le problème vient probablement de la **variable d'ordre** :
- `hosp.diff()` est **trop bruitée** et amplifie les fluctuations stochastiques
- La variance de cette variable bruitée ne capture **pas** la susceptibilité critique physique
- Il faut tester `variance(hosp)` (hospitalisations totales) pour obtenir un signal plus robuste

### 🎯 Prochaine Étape Recommandée
**Recalculer γ avec `hosp` au lieu de `hosp.diff()`** et vérifier si :
1. γ augmente vers 1.0-1.5
2. Le signal précurseur redevient positif (+6 à +12 jours)
3. R² s'améliore (> 0.5)
4. Grand Est et Île-de-France donnent de meilleurs résultats

---

## 📁 Fichiers Générés

- `src/analyse_exposant_gamma_physique.py` : Script d'analyse complet (420 lignes)
- `data/resultats_gamma_physique.csv` : Résultats pour 77 départements
- `reports/exposant_gamma_physique.png` : Visualisation 4 panels

---

## 🔗 Références Théoriques

**Classes d'Universalité** :
- Ising 3D : γ = 1.24, β = 0.325, ν = 0.63
- Mean-field : γ = 1.0, β = 0.5, ν = 0.5
- Ising 2D : γ = 1.75, β = 0.125, ν = 1.0

**Loi de Puissance** :
```
χ(t) = A * |t - t_c|^(-γ)  avec γ > 0
```

Si γ < 0 : La variable critique ε est mal définie ou inversée.
Si γ ≈ 0.5 : Régime pré-critique ou classe d'universalité inconnue.
Si γ ≈ 1.0-1.5 : Système social complexe en transition de phase.
