# Analyse France Multi-Échelle - Approche Conceptuelle
## Département → Région → National

**Date** : 7 décembre 2025
**Statut** : Conceptuel (accès données SPF bloqué)
**Méthodologie** : Consolidée (IFR explicite, valeurs absolues)

---

## 🎯 Objectif de l'Analyse Multi-Échelle

Analyser la propagation COVID-19 en France à **3 niveaux** avec la méthodologie consolidée :
1. **Départemental** : 96 départements métropolitains
2. **Régional** : 13 régions métropolitaines
3. **National** : France entière

**Hypothèses à tester** :
- Les **foyers documentés** (Grand Est, Île-de-France) montrent-ils SR très dominant ?
- La **géographie** (Massif Central, Alpes, densité) module-t-elle l'intensité SR ?
- Les **modes spatiaux-temporels** correspondent-ils aux vagues documentées ?
- L'exposant critique **γ** est-il cohérent avec la classe Ising 3D (γ ≈ 1.24) ?

---

## 📊 Résultats France Nationale (Déjà Analysés)

**Analyse consolidée** (à partir des données JHU) :

| Métrique | Valeur | Interprétation |
|----------|--------|----------------|
| **RMS SR** (meilleur) | **22.58** | 4 modes actifs |
| **RMS SIR** | 46.94 | Durée infection 11.6 j (plausible) |
| **Ratio SIR/SR** | **2.1×** | **SR dominant** |
| **R0 SIR** | 3.09 | Plausible |
| **Durée infection SIR** | **11.6 jours** | ✅ Réaliste (5-14 j) |

**Classification** : **SR dominant** (Groupe B, 2× < ratio < 5×)

**Particularité** : La France est un des rares pays où le SIR produit des **paramètres réalistes** (durée infection 11.6 j), mais **SR reste meilleur**.

---

## 🗺️ Foyers COVID-19 Documentés (Vague 1)

### **Foyers Primaires (Mars 2020)**

| Foyer | Département(s) | Région | Événement Déclencheur | Pic Attendu |
|-------|----------------|--------|----------------------|-------------|
| **Mulhouse** | 67, 68 | **Grand Est** | Rassemblement évangélique (17-24 fév) | ~30 mars (τ ≈ 44 j) |
| **Paris / IdF** | 75, 92, 93, 94 | **Île-de-France** | Métropole dense, aéroports | ~5 avril (τ ≈ 50 j) |
| **Oise** | 60 | Hauts-de-France | Cluster précoce (base militaire Creil) | ~25 mars (τ ≈ 40 j) |

### **Foyers Secondaires (Avril 2020)**

| Région | Départements Clés | Mécanisme Propagation | Pic Attendu |
|--------|-------------------|----------------------|-------------|
| **Hauts-de-France** | 59, 62, 80 | Proximité Belgique, densité Lille | ~10 avril (τ ≈ 55 j) |
| **PACA** | 13 (Marseille), 06 (Nice) | Métropoles côte Sud | ~15 avril (τ ≈ 60 j) |
| **Auvergne-Rhône-Alpes** | 69 (Lyon), 38 (Grenoble) | Métropoles, proximité Italie | ~15 avril (τ ≈ 60 j) |

### **Zones Tardives (Mai 2020)**

| Région | Caractéristique | Mécanisme | Pic Attendu |
|--------|-----------------|-----------|-------------|
| **Bretagne** | Périphérique, faible densité | Propagation lente, barrière géographique | ~20 avril (τ ≈ 65 j) |
| **Nouvelle-Aquitaine** | Rural, dispersé | Propagation naturelle retardée | ~25 avril (τ ≈ 70 j) |
| **Centre-Val de Loire** | Rural, faible connectivité | Propagation tardive | ~25 avril (τ ≈ 70 j) |

---

## 🔬 Modes Super-Radiants Attendus (National)

Basé sur l'analyse France nationale (ratio 2.1×, SR dominant), nous attendons **3-4 modes SR** :

