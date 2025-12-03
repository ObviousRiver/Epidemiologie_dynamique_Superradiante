#!/usr/bin/env python3
"""
Script de test avec données simulées pour démontrer le modèle super-radiant.
Génère des données synthétiques imitant la première vague COVID-19.
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/home/user/Epid-miologie/src')

from models import SuperRadiantModel, SIRModel
from visualization import (
    plot_model_comparison,
    plot_mode_decomposition,
    print_analysis_summary,
    create_report_figure
)

print("="*70)
print("DEMO - ANALYSE SUPER-RADIANTE AVEC DONNÉES SIMULÉES")
print("="*70)

# ===== GÉNÉRATION DE DONNÉES SIMULÉES =====
print("\n[1/4] Génération de données simulées (imitant COVID-19 Italie)...")

np.random.seed(42)
t_data = np.arange(0, 120)

# Génération de données multi-modes réalistes
def generate_covid_like_data(t):
    """Génère des données imitant la première vague COVID-19"""
    # 4 modes avec paramètres réalistes
    modes = [
        {'A': 0.15, 'tau': 5, 'T': 15},    # Urbain
        {'A': 0.35, 'tau': 12, 'T': 20},   # Péri-urbain
        {'A': 0.30, 'tau': 22, 'T': 18},   # Rural
        {'A': 0.20, 'tau': 35, 'T': 25},   # Isolé
    ]

    intensity = np.zeros_like(t, dtype=float)
    for mode in modes:
        A, tau, T = mode['A'], mode['tau'], mode['T']
        effective_t = np.maximum(t - tau, 0)
        intensity += A * (effective_t**2) * np.exp(-effective_t / T)

    # Ajouter du bruit réaliste
    noise = np.random.normal(0, 0.02, len(t))
    intensity += noise
    intensity = np.maximum(intensity, 0)  # Pas de valeurs négatives

    # Normaliser
    intensity = intensity / intensity[10] if intensity[10] > 0 else intensity

    return intensity

y_data = generate_covid_like_data(t_data)

print(f"✅ Données générées : {len(t_data)} jours")
print(f"   Valeur min: {y_data.min():.3f}, max: {y_data.max():.3f}")

# ===== AJUSTEMENT SUPER-RADIANT =====
print("\n[2/4] Ajustement du modèle Super-Radiant (4 modes)...")

sr_model = SuperRadiantModel(n_modes=4)
try:
    params_sr, rms_sr = sr_model.fit(t_data, y_data, maxfev=50000)
    print(f"✅ Ajustement terminé. Erreur RMS: {rms_sr:.4f}")

    modes = sr_model.get_mode_parameters()
    print("\nParamètres des modes (triés par τ):")
    for mode in modes:
        print(f"  Mode {mode['mode']}: "
              f"A={mode['A']:.3f}, "
              f"τ={mode['tau']:.2f}j, "
              f"T={mode['T']:.2f}j")
except Exception as e:
    print(f"❌ Erreur lors de l'ajustement super-radiant: {e}")
    sys.exit(1)

# ===== AJUSTEMENT SIR =====
print("\n[3/4] Ajustement du modèle SIR (comparaison)...")

sir_model = SIRModel(population=60e6)
try:
    params_sir, rms_sir = sir_model.fit(t_data, y_data)
    print(f"✅ Ajustement terminé. Erreur RMS: {rms_sir:.4f}")

    sir_params = sir_model.get_parameters()
    print(f"\nParamètres SIR:")
    print(f"  β = {sir_params['beta']:.4f}")
    print(f"  γ = {sir_params['gamma']:.4f}")
    print(f"  R₀ = {sir_params['R0']:.2f}")
except Exception as e:
    print(f"❌ Erreur lors de l'ajustement SIR: {e}")
    sys.exit(1)

# ===== VISUALISATION =====
print("\n[4/4] Génération des visualisations...")

y_fit_sr = sr_model.predict(t_data)
y_fit_sir = sir_model.predict(t_data, y_data.max())

# Graphique de comparaison
print("\nCréation du graphique de comparaison...")
plot_model_comparison(
    t_data, y_data, y_fit_sr, y_fit_sir,
    rms_sr, rms_sir, n_modes=4,
    title="DEMO: Modèle Super-Radiant (Données Simulées)",
    save_path='/home/user/Epid-miologie/reports/demo_comparison.png'
)

# Décomposition en modes
print("Création de la décomposition en modes...")
plot_mode_decomposition(
    t_data, sr_model,
    save_path='/home/user/Epid-miologie/reports/demo_modes.png'
)

# Rapport complet
print("Création du rapport complet...")
create_report_figure(
    t_data, y_data, sr_model, sir_model,
    rms_sr, rms_sir,
    save_path='/home/user/Epid-miologie/reports/demo_full_report.png'
)

# Résumé textuel
print_analysis_summary(sr_model, sir_model, rms_sr, rms_sir)

print("\n" + "="*70)
print("✅ DEMO TERMINÉE AVEC SUCCÈS!")
print("="*70)
print("\nFigures sauvegardées dans reports/:")
print("  - demo_comparison.png")
print("  - demo_modes.png")
print("  - demo_full_report.png")
print("\nPour utiliser avec de vraies données COVID-19,")
print("configurez vos credentials Kaggle (voir USAGE.md)")
