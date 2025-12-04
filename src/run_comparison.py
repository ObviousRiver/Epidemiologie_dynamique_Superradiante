#!/usr/bin/env python3
"""
Script de comparaison complète: Super-Radiant vs SIR
Basé sur le modèle théorique Dicke-Ising-Champ

Reproduit la validation empirique du document théorique avec la formule sech² correcte.
"""

import numpy as np
import matplotlib.pyplot as plt
from models import SuperRadiantModel, SIRModel
from data_loader import load_italy_wave1
from visualization import (
    plot_model_comparison,
    plot_mode_decomposition,
    plot_residuals
)

# Configuration Matplotlib
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)


def print_section_header(title):
    """Affiche un en-tête de section formaté."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    """Fonction principale pour la comparaison des modèles."""

    print_section_header("1. CHARGEMENT DES DONNÉES")

    # Chargement des données COVID-19 Italie
    t_data, y_data, dates = load_italy_wave1()
    t_data = np.array(list(t_data))

    print(f"Période: {dates.min().date()} au {dates.max().date()}")
    print(f"Nombre de points: {len(t_data)}")
    print(f"Valeur min: {y_data.min():.3f}, max: {y_data.max():.3f}")

    # Visualisation données brutes
    plt.figure(figsize=(14, 6))
    plt.plot(t_data, y_data, 'ko-', linewidth=2, markersize=4)
    plt.xlabel('Jours depuis le début de la vague', fontsize=12)
    plt.ylabel('Nombre de décès (normalisé)', fontsize=12)
    plt.title('Données COVID-19 - Italie, Première Vague (lissées)',
              fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('../reports/data_raw_italy.png', dpi=150, bbox_inches='tight')
    print("✓ Graphique sauvegardé: reports/data_raw_italy.png")
    plt.show()

    # ========================================================
    print_section_header("2. MODÈLE SUPER-RADIANT (FORMULE SECH²)")

    # Nombre de modes à tester
    N_MODES = 3
    print(f"\nConfiguration: {N_MODES} modes super-radiants")
    print("Formule théorique: I(t) = Σ A_k * sech²((t - τ_k) / (2T_k))")

    # Création et ajustement du modèle
    print("\nAjustement en cours...")
    sr_model = SuperRadiantModel(n_modes=N_MODES)
    params_sr, rms_sr = sr_model.fit(t_data, y_data, maxfev=50000)

    print(f"\n✅ Ajustement terminé!")
    print(f"Erreur RMS: {rms_sr:.4f}")

    # Afficher les paramètres
    modes = sr_model.get_mode_parameters()
    print("\n📊 Paramètres des modes (triés par τ):")
    print("-" * 60)
    print(f"{'Mode':<8} {'Amplitude (A)':<18} {'Délai τ (j)':<15} {'Temps T (j)':<12}")
    print("-" * 60)
    for mode in modes:
        print(f"  {mode['mode']:<6} {mode['A']:>15.3f}    {mode['tau']:>12.2f}    {mode['T']:>10.2f}")
    print("-" * 60)

    # ========================================================
    print_section_header("3. MODÈLE SIR CLASSIQUE")

    print("\nAjustement du modèle SIR...")
    sir_model = SIRModel(population=60e6)
    params_sir, rms_sir = sir_model.fit(t_data, y_data)

    print(f"\n✅ Ajustement terminé!")
    print(f"Erreur RMS: {rms_sir:.4f}")

    # Afficher les paramètres SIR
    sir_params = sir_model.get_parameters()
    print("\n📊 Paramètres SIR:")
    print("-" * 60)
    print(f"  β (transmission):  {sir_params['beta']:.4f}")
    print(f"  γ (récupération):  {sir_params['gamma']:.4f}")
    print(f"  R₀:                {sir_params['R0']:.2f}")
    print(f"  I₀:                {sir_params['I0']:.0f}")
    print("-" * 60)

    # ========================================================
    print_section_header("4. COMPARAISON DES MODÈLES")

    # Générer les prédictions
    y_fit_sr = sr_model.predict(t_data)
    y_fit_sir = sir_model.predict(t_data, y_data.max())

    # Tracer la comparaison
    plot_model_comparison(
        t_data, y_data, y_fit_sr, y_fit_sir,
        rms_sr, rms_sir, n_modes=N_MODES,
        title="Validation COVID-19 Vague 1 (Italie) - Formule sech² Correcte"
    )
    plt.savefig('../reports/comparison_italy_sech2.png', dpi=150, bbox_inches='tight')
    print("✓ Graphique sauvegardé: reports/comparison_italy_sech2.png")
    plt.show()

    # ========================================================
    print_section_header("5. DÉCOMPOSITION EN MODES")

    plot_mode_decomposition(t_data, sr_model)
    plt.savefig('../reports/mode_decomposition_italy.png', dpi=150, bbox_inches='tight')
    print("✓ Graphique sauvegardé: reports/mode_decomposition_italy.png")
    plt.show()

    # ========================================================
    print_section_header("6. ANALYSE DES RÉSIDUS")

    plot_residuals(t_data, y_data, y_fit_sr, y_fit_sir)
    plt.savefig('../reports/residuals_italy.png', dpi=150, bbox_inches='tight')
    print("✓ Graphique sauvegardé: reports/residuals_italy.png")
    plt.show()

    # ========================================================
    print_section_header("7. INTERPRÉTATION SOCIOLOGIQUE")

    # Tableau d'interprétation
    mode_names = ["Urbain", "Péri-urbain", "Rural", "Isolé"]

    print("\n📊 Interprétation des modes:")
    print("-" * 80)
    print(f"{'Mode':<8} {'Type':<15} {'Amplitude':<12} {'Délai τ':<12} {'Temps T':<12}")
    print("-" * 80)
    for i, mode in enumerate(modes):
        mode_type = mode_names[i] if i < len(mode_names) else f"Mode {i+1}"
        print(f"  {mode['mode']:<6} {mode_type:<15} {mode['A']:>9.1f}   {mode['tau']:>9.1f}j   {mode['T']:>9.1f}j")
    print("-" * 80)

    # ========================================================
    print_section_header("8. RÉSUMÉ FINAL")

    improvement = rms_sir / rms_sr
    print(f"\n🎯 PERFORMANCE:")
    print(f"   • Erreur RMS Super-Radiant (sech²): {rms_sr:.4f}")
    print(f"   • Erreur RMS SIR Classique:         {rms_sir:.4f}")
    print(f"\n🏆 Le modèle super-radiant est {improvement:.2f}x plus précis!")

    print(f"\n📈 VALIDATION THÉORIQUE:")
    print(f"   • Formule utilisée: I(t) = Σ A_k * sech²((t - τ_k) / (2T_k))")
    print(f"   • Référence: Document 'Dynamique Radiative des Épidémies'")
    print(f"   • Modèle: Dicke-Ising-Champ unifié")

    print(f"\n✅ Analyse complète terminée!\n")


if __name__ == "__main__":
    main()
