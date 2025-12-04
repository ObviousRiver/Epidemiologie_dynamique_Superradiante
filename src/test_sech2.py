#!/usr/bin/env python3
"""
Script de test simple pour valider la formule sech² du modèle Super-Radiant.
"""

import numpy as np
import sys
sys.path.insert(0, '/home/user/Epid-miologie/src')

from models import SuperRadiantModel

print("="*70)
print("TEST DU MODÈLE SUPER-RADIANT AVEC FORMULE SECH²")
print("="*70)

# Créer des données synthétiques avec 2 pics sech²
print("\n1. Génération de données synthétiques...")
t = np.linspace(0, 100, 200)

# Paramètres théoriques
A1, tau1, T1 = 1.0, 20.0, 5.0
A2, tau2, T2 = 0.6, 50.0, 8.0

# Générer données avec formule sech²
y_true = A1 / (np.cosh((t - tau1) / (2*T1)))**2 + \
         A2 / (np.cosh((t - tau2) / (2*T2)))**2

# Ajouter un peu de bruit
np.random.seed(42)
y_noisy = y_true + np.random.normal(0, 0.01, len(t))

print(f"   • Points de données: {len(t)}")
print(f"   • Plage temporelle: {t[0]:.1f} à {t[-1]:.1f}")
print(f"   • Valeur max: {y_noisy.max():.3f}")

# Ajuster le modèle
print("\n2. Ajustement du modèle Super-Radiant (2 modes)...")
model = SuperRadiantModel(n_modes=2)
params, rms = model.fit(t, y_noisy, maxfev=50000)

print(f"   ✓ Ajustement terminé!")
print(f"   • Erreur RMS: {rms:.6f}")

# Vérifier les paramètres
print("\n3. Paramètres ajustés vs théoriques:")
print("-"*70)
modes = model.get_mode_parameters()

theoretical = [
    {'A': A1, 'tau': tau1, 'T': T1},
    {'A': A2, 'tau': tau2, 'T': T2}
]

for i, (mode, theory) in enumerate(zip(modes, theoretical)):
    print(f"\nMode {i+1}:")
    print(f"   Amplitude (A):")
    print(f"      Théorique: {theory['A']:.4f}")
    print(f"      Ajusté:    {mode['A']:.4f}")
    print(f"      Erreur:    {abs(mode['A'] - theory['A'])/theory['A']*100:.2f}%")

    print(f"   Délai (τ):")
    print(f"      Théorique: {theory['tau']:.4f}")
    print(f"      Ajusté:    {mode['tau']:.4f}")
    print(f"      Erreur:    {abs(mode['tau'] - theory['tau'])/theory['tau']*100:.2f}%")

    print(f"   Temps (T):")
    print(f"      Théorique: {theory['T']:.4f}")
    print(f"      Ajusté:    {mode['T']:.4f}")
    print(f"      Erreur:    {abs(mode['T'] - theory['T'])/theory['T']*100:.2f}%")

# Test de prédiction
print("\n4. Test de prédiction...")
y_pred = model.predict(t)
prediction_error = np.sqrt(np.mean((y_true - y_pred)**2))
print(f"   • Erreur RMS vs données vraies (sans bruit): {prediction_error:.6f}")

# Vérifier la forme sech²
print("\n5. Vérification de la forme sech²...")
# Calculer l'intensité d'un mode individuel
mode_0_intensity = model.get_mode_intensity(t, 0)
# Vérifier que le maximum est proche de A
max_intensity = mode_0_intensity.max()
print(f"   • Mode 1 - Maximum théorique (A): {A1:.4f}")
print(f"   • Mode 1 - Maximum calculé:       {max_intensity:.4f}")
print(f"   • Différence:                     {abs(max_intensity - A1):.6f}")

# Test réussi
print("\n" + "="*70)
if rms < 0.02 and prediction_error < 0.02:
    print("✅ TEST RÉUSSI: La formule sech² fonctionne correctement!")
    print(f"   RMS final: {rms:.6f} (seuil: 0.02)")
    print(f"   Erreur prédiction: {prediction_error:.6f} (seuil: 0.02)")
else:
    print("⚠️  ATTENTION: Erreurs supérieures au seuil attendu")
    print(f"   RMS final: {rms:.6f}")
    print(f"   Erreur prédiction: {prediction_error:.6f}")

print("="*70 + "\n")
