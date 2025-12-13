#!/usr/bin/env python3
"""
Analyse Comparative Exhaustive : UK vs Norway vs Sweden
========================================================

Test de falsifiabilité de la théorie épidémique Super-Radiante sur 3 cas extrêmes :

- **UK** : Lockdown strict + structure monocentrique (Londres)
- **Norway** : Lockdown strict + structure dispersée
- **Sweden** : PAS de lockdown (stratégie immunité collective)

Analyse complète incluant :
1. Fits SR (4 modes) et SIR (DOGBOX)
2. Validation BIC (pénalité complexité)
3. Décomposition en modes individuels
4. Diagrammes de Nyquist (stabilité)
5. Analyse FFT comparative (128 pts, sans zero-padding)
6. Analyse de variance et résidus détaillée
7. Visualisations comparatives multi-pays

Auteur : Analyse automatisée
Date : 12 décembre 2025
Branche : UK-Norway-Sweden-comparison
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, windows
from scipy.integrate import odeint
from pathlib import Path
import sys

# Ajouter le répertoire src/core au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'core'))
from models import SuperRadiantModel, SIRModel

# Configuration
OUTPUT_DIR = Path(__file__).parent.parent / 'results' / 'uk_norway_sweden_comparison'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Paramètres d'analyse
WAVE1_START = '2020-02-15'
WAVE1_END = '2020-06-30'
N_MODES_SR = 4
FFT_SIZE = 128  # 2^7, sans zero-padding

# Métadonnées pays
COUNTRIES_METADATA = {
    'United Kingdom': {
        'name': 'UK',
        'population': 67e6,
        'lockdown': 'Strict (23 mars 2020)',
        'structure': 'Monocentrique (Londres dominant)',
        'color': '#FF6B6B'
    },
    'Norway': {
        'name': 'Norway',
        'population': 5.4e6,
        'lockdown': 'Strict (12 mars 2020)',
        'structure': 'Dispersée (Oslo + villes côtières)',
        'color': '#4ECDC4'
    },
    'Sweden': {
        'name': 'Sweden',
        'population': 10.3e6,
        'lockdown': 'AUCUN (immunité collective)',
        'structure': 'Multi-centres (Stockholm, Göteborg, Malmö)',
        'color': '#FFE66D'
    }
}


def load_country_data(country_name):
    """
    Charge les données COVID-19 pour un pays depuis JHU GitHub.

    Returns:
        t_data: Array temporel (jours)
        y_data: Décès quotidiens lissés 7j
        dates: Index pandas des dates
    """
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    print(f"  Téléchargement {country_name}...")
    df = pd.read_csv(url)

    country_data = df[df['Country/Region'] == country_name]
    if len(country_data) == 0:
        raise ValueError(f"{country_name} non trouvé dans le dataset")

    # Sommer toutes les régions
    cumul_deaths = country_data.iloc[:, 4:].sum(axis=0)

    # Créer DataFrame avec dates
    df_country = pd.DataFrame({'deaths': cumul_deaths})
    df_country.index = pd.to_datetime(df_country.index)

    # Filtrer vague 1
    df_country = df_country.loc[WAVE1_START:WAVE1_END]

    # Décès quotidiens
    daily_deaths = df_country['deaths'].diff().fillna(0).clip(lower=0)

    # Lissage 7 jours
    daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

    t_data = np.arange(len(daily_deaths_smooth))
    y_data = daily_deaths_smooth.values
    dates = df_country.index

    print(f"  ✓ {len(y_data)} points, max={y_data.max():.1f} décès/j")

    return t_data, y_data, dates


def fit_sr_model(t_data, y_data, n_modes=4):
    """Ajuste le modèle SR et retourne paramètres + métriques."""
    sr_model = SuperRadiantModel(n_modes=n_modes)
    fitted_params, rms = sr_model.fit(t_data, y_data)

    # Extraire paramètres (format bloc)
    params = []
    for i in range(n_modes):
        A = fitted_params[i]
        tau = fitted_params[n_modes + i]
        T = fitted_params[2*n_modes + i]
        params.append({'A': A, 'tau': tau, 'T': T})

    # Métriques
    y_fit = sr_model.predict(t_data)
    nrmse = rms / (y_data.max() - y_data.min()) * 100
    ss_res = np.sum((y_data - y_fit)**2)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r2 = 1 - (ss_res / ss_tot)

    return {
        'params': params,
        'y_fit': y_fit,
        'rms': rms,
        'nrmse': nrmse,
        'r2': r2,
        'model': sr_model
    }


def fit_sir_model(t_data, y_data, population):
    """Ajuste le modèle SIR et retourne paramètres + métriques."""
    sir_model = SIRModel(population=population)
    sir_model.fit(t_data, y_data)

    # Métriques
    y_fit = sir_model.predict(t_data)
    rms = np.sqrt(np.mean((y_data - y_fit)**2))
    nrmse = rms / (y_data.max() - y_data.min()) * 100
    ss_res = np.sum((y_data - y_fit)**2)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r2 = 1 - (ss_res / ss_tot)

    # Paramètres épidémiologiques via get_parameters()
    params = sir_model.get_parameters()

    return {
        'y_fit': y_fit,
        'rms': rms,
        'nrmse': nrmse,
        'r2': r2,
        'beta': params['beta'],
        'gamma': params['gamma'],
        'R0': params['R0'],
        'duration_days': params['infection_duration_days'],
        'I0': params['I0'],
        'scale': params['scale'],
        'model': sir_model
    }


def calculate_bic(rms, n_points, k_params):
    """Calcule le BIC : BIC = n*ln(RSS/n) + k*ln(n)"""
    rss = n_points * (rms ** 2)
    bic = n_points * np.log(rss / n_points) + k_params * np.log(n_points)
    return bic


def compute_fft_spectrum_128(y_data, dt=1.0):
    """
    Calcule FFT sur 128 premiers points (sans zero-padding).
    Fenêtrage Hanning + detrending.
    """
    # Tronquer à 128 points
    y_128 = y_data[:128]

    # Detrending
    y_detrended = y_128 - np.mean(y_128)

    # Fenêtrage Hanning
    window = windows.hann(128)
    y_windowed = y_detrended * window

    # FFT
    spectrum = fft(y_windowed, n=128)
    freqs = fftfreq(128, d=dt)

    # Fréquences positives uniquement
    positive_mask = freqs >= 0
    freqs = freqs[positive_mask]
    spectrum = np.abs(spectrum[positive_mask])

    return freqs, spectrum


def compute_nyquist_diagram(sir_model, t_data):
    """
    Calcule diagramme de Nyquist pour analyse de stabilité.

    Représente la dynamique SIR dans le plan (S, I).
    """
    # Simuler trajectoire SIR complète
    N = sir_model.N
    params = sir_model.get_parameters()
    beta = params['beta']
    gamma = params['gamma']

    # Conditions initiales (estimées depuis le fit)
    I0 = params['I0']
    S0 = N - I0
    R0_init = 0

    def sir_derivatives(y, t):
        S, I, R = y
        dS = -beta * S * I / N
        dI = beta * S * I / N - gamma * I
        dR = gamma * I
        return [dS, dI, dR]

    # Intégration
    t_extended = np.linspace(0, max(t_data) * 2, 500)
    solution = odeint(sir_derivatives, [S0, I0, R0_init], t_extended)

    S_trajectory = solution[:, 0]
    I_trajectory = solution[:, 1]

    return S_trajectory, I_trajectory


def analyze_country_complete(country_name):
    """
    Analyse exhaustive d'un pays : SR, SIR, BIC, FFT, Nyquist, variance.
    """
    print(f"\n{'='*70}")
    print(f"ANALYSE COMPLÈTE : {country_name.upper()}")
    print(f"{'='*70}\n")

    metadata = COUNTRIES_METADATA[country_name]

    # 1. Chargement données
    print("📥 CHARGEMENT DONNÉES")
    print("-" * 70)
    t_data, y_data, dates = load_country_data(country_name)
    population = metadata['population']
    print()

    # 2. Fit SR
    print("🔧 AJUSTEMENT SR (4 modes)")
    print("-" * 70)
    sr_results = fit_sr_model(t_data, y_data, n_modes=N_MODES_SR)
    print(f"  RMS = {sr_results['rms']:.2f}")
    print(f"  NRMSE = {sr_results['nrmse']:.2f}%")
    print(f"  R² = {sr_results['r2']:.4f}")
    for i, p in enumerate(sr_results['params'], 1):
        print(f"  Mode {i}: A={p['A']:7.2f}, τ={p['tau']:5.1f}j, T={p['T']:5.1f}j")
    print()

    # 3. Fit SIR
    print("🦠 AJUSTEMENT SIR (DOGBOX)")
    print("-" * 70)
    sir_results = fit_sir_model(t_data, y_data, population)
    print(f"  RMS = {sir_results['rms']:.2f}")
    print(f"  NRMSE = {sir_results['nrmse']:.2f}%")
    print(f"  R² = {sir_results['r2']:.4f}")
    print(f"  R0 = {sir_results['R0']:.2f}")
    print(f"  Durée infection = {sir_results['duration_days']:.1f}j")
    print()

    # 4. Comparaison BIC
    print("📊 VALIDATION BIC")
    print("-" * 70)
    n_points = len(t_data)
    bic_sr = calculate_bic(sr_results['rms'], n_points, k_params=12)
    bic_sir = calculate_bic(sir_results['rms'], n_points, k_params=4)
    delta_bic = bic_sir - bic_sr

    ratio_rms = sir_results['rms'] / sr_results['rms']

    print(f"  BIC SR  = {bic_sr:.2f} (k=12)")
    print(f"  BIC SIR = {bic_sir:.2f} (k=4)")
    print(f"  ΔBIC = {delta_bic:+.2f} (SIR - SR)")
    print(f"  Ratio RMS (SIR/SR) = {ratio_rms:.2f}×")

    if abs(delta_bic) < 2:
        bic_winner = "Équivalents"
    elif delta_bic > 0:
        bic_winner = "SR"
    else:
        bic_winner = "SIR"

    rms_winner = "SR" if ratio_rms > 1 else "SIR"

    print(f"  → RMS Winner: {rms_winner}")
    print(f"  → BIC Winner: {bic_winner}")
    print(f"  → Accord: {'OUI ✓' if rms_winner == bic_winner or bic_winner == 'Équivalents' else 'NON ✗'}")
    print()

    # 5. FFT Analysis (128 pts)
    print("📡 ANALYSE FFT (128 pts, sans zero-padding)")
    print("-" * 70)
    freqs, spectrum = compute_fft_spectrum_128(y_data, dt=1.0)

    # Trouver pic dominant
    peak_idx = np.argmax(spectrum[1:]) + 1  # Ignorer f=0
    peak_freq = freqs[peak_idx]
    peak_period = 1 / peak_freq if peak_freq > 0 else np.inf
    peak_amp = spectrum[peak_idx]

    print(f"  Pic FFT dominant:")
    print(f"    f = {peak_freq:.5f} jour⁻¹")
    print(f"    T = {peak_period:.1f}j")
    print(f"    Amp = {peak_amp:.1f}")
    print()

    # 6. Nyquist Diagram
    print("🔄 DIAGRAMME DE NYQUIST (stabilité SIR)")
    print("-" * 70)
    S_traj, I_traj = compute_nyquist_diagram(sir_results['model'], t_data)
    print(f"  Trajectoire calculée (500 pts)")
    print(f"  S₀ = {S_traj[0]:.0f}")
    print(f"  I_max = {I_traj.max():.0f}")
    print()

    # 7. Analyse de variance
    print("📈 ANALYSE DE VARIANCE")
    print("-" * 70)

    # Variance totale des données
    var_total = np.var(y_data)

    # Variance expliquée par SR
    var_explained_sr = np.var(sr_results['y_fit'])
    var_residuals_sr = np.var(y_data - sr_results['y_fit'])

    # Variance expliquée par SIR
    var_explained_sir = np.var(sir_results['y_fit'])
    var_residuals_sir = np.var(y_data - sir_results['y_fit'])

    print(f"  Variance totale données = {var_total:.2f}")
    print(f"  ")
    print(f"  SR:")
    print(f"    Variance expliquée = {var_explained_sr:.2f} ({var_explained_sr/var_total*100:.1f}%)")
    print(f"    Variance résiduelle = {var_residuals_sr:.2f} ({var_residuals_sr/var_total*100:.1f}%)")
    print(f"  ")
    print(f"  SIR:")
    print(f"    Variance expliquée = {var_explained_sir:.2f} ({var_explained_sir/var_total*100:.1f}%)")
    print(f"    Variance résiduelle = {var_residuals_sir:.2f} ({var_residuals_sir/var_total*100:.1f}%)")
    print()

    # Retourner tous les résultats pour visualisation
    return {
        'country': country_name,
        'metadata': metadata,
        't_data': t_data,
        'y_data': y_data,
        'dates': dates,
        'sr': sr_results,
        'sir': sir_results,
        'bic_sr': bic_sr,
        'bic_sir': bic_sir,
        'delta_bic': delta_bic,
        'ratio_rms': ratio_rms,
        'rms_winner': rms_winner,
        'bic_winner': bic_winner,
        'fft': {'freqs': freqs, 'spectrum': spectrum, 'peak_period': peak_period},
        'nyquist': {'S': S_traj, 'I': I_traj},
        'variance': {
            'total': var_total,
            'sr_explained': var_explained_sr,
            'sr_residual': var_residuals_sr,
            'sir_explained': var_explained_sir,
            'sir_residual': var_residuals_sir
        }
    }


def create_comprehensive_visualizations(results_dict):
    """
    Crée toutes les visualisations comparatives pour les 3 pays.
    """
    print("\n" + "="*70)
    print("GÉNÉRATION VISUALISATIONS COMPARATIVES")
    print("="*70 + "\n")

    countries = list(results_dict.keys())

    # === Figure 1 : Fits temporels comparés ===
    fig1, axes = plt.subplots(3, 2, figsize=(16, 12))

    for idx, country in enumerate(countries):
        res = results_dict[country]
        ax_left = axes[idx, 0]
        ax_right = axes[idx, 1]

        # Graphique gauche : Données + SR fit
        ax_left.plot(res['t_data'], res['y_data'], 'ko', markersize=3, alpha=0.5, label='Données réelles')
        ax_left.plot(res['t_data'], res['sr']['y_fit'], color=res['metadata']['color'], linewidth=2, label=f'Fit SR (4 modes)')

        # Décomposition en modes individuels
        for i, mode_params in enumerate(res['sr']['params'], 1):
            A, tau, T = mode_params['A'], mode_params['tau'], mode_params['T']
            x = (res['t_data'] - tau) / (2.0 * T)
            y_mode = A * (1.0 / np.cosh(x))**2
            ax_left.plot(res['t_data'], y_mode, '--', alpha=0.6, linewidth=1, label=f'Mode {i}')

        ax_left.set_xlabel('Jours depuis 15 fév 2020', fontsize=10)
        ax_left.set_ylabel('Décès quotidiens (lissé 7j)', fontsize=10)
        ax_left.set_title(f'{res["metadata"]["name"]} - Décomposition SR\n' +
                          f'{res["metadata"]["lockdown"]} | {res["metadata"]["structure"]}',
                          fontsize=11, fontweight='bold')
        ax_left.legend(fontsize=8, loc='upper right')
        ax_left.grid(True, alpha=0.3)

        # Graphique droite : Comparaison SR vs SIR
        ax_right.plot(res['t_data'], res['y_data'], 'ko', markersize=3, alpha=0.5, label='Données')
        ax_right.plot(res['t_data'], res['sr']['y_fit'], color=res['metadata']['color'], linewidth=2, label='SR')
        ax_right.plot(res['t_data'], res['sir']['y_fit'], 'r--', linewidth=2, label='SIR')

        ax_right.set_xlabel('Jours depuis 15 fév 2020', fontsize=10)
        ax_right.set_ylabel('Décès quotidiens (lissé 7j)', fontsize=10)
        ax_right.set_title(f'{res["metadata"]["name"]} - SR vs SIR\n' +
                           f'RMS SR={res["sr"]["rms"]:.1f} | SIR={res["sir"]["rms"]:.1f} | ' +
                           f'ΔBIC={res["delta_bic"]:+.1f}',
                           fontsize=11, fontweight='bold')
        ax_right.legend(fontsize=8)
        ax_right.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig1_temporal_fits_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 1 sauvegardée : Fits temporels + décomposition modes")
    plt.close()

    # === Figure 2 : FFT Comparative ===
    fig2, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, country in enumerate(countries):
        res = results_dict[country]
        ax = axes[idx]

        freqs = res['fft']['freqs']
        spectrum = res['fft']['spectrum']

        ax.plot(freqs, spectrum, color=res['metadata']['color'], linewidth=2)
        ax.axvline(1/res['fft']['peak_period'], color='red', linestyle='--', alpha=0.7,
                   label=f'Pic T={res["fft"]["peak_period"]:.1f}j')

        ax.set_xlabel('Fréquence (jour⁻¹)', fontsize=10)
        ax.set_ylabel('Amplitude FFT', fontsize=10)
        ax.set_title(f'{res["metadata"]["name"]} - Spectre FFT\n(128 pts, Hanning, sans zero-padding)',
                     fontsize=11, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 0.15)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig2_fft_comparison.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 2 sauvegardée : Spectres FFT comparés")
    plt.close()

    # === Figure 3 : Diagrammes de Nyquist ===
    fig3, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, country in enumerate(countries):
        res = results_dict[country]
        ax = axes[idx]

        S_traj = res['nyquist']['S']
        I_traj = res['nyquist']['I']

        ax.plot(S_traj, I_traj, color=res['metadata']['color'], linewidth=2)
        ax.plot(S_traj[0], I_traj[0], 'go', markersize=8, label='Début')
        ax.plot(S_traj[-1], I_traj[-1], 'ro', markersize=8, label='Fin')

        ax.set_xlabel('Susceptibles (S)', fontsize=10)
        ax.set_ylabel('Infectés (I)', fontsize=10)
        ax.set_title(f'{res["metadata"]["name"]} - Diagramme de Nyquist\n' +
                     f'R0={res["sir"]["R0"]:.2f} | Durée={res["sir"]["duration_days"]:.1f}j',
                     fontsize=11, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig3_nyquist_diagrams.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 3 sauvegardée : Diagrammes de Nyquist")
    plt.close()

    # === Figure 4 : Résidus et variance ===
    fig4, axes = plt.subplots(3, 2, figsize=(16, 12))

    for idx, country in enumerate(countries):
        res = results_dict[country]
        ax_left = axes[idx, 0]
        ax_right = axes[idx, 1]

        # Résidus SR
        residuals_sr = res['y_data'] - res['sr']['y_fit']
        ax_left.plot(res['t_data'], residuals_sr, color=res['metadata']['color'], linewidth=1)
        ax_left.axhline(0, color='black', linestyle='--', alpha=0.5)
        ax_left.fill_between(res['t_data'], 0, residuals_sr, alpha=0.3, color=res['metadata']['color'])
        ax_left.set_xlabel('Jours', fontsize=10)
        ax_left.set_ylabel('Résidus SR', fontsize=10)
        ax_left.set_title(f'{res["metadata"]["name"]} - Résidus SR\nVariance résiduelle = {res["variance"]["sr_residual"]:.1f}',
                          fontsize=11, fontweight='bold')
        ax_left.grid(True, alpha=0.3)

        # Résidus SIR
        residuals_sir = res['y_data'] - res['sir']['y_fit']
        ax_right.plot(res['t_data'], residuals_sir, 'r-', linewidth=1)
        ax_right.axhline(0, color='black', linestyle='--', alpha=0.5)
        ax_right.fill_between(res['t_data'], 0, residuals_sir, alpha=0.3, color='red')
        ax_right.set_xlabel('Jours', fontsize=10)
        ax_right.set_ylabel('Résidus SIR', fontsize=10)
        ax_right.set_title(f'{res["metadata"]["name"]} - Résidus SIR\nVariance résiduelle = {res["variance"]["sir_residual"]:.1f}',
                           fontsize=11, fontweight='bold')
        ax_right.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig4_residuals_variance.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 4 sauvegardée : Résidus et variance")
    plt.close()

    print()


def create_summary_table_csv(results_dict):
    """Crée tableau récapitulatif CSV."""
    rows = []

    for country, res in results_dict.items():
        row = {
            'Country': res['metadata']['name'],
            'Lockdown': res['metadata']['lockdown'],
            'Structure': res['metadata']['structure'],
            'RMS_SR': res['sr']['rms'],
            'NRMSE_SR_%': res['sr']['nrmse'],
            'R2_SR': res['sr']['r2'],
            'RMS_SIR': res['sir']['rms'],
            'NRMSE_SIR_%': res['sir']['nrmse'],
            'R2_SIR': res['sir']['r2'],
            'R0_SIR': res['sir']['R0'],
            'Duration_SIR_days': res['sir']['duration_days'],
            'BIC_SR': res['bic_sr'],
            'BIC_SIR': res['bic_sir'],
            'Delta_BIC': res['delta_bic'],
            'Ratio_RMS_SIR_SR': res['ratio_rms'],
            'RMS_Winner': res['rms_winner'],
            'BIC_Winner': res['bic_winner'],
            'FFT_Peak_Period_days': res['fft']['peak_period'],
            'Variance_Total': res['variance']['total'],
            'Variance_SR_Explained': res['variance']['sr_explained'],
            'Variance_SR_Residual': res['variance']['sr_residual'],
            'Variance_SIR_Explained': res['variance']['sir_explained'],
            'Variance_SIR_Residual': res['variance']['sir_residual']
        }

        # Ajouter paramètres SR
        for i, mode in enumerate(res['sr']['params'], 1):
            row[f'SR_Mode{i}_A'] = mode['A']
            row[f'SR_Mode{i}_tau'] = mode['tau']
            row[f'SR_Mode{i}_T'] = mode['T']

        rows.append(row)

    df = pd.DataFrame(rows)
    output_path = OUTPUT_DIR / 'summary_table.csv'
    df.to_csv(output_path, index=False, float_format='%.4f')
    print(f"✓ Tableau récapitulatif CSV sauvegardé : {output_path}")

    return df


def main():
    """Fonction principale : analyse complète des 3 pays."""
    print("\n" + "="*70)
    print("ANALYSE COMPARATIVE EXHAUSTIVE : UK vs NORWAY vs SWEDEN")
    print("Test de Falsifiabilité de la Théorie Super-Radiante")
    print("="*70)

    # Analyser les 3 pays
    countries = ['United Kingdom', 'Norway', 'Sweden']
    results_dict = {}

    for country in countries:
        results_dict[country] = analyze_country_complete(country)

    # Créer visualisations
    create_comprehensive_visualizations(results_dict)

    # Créer tableau récapitulatif
    df_summary = create_summary_table_csv(results_dict)

    print("\n" + "="*70)
    print("✅ ANALYSE COMPLÈTE TERMINÉE")
    print("="*70)
    print(f"\n📁 Répertoire outputs : {OUTPUT_DIR}")
    print(f"\nFichiers générés :")
    print(f"  - fig1_temporal_fits_comparison.png")
    print(f"  - fig2_fft_comparison.png")
    print(f"  - fig3_nyquist_diagrams.png")
    print(f"  - fig4_residuals_variance.png")
    print(f"  - summary_table.csv")
    print()


if __name__ == "__main__":
    main()
