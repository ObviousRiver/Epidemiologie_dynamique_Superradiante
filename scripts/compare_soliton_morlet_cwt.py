"""
Comparaison SolitonCWT vs Morlet CWT vs SR vs SIR.

Ce script teste si l'ondelette personnalisée (dérivée de sech) améliore
la détection des modes comparée à l'ondelette de Morlet.

Hypothèse : L'ondelette soliton devrait donner :
1. Meilleure convergence vers les modes SR (Δτ, ΔT plus faibles)
2. Meilleur R² (fit plus fidèle)
3. Modes plus cohérents temporellement
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import sys
import os

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel, SIRModel

# Import des modèles CWT depuis le répertoire models/
sys.path.insert(0, 'models')
from cwt_model import CWTModel
from soliton_cwt_model import SolitonCWTModel


def load_france_data():
    """Charge les données France vague 1."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"

    df = pd.read_csv(url)
    france_data = df[df['Country/Region'] == 'France']

    cumul_cases = france_data.iloc[:, 4:].sum(axis=0)
    df_france = pd.DataFrame({'cases': cumul_cases})
    df_france.index = pd.to_datetime(df_france.index, format='%m/%d/%y')
    df_france = df_france.loc['2020-02-15':'2020-06-30']

    new_cases = df_france['cases'].diff().fillna(0)
    new_cases[new_cases < 0] = 0

    return np.arange(len(new_cases)), new_cases.values, new_cases.index


def analyze_all_models(t_data, y_data, n_modes=3):
    """Analyse avec les 4 modèles."""
    results = {}

    # 1. SuperRadiant (référence)
    print("🔬 SuperRadiant...")
    sr_model = SuperRadiantModel(n_modes=n_modes)
    sr_params, sr_rms = sr_model.fit(t_data, y_data, maxfev=100000)
    sr_fit = sr_model.predict(t_data)

    residuals_sr = y_data - sr_fit
    r2_sr = 1 - (np.sum(residuals_sr**2) / np.sum((y_data - np.mean(y_data))**2))

    results['SR'] = {
        'rms': sr_rms,
        'r2': r2_sr,
        'fit': sr_fit,
        'model': sr_model,
        'modes': sr_model.get_mode_parameters()
    }
    print(f"  ✅ RMS={sr_rms:.0f}, R²={r2_sr:.3f}")

    # 2. SIR
    print("🔬 SIR...")
    sir_model = SIRModel(population=67e6)
    sir_model.fit(t_data, y_data)
    sir_fit = sir_model.predict(t_data)

    # Calculer métriques manuellement
    residuals_sir = y_data - sir_fit
    sir_rms = np.sqrt(np.mean(residuals_sir**2))
    r2_sir = 1 - (np.sum(residuals_sir**2) / np.sum((y_data - np.mean(y_data))**2))

    results['SIR'] = {
        'rms': sir_rms,
        'r2': r2_sir,
        'fit': sir_fit
    }
    print(f"  ✅ RMS={sir_rms:.0f}, R²={r2_sir:.3f}")

    # 3. Morlet CWT (version améliorée)
    print("🔬 Morlet CWT (v2 amélioré)...")
    morlet_cwt = CWTModel(
        n_modes=n_modes,
        threshold_factor=1.2,
        min_time_separation=8
    )
    morlet_rms = morlet_cwt.fit(t_data, y_data)
    morlet_fit = morlet_cwt.predict(t_data)
    morlet_quality = morlet_cwt.get_fit_quality(t_data, y_data)

    results['Morlet_CWT'] = {
        'rms': morlet_quality['rms'],
        'r2': morlet_quality['r2'],
        'fit': morlet_fit,
        'model': morlet_cwt,
        'modes': morlet_cwt.get_mode_parameters()
    }
    print(f"  ✅ RMS={morlet_quality['rms']:.0f}, R²={morlet_quality['r2']:.3f}, Modes détectés: {len(morlet_cwt.get_mode_parameters())}")

    # 4. Soliton CWT (NOUVEAU)
    print("🔬 Soliton CWT (ondelette personnalisée)...")
    soliton_cwt = SolitonCWTModel(
        n_modes=n_modes,
        scale_range=(2, 40),
        n_scales=80,
        # threshold_factor uses default (0.8) for better detection
        min_time_separation=8
    )
    soliton_rms = soliton_cwt.fit(t_data, y_data)
    soliton_fit = soliton_cwt.predict(t_data)
    soliton_quality = soliton_cwt.get_fit_quality(t_data, y_data)

    results['Soliton_CWT'] = {
        'rms': soliton_quality['rms'],
        'r2': soliton_quality['r2'],
        'fit': soliton_fit,
        'model': soliton_cwt,
        'modes': soliton_cwt.get_mode_parameters()
    }
    print(f"  ✅ RMS={soliton_quality['rms']:.0f}, R²={soliton_quality['r2']:.3f}, Modes détectés: {len(soliton_cwt.get_mode_parameters())}")

    # Comparaisons SR-CWT
    print("\n📊 Comparaison SR ↔ Morlet CWT:")
    if len(morlet_cwt.get_mode_parameters()) > 0:
        comp_morlet = morlet_cwt.compare_with_sr_modes(sr_model)
        results['comparison_morlet'] = comp_morlet
        for mc in comp_morlet['mode_comparison']:
            print(f"  Mode {mc['mode_index']+1}: Δτ={abs(mc['delta_tau']):.1f}j, ΔT={abs(mc['delta_T']):.1f}j")

    print("\n📊 Comparaison SR ↔ Soliton CWT:")
    if len(soliton_cwt.get_mode_parameters()) > 0:
        comp_soliton = soliton_cwt.compare_with_sr_modes(sr_model)
        results['comparison_soliton'] = comp_soliton
        for mc in comp_soliton['mode_comparison']:
            print(f"  Mode {mc['mode_index']+1}: Δτ={abs(mc['delta_tau']):.1f}j, ΔT={abs(mc['delta_T']):.1f}j, Corrélation={mc['correlation_strength']:.1f}")

    return results


