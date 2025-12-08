#!/usr/bin/env python3
"""
Analyse Consolidée COVID-19 - Méthodologie Rigoureuse
======================================================

Combine les approches complémentaires :
1. Fits de modèles (SR multi-modes, SIR classique)
2. Analyse spectrale (FFT, Nyquist, modes propres)
3. Susceptibilité dynamique (variance glissante, signal précurseur)
4. Analyse des résidus (tests statistiques, autocorrélation)

Corrections méthodologiques :
- SIR avec IFR explicite et échelle temporelle rigoureuse
- Documentation des limites (β/γ non-identifiables)
- Analyse spectrale indépendante des modèles paramétriques

Usage :
    python src/analyse_consolidee.py --country Austria --output reports/
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.stats import linregress
from pathlib import Path
import argparse
import sys

# Import des modèles
from models import SuperRadiantModel, SIRModel


# ============================================================================
# CONFIGURATION
# ============================================================================

WAVE1_START = '2020-02-15'
WAVE1_END = '2020-06-30'
WINDOW_VARIANCE = 21  # Fenêtre pour variance glissante (3 semaines)

# Populations des pays (millions)
POPULATIONS = {
    'Austria': 8.9e6,
    'Belgium': 11.5e6,
    'Denmark': 5.8e6,
    'Finland': 5.5e6,
    'France': 67.0e6,
    'Germany': 83.0e6,
    'Ireland': 5.0e6,
    'Italy': 60.0e6,
    'Netherlands': 17.4e6,
    'Norway': 5.4e6,
    'Portugal': 10.3e6,
    'Spain': 47.0e6,
    'Sweden': 10.3e6,
    'Switzerland': 8.6e6,
    'United Kingdom': 67.0e6
}


# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

def load_country_data(country_name):
    """
    Télécharge les données COVID-19 d'un pays depuis GitHub JHU CSSE.

    Args:
        country_name (str): Nom du pays (ex: 'Austria', 'France')

    Returns:
        tuple: (t_data, y_data, dates, max_deaths_raw)
    """
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    print(f"\n📥 Téléchargement données {country_name} depuis GitHub JHU CSSE...")

    try:
        df = pd.read_csv(url)
        country_data = df[df['Country/Region'] == country_name].iloc[:, 4:].sum(axis=0)
        country_df = pd.DataFrame({'deaths': country_data})
        country_df.index = pd.to_datetime(country_df.index)

        # Filtrer Vague 1
        country_df = country_df.loc[WAVE1_START:WAVE1_END]

        # Calculer décès quotidiens
        daily_deaths = country_df['deaths'].diff().fillna(0)
        daily_deaths = daily_deaths.clip(lower=0)  # Enlever valeurs négatives

        # Lissage sur 7 jours (rolling mean centré)
        daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

        # NE PAS normaliser - garder les vraies valeurs pour le SIR avec IFR
        max_deaths_raw = daily_deaths_smooth.max()

        # Préparer données pour ajustement
        t_data = np.arange(len(daily_deaths_smooth))
        y_data = daily_deaths_smooth.values
        dates = country_df.index

        print(f"✅ Données {country_name} chargées : {len(t_data)} points")
        print(f"   Période : {dates[0].strftime('%Y-%m-%d')} → {dates[-1].strftime('%Y-%m-%d')}")
        print(f"   Max décès quotidiens : {int(max_deaths_raw)}")
        print(f"   Population : {POPULATIONS.get(country_name, 'N/A')}")

        return t_data, y_data, dates, max_deaths_raw

    except Exception as e:
        print(f"❌ Erreur : {e}")
        sys.exit(1)


# ============================================================================
# ANALYSE SPECTRALE
# ============================================================================

def analyze_spectrum(t_data, y_data):
    """
    Analyse spectrale FFT pour identifier les modes propres.

    Returns:
        dict: {'freqs', 'power', 'chi_real', 'chi_imag'}
    """
    # Pré-traitement
    y_detrended = y_data - np.mean(y_data)
    window = np.hanning(len(y_data))
    y_windowed = y_detrended * window

    # FFT
    n_fft = 4096
    fft_vals = fft(y_windowed, n=n_fft)
    freqs = fftfreq(n_fft, d=1.0)  # 1 jour

    # Fréquences positives uniquement
    mask = freqs > 0
    freqs = freqs[mask]
    fft_vals = fft_vals[mask]

    # Spectre de puissance et composantes complexes
    power = np.abs(fft_vals)**2
    chi_real = np.real(fft_vals)
    chi_imag = np.imag(fft_vals)

    return {
        'freqs': freqs,
        'power': power,
        'chi_real': chi_real,
        'chi_imag': chi_imag
    }


def calculate_dynamic_susceptibility(t_data, y_data, window=21):
    """
    Calcule la susceptibilité dynamique (variance glissante).

    Returns:
        tuple: (t_chi, chi)
    """
    susceptibility = []
    time = []

    for i in range(window, len(y_data)):
        segment = y_data[i-window : i]
        chi = np.var(segment)
        susceptibility.append(chi)
        time.append(t_data[i])

    return np.array(time), np.array(susceptibility)


# ============================================================================
# AJUSTEMENT DES MODÈLES
# ============================================================================

def fit_all_models(t_data, y_data, population):
    """
    Ajuste tous les modèles : SR 3 modes, SR 4 modes, SIR.

    Returns:
        dict: Modèles ajustés et RMS
    """
    results = {}

    # SR 3 modes
    print("   Ajustement SR 3 modes...")
    sr3 = SuperRadiantModel(n_modes=3)
    try:
        params_sr3, rms_sr3 = sr3.fit(t_data, y_data)
        results['sr3'] = sr3
        results['rms_sr3'] = rms_sr3
        print(f"      ✓ RMS = {rms_sr3:.2f}")
    except Exception as e:
        print(f"      ✗ Échec : {e}")
        results['sr3'] = None
        results['rms_sr3'] = np.inf

    # SR 4 modes
    print("   Ajustement SR 4 modes...")
    sr4 = SuperRadiantModel(n_modes=4)
    try:
        params_sr4, rms_sr4 = sr4.fit(t_data, y_data)
        results['sr4'] = sr4
        results['rms_sr4'] = rms_sr4
        print(f"      ✓ RMS = {rms_sr4:.2f}")
    except Exception as e:
        print(f"      ✗ Échec : {e}")
        results['sr4'] = None
        results['rms_sr4'] = np.inf

    # SIR (avec IFR explicite)
    print("   Ajustement SIR (IFR=0.01)...")
    sir = SIRModel(population=population, IFR=0.01)
    try:
        params_sir, rms_sir = sir.fit(t_data, y_data)
        if params_sir is not None:
            results['sir'] = sir
            results['rms_sir'] = rms_sir
            sir_params = sir.get_parameters()
            print(f"      ✓ RMS = {rms_sir:.2f}")
            print(f"      R0 = {sir_params['R0']:.2f}, Durée infection = {sir_params['infection_duration_days']:.1f} jours")
        else:
            results['sir'] = None
            results['rms_sir'] = np.inf
            print(f"      ✗ Fit échoué")
    except Exception as e:
        print(f"      ✗ Échec : {e}")
        results['sir'] = None
        results['rms_sir'] = np.inf

    return results


# ============================================================================
# ANALYSE DES RÉSIDUS
# ============================================================================

def analyze_residuals(y_data, y_fit):
    """
    Analyse statistique des résidus.

    Returns:
        dict: Statistiques des résidus
    """
    residuals = y_data - y_fit

    return {
        'mean': np.mean(residuals),
        'std': np.std(residuals),
        'max_abs': np.max(np.abs(residuals)),
        'rmse': np.sqrt(np.mean(residuals**2))
    }


# ============================================================================
# VISUALISATION
# ============================================================================

def create_comprehensive_plot(country_name, t_data, y_data, dates, models, spectrum, susceptibility, output_dir):
    """
    Crée une visualisation complète (8 panels).
    """
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Dates pour axe x
    date_labels = [dates[i].strftime('%Y-%m-%d') for i in range(0, len(dates), 20)]
    date_positions = list(range(0, len(dates), 20))

    # === PANEL 1 : Signal temporel + Fits ===
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(t_data, y_data, 'o', markersize=3, alpha=0.5, label='Données', color='black')

    if models['sr3'] is not None:
        y_sr3 = models['sr3'].predict(t_data)
        ax1.plot(t_data, y_sr3, '--', lw=2, label=f"SR 3 modes (RMS={models['rms_sr3']:.1f})", color='blue')

    if models['sr4'] is not None:
        y_sr4 = models['sr4'].predict(t_data)
        ax1.plot(t_data, y_sr4, '-', lw=2, label=f"SR 4 modes (RMS={models['rms_sr4']:.1f})", color='green')

    ax1.set_title(f"1. Signal Temporel - {country_name}", fontweight='bold')
    ax1.set_xlabel("Jours")
    ax1.set_ylabel("Décès quotidiens")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)
    ax1.set_xticks(date_positions)
    ax1.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=7)

    # === PANEL 2 : SR vs SIR ===
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(t_data, y_data, 'o', markersize=3, alpha=0.5, label='Données', color='black')

    best_sr = models['sr4'] if models['rms_sr4'] < models['rms_sr3'] else models['sr3']
    best_rms_sr = min(models['rms_sr3'], models['rms_sr4'])

    if best_sr is not None:
        y_sr = best_sr.predict(t_data)
        ax2.plot(t_data, y_sr, '--', lw=2, label=f"SR (RMS={best_rms_sr:.1f})", color='blue')

    if models['sir'] is not None:
        y_sir = models['sir'].predict(t_data)
        ax2.plot(t_data, y_sir, ':', lw=2, label=f"SIR (RMS={models['rms_sir']:.1f})", color='red')

    ax2.set_title("2. Super-Radiant vs SIR", fontweight='bold')
    ax2.set_xlabel("Jours")
    ax2.set_ylabel("Décès quotidiens")
    ax2.legend(fontsize=9)
    ax2.grid(alpha=0.3)
    ax2.set_xticks(date_positions)
    ax2.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=7)

    # === PANEL 3 : Décomposition en modes ===
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(t_data, y_data, 'o', markersize=2, alpha=0.4, label='Données', color='black')

    if models['sr4'] is not None:
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        for i in range(4):
            y_mode = models['sr4'].get_mode_intensity(t_data, i)
            ax3.plot(t_data, y_mode, '-', lw=1.5, label=f'Mode {i+1}', color=colors[i], alpha=0.7)

        y_total = models['sr4'].predict(t_data)
        ax3.plot(t_data, y_total, '--', lw=2, label='Total SR', color='blue')

    ax3.set_title("3. Décomposition en modes SR", fontweight='bold')
    ax3.set_xlabel("Jours")
    ax3.set_ylabel("Intensité")
    ax3.legend(fontsize=8, ncol=2)
    ax3.grid(alpha=0.3)
    ax3.set_xticks(date_positions)
    ax3.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=7)

    # === PANEL 4 : Résidus SR vs SIR ===
    ax4 = fig.add_subplot(gs[1, 0])

    if best_sr is not None:
        res_sr = y_data - best_sr.predict(t_data)
        ax4.plot(t_data, res_sr, 'o-', markersize=2, lw=1, label=f"Résidus SR", color='blue', alpha=0.7)

    if models['sir'] is not None:
        res_sir = y_data - models['sir'].predict(t_data)
        ax4.plot(t_data, res_sir, 'o-', markersize=2, lw=1, label=f"Résidus SIR", color='red', alpha=0.7)

    ax4.axhline(0, color='black', ls='--', lw=1, alpha=0.5)
    ax4.set_title("4. Analyse des résidus", fontweight='bold')
    ax4.set_xlabel("Jours")
    ax4.set_ylabel("Résidus")
    ax4.legend(fontsize=9)
    ax4.grid(alpha=0.3)
    ax4.set_xticks(date_positions)
    ax4.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=7)

    # === PANEL 5 : Spectre de puissance ===
    ax5 = fig.add_subplot(gs[1, 1])

    freqs = spectrum['freqs']
    power = spectrum['power']
    mask_zoom = (freqs > 0.005) & (freqs < 0.15)

    ax5.plot(freqs[mask_zoom], power[mask_zoom], 'r-', lw=2)
    ax5.set_title("5. Spectre de Puissance |χ(ω)|²", fontweight='bold')
    ax5.set_xlabel("Fréquence (jour⁻¹)")
    ax5.set_ylabel("Puissance")
    ax5.grid(alpha=0.3)

    # Axe secondaire période
    secax = ax5.twiny()
    secax.set_xlim(ax5.get_xlim())
    period_ticks = [100, 50, 33, 25, 20, 14, 10, 7]
    freq_ticks = [1/T for T in period_ticks if freqs[mask_zoom].min() <= 1/T <= freqs[mask_zoom].max()]
    if len(freq_ticks) > 0:
        secax.set_xticks(freq_ticks)
        secax.set_xticklabels([str(int(1/f)) for f in freq_ticks], fontsize=8)
        secax.set_xlabel('Période (jours)', fontsize=10)

    # === PANEL 6 : Nyquist (modes rapides) ===
    ax6 = fig.add_subplot(gs[1, 2])

    chi_real = spectrum['chi_real']
    chi_imag = spectrum['chi_imag']
    mask_rapid = (freqs > 0.033) & (freqs < 0.14)  # 7-30 jours

    if np.sum(mask_rapid) > 5:
        ax6.plot(chi_real[mask_rapid], chi_imag[mask_rapid], 'g-', lw=1.5, alpha=0.7)
        ax6.scatter(chi_real[mask_rapid][0], chi_imag[mask_rapid][0], color='green', s=60, marker='o', label='Début', zorder=5)
        ax6.scatter(chi_real[mask_rapid][-1], chi_imag[mask_rapid][-1], color='red', s=60, marker='s', label='Fin', zorder=5)

    ax6.axhline(0, color='k', lw=0.5)
    ax6.axvline(0, color='k', lw=0.5)
    ax6.set_title("6. Nyquist χ'(ω) vs χ''(ω)", fontweight='bold')
    ax6.set_xlabel("χ' (Dispersion)")
    ax6.set_ylabel("χ'' (Absorption)")
    ax6.legend(fontsize=9)
    ax6.grid(alpha=0.3)

    # === PANEL 7 : Susceptibilité dynamique ===
    ax7 = fig.add_subplot(gs[2, 0])

    t_chi, chi = susceptibility
    ax7.plot(t_chi, chi, color='purple', lw=2, label='χ_eff(t)')

    # Pic de susceptibilité
    idx_chi_max = np.argmax(chi)
    t_c = t_chi[idx_chi_max]
    ax7.axvline(t_c, color='red', ls='--', lw=2, label=f'Pic χ (t={t_c:.0f}j)')
    ax7.scatter(t_c, chi[idx_chi_max], color='red', s=150, marker='*', zorder=5)

    # Pic de décès
    idx_deaths_max = np.argmax(y_data)
    t_deaths = t_data[idx_deaths_max]
    ax7.axvline(t_deaths, color='orange', ls=':', lw=2, alpha=0.7, label=f'Pic décès (t={t_deaths:.0f}j)')

    # Avance
    advance = t_deaths - t_c
    if abs(advance) > 0:
        ax7.annotate('', xy=(t_c, chi.max()*0.5), xytext=(t_deaths, chi.max()*0.5),
                    arrowprops=dict(arrowstyle='<->', color='green', lw=2))
        ax7.text((t_c + t_deaths)/2, chi.max()*0.55, f'Avance\n{advance:.0f}j',
                ha='center', fontsize=9, color='green', fontweight='bold')

    ax7.set_title("7. Susceptibilité Dynamique χ_eff(t)", fontweight='bold')
    ax7.set_xlabel("Jours")
    ax7.set_ylabel("Variance glissante")
    ax7.legend(fontsize=9)
    ax7.grid(alpha=0.3)

    # === PANEL 8 : Synthèse régimes ===
    ax8 = fig.add_subplot(gs[2, 1:])
    ax8.axis('off')

    # Tableau synthétique
    summary_text = f"SYNTHÈSE - {country_name}\n" + "="*60 + "\n\n"

    # RMS
    summary_text += "QUALITÉ DES FITS (RMS) :\n"
    summary_text += f"  • SR 3 modes : {models['rms_sr3']:.2f}\n"
    summary_text += f"  • SR 4 modes : {models['rms_sr4']:.2f}\n"
    summary_text += f"  • SIR        : {models['rms_sir']:.2f}\n\n"

    # Ratio
    if models['rms_sir'] < np.inf and best_rms_sr < np.inf:
        ratio = models['rms_sir'] / best_rms_sr
        summary_text += f"RATIO RMS_SIR / RMS_SR : {ratio:.2f}×\n"
        if ratio > 1.5:
            summary_text += "  → RÉGIME SR DOMINANT (ratio > 1.5×) ✅\n\n"
        elif ratio < 0.75:
            summary_text += "  → RÉGIME SIR DOMINANT (ratio < 0.75×)\n\n"
        else:
            summary_text += "  → RÉGIME INTERMÉDIAIRE\n\n"

    # Paramètres SIR
    if models['sir'] is not None:
        sir_params = models['sir'].get_parameters()
        summary_text += "PARAMÈTRES SIR :\n"
        summary_text += f"  • R0 = {sir_params['R0']:.2f}\n"
        summary_text += f"  • Durée infection = {sir_params['infection_duration_days']:.1f} jours\n"
        summary_text += f"  • IFR effectif = {sir_params['IFR_effective']*100:.2f}%\n\n"

    # Signal précurseur
    summary_text += "SIGNAL PRÉCURSEUR :\n"
    summary_text += f"  • Avance pic χ : {advance:+.0f} jours\n"
    if advance > 3:
        summary_text += "  → Signal d'alerte précoce ✅\n"
    elif advance < -3:
        summary_text += "  → Pic χ retardé (pas de signal précurseur)\n"
    else:
        summary_text += "  → Simultané\n"

    ax8.text(0.05, 0.95, summary_text, fontsize=11, verticalalignment='top',
            fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.suptitle(f"Analyse Consolidée COVID-19 - {country_name} - Vague 1 (Mars-Juin 2020)",
                fontsize=16, fontweight='bold')

    # Sauvegarder
    output_path = Path(output_dir) / f"analyse_consolidee_{country_name.replace(' ', '_').lower()}.png"
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    print(f"\n✓ Visualisation sauvegardée : {output_path}")
    plt.close()


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

def analyze_country(country_name, output_dir='reports'):
    """
    Pipeline complet d'analyse pour un pays.
    """
    print(f"\n{'='*80}")
    print(f"ANALYSE CONSOLIDÉE : {country_name.upper()}")
    print(f"{'='*80}")

    # 1. Charger données
    t_data, y_data, dates, max_deaths = load_country_data(country_name)
    population = POPULATIONS.get(country_name, 60e6)

    # 2. Ajuster modèles
    print("\n📊 Ajustement des modèles...")
    models = fit_all_models(t_data, y_data, population)

    # 3. Analyse spectrale
    print("\n🔬 Analyse spectrale...")
    spectrum = analyze_spectrum(t_data, y_data)

    # 4. Susceptibilité dynamique
    print(f"\n⚡ Susceptibilité dynamique (fenêtre {WINDOW_VARIANCE}j)...")
    susceptibility = calculate_dynamic_susceptibility(t_data, y_data, window=WINDOW_VARIANCE)

    # 5. Visualisation
    print("\n📈 Génération visualisation complète...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    create_comprehensive_plot(country_name, t_data, y_data, dates, models, spectrum, susceptibility, output_dir)

    print(f"\n{'='*80}")
    print("ANALYSE TERMINÉE")
    print(f"{'='*80}\n")

    return {
        'country': country_name,
        'models': models,
        'spectrum': spectrum,
        'susceptibility': susceptibility
    }


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(description='Analyse consolidée COVID-19')
    parser.add_argument('--country', type=str, default='Austria',
                       help='Nom du pays à analyser (ex: Austria, France, Italy)')
    parser.add_argument('--output', type=str, default='reports',
                       help='Répertoire de sortie pour les visualisations')

    args = parser.parse_args()

    analyze_country(args.country, args.output)


if __name__ == "__main__":
    main()
