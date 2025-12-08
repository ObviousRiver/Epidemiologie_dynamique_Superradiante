# Données COVID-19 France - Santé Publique France

## 📥 Sources des Données

Ce répertoire contient les données historiques COVID-19 France (Vague 1) utilisées pour les analyses régionales.

### **Fichier Principal**

**Nom**: `donnees-hospitalieres-covid19-wave1.csv`

**Source**: Santé Publique France via data.gouv.fr

**URL de téléchargement**:
- Lien direct: https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4
- Page dataset: https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/

**Période**: 15 février 2020 - 30 juin 2020 (Vague 1)

**Colonnes**:
- `dep`: Code département (01-95, 2A, 2B)
- `jour`: Date (AAAA-MM-JJ)
- `sexe`: 0=tous, 1=homme, 2=femme
- `hosp`: Nombre de personnes hospitalisées
- `rea`: Nombre de personnes en réanimation
- `rad`: Nombre cumulé de retours à domicile
- `dc`: Nombre cumulé de décès hospitaliers

**Licence**: Licence Ouverte / Open License v2.0 (Etalab)
- ✅ Utilisation libre (y compris commerciale)
- ✅ Reproduction autorisée
- ✅ Modification autorisée
- Attribution requise: "Santé Publique France"

**Taille**: ~3 MB (Vague 1 uniquement)

---

## 🛠️ Comment Télécharger

### **Option 1: Téléchargement Manuel (Recommandé)**

1. Aller sur: https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/

2. Trouver le fichier "donnees-hospitalieres-covid19.csv"

3. Clic droit → Enregistrer sous → Placer dans ce répertoire (`data/`)

4. (Optionnel) Filtrer pour Vague 1 seulement:
   ```bash
   # Garder seulement février-juin 2020
   head -n 1 donnees-hospitalieres-covid19.csv > donnees-hospitalieres-covid19-wave1.csv
   grep "2020-0[2-6]" donnees-hospitalieres-covid19.csv >> donnees-hospitalieres-covid19-wave1.csv
   ```

### **Option 2: Téléchargement via wget/curl**

```bash
cd data/
wget https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4 \
     -O donnees-hospitalieres-covid19-wave1.csv
```

Ou avec curl:
```bash
curl -o donnees-hospitalieres-covid19-wave1.csv \
     https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4
```

---

## 📊 Utilisation avec les Scripts

Une fois le fichier téléchargé dans `data/`, les scripts suivants l'utiliseront automatiquement:

**Scripts compatibles**:
- `src/run_analysis_france_regional_real_data.py` → Cherche `data/donnees-hospitalieres-covid19.csv`
- `src/ComparatifSR_SIR_Region_France_enhanced.py` → Cherche `data/donnees-hospitalieres-nouvelle-france.csv`

**Exemple d'utilisation**:
```python
# Le script tente dans l'ordre:
# 1. Téléchargement depuis URL (si accessible)
# 2. Fichier local dans data/
# 3. Données synthétiques (fallback)

python3 src/run_analysis_france_regional_real_data.py
# → Utilisera automatiquement data/donnees-hospitalieres-covid19-wave1.csv si présent
```

---

## 🔍 Vérification de l'Intégrité

Après téléchargement, vérifiez:

```bash
# Taille du fichier (doit être ~3-30 MB selon filtrage)
ls -lh donnees-hospitalieres-covid19-wave1.csv

# Nombre de lignes
wc -l donnees-hospitalieres-covid19-wave1.csv

# Aperçu des données
head -n 10 donnees-hospitalieres-covid19-wave1.csv
```

**Résultat attendu** (exemple pour Vague 1):
```
dep;sexe;jour;hosp;rea;rad;dc
01;0;2020-03-18;17;3;0;0
01;0;2020-03-19;29;7;0;1
...
```

---

## 📝 Citation

Si vous utilisez ces données dans vos publications:

```bibtex
@dataset{spf_covid19_2020,
  title={Données hospitalières relatives à l'épidémie de COVID-19},
  author={{Santé Publique France}},
  year={2020},
  publisher={data.gouv.fr},
  url={https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/},
  note={Licence Ouverte / Open License v2.0}
}
```

---

## ⚠️ Notes Importantes

### **Pourquoi Versionner ces Données?**

Normalement, versionner des données dans Git n'est pas recommandé, MAIS ici c'est justifié:

1. ✅ **Données historiques figées** (Vague 1 2020 ne changera jamais)
2. ✅ **Reproductibilité scientifique** (autres chercheurs peuvent valider)
3. ✅ **Taille raisonnable** (<5 MB pour Vague 1)
4. ✅ **Licence ouverte** (autorisation explicite de redistribution)
5. ✅ **Cohérence** (PDFs théoriques déjà versionnés)

### **Alternatives non Retenues**

- **Git LFS**: Complexe à setup, inutile pour 3 MB
- **Archive externe** (Zenodo): Moins pratique pour utilisateurs
- **Download automatique**: Bloqué par proxies/firewalls

### **Fichiers à .gitignore (si volumineux)**

Si le fichier complet (toutes périodes) est trop gros (>20 MB), ajoutez à `.gitignore`:

```
# .gitignore
data/donnees-hospitalieres-covid19-full.csv  # Fichier complet trop gros
```

Et gardez seulement la version filtrée Vague 1.

---

## 📁 Structure du Répertoire `data/`

```
data/
├── README.md                                    # Ce fichier
├── donnees-hospitalieres-covid19-wave1.csv     # Données Vague 1 (à télécharger)
└── (optionnel) autres datasets régionaux...
```

---

**Dernière mise à jour**: Décembre 2025
**Licence des données**: Licence Ouverte / Open License v2.0 (Etalab)
**Source**: Santé Publique France
