# epidemiologie-radiative-model

# Dynamique Radiative des Épidémies

## Résumé
Un cadre théorique novateur pour la dynamique épidémique, modélisant les phénomènes collectifs comme des transitions de phase radiatives hors-équilibre.
Basé sur un modèle unifié Dicke-Ising-Champ, ce projet intègre la super-radiance de l'optique quantique et la physique statistique pour dépasser les limites des modèles SIR/SEIR.
Validation empirique sur les données COVID-19 (France, Italie) montrant une précision >40x supérieure au SIR.
Implémentation en Python.

## Proposition Centrale
Les épidémies ne sont pas des processus aléatoires (modèles SIR) mais des transitions de phase radiatives hors-équilibre...

## Résultats Clés
- Modèle Dicke-Ising-Champ unifié.
- Validation sur COVID-19 France (Erreur RMS 4.3% vs 15.2% pour SIR).
- Validation sur COVID-19 Italie (Erreur RMS ~11 vs ~458 pour SIR).
- Identification de 3-4 modes sociaux (urbain, péri-urbain, rural, isolé).

## Structure du Dépôt
- `/data/` : Scripts de téléchargement et de prétraitement des données.
- `/notebooks/` : Notebooks Jupyter pour l'analyse exploratoire et la validation (ex: `validation_italy.ipynb`).
- `/src/` : Modules Python réutilisables (ex: `models.py`, `utils.py`).
- `/reports/` : Rapports de recherche (PDF) et figures générées.

## Installation
```bash
git clone https://github.com/VotreNom/Epidemiologie.git
cd Epidemiologie
pip install -r requirements.txt

## Utilisation

Exemple pour lancer la validation sur l'Italie avec 4 modes :
bash
python src/main.py --country Italy --modes 4