def plot_comparison(t_data, y_data, dates, results, output_dir):
    """Génère figure comparative complète."""
    fig = plt.figure(figsize=(18, 12))
    gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

    # Subplot 1: Comparaison des fits
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(t_data, y_data, 'o', color='black', markersize=3, alpha=0.6, label='Données réelles')
    ax1.plot(t_data, results['SR']['fit'], '-', color='#FF6B6B', linewidth=2.5,
            label=f"SR (R²={results['SR']['r2']:.3f})")
    ax1.plot(t_data, results['SIR']['fit'], '--', color='purple', linewidth=2,
            label=f"SIR (R²={results['SIR']['r2']:.3f})")
    ax1.plot(t_data, results['Morlet_CWT']['fit'], '-.', color='#4ECDC4', linewidth=2,
            label=f"Morlet CWT (R²={results['Morlet_CWT']['r2']:.3f})")
    ax1.plot(t_data, results['Soliton_CWT']['fit'], ':', color='#FFE66D', linewidth=3,
            label=f"Soliton CWT (R²={results['Soliton_CWT']['r2']:.3f})")

    ax1.set_title('Comparaison des Reconstructions : SR vs SIR vs Morlet CWT vs Soliton CWT',
                 fontsize=14, fontweight='bold')
    ax1.set_xlabel('Jours depuis 15/02/2020', fontsize=12)
    ax1.set_ylabel('Nouveaux cas quotidiens', fontsize=12)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Subplot 2: Décomposition SR
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(t_data, y_data, 'o', color='black', markersize=2, alpha=0.5, label='Données')
    colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3']
    for i, mode in enumerate(results['SR']['modes']):
        mode_fit = results['SR']['model'].get_mode_intensity(t_data, i)
        ax2.plot(t_data, mode_fit, '--', color=colors[i % len(colors)], linewidth=1.5,
                label=f"SR Mode {i+1} (τ={mode['tau']:.1f}j, T={mode['T']:.1f}j)")
    ax2.plot(t_data, results['SR']['fit'], '-', color='black', linewidth=2, label='SR Total')

    ax2.set_title('SR: Décomposition en Modes', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Jours depuis 15/02/2020')
    ax2.set_ylabel('Nouveaux cas quotidiens')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Subplot 3: Décomposition Morlet CWT
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(t_data, y_data, 'o', color='black', markersize=2, alpha=0.5, label='Données')
    for i, mode in enumerate(results['Morlet_CWT']['modes']):
        mode_fit = results['Morlet_CWT']['model'].get_mode_intensity(t_data, i)
        ax3.plot(t_data, mode_fit, '--', color=colors[i % len(colors)], linewidth=1.5,
                label=f"Morlet Mode {i+1} (τ={mode['tau']:.1f}j, T={mode['T']:.1f}j)")
    ax3.plot(t_data, results['Morlet_CWT']['fit'], '-', color='#4ECDC4', linewidth=2, label='Morlet Total')

    ax3.set_title('Morlet CWT: Décomposition en Modes', fontsize=12, fontweight='bold')
    ax3.set_xlabel('Jours depuis 15/02/2020')
    ax3.set_ylabel('Nouveaux cas quotidiens')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # Subplot 4: Décomposition Soliton CWT
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.plot(t_data, y_data, 'o', color='black', markersize=2, alpha=0.5, label='Données')
    for i, mode in enumerate(results['Soliton_CWT']['modes']):
        mode_fit = results['Soliton_CWT']['model'].get_mode_intensity(t_data, i)
        ax4.plot(t_data, mode_fit, '--', color=colors[i % len(colors)], linewidth=1.5,
                label=f"Soliton Mode {i+1} (τ={mode['tau']:.1f}j, T={mode['T']:.1f}j)")
    ax4.plot(t_data, results['Soliton_CWT']['fit'], '-', color='#FFE66D', linewidth=2, label='Soliton Total')

    ax4.set_title('Soliton CWT: Décomposition en Modes (Ondelette Personnalisée)', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Jours depuis 15/02/2020')
    ax4.set_ylabel('Nouveaux cas quotidiens')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # Subplot 5: Résidus
    ax5 = fig.add_subplot(gs[2, 1])
    residuals_sr = y_data - results['SR']['fit']
    residuals_morlet = y_data - results['Morlet_CWT']['fit']
    residuals_soliton = y_data - results['Soliton_CWT']['fit']

    ax5.plot(t_data, residuals_sr, '-', color='#FF6B6B', linewidth=1.5, alpha=0.7, label='Résidus SR')
    ax5.plot(t_data, residuals_morlet, '--', color='#4ECDC4', linewidth=1.5, alpha=0.7, label='Résidus Morlet')
    ax5.plot(t_data, residuals_soliton, ':', color='#FFE66D', linewidth=2, alpha=0.7, label='Résidus Soliton')
    ax5.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    ax5.set_title('Comparaison des Résidus', fontsize=12, fontweight='bold')
    ax5.set_xlabel('Jours depuis 15/02/2020')
    ax5.set_ylabel('Résidus')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)

    fig_path = os.path.join(output_dir, 'soliton_vs_morlet_comparison.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ Figure sauvegardée: {fig_path}")
    plt.close()


def main():
    print("="*80)
    print("COMPARAISON SOLITON CWT vs MORLET CWT vs SR vs SIR")
    print("Test de l'Ondelette Personnalisée (dérivée sech)")
    print("="*80 + "\n")

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'soliton_cwt_validation')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Charger données France
    print("📊 Chargement France (vague 1)...")
    t_data, y_data, dates = load_france_data()
    print(f"  ✅ {len(y_data)} points chargés\n")

    # Analyser avec tous les modèles
    results = analyze_all_models(t_data, y_data, n_modes=3)

    # Générer figure comparative
    print("\n📊 Génération figure comparative...")
    plot_comparison(t_data, y_data, dates, results, output_dir)

    # Tableau récapitulatif
    summary = pd.DataFrame({
        'Modèle': ['SR', 'SIR', 'Morlet_CWT', 'Soliton_CWT'],
        'RMS': [results['SR']['rms'], results['SIR']['rms'],
                results['Morlet_CWT']['rms'], results['Soliton_CWT']['rms']],
        'R²': [results['SR']['r2'], results['SIR']['r2'],
               results['Morlet_CWT']['r2'], results['Soliton_CWT']['r2']],
        'N_modes': [len(results['SR']['modes']), 1,
                    len(results['Morlet_CWT']['modes']), len(results['Soliton_CWT']['modes'])]
    })

    csv_path = os.path.join(output_dir, 'comparison_summary.csv')
    summary.to_csv(csv_path, index=False)

    print("\n" + "="*80)
    print("TABLEAU RÉCAPITULATIF")
    print("="*80)
    print(summary.to_string(index=False))

    print(f"\n✅ Résultats sauvegardés: {output_dir}")

    # Verdict
    print("\n" + "="*80)
    print("VERDICT : SOLITON CWT vs MORLET CWT")
    print("="*80)

    improvement_rms = (results['Morlet_CWT']['rms'] - results['Soliton_CWT']['rms']) / results['Morlet_CWT']['rms'] * 100
    improvement_r2 = results['Soliton_CWT']['r2'] - results['Morlet_CWT']['r2']

    print(f"\n📈 Amélioration RMS: {improvement_rms:+.1f}% {'✅' if improvement_rms > 0 else '❌'}")
    print(f"📈 Amélioration R²: {improvement_r2:+.3f} {'✅' if improvement_r2 > 0 else '❌'}")

    if results['Soliton_CWT']['r2'] > results['Morlet_CWT']['r2']:
        print("\n🎉 SOLITON CWT SUPÉRIEUR À MORLET CWT !")
        print("   L'ondelette personnalisée améliore la détection des modes sech²")
    else:
        print("\n⚠️  Morlet CWT reste meilleur (optimisations Soliton nécessaires)")


if __name__ == '__main__':
    main()
