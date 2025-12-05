# Utilisation des Données Réelles Santé Publique France

## 📥 Source des Données

**Lien direct (data.gouv.fr):**
```
https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4
```

**Fichier:** `donnees-hospitalieres-covid19.csv`

**Contenu:** Données hospitalières COVID-19 par département français (historique complet).

**Colonnes principales:**
- `dep`: Code département (01-95, 2A, 2B, 971-976)
- `jour`: Date (format AAAA-MM-JJ)
- `hosp`: Nombre de personnes actuellement hospitalisées
- `rea`: Nombre de personnes actuellement en réanimation
- `rad`: Nombre cumulé de retours à domicile
- `dc`: Nombre cumulé de décès hospitaliers

---

## 🛠️ Utilisation avec le Script d'Analyse Régionale

### Option 1: Script Automatique (si connexion disponible)

Le script `run_analysis_france_regional_real_data.py` tente automatiquement de télécharger les données:

```bash
python3 src/run_analysis_france_regional_real_data.py
```

Si le téléchargement échoue (problème réseau, proxy), le script utilise des données synthétiques en fallback.

---

### Option 2: Téléchargement Manuel

Si vous ne pouvez pas télécharger automatiquement (proxy, firewall):

**1. Télécharger le fichier manuellement**
   - Aller sur: https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/
   - Télécharger `donnees-hospitalieres-covid19.csv`
   - Placer dans: `data/donnees-hospitalieres-covid19.csv`

**2. Modifier le script pour charger localement**

Éditer `src/run_analysis_france_regional_real_data.py`, fonction `load_real_data_spf()`:

```python
def load_real_data_spf():
    """Charge les données depuis un fichier local."""

    # Option A: Fichier local
    file_path = 'data/donnees-hospitalieres-covid19.csv'

    print(f"📥 Chargement depuis fichier local: {file_path}")

    try:
        df = pd.read_csv(file_path, sep=';', low_memory=False)
        # ... reste du code inchangé
```

---

## 🗺️ Correspondance Départements → Régions

Le script utilise la nomenclature **régions 2016** (13 régions métropolitaines):

| Région | Départements | Population | Capitale |
|--------|--------------|------------|----------|
| **Grand Est** | 08, 10, 51, 52, 54, 55, 57, 67, 68, 88 | 5.6M | Strasbourg |
| **Île-de-France** | 75, 77, 78, 91, 92, 93, 94, 95 | 12.2M | Paris |
| **Hauts-de-France** | 02, 59, 60, 62, 80 | 6.0M | Lille |
| **PACA** | 04, 05, 06, 13, 83, 84 | 5.1M | Marseille |
| **Auvergne-Rhône-Alpes** | 01, 03, 07, 15, 26, 38, 42, 43, 63, 69, 73, 74 | 8.0M | Lyon |
| **Nouvelle-Aquitaine** | 16, 17, 19, 23, 24, 33, 40, 47, 64, 79, 86, 87 | 6.0M | Bordeaux |
| **Occitanie** | 09, 11, 12, 30, 31, 32, 34, 46, 48, 65, 66, 81, 82 | 5.9M | Toulouse |
| **Bretagne** | 22, 29, 35, 56 | 3.3M | Rennes |
| **Normandie** | 14, 27, 50, 61, 76 | 3.3M | Rouen |
| **Pays de la Loire** | 44, 49, 53, 72, 85 | 3.8M | Nantes |
| **Centre-Val de Loire** | 18, 28, 36, 37, 41, 45 | 2.6M | Orléans |
| **Bourgogne-Franche-Comté** | 21, 25, 39, 58, 70, 71, 89, 90 | 2.8M | Dijon |
| **Corse** | 2A, 2B | 0.3M | Ajaccio |

---

## 📊 Métrique Utilisée

Le script utilise **`hosp`** (hospitalisations) comme métrique primaire:

```python
metric = 'hosp'  # Nombre de personnes hospitalisées
```

**Alternatives possibles:**
- `rea`: Réanimations (plus sévère, signal plus précoce)
- `dc`: Décès hospitaliers cumulés (retardé)
- `rad`: Retours à domicile (proxy guérisons)

Pour changer la métrique, modifier dans `load_real_data_spf()`:

```python
metric = 'rea'  # Utiliser réanimations au lieu d'hospitalisations
```

---

## 🎯 Traitement des Données

Le script effectue automatiquement:

1. **Filtrage Vague 1:** 15 février - 30 juin 2020
2. **Agrégation départements → régions:** Somme des départements par région
3. **Calcul de l'incidence:** Dérivée des hospitalisations (nouveaux cas/jour)
4. **Lissage:** Moyenne mobile 7 jours (centre)
5. **Normalisation:** Division par le maximum

```python
# Incidence quotidienne lissée
daily_new = daily.diff().fillna(0)  # Nouveaux cas/jour
daily_smooth = daily_new.rolling(window=7, center=True).mean()

# Normalisation
daily_norm = daily_smooth / daily_smooth.max()
```

---

## 🔬 Résultats Attendus avec Données Réelles

### **Grand Est** - Régime SR Multi-Modes Attendu

