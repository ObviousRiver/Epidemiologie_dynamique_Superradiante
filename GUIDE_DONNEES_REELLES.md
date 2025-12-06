# Guide d'Utilisation des Données Réelles SPF

## 🎯 Objectif

Ce guide vous explique comment télécharger et utiliser les **données réelles Santé Publique France** pour valider les analyses régionales avec des observations terrain.

---

## 📥 Étape 1: Téléchargement des Données

### **Option A: Via Navigateur (Recommandé)**

1. **Ouvrir la page du dataset**:
   ```
   https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/
   ```

2. **Chercher le fichier**: `donnees-hospitalieres-covid19.csv`

3. **Télécharger**:
   - Clic sur "Télécharger" ou lien direct:
   - https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4

4. **Placer dans le répertoire `data/`**:
   ```bash
   mv ~/Downloads/donnees-hospitalieres-covid19.csv ./data/
   ```

### **Option B: Via Ligne de Commande**

Si votre terminal a accès internet:

```bash
cd data/
wget https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4 \
     -O donnees-hospitalieres-covid19.csv
```

Ou avec curl:

```bash
curl -L -o data/donnees-hospitalieres-covid19.csv \
     https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4
```

### **Option C: Fichier Filtré Vague 1 Seulement (Recommandé pour Git)**

Pour réduire la taille (fichier complet ≈ 30 MB, Vague 1 ≈ 3 MB):

```bash
# Télécharger le fichier complet
wget https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4 \
     -O temp_full.csv

# Filtrer Vague 1 (février-juin 2020)
head -n 1 temp_full.csv > data/donnees-hospitalieres-covid19-wave1.csv
grep "2020-0[2-6]" temp_full.csv >> data/donnees-hospitalieres-covid19-wave1.csv

# Nettoyer
rm temp_full.csv
```

---

## ✅ Étape 2: Vérification

```bash
# Vérifier que le fichier existe
ls -lh data/donnees-hospitalieres-covid19*.csv

# Aperçu des premières lignes
head -n 5 data/donnees-hospitalieres-covid19-wave1.csv
```

**Sortie attendue**:
```
dep;sexe;jour;hosp;rea;rad;dc
01;0;2020-03-18;17;3;0;0
01;0;2020-03-19;29;7;0;1
```

---

## 🚀 Étape 3: Utilisation avec les Scripts

### **Script 1: Analyse Régionale Enhanced**

```bash
python3 src/ComparatifSR_SIR_Region_France_enhanced.py
```

**Comportement**:
1. ✅ Tente téléchargement URL (échouera si proxy)
2. ✅ Cherche `data/donnees-hospitalieres-nouvelle-france.csv` (si existe)
3. ✅ Cherche `data/donnees-hospitalieres-covid19.csv` (votre fichier!)
4. ✅ Fallback données synthétiques si rien trouvé

**Pour que votre fichier soit détecté**, renommez-le ou créez un lien symbolique:

```bash
# Option 1: Renommer
mv data/donnees-hospitalieres-covid19.csv \
   data/donnees-hospitalieres-nouvelle-france.csv

# Option 2: Lien symbolique (garde les deux)
ln -s donnees-hospitalieres-covid19.csv \
      data/donnees-hospitalieres-nouvelle-france.csv
```

### **Script 2: Analyse Régionale avec Données Réelles**

```bash
python3 src/run_analysis_france_regional_real_data.py
```

**Comportement**:
1. ✅ Tente téléchargement URL
2. ✅ Cherche `data/donnees-hospitalieres-covid19.csv` (votre fichier!)
3. ✅ Fallback données synthétiques

**Aucune modification nécessaire** si vous avez nommé le fichier `donnees-hospitalieres-covid19.csv`.

---

## 📊 Résultats Attendus avec Données Réelles

### **Comparaison Synthétique vs Réel**

| Aspect | Données Synthétiques | **Données Réelles SPF** |
|--------|---------------------|-------------------------|
| **Source** | Générées via sech² | Hospitalisations terrain |
| **Temporalités** | Estimées (τ ≈ 28j, 38j, 52j) | **Observées exactes** |
| **Grand Est** | SR gagne 5.20x | SR gagne **??x** (à valider!) |
| **Variance précurseur** | +8 jours (synthétique) | **+? jours** (réel) |
| **Validation** | Conceptuelle | **Quantitative** ✅ |

### **Questions à Valider**

Avec les données réelles, vous pourrez vérifier:

1. ✅ **Grand Est est-il vraiment en régime SR?**
   - Attendu: Oui (vague précoce, propagation libre)
   - À mesurer: Ratio RMS SIR/SR

2. ✅ **La variance pic-t-elle avant l'épidémie?**
   - Attendu: Oui, ~7-12 jours avant
   - À mesurer: Délai exact pic variance → pic épidémie

3. ✅ **Les temporalités correspondent-elles aux faits historiques?**
   - Grand Est: pic attendu ~15 mars (jour 30)
   - Île-de-France: pic attendu ~24 mars (jour 39)