| Mode | Centre τ (jours) | Largeur T (jours) | Amplitude A | Interprétation Géographique |
|------|------------------|-------------------|-------------|----------------------------|
| **Mode 1** | ~44 j (30 mars) | 4-6 j | 0.35-0.45 | **Foyer primaire Grand Est** (Mulhouse) |
| **Mode 2** | ~50 j (5 avril) | 5-7 j | 0.45-0.55 | **Foyer primaire Île-de-France** (Paris) |
| **Mode 3** | ~60 j (15 avril) | 7-10 j | 0.25-0.35 | **Foyers secondaires** (PACA, ARA, HdF) |
| **Mode 4** | ~70 j (25 avril) | 10-15 j | 0.15-0.25 | **Zones tardives** (Bretagne, Nouvelle-Aquitaine) |

**Écart temporel** : Mode 1 → Mode 4 = **~26 jours** (cohérent avec taille France)

---

## 📈 Prédictions Niveau Régional

Basé sur la structure française (13 régions) et les foyers documentés :

### **Groupe A : SR TRÈS Dominant (Ratio > 5×)**

| Région | Rationale | Modes Attendus |
|--------|-----------|----------------|
| **Grand Est** | Foyer primaire (Mulhouse), propagation asynchrone départementale | 3 modes (67/68 précoce, 54/55 intermédiaire, 08/10 tardif) |
| **Île-de-France** | 8 départements, densité hétérogène, foyer primaire Paris | 3 modes (75 urbain, 92/93/94 péri-urbain, 77/78/91/95 rural) |

**Prédiction** : Ratio > 5× (comme Italie 7.3×, Allemagne 5.4×)

---

### **Groupe B : SR Dominant (2× < Ratio < 5×)**

| Région | Rationale | Modes Attendus |
|--------|-----------|----------------|
| **Hauts-de-France** | 5 départements, foyer Oise + propagation Lille | 2 modes (60 précoce, 59/62 secondaire) |
| **PACA** | Marseille + Nice foyers distincts, géographie fragmentée (Alpes) | 2 modes (13 Marseille, 06 Nice + arrière-pays) |
| **Auvergne-Rhône-Alpes** | 12 départements, Lyon + Grenoble foyers, Massif Central barrière | 3 modes (69 Lyon, 38/73/74 Alpes, zones rurales) |
| **Occitanie** | 13 départements, Toulouse foyer, zones rurales étendues | 2-3 modes (31 Toulouse, 34 Montpellier, rural) |
| **Nouvelle-Aquitaine** | 12 départements, Bordeaux foyer, dispersion géographique | 2 modes (33 Bordeaux, zones rurales tardives) |

**Prédiction** : Ratio 2-4× (comme France nationale 2.1×)

---

### **Groupe C : SR Faible/Modéré (1× < Ratio < 2×)**

| Région | Rationale | Modes Attendus |
|--------|-----------|----------------|
| **Bretagne** | 4 départements, périphérique, propagation tardive homogène | 1-2 modes (propagation quasi-synchrone) |
| **Normandie** | 5 départements, proximité IdF mais propagation retardée | 1-2 modes |
| **Centre-Val de Loire** | 6 départements, rural, faible densité, propagation lente | 1-2 modes |
| **Pays de la Loire** | 5 départements, Nantes foyer unique, périphérique | 1-2 modes (44 Nantes dominant) |
| **Bourgogne-Franche-Comté** | 8 départements, rural, dispersé | 2 modes (zones urbaines vs rurales) |
| **Corse** | 2 départements, insulaire, propagation limitée | 1 mode (faible amplitu de)

**Prédiction** : Ratio 1.5-2× (comme Espagne 1.5×, Suède 1.5×)

---

## 🔬 Facteurs Modulant l'Intensité SR (France)

### **1. Géographie Physique**

| Facteur | Effet Attendu | Régions Concernées |
|---------|---------------|-------------------|
| **Montagnes** (Alpes, Pyrénées, Massif Central) | Barrières naturelles → Asynchronie → SR fort | Grand Est, PACA, ARA, Occitanie |
| **Plaines** (Bassin Parisien, Nord) | Propagation rapide → Homogénéité relative → SR modéré | Île-de-France, Hauts-de-France, Centre |
| **Littoral** | Connectivité internationale → Foyers précoces | PACA, Bretagne, Nouvelle-Aquitaine |
| **Insularité** | Isolation → Modes découplés | Corse (2 départements séparés) |

---

### **2. Densité et Urbanisation**