**Faits historiques:**
- **Cluster Mulhouse** (rassemblement évangélique 17-24 février)
- Vague précoce **avant confinement national** (17 mars)
- Saturation hospitalière dès mi-mars (Mulhouse, Colmar)

**Prédiction:**
- Mode urbain précoce (τ ≈ 25-30j ~ 10-15 mars)
- Mode péri-urbain (τ ≈ 35-40j ~ 20-25 mars)
- Mode rural tardif (τ ≈ 50-55j ~ 5-10 avril)
- **Régime SR dominant** (multi-modes, propagation asynchrone)

---

### **Île-de-France** - Régime Mixte Attendu

**Faits historiques:**
- Densité très élevée (21,000 hab/km² Paris)
- Confinement 17 mars mais propagation rapide
- Saturation hospitalière fin mars

**Prédiction:**
- Mode principal (τ ≈ 35-40j ~ 20-25 mars)
- Mode secondaire banlieue (τ ≈ 45-50j ~ 1-6 avril)
- **Régime SR ou mixte** (densité empêche synchronisation complète)

---

### **Autres Régions** - Régime SIR Attendu

**Faits historiques:**
- Vagues plus tardives (avril)
- Confinement effectif limite propagation
- Pics synchronisés

**Prédiction:**
- Pics uniques (τ ≈ 45-55j ~ 1-11 avril)
- **Régime SIR dominant** (confinement synchronise)

---

## 📈 Comparaison Données Réelles vs Synthétiques

| Aspect | Données Synthétiques | Données Réelles SPF |
|--------|---------------------|---------------------|
| **Source** | Générées via sech² | Hospitalisations réelles |
| **Validation** | Basées sur faits documentés | Observations terrain |
| **Temporalités** | Estimées (τ ≈ 28j, 38j, 52j) | **Mesurées précisément** |
| **Amplitudes** | Normalisées arbitrairement | Proportions réelles |
| **Bruit** | Aucun (courbes lisses) | Variabilité réelle |
| **Utilité** | Démonstration concept | **Validation quantitative** |

---

## 🚀 Extensions Possibles

### 1. Analyse par Département

Au lieu d'agréger par région, analyser **chaque département individuellement**:

```python
# Analyser département 67 (Bas-Rhin)
dept_67 = wave1[wave1['dep'] == '67']
daily_67 = dept_67.groupby('jour')['hosp'].sum()
```

Permettrait de:
- Identifier clusters locaux (Mulhouse vs Strasbourg)
- Détecter propagation intra-régionale
- Valider modes urbain/péri-urbain/rural

---

### 2. Comparaison Hospitalisations vs Décès

Tester si les régimes SR/SIR diffèrent selon la métrique:

```python
# Hospitalisation (précoce)
hosp_regime = analyze_region(region, data_hosp)

# Décès (retardé ~2 semaines)
dc_regime = analyze_region(region, data_dc)
```

**Hypothèse:** Les décès (retardés) pourraient montrer plus de synchronisation (régime SIR) que les hospitalisations (régime SR).

---

### 3. Analyse Multi-Vagues

Étendre à la **Vague 2** (automne 2020) et **Vague 3** (2021):

```python
wave2 = df[(df['jour'] >= '2020-09-01') & (df['jour'] <= '2020-12-31')]
wave3 = df[(df['jour'] >= '2021-03-01') & (df['jour'] <= '2021-06-30')]
```

**Question:** Le régime change-t-il entre vagues (apprentissage, vaccination)?

---

### 4. Corrélation avec Mobilité

Croiser avec données de mobilité Google/Apple:
- Régions SR → Mobilité élevée pendant Vague 1?
- Régions SIR → Mobilité réduite (confinement effectif)?

---

## 📝 Citation

Si vous utilisez ces données dans vos recherches:

```bibtex
@dataset{spf_covid19_2024,
  title={Données hospitalières relatives à l'épidémie de COVID-19},
  author={{Santé Publique France}},
  year={2024},
  url={https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/},
  note={Données mises à jour quotidiennement}
}
```

---

## ⚠️ Limitations et Précautions

### Biais dans les Données Hospitalières

1. **Sous-déclaration précoce:**
   - Février-début mars 2020: capacités de test limitées
   - Beaucoup de cas légers non hospitalisés/non détectés

2. **Saturation hospitalière:**
   - Grand Est mi-mars: transferts vers autres régions (TGV médicalisés)
   - Biais dans les comptages régionaux

3. **Définitions évolutives:**
   - Critères d'hospitalisation ont changé durant la pandémie
   - Protocoles de tests différents par période

### Recommandations

- **Toujours vérifier la date de mise à jour** du fichier CSV
- **Comparer avec d'autres sources** (ECDC, Johns Hopkins)
- **Interpréter les tendances** plutôt que les valeurs absolues
- **Documenter la métrique utilisée** (hosp, rea, dc)

---

## 📞 Support

Pour questions sur les données SPF:
- **Documentation officielle:** https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/
- **Contact Santé Publique France:** https://www.santepubliquefrance.fr/

Pour questions sur le script d'analyse:
- **Voir:** `src/run_analysis_france_regional_real_data.py`
- **Issues GitHub:** https://github.com/VotreUsername/Epid-miologie/issues

---

**Dernière mise à jour:** Décembre 2025