4. ✅ **L'Alsace (départements 67, 68) domine-t-elle le Grand Est?**
   - Cluster Mulhouse → modes urbains précoces
   - À vérifier: Décomposition par département

---

## 🔧 Adaptation des Scripts (Optionnel)

Si vous voulez standardiser le nom de fichier dans les scripts:

### **Modifier `LOCAL_DATA_PATH`**

Dans `src/ComparatifSR_SIR_Region_France_enhanced.py` (ligne 15):

```python
# Avant
LOCAL_DATA_PATH = "data/donnees-hospitalieres-nouvelle-france.csv"

# Après (standardisé)
LOCAL_DATA_PATH = "data/donnees-hospitalieres-covid19.csv"
```

Dans `src/run_analysis_france_regional_real_data.py` (ligne 11):

```python
# Déjà correct:
LOCAL_DATA_PATH = "data/donnees-hospitalieres-covid19.csv"
```

---

## 📤 Étape 4: Versionner les Données (Optionnel)

### **Pourquoi versionner?**

✅ **Arguments pour**:
- Reproductibilité scientifique
- Données historiques figées (Vague 1 ne changera jamais)
- Taille raisonnable (~3 MB pour Vague 1)
- Licence ouverte (redistribution autorisée)

❌ **Arguments contre**:
- Augmente taille du repo Git
- Données publiques (disponibles sur data.gouv.fr)

### **Si vous décidez de versionner**:

```bash
# Vérifier que le .gitignore autorise data/*.csv
grep "!data/\*\.csv" .gitignore
# Doit afficher: !data/*.csv

# Ajouter le fichier
git add data/donnees-hospitalieres-covid19-wave1.csv
git add data/README.md

# Commit
git commit -m "Add SPF COVID-19 Wave 1 dataset (historical, 3MB)

- Source: Santé Publique France via data.gouv.fr
- Period: February-June 2020 (Wave 1)
- License: Licence Ouverte / Open License v2.0
- Size: ~3 MB (filtered for Wave 1)
- Purpose: Reproducibility of regional analyses"

# Push
git push origin <your-branch>
```

### **Alternatives (si fichier trop gros)**:

**Option 1: Compresser**

```bash
gzip data/donnees-hospitalieres-covid19-wave1.csv
# → Réduit à ~500 KB
git add data/donnees-hospitalieres-covid19-wave1.csv.gz
```

**Option 2: Archive externe**

Uploader sur Zenodo/Figshare et mettre le lien dans `data/README.md`.

**Option 3: .gitignore le gros fichier**

```bash
# .gitignore
data/donnees-hospitalieres-covid19-full.csv  # Fichier complet ignoré

# Mais autoriser la version filtrée
!data/donnees-hospitalieres-covid19-wave1.csv  # Vague 1 versionnée
```

---

## 🎯 Checklist Finale

Avant d'exécuter les analyses avec données réelles:

- [ ] Fichier téléchargé dans `data/`
- [ ] Nom standardisé (`donnees-hospitalieres-covid19.csv` ou `*-wave1.csv`)
- [ ] Vérification intégrité (head/tail/wc)
- [ ] Scripts modifiés (si nécessaire) pour pointer vers le bon fichier
- [ ] (Optionnel) Fichier ajouté à Git pour reproductibilité

**Commande de test**:

```bash
# Test rapide
python3 -c "
import pandas as pd
df = pd.read_csv('data/donnees-hospitalieres-covid19.csv', sep=';', nrows=5)
print(df.head())
"
# Si ça marche → prêt pour les analyses!
```

---

## 📞 Dépannage

### **Problème 1: Fichier non trouvé**

```
FileNotFoundError: [Errno 2] No such file or directory: 'data/...'
```

**Solution**: Vérifier le chemin et le nom du fichier

```bash
ls -la data/
# Ajuster le nom dans le script ou renommer le fichier
```

### **Problème 2: Erreur de parsing CSV**

```
ParserError: Error tokenizing data
```

**Solution**: Vérifier le séparateur (`;` pour SPF)

```python
df = pd.read_csv('data/...', sep=';')  # Pas ','
```

### **Problème 3: Données incohérentes**

**Solution**: Filtrer pour Vague 1 uniquement

```python
df = df[(df['jour'] >= '2020-02-15') & (df['jour'] <= '2020-06-30')]
```

---

## 🎉 Prêt pour l'Analyse!

Une fois les données téléchargées, vous pourrez:

1. ✅ Valider les prédictions avec observations réelles
2. ✅ Mesurer précisément les délais variance → pic
3. ✅ Identifier les régions SR vs SIR
4. ✅ Publier des résultats reproductibles

**Prochaine étape**: Exécutez les scripts et comparez avec les résultats synthétiques!

```bash
python3 src/ComparatifSR_SIR_Region_France_enhanced.py
# Devrait maintenant utiliser les données réelles! 🎯
```

---

**Document créé**: Décembre 2025
**Données**: Santé Publique France (Licence Ouverte v2.0)