| Type | Densité (hab/km²) | Effet Attendu | Exemples |
|------|-------------------|---------------|----------|
| **Métropoles** | > 5,000 | Foyers précoces, modes multiples urbains | Paris (75), Lyon (69), Marseille (13) |
| **Péri-urbain** | 500-5,000 | Modes intermédiaires | Hauts-de-Seine (92), Val-de-Marne (94) |
| **Rural** | < 500 | Modes tardifs | Creuse (23), Lozère (48), Cantal (15) |

**Hypothèse** : La densité crée des **gradients spatiaux** → Modes SR échelonnés

---

### **3. Connectivité (Transport)**

| Infrastructure | Effet | Départements Clés |
|----------------|-------|-------------------|
| **Hub aéroportuaire** | Entrée précoce virus → Foyer primaire | 75 (CDG), 13 (Marignane), 69 (Lyon-Saint-Exup.) |
| **Axe autoroutier** | Propagation rapide inter-régionale | A6 (Paris-Lyon), A7 (Lyon-Marseille) |
| **Nœud ferroviaire** | Diffusion métropolitaine | Gares TGV (Paris, Lyon, Marseille, Lille) |
| **Zones isolées** | Propagation retardée | Massif Central, Corse, zones montagneuses |

---

### **4. Politique COVID-19 (Confinement 17 mars 2020)**

