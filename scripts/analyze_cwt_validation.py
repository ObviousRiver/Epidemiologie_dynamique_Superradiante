"""
Analyse comparative SR vs SIR vs CWT pour validation non-paramétrique.

Ce script compare trois approches pour la modélisation épidémiologique:
1. SuperRadiantModel (SR): Ajustement paramétrique global avec n modes sech²
2. SIRModel: Modèle compartimentel classique
3. CWTModel: Identification non-paramétrique des modes via ondelettes

Objectif: Vérifier si la décomposition CWT (data-driven) converge vers
les mêmes modes que le modèle SR (théorique), validant ainsi l'hypothèse
de décomposition en modes super-radiants.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour génération fichiers
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, 'src/core')

from models import SuperRadiantModel, SIRModel, CWTModel


def load_france_national_data():
    """
    Charge les données France nationale (vague 1).

    Returns:
        tuple: (t_data, y_data, dates)
    """
    # Charger depuis JHU (cas confirmés)
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"

    df = pd.read_csv(url)
    france_data = df[df['Country/Region'] == 'France']

    # Sommer toutes les régions (colonnes 4 onwards sont les dates)
    cumul_cases = france_data.iloc[:, 4:].sum(axis=0)

    # Créer DataFrame avec dates
    df_france = pd.DataFrame({'cases': cumul_cases})
    df_france.index = pd.to_datetime(df_france.index, format='%m/%d/%y')

    # Filtrer vague 1 (15 février - 30 juin 2020)
    df_france = df_france.loc['2020-02-15':'2020-06-30']

    # Calculer nouveaux cas quotidiens
    new_cases = df_france['cases'].diff().fillna(0)
    new_cases[new_cases < 0] = 0

    y_data = new_cases.values
    t_data = np.arange(len(y_data))
    dates = new_cases.index

    return t_data, y_data, dates


def analyze_with_all_models(t_data, y_data, n_modes=4):
    """
    Analyse les données avec les 3 modèles.

    Args:
        t_data (array): Temps
        y_data (array): Données observées
        n_modes (int): Nombre de modes pour SR et CWT

    Returns:
        dict: Résultats des 3 modèles
    """
    results = {}

    # 1. SuperRadiant Model
    print("🔬 Ajustement SuperRadiant Model...")
    sr_model = SuperRadiantModel(n_modes=n_modes)
    sr_params, sr_rms = sr_model.fit(t_data, y_data, maxfev=100000)  # Augmenter maxfev
    sr_fit = sr_model.predict(t_data)  # predict() utilise self.params

    # Calculer métriques de qualité manuellement
    residuals_sr = y_data - sr_fit
    nrmse_sr = (sr_rms / np.mean(y_data)) * 100
    ss_res_sr = np.sum(residuals_sr**2)
    ss_tot_sr = np.sum((y_data - np.mean(y_data))**2)
    r2_sr = 1 - (ss_res_sr / ss_tot_sr)

    sr_quality = {
        'rms': sr_rms,
        'nrmse': nrmse_sr,
        'r2': r2_sr
    }

    results['SR'] = {
        'model': sr_model,
        'params': sr_params,
        'fit': sr_fit,
        'rms': sr_rms,
        'quality': sr_quality,
        'modes': sr_model.get_mode_parameters()
    }
    print(f"  ✅ SR: RMS={sr_rms:.2f}, R²={sr_quality['r2']:.4f}")

    # 2. SIR Model
    print("🔬 Ajustement SIR Model...")
    sir_model = SIRModel(population=67e6)  # France
    sir_model.fit(t_data, y_data)
    sir_fit = sir_model.predict(t_data)
    sir_quality = sir_model.get_fit_quality(t_data, y_data)
    sir_params = sir_model.get_parameters()

    results['SIR'] = {
        'model': sir_model,
        'fit': sir_fit,
        'quality': sir_quality,
        'params': sir_params
    }
    print(f"  ✅ SIR: RMS={sir_quality['rms']:.2f}, R²={sir_quality['r2']:.4f}, R0={sir_params['R0']:.2f}")

    # 3. CWT Model (VERSION AMÉLIORÉE)
    print("🔬 Ajustement CWT Model (algorithme amélioré)...")
    cwt_model = CWTModel(
        n_modes=n_modes,
        wavelet='morl',
        threshold_factor=1.2,  # Réduit pour détecter plus de modes
        min_time_separation=8  # Force séparation temporelle 8 jours minimum
    )
    cwt_rms = cwt_model.fit(t_data, y_data)
    cwt_fit = cwt_model.predict(t_data)
    cwt_quality = cwt_model.get_fit_quality(t_data, y_data)

    results['CWT'] = {
        'model': cwt_model,
        'fit': cwt_fit,
        'rms': cwt_rms,
        'quality': cwt_quality,
        'modes': cwt_model.get_mode_parameters()
    }
    print(f"  ✅ CWT: RMS={cwt_rms:.2f}, R²={cwt_quality['r2']:.4f}")

    # 4. Comparaison SR vs CWT
    print("\n📊 Comparaison SR vs CWT:")
    comparison = cwt_model.compare_with_sr_modes(sr_model)

    print(f"  Nombre de modes: CWT={comparison['n_modes_cwt']}, SR={comparison['n_modes_sr']}")
    for mode_comp in comparison['mode_comparison']:
        print(f"  Mode {mode_comp['mode_index']+1}:")
        print(f"    τ (temps pic): CWT={mode_comp['cwt_tau']:.1f}j, SR={mode_comp['sr_tau']:.1f}j, Δ={mode_comp['delta_tau']:.1f}j")
        print(f"    T (largeur):   CWT={mode_comp['cwt_T']:.1f}j, SR={mode_comp['sr_T']:.1f}j, Δ={mode_comp['delta_T']:.1f}j")
        print(f"    A (amplitude): CWT={mode_comp['cwt_A']:.1f}, SR={mode_comp['sr_A']:.1f}, Ratio={mode_comp['ratio_A']:.2f}")

    results['comparison'] = comparison

    return results


def plot_figure_8_cwt_decomposition(t_data, y_data, dates, results, output_path):
    """
    Figure 8: Décomposition en modes par CWT.

    Montre:
    - Données réelles
    - Reconstruction totale CWT
    - Modes individuels CWT
    - Comparaison avec SR
    """
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

    cwt_model = results['CWT']['model']
    sr_model = results['SR']['model']

    # Subplot 1: Décomposition modes CWT
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(t_data, y_data, 'o', color='black', markersize=4, alpha=0.6, label='Données réelles')

    # Modes individuels CWT
    colors_cwt = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3']
    for i, mode in enumerate(results['CWT']['modes']):
        mode_curve = cwt_model.get_mode_intensity(t_data, i)
        ax1.plot(t_data, mode_curve, '--', color=colors_cwt[i % len(colors_cwt)],
                linewidth=2, alpha=0.7,
                label=f'Mode CWT {i+1} (τ={mode["tau"]:.1f}j, T={mode["T"]:.1f}j)')

    # Reconstruction totale CWT
    ax1.plot(t_data, results['CWT']['fit'], '-', color='purple', linewidth=2.5,
            label=f'Total CWT (RMS={results["CWT"]["rms"]:.2f})')

    ax1.set_title('Figure 8a: Décomposition en Modes par CWT (Continuous Wavelet Transform)',
                 fontsize=14, fontweight='bold')
    ax1.set_xlabel('Jours depuis 15/02/2020', fontsize=12)
    ax1.set_ylabel('Nouveaux cas quotidiens', fontsize=12)
    ax1.legend(loc='upper right', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Subplot 2: Comparaison CWT vs SR (fits totaux)
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(t_data, y_data, 'o', color='black', markersize=3, alpha=0.6, label='Données')
    ax2.plot(t_data, results['SR']['fit'], '-', color='#FF6B6B', linewidth=2.5,
            label=f'SR (RMS={results["SR"]["rms"]:.2f})')
    ax2.plot(t_data, results['CWT']['fit'], '--', color='#4ECDC4', linewidth=2.5,
            label=f'CWT (RMS={results["CWT"]["rms"]:.2f})')
    ax2.plot(t_data, results['SIR']['fit'], '-.', color='purple', linewidth=2.5,
            label=f'SIR (RMS={results["SIR"]["quality"]["rms"]:.2f})')

    ax2.set_title('Figure 8b: Comparaison Reconstructions SR vs CWT vs SIR',
                 fontsize=12, fontweight='bold')
    ax2.set_xlabel('Jours depuis 15/02/2020', fontsize=11)
    ax2.set_ylabel('Nouveaux cas quotidiens', fontsize=11)
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3)

    # Subplot 3: Résidus SR vs CWT
    ax3 = fig.add_subplot(gs[1, 1])
    residuals_sr = y_data - results['SR']['fit']
    residuals_cwt = y_data - results['CWT']['fit']

    ax3.plot(t_data, residuals_sr, '-', color='#FF6B6B', linewidth=1.5, alpha=0.7, label='Résidus SR')
    ax3.plot(t_data, residuals_cwt, '--', color='#4ECDC4', linewidth=1.5, alpha=0.7, label='Résidus CWT')
    ax3.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    ax3.set_title('Figure 8c: Résidus SR vs CWT', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Jours depuis 15/02/2020', fontsize=11)
    ax3.set_ylabel('Résidus', fontsize=11)
    ax3.legend(loc='upper right', fontsize=9)
    ax3.grid(True, alpha=0.3)

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Figure 8 sauvegardée: {output_path}")
    plt.close()


def plot_figure_9_scalogram(t_data, y_data, dates, results, output_path):
    """
    Figure 9: Scalogramme CWT (temps-échelle).

    Montre l'analyse temps-échelle complète avec identification des modes.
    """
    cwt_model = results['CWT']['model']
    coefficients, scales, frequencies = cwt_model.get_scalogram()

    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

    # Subplot 1: Scalogramme complet
    ax1 = fig.add_subplot(gs[0, :])

    # Convertir échelles en périodes temporelles (en jours)
    dt = np.mean(np.diff(t_data))
    periods = 1 / (frequencies + 1e-10)  # Éviter division par zéro

    # Scalogramme avec échelle log pour les périodes
    im = ax1.contourf(t_data, periods, np.abs(coefficients),
                     levels=50, cmap='viridis', extend='both')

    # Marquer les modes identifiés
    for i, mode in enumerate(results['CWT']['modes']):
        ax1.plot(mode['tau'], 1/(frequencies[mode['scale_idx']] + 1e-10),
                'r*', markersize=20, markeredgecolor='white', markeredgewidth=2,
                label=f'Mode {i+1}' if i == 0 else '')

    ax1.set_title('Figure 9a: Scalogramme CWT (Temps-Échelle)',
                 fontsize=14, fontweight='bold')
    ax1.set_xlabel('Jours depuis 15/02/2020', fontsize=12)
    ax1.set_ylabel('Période (jours)', fontsize=12)
    ax1.set_yscale('log')
    ax1.set_ylim([3, 80])
    cbar = plt.colorbar(im, ax=ax1)
    cbar.set_label('|Coefficients CWT|', fontsize=11)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3, which='both')

    # Subplot 2: Coupe temporelle (échelle fixée au mode dominant)
    ax2 = fig.add_subplot(gs[1, 0])

    # Trouver le mode avec la plus grande amplitude
    dominant_mode_idx = np.argmax([m['A'] for m in results['CWT']['modes']])
    dominant_scale = results['CWT']['modes'][dominant_mode_idx]['scale_idx']

    ax2.plot(t_data, np.abs(coefficients[dominant_scale, :]), '-', color='#4ECDC4', linewidth=2)
    ax2.axvline(results['CWT']['modes'][dominant_mode_idx]['tau'],
               color='red', linestyle='--', linewidth=2, label=f'Mode dominant (τ={results["CWT"]["modes"][dominant_mode_idx]["tau"]:.1f}j)')

    ax2.set_title(f'Figure 9b: Coupe Temporelle (Période ≈ {1/(frequencies[dominant_scale]+1e-10):.1f}j)',
                 fontsize=12, fontweight='bold')
    ax2.set_xlabel('Jours depuis 15/02/2020', fontsize=11)
    ax2.set_ylabel('|Coefficients CWT|', fontsize=11)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    # Subplot 3: Distribution des modes dans l'espace temps-échelle
    ax3 = fig.add_subplot(gs[1, 1])

    mode_taus = [m['tau'] for m in results['CWT']['modes']]
    mode_periods = [1/(frequencies[m['scale_idx']] + 1e-10) for m in results['CWT']['modes']]
    mode_amps = [m['A'] for m in results['CWT']['modes']]

    # Normaliser les amplitudes pour le scatter
    mode_amps_norm = np.array(mode_amps) / np.max(mode_amps) * 500

    scatter = ax3.scatter(mode_taus, mode_periods, s=mode_amps_norm, c=range(len(mode_taus)),
                         cmap='rainbow', alpha=0.7, edgecolors='black', linewidth=2)

    for i, (tau, period, amp) in enumerate(zip(mode_taus, mode_periods, mode_amps)):
        ax3.annotate(f'M{i+1}', (tau, period), fontsize=10, fontweight='bold',
                    ha='center', va='center')

    ax3.set_title('Figure 9c: Distribution des Modes CWT', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Temps du pic τ (jours)', fontsize=11)
    ax3.set_ylabel('Période (jours)', fontsize=11)
    ax3.set_yscale('log')
    ax3.set_ylim([3, 80])
    ax3.grid(True, alpha=0.3, which='both')

    # Légende pour les tailles
    handles, labels = scatter.legend_elements(prop="sizes", alpha=0.6, num=4)
    ax3.legend(handles, labels, loc="upper right", title="Amplitude", fontsize=9)

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Figure 9 sauvegardée: {output_path}")
    plt.close()


def generate_comparison_table(results, output_path):
    """
    Génère un tableau CSV de comparaison SR vs CWT vs SIR.
    """
    data = {
        'Modèle': ['SR', 'CWT', 'SIR'],
        'RMS': [
            results['SR']['rms'],
            results['CWT']['rms'],
            results['SIR']['quality']['rms']
        ],
        'NRMSE_%': [
            results['SR']['quality']['nrmse'],
            results['CWT']['quality']['nrmse'],
            results['SIR']['quality']['nrmse']
        ],
        'R²': [
            results['SR']['quality']['r2'],
            results['CWT']['quality']['r2'],
            results['SIR']['quality']['r2']
        ],
        'N_params': [
            len(results['SR']['modes']) * 3,  # 3 params par mode
            len(results['CWT']['modes']) * 3,
            4  # β, γ, I0, scale
        ]
    }

    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)
    print(f"✅ Tableau comparatif sauvegardé: {output_path}")

    return df


def main():
    """
    Fonction principale.
    """
    print("="*80)
    print("ANALYSE COMPARATIVE SR vs SIR vs CWT")
    print("Validation Non-Paramétrique du Modèle Super-Radiant")
    print("="*80 + "\n")

    # Créer répertoire de sortie (chemin absolu)
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'cwt_validation')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Répertoire de sortie: {output_dir}\n")

    # 1. Charger données France nationale
    print("📊 Chargement des données France (vague 1)...")
    t_data, y_data, dates = load_france_national_data()
    print(f"  ✅ {len(y_data)} points chargés ({dates[0].strftime('%d/%m/%Y')} → {dates[-1].strftime('%d/%m/%Y')})\n")

    # 2. Analyser avec les 3 modèles (utiliser 3 modes pour convergence plus rapide)
    results = analyze_with_all_models(t_data, y_data, n_modes=3)

    # 3. Générer Figure 8: Décomposition CWT
    print("\n📊 Génération Figure 8...")
    plot_figure_8_cwt_decomposition(
        t_data, y_data, dates, results,
        os.path.join(output_dir, 'fig8_cwt_decomposition.png')
    )

    # 4. Générer Figure 9: Scalogramme
    print("📊 Génération Figure 9...")
    plot_figure_9_scalogram(
        t_data, y_data, dates, results,
        os.path.join(output_dir, 'fig9_cwt_scalogram.png')
    )

    # 5. Générer tableau comparatif
    print("📊 Génération tableau comparatif...")
    df_comparison = generate_comparison_table(
        results,
        os.path.join(output_dir, 'comparison_sr_cwt_sir.csv')
    )

    # 6. Afficher résumé
    print("\n" + "="*80)
    print("RÉSUMÉ COMPARATIF")
    print("="*80)
    print(df_comparison.to_string(index=False))

    print("\n" + "="*80)
    print("CONVERGENCE SR ↔ CWT")
    print("="*80)
    comparison = results['comparison']
    for mode_comp in comparison['mode_comparison']:
        i = mode_comp['mode_index']
        print(f"\nMode {i+1}:")
        print(f"  Δτ (écart temps pic): {abs(mode_comp['delta_tau']):.1f} jours")
        print(f"  ΔT (écart largeur):   {abs(mode_comp['delta_T']):.1f} jours")
        print(f"  Convergence τ: {'✅ Excellente' if abs(mode_comp['delta_tau']) < 5 else '⚠️ Modérée' if abs(mode_comp['delta_tau']) < 10 else '❌ Faible'}")
        print(f"  Convergence T: {'✅ Excellente' if abs(mode_comp['delta_T']) < 2 else '⚠️ Modérée' if abs(mode_comp['delta_T']) < 5 else '❌ Faible'}")

    print("\n✅ Analyse terminée. Résultats dans:", output_dir)


if __name__ == '__main__':
    main()
