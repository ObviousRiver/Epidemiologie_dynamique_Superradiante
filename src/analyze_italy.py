#!/usr/bin/env python3
"""
Script refactorisé pour l'analyse super-radiante de la première vague COVID-19 en Italie.

Ce script utilise les modules pour une analyse complète:
- Téléchargement et prétraitement des données
- Ajustement des modèles super-radiant et SIR
- Visualisation et analyse comparative
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt

from models import SuperRadiantModel, SIRModel
from data_loader import load_italy_wave1
from visualization import (
    plot_model_comparison,
    plot_mode_decomposition,
    print_analysis_summary,
    create_report_figure
)


def main(n_modes=4, save_figures=True, output_dir='../reports'):
    """
    Fonction principale d'analyse.

    Args:
        n_modes (int): Nombre de modes super-radiants
        save_figures (bool): Sauvegarder les figures
        output_dir (str): Répertoire de sortie pour les figures
    """
    print("="*70)
    print("ANALYSE SUPER-RADIANTE - COVID-19 ITALIE (Vague 1)")
    print("="*70)

    # ===== ÉTAPE 1 : CHARGEMENT DES DONNÉES =====
    print("\n[1/4] Chargement et prétraitement des données...")
    try:
        t_data, y_data, dates = load_italy_wave1()
        t_data = np.array(list(t_data))
    except Exception as e:
        print(f"❌ Erreur lors du chargement des données: {e}")
        return

    # ===== ÉTAPE 2 : AJUSTEMENT DU MODÈLE SUPER-RADIANT =====
    print(f"\n[2/4] Ajustement du modèle Super-Radiant ({n_modes} modes)...")
    sr_model = SuperRadiantModel(n_modes=n_modes)

    try:
        params_sr, rms_sr = sr_model.fit(t_data, y_data)
        print(f"✅ Ajustement terminé. Erreur RMS: {rms_sr:.4f}")

        # Afficher les paramètres
        modes = sr_model.get_mode_parameters()
        print("\nParamètres des modes (triés par τ croissant):")
        for mode in modes:
            print(f"  Mode {mode['mode']}: "
                  f"A={mode['A']:.3f}, "
                  f"τ={mode['tau']:.2f} jours, "
                  f"T={mode['T']:.2f} jours")

    except Exception as e:
        print(f"❌ Erreur lors de l'ajustement super-radiant: {e}")
        return

    # ===== ÉTAPE 3 : AJUSTEMENT DU MODÈLE SIR =====
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
        return

    # ===== ÉTAPE 4 : VISUALISATION ET ANALYSE =====
    print("\n[4/4] Génération des visualisations...")

    # Prédictions
    y_fit_sr = sr_model.predict(t_data)
    y_fit_sir = sir_model.predict(t_data, y_data.max())

    # Graphique de comparaison
    save_path_main = f"{output_dir}/italy_wave1_{n_modes}modes.png" if save_figures else None
    plot_model_comparison(
        t_data, y_data, y_fit_sr, y_fit_sir,
        rms_sr, rms_sir, n_modes=n_modes,
        title="Validation COVID-19 Vague 1 (Italie)",
        save_path=save_path_main
    )

    # Décomposition en modes
    save_path_modes = f"{output_dir}/italy_modes_decomposition_{n_modes}.png" if save_figures else None
    plot_mode_decomposition(t_data, sr_model, save_path=save_path_modes)

    # Rapport complet
    save_path_report = f"{output_dir}/italy_full_report_{n_modes}modes.png" if save_figures else None
    create_report_figure(
        t_data, y_data, sr_model, sir_model,
        rms_sr, rms_sir,
        save_path=save_path_report
    )

    # Afficher le résumé textuel
    print_analysis_summary(sr_model, sir_model, rms_sr, rms_sir)

    # Afficher les graphiques
    if not save_figures:
        plt.show()

    print("✅ Analyse terminée avec succès!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyse super-radiante de la première vague COVID-19 en Italie"
    )
    parser.add_argument(
        '--modes', '-m',
        type=int,
        default=4,
        help='Nombre de modes super-radiants (défaut: 4)'
    )
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Ne pas sauvegarder les figures (affichage uniquement)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='../reports',
        help='Répertoire de sortie pour les figures (défaut: ../reports)'
    )

    args = parser.parse_args()

    main(
        n_modes=args.modes,
        save_figures=not args.no_save,
        output_dir=args.output
    )
