# Guide d'Utilisation

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/VotreNom/Epid-miologie.git
cd Epid-miologie
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Configuration Kaggle API

Pour télécharger les données COVID-19, vous devez configurer votre clé API Kaggle:

1. Créez un compte sur [Kaggle](https://www.kaggle.com/)
2. Allez dans votre profil > Account > API > "Create New API Token"
3. Cela téléchargera un fichier `kaggle.json`
4. Placez ce fichier dans `~/.kaggle/kaggle.json` (Linux/Mac) ou `C:\Users\<Utilisateur>\.kaggle\kaggle.json` (Windows)
5. Définissez les permissions: `chmod 600 ~/.kaggle/kaggle.json`

## Utilisation

### Option 1: Script Original (src/main.py)

Le script original monolithe peut être exécuté directement:

```bash
cd src
python main.py
```

Pour modifier le nombre de modes, éditez la variable `N_MODES` dans le fichier.

### Option 2: Script Refactorisé (src/analyze_italy.py)

Version modulaire avec arguments en ligne de commande:

```bash
cd src
python analyze_italy.py --modes 4
```

**Options disponibles:**
- `--modes, -m`: Nombre de modes super-radiants (défaut: 4)
- `--no-save`: Afficher les graphiques sans les sauvegarder
- `--output, -o`: Répertoire de sortie pour les figures (défaut: ../reports)

**Exemples:**

```bash
# Analyse avec 3 modes
python analyze_italy.py --modes 3

# Analyse avec 5 modes, affichage uniquement (pas de sauvegarde)
python analyze_italy.py --modes 5 --no-save

# Analyse avec sortie dans un dossier personnalisé
python analyze_italy.py --modes 4 --output ../mes_resultats
```

### Option 3: Jupyter Notebook (notebooks/validation_italy.ipynb)

Pour une exploration interactive:

```bash
jupyter notebook notebooks/validation_italy.ipynb
```

Le notebook permet:
- D'exécuter l'analyse pas à pas
- De modifier les paramètres interactivement
- De visualiser les résultats en temps réel
- De tester différents nombres de modes
- D'expérimenter avec les visualisations

### Option 4: En tant que module Python

Vous pouvez également utiliser les modules dans vos propres scripts:

```python
import sys
sys.path.append('src')

from models import SuperRadiantModel, SIRModel
from data_loader import load_italy_wave1
from visualization import plot_model_comparison

# Charger les données
t_data, y_data, dates = load_italy_wave1()

# Créer et ajuster un modèle
model = SuperRadiantModel(n_modes=4)
params, rms = model.fit(t_data, y_data)

# Visualiser
y_fit = model.predict(t_data)
plot_model_comparison(t_data, y_data, y_fit, ...)
```

## Structure des Sorties

### Fichiers générés

Après exécution, vous trouverez dans le dossier `reports/`:

- `italy_wave1_Nmodes.png`: Comparaison des modèles
- `italy_modes_decomposition_N.png`: Décomposition en modes
- `italy_full_report_Nmodes.png`: Rapport complet (4 sous-graphiques)

### Sortie console

Le programme affiche:
1. Progression du téléchargement des données
2. Paramètres ajustés pour chaque mode (A, τ, T)
3. Erreurs RMS des deux modèles
4. Facteur d'amélioration (Super-Radiant vs SIR)
5. Interprétation sociologique des modes

## Exemples de Résultats

### Avec 4 modes (configuration par défaut)

```
Mode 1 (Urbain):      τ ≈ 5-10 jours
Mode 2 (Péri-urbain): τ ≈ 15-20 jours
Mode 3 (Rural):       τ ≈ 25-30 jours
Mode 4 (Isolé):       τ ≈ 35-45 jours
```

**Performance typique:**
- Erreur RMS Super-Radiant: ~0.05-0.15
- Erreur RMS SIR: ~0.20-0.50
- **Amélioration: 3-10x plus précis**

## Adaptation pour d'autres pays

Pour analyser d'autres pays, utilisez la fonction `load_country_wave`:

```python
from data_loader import load_country_wave

# Exemple: France
t, y, dates = load_country_wave(
    country='France',
    start_date='2020-03-01',
    end_date='2020-06-30',
    window=7
)
```

Pays disponibles dans le dataset:
- Italy
- France
- Spain
- US
- United Kingdom
- Germany
- Et beaucoup d'autres...

## Troubleshooting

### Erreur d'authentification Kaggle

```
OSError: Could not find kaggle.json
```

**Solution:** Vérifiez que le fichier `kaggle.json` est dans `~/.kaggle/` avec les bonnes permissions (600).

### Erreur de convergence

```
OptimizeWarning: Covariance of the parameters could not be estimated
```

**Solution:**
- Essayez un nombre différent de modes
- Augmentez `maxfev` dans l'appel à `fit()`
- Vérifiez que les données sont bien prétraitées

### Import errors

```
ModuleNotFoundError: No module named 'src'
```

**Solution:** Assurez-vous d'être dans le bon répertoire ou ajoutez `src` au PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:./src"
```

## Contribuer

Pour contribuer au projet:
1. Forkez le dépôt
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Soumettez une Pull Request

## Citation

Si vous utilisez ce code dans vos recherches, veuillez citer:

```bibtex
@software{epidemiologie_radiative,
  title={Modèle Super-Radiant pour la Dynamique Épidémique},
  author={Votre Nom},
  year={2024},
  url={https://github.com/VotreNom/Epid-miologie}
}
```