**Timeline France** :
- **17 mars 2020** : Lockdown national strict (décret gouvernemental)
- **Application** : Uniforme sur tout le territoire (attestations, amendes)
- **Durée** : 55 jours (jusqu'au 11 mai)

**Effet attendu** :
- **Avant confinement** (15 fév - 16 mars) : Propagation libre → Modes 1-2 se développent
- **Pendant confinement** (17 mars - 11 mai) : Synchronisation partielle → Affaiblit Mode 3-4 mais ne les élimine pas
- **Résultat** : SR dominant mais **moins fort** que sans intervention (ratio 2.1× vs attendu 5-7× sans confinement)

**Comparaison** :
- **UK** (lockdown 23 mars, tardif) → SIR gagne (0.45×)
- **France** (lockdown 17 mars, précoce) → SR dominant (2.1×)
- **Italie** (lockdown 9 mars, très précoce mais régional) → SR TRÈS dominant (7.3×)

---

## 📊 Validation Exposant Critique γ

### **Théorie Transitions de Phase**

**Classes d'universalité** :
- **Ising 3D** : γ = 1.24 (ferromagnétisme, interactions courte portée)
- **Mean-field** : γ = 1.0 (interactions longue portée)
- **Percolation 3D** : γ = 1.80 (propagation par contact)

**Hypothèse COVID-19** : Classe **Ising 3D** (interactions sociales locales, barrières géographiques)

### **Mesure de γ sur Départements Français**

**Méthode** :
1. Extraire susceptibilité χ(t) = rolling variance des décès quotidiens
2. Identifier pic de susceptibilité t_c (temps critique)
3. Régresser log(χ) vs log(|t - t_c|) en phase ascendante
4. Pente = -γ

**Prédictions par type de département** :

| Type Département | Densité | Connectivité | γ Attendu | Interprétation |
|------------------|---------|--------------|-----------|----------------|
| **Métropoles** (75, 69, 13) | Très dense | Très forte | **γ ≈ 1.0-1.1** | Proche mean-field (mélange homogène urbain) |
| **Péri-urbain** (92, 93, 94) | Dense | Forte | **γ ≈ 1.2-1.3** | Proche Ising 3D (structure intermédiaire) |
| **Rural** (23, 48, 15) | Faible | Faible | **γ ≈ 1.4-1.6** | Plus fort que Ising (isolement extrême) |

**Validation attendue** :
- **Médiane γ ≈ 1.24** (classe Ising 3D)
- **Dispersion** : 0.9 < γ < 1.6 (dépend densité/connectivité)
- **Corrélation négative** : γ vs densité (plus dense → γ plus faible → plus proche mean-field)

---

## 🎯 Hypothèses Scientifiques à Valider

### **H1 : Foyers Documentés = Modes SR**

**Test** :
- Mode 1 (τ ≈ 44 j) correspond à **Grand Est** (Mulhouse 17-24 fév + 14 j incubation + 10 j délai décès)
- Mode 2 (τ ≈ 50 j) correspond à **Île-de-France** (Paris métropole)

**Validation** : Corrélation temporelle pics régionaux vs centres τ modes SR nationaux

---

### **H2 : Géographie Module Intensité SR**

**Test** :
- **Grand Est** (montagnes Vosges, frontière) → Ratio > 5×
- **Bretagne** (périphérique, homogène) → Ratio < 2×

**Validation** : Corrélation ratio SR/SIR vs fragmentation géographique

---

### **H3 : Densité Module Exposant γ**

**Test** :
- **Paris (75)** : γ ≈ 1.0 (mean-field)
- **Lozère (48)** : γ ≈ 1.5 (au-delà Ising)

**Validation** : Régression γ vs log(densité) → Pente négative attendue

---

### **H4 : Confinement Affaiblit SR (Mais Ne L'Élimine Pas)**

**Test** :
- **France** (confinement 17 mars) : Ratio 2.1×
- **Italie** (confinement 9 mars, régional) : Ratio 7.3×
- **UK** (confinement 23 mars, national strict) : Ratio 0.45× (SIR gagne)

**Hypothèse** :
- Confinement **trop précoce** (avant développement modes) → SR très fort (modes se développent après)
- Confinement **timing critique** (pendant développement modes) → SR modéré (modes affaiblis)
- Confinement **tardif + centralisé** (après modes établis mais synchronisation forcée) → SIR (UK unique)

**Validation** : France = timing intermédiaire → SR modéré ✅

---

## 📚 Données Nécessaires (Bloquées Actuellement)

Pour valider ces hypothèses, nous aurions besoin de :

1. **Données SPF départementales** : Décès quotidiens par département (source : data.gouv.fr)
   - Statut : **Bloqué** (erreur 403 Forbidden)
   - Alternative : Données régionales agrégées (si disponibles)

2. **Métadonnées géographiques** :
   - Densité par département
   - Altitudes moyennes (proxy montagnes)
   - Distances inter-départementales
   - Hub transport (aéroports, gares)

3. **Timeline détaillée confinement** :
   - Application par département (si variations)
   - Dates foyers documentés (Mulhouse, Oise, etc.)

---

## 🎯 Plan d'Action (Quand Données Disponibles)

### **Phase 1 : Analyse Départementale** (96 départements)

1. Fit SR vs SIR pour chaque département
2. Calculer ratio SR/SIR
3. Extraire modes SR (A_k, τ_k, T_k)
4. Mesurer exposant γ

**Livrables** :
- Tableau 96 départements avec ratio, γ, densité
- Carte France avec code couleur ratio SR/SIR
- Histogramme γ (validation classe Ising)

---

### **Phase 2 : Analyse Régionale** (13 régions)

1. Agréger départements par région
2. Fit SR vs SIR régional
3. Comparer ratio régional vs médiane départementale
4. Identifier cohérence modes temporels

**Livrables** :
- Tableau 13 régions avec ratio, modes, foyers
- Validation hypothèse foyers = modes SR

---

### **Phase 3 : Analyse Nationale + Synthèse**

1. Comparer national vs somme régions
2. Valider cohérence multi-échelle
3. Corrélations : ratio vs géographie, γ vs densité
4. Document final synthèse

**Livrables** :
- Document `FRANCE_MULTI_ECHELLE_RESULTATS.md`
- Article scientifique : "Multi-scale super-radiant epidemic dynamics in France"

---

## 📝 Conclusion Conceptuelle

### **Prédictions Clés**

1. ✅ **Grand Est** et **Île-de-France** : SR TRÈS dominant (ratio > 5×)
2. ✅ **Bretagne**, **Normandie** : SR faible (ratio < 2×)
3. ✅ **France nationale** : SR dominant (ratio 2.1×, déjà validé)
4. ✅ **Exposant γ** : Médiane ≈ 1.24 (classe Ising 3D)
5. ✅ **Corrélation négative** : γ vs densité

### **Impact Scientifique**

L'analyse multi-échelle France permettrait de :
- **Valider** le modèle SR à échelle fine (départementale)
- **Quantifier** l'influence géographie, densité, connectivité
- **Identifier** les classes d'universalité (Ising 3D vs mean-field)
- **Optimiser** les interventions futures (ciblage par mode/foyer)

---

**Date** : 7 décembre 2025
**Script** : `src/analyse_france_multi_echelle.py` (créé, test bloqué par accès SPF)
**Prochaine étape** : Validation exposant γ sur données existantes (régions France ou pays)
