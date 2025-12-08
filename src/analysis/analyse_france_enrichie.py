#!/usr/bin/env python3
"""
Analyse Enrichie France Multi-Échelle
======================================

Ajoute les analyses de validation :
- Susceptibilité χ(t) (variance glissante)
- Analyse spectrale (FFT, puissance)
- Diagramme Nyquist (χ' vs χ'')
- Analyse résidus
- Visualisations complètes

Sélection intelligente :
- Départements : seuil > 10 décès/jour max
- Régions : tous (données suffisantes)
- National : complet

Objectif : Mêmes outils que pour les 19 pays
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.stats import linregress
from scipy.signal import hilbert
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')

# ============================================================================
# ANALYSE SUSCEPTIBILITÉ χ(t)
# ============================================================================

def calculate_susceptibility(y_signal, window=21):
    """
    Calcule la susceptibilité dynamique χ(t) = rolling variance.

    Args:
        y_signal: Signal temporel (décès quotidiens)
        window: Fenêtre rolling (jours)

    Returns:
        t_chi, chi (temps, susceptibilité)
    """
    chi = []
    t_chi = []

    for i in range(window, len(y_signal)):
        segment = y_signal[i-window:i]
        variance = np.var(segment)
        chi.append(variance)
        t_chi.append(i)

    return np.array(t_chi), np.array(chi)


def extract_gamma(t_chi, chi):
    """
    Extrait l'exposant critique γ par régression log-log.

    Returns:
        gamma, t_c, R²
    """
    if len(chi) == 0 or np.max(chi) < 1e-6:
        return np.nan, np.nan, np.nan

    # 1. Identifier t_c (pic)
    t_c_idx = np.argmax(chi)
    t_c = t_chi[t_c_idx]

    # 2. Phase ascendante (avant pic)
    ascending = (t_chi < t_c) & (t_chi > t_c - 30)

    if np.sum(ascending) < 5:
        return np.nan, t_c, np.nan

    t_asc = t_chi[ascending]
    chi_asc = chi[ascending]

    # Filtrer χ > 0
    valid = chi_asc > 1e-6
    t_asc = t_asc[valid]
    chi_asc = chi_asc[valid]

    if len(t_asc) < 5:
        return np.nan, t_c, np.nan

    # 3. Distance au point critique
    epsilon = np.abs(t_asc - t_c)

    # Logarithmes
    log_epsilon = np.log(epsilon)
    log_chi = np.log(chi_asc)

    # 4. Régression linéaire
    slope, intercept, r_value, p_value, std_err = linregress(log_epsilon, log_chi)

    gamma = -slope
    R2 = r_value**2

    return gamma, t_c, R2


# ============================================================================
# ANALYSE SPECTRALE (FFT)
# ============================================================================

def spectral_analysis(y_signal, dt=1.0):
    """
    Analyse spectrale FFT du signal.

    Args:
        y_signal: Signal temporel
        dt: Pas de temps (jours)

    Returns:
        freqs, power_spectrum
    """
    N = len(y_signal)

    # FFT
    y_fft = fft(y_signal)
    freqs = fftfreq(N, d=dt)

    # Puissance (moitié positive uniquement)
    positive = freqs > 0
    freqs_pos = freqs[positive]
    power = np.abs(y_fft[positive])**2

    return freqs_pos, power


# ============================================================================
# DIAGRAMME NYQUIST
# ============================================================================

def nyquist_analysis(y_signal, dt=1.0):
    """
    Calcule le diagramme de Nyquist (partie réelle vs imaginaire de χ(ω)).

    Approximation :
    - χ(ω) calculée via transformée de Hilbert
    - χ'(ω) = partie réelle
    - χ''(ω) = partie imaginaire

    Returns:
        chi_real, chi_imag, freqs
    """
    # Transformée de Hilbert pour obtenir partie imaginaire
    analytic_signal = hilbert(y_signal)

    # FFT du signal analytique
    N = len(analytic_signal)
    chi_fft = fft(analytic_signal)
    freqs = fftfreq(N, d=dt)

    # Parties réelle et imaginaire
    positive = freqs > 0
    freqs_pos = freqs[positive]
    chi_real = np.real(chi_fft[positive])
    chi_imag = np.imag(chi_fft[positive])

    return chi_real, chi_imag, freqs_pos


# ============================================================================
# ANALYSE RÉSIDUS
# ============================================================================

def analyze_residuals(y_data, y_fit_sr, y_fit_sir):
    """
    Analyse les résidus des fits SR et SIR.

    Returns:
        residuals_sr, residuals_sir, stats
    """
    residuals_sr = y_data - y_fit_sr
    residuals_sir = y_data - y_fit_sir

    stats = {
        'sr': {
            'mean': np.mean(residuals_sr),
            'std': np.std(residuals_sr),
            'max': np.max(np.abs(residuals_sr))
        },
        'sir': {
            'mean': np.mean(residuals_sir),
            'std': np.std(residuals_sir),
            'max': np.max(np.abs(residuals_sir))
        }
    }

    return residuals_sr, residuals_sir, stats


# ============================================================================
# VISUALISATION ENRICHIE
# ============================================================================

def plot_enriched_analysis(location_name, t_data, y_data, result, output_file):
    """
    Génère une visualisation complète avec toutes les analyses.

    Layout : 3x2 subplots
    - (0,0) : Fits SR vs SIR
    - (0,1) : Résidus
    - (1,0) : Susceptibilité χ(t) + γ
    - (1,1) : Spectre FFT
    - (2,0) : Nyquist χ' vs χ''
    - (2,1) : Statistiques texte
    """
    fig = plt.figure(figsize=(16, 18))

    # --- Panel (0,0) : Fits SR vs SIR ---
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(t_data, y_data, 'ko', markersize=3, alpha=0.5, label='Données SPF')

    if result['fit_sr'] is not None:
        ax1.plot(t_data, result['fit_sr'], 'b-', linewidth=2,
                label=f"SR {result['n_modes_sr']} modes (RMS={result['rms_sr']:.2f})")

    if result['fit_sir'] is not None:
        ax1.plot(t_data, result['fit_sir'], 'r--', linewidth=2,
                label=f"SIR (RMS={result['rms_sir']:.2f})")

    ax1.set_xlabel('Temps (jours depuis 15/02/2020)', fontsize=11)
    ax1.set_ylabel('Décès quotidiens (lissés 7j)', fontsize=11)
    ax1.set_title(f'{location_name} - Fits SR vs SIR', fontsize=12, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # --- Panel (0,1) : Résidus ---
    ax2 = plt.subplot(3, 2, 2)

    if result['fit_sr'] is not None and result['fit_sir'] is not None:
        res_sr, res_sir, stats = analyze_residuals(y_data, result['fit_sr'], result['fit_sir'])

        ax2.plot(t_data, res_sr, 'b-', linewidth=1, alpha=0.7, label='Résidus SR')
        ax2.plot(t_data, res_sir, 'r-', linewidth=1, alpha=0.7, label='Résidus SIR')
        ax2.axhline(0, color='k', linestyle='--', linewidth=1)

        ax2.set_xlabel('Temps (jours)', fontsize=11)
        ax2.set_ylabel('Résidus (Données - Fit)', fontsize=11)
        ax2.set_title('Analyse Résidus', fontsize=12, fontweight='bold')
        ax2.legend(loc='best')
        ax2.grid(True, alpha=0.3)

    # --- Panel (1,0) : Susceptibilité χ(t) ---
    ax3 = plt.subplot(3, 2, 3)

    t_chi, chi = calculate_susceptibility(y_data, window=21)
    gamma, t_c, R2 = extract_gamma(t_chi, chi)

    ax3.plot(t_chi, chi, 'g-', linewidth=2, label='χ(t) = variance glissante (21j)')

    if not np.isnan(t_c):
        ax3.axvline(t_c, color='red', linestyle='--', linewidth=1,
                   label=f't_c = {t_c:.0f} j')

    ax3.set_xlabel('Temps (jours)', fontsize=11)
    ax3.set_ylabel('Susceptibilité χ(t)', fontsize=11)

    if not np.isnan(gamma):
        title = f'Susceptibilité Critique (γ = {gamma:.3f}, R² = {R2:.3f})'
    else:
        title = 'Susceptibilité Critique (γ indéterminé)'

    ax3.set_title(title, fontsize=12, fontweight='bold')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    # --- Panel (1,1) : Spectre FFT ---
    ax4 = plt.subplot(3, 2, 4)

    freqs, power = spectral_analysis(y_data, dt=1.0)

    # Limiter à fréquences basses (périodes > 3 jours)
    mask = freqs < 0.33  # f < 1/3 jour⁻¹
    freqs_plot = freqs[mask]
    power_plot = power[mask]

    ax4.semilogy(freqs_plot, power_plot, 'purple', linewidth=1.5)
    ax4.set_xlabel('Fréquence (jour⁻¹)', fontsize=11)
    ax4.set_ylabel('Puissance spectrale |χ(ω)|²', fontsize=11)
    ax4.set_title('Analyse Spectrale (FFT)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # Ajouter périodes en haut
    ax4_top = ax4.twiny()
    periods = 1 / freqs_plot[freqs_plot > 0][:5]  # 5 premières périodes
    ax4_top.set_xlim(ax4.get_xlim())
    ax4_top.set_xlabel('Période (jours)', fontsize=10, color='gray')

    # --- Panel (2,0) : Nyquist ---
    ax5 = plt.subplot(3, 2, 5)

    chi_real, chi_imag, freqs_nyq = nyquist_analysis(y_data, dt=1.0)

    # Limiter pour visualisation
    mask_nyq = (freqs_nyq > 0.01) & (freqs_nyq < 0.33)
    chi_real_plot = chi_real[mask_nyq]
    chi_imag_plot = chi_imag[mask_nyq]

    ax5.plot(chi_real_plot, chi_imag_plot, 'o-', color='darkblue',
            markersize=3, linewidth=1, alpha=0.7)
    ax5.axhline(0, color='k', linestyle='--', linewidth=0.5)
    ax5.axvline(0, color='k', linestyle='--', linewidth=0.5)

    ax5.set_xlabel("χ'(ω) - Partie réelle", fontsize=11)
    ax5.set_ylabel("χ''(ω) - Partie imaginaire", fontsize=11)
    ax5.set_title('Diagramme de Nyquist', fontsize=12, fontweight='bold')
    ax5.grid(True, alpha=0.3)

    # Annoter régime
    if np.mean(chi_real_plot) < 0:
        regime_text = "χ' < 0 (inductif)\n→ Signature SR"
    else:
        regime_text = "χ' > 0 (capacitif)\n→ Signature SIR"

    ax5.text(0.05, 0.95, regime_text, transform=ax5.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # --- Panel (2,1) : Statistiques texte ---
    ax6 = plt.subplot(3, 2, 6)
    ax6.axis('off')

    # Compiler stats
    stats_text = f"📊 STATISTIQUES - {location_name}\n"
    stats_text += "="*50 + "\n\n"

    stats_text += f"🏆 Régime dominant : {result['winner']}\n"
    stats_text += f"   Ratio SR/SIR : {result['ratio']:.2f}×\n\n"

    stats_text += f"📈 Modèle SR ({result['n_modes_sr']} modes)\n"
    stats_text += f"   RMS : {result['rms_sr']:.3f}\n"

    if result['params_sr'] is not None and len(result['params_sr']) >= 3:
        stats_text += f"   Mode 1 : A={result['params_sr'][0]:.1f}, τ={result['params_sr'][1]:.0f}j, T={result['params_sr'][2]:.1f}j\n\n"
    else:
        stats_text += "\n"

    stats_text += f"📉 Modèle SIR\n"
    stats_text += f"   RMS : {result['rms_sir']:.3f}\n"

    if result['params_sir'] is not None:
        stats_text += f"   R0 : {result['params_sir'].get('R0', np.nan):.2f}\n"
        stats_text += f"   Durée infection : {result['params_sir'].get('duration', np.nan):.1f} jours\n\n"
    else:
        stats_text += "\n"

    stats_text += f"🔬 Exposant critique γ\n"
    if not np.isnan(gamma):
        stats_text += f"   γ : {gamma:.3f} ± {np.nan:.3f}\n"
        stats_text += f"   t_c : {t_c:.0f} jours\n"
        stats_text += f"   R² : {R2:.3f}\n\n"
    else:
        stats_text += "   Indéterminé (données insuffisantes)\n\n"

    stats_text += f"📊 Données\n"
    stats_text += f"   Population : {result['population']/1e6:.2f} M\n"
    stats_text += f"   Max décès/jour : {result['max_deaths']:.1f}\n"
    stats_text += f"   Points temporels : {len(t_data)}\n"

    ax6.text(0.1, 0.95, stats_text, transform=ax6.transAxes,
            fontsize=10, verticalalignment='top', family='monospace')

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"   ✅ Visualisation enrichie sauvegardée : {output_file}")


# ============================================================================
# MAIN - GÉNÉRATION ANALYSES ENRICHIES
# ============================================================================

def main():
    """
    Génère analyses enrichies pour territoires sélectionnés.

    Sélection :
    - Départements : max_deaths > 10 (statistique suffisante)
    - Régions : toutes
    - National : France entière
    """
    import os

    print("="*80)
    print("🔬 ANALYSE ENRICHIE FRANCE - VALIDATION SPECTRALE")
    print("="*80)

    # Charger résultats
    df_dept = pd.read_csv('results/france_departements_consolidee.csv')
    df_region = pd.read_csv('results/france_regions_consolidee.csv')
    df_national = pd.read_csv('results/france_national_consolidee.csv')

    # Charger données SPF
    from analyse_france_multi_echelle import (
        load_spf_data, extract_departement_deaths, extract_region_deaths,
        extract_national_deaths
    )

    df_spf = load_spf_data()

    if df_spf is None:
        print("❌ Impossible de charger données SPF")
        return

    os.makedirs('results/france_enriched', exist_ok=True)

    # ========================================================================
    # DÉPARTEMENTS SÉLECTIONNÉS (max_deaths > 10)
    # ========================================================================

    print("\n📍 DÉPARTEMENTS (seuil > 10 décès/jour)")
    print("-" * 80)

    df_dept_selected = df_dept[df_dept['max_deaths'] > 10].copy()
    print(f"   Sélectionnés : {len(df_dept_selected)}/{len(df_dept)} départements")

    for idx, row in df_dept_selected.iterrows():
        dept_code = row['departement']

        print(f"\n   🔍 Département {dept_code} ({row['max_deaths']:.1f} décès/j max)")

        t_data, y_data, dates = extract_departement_deaths(df_spf, dept_code)

        if t_data is None:
            print(f"      ⚠️  Données manquantes")
            continue

        # Construire résultat (simulé pour démo - à charger depuis analyse complète)
        result = {
            'location': f"Département {dept_code}",
            'population': row['population'],
            'max_deaths': row['max_deaths'],
            'rms_sr': row['rms_sr'],
            'rms_sir': row['rms_sir'],
            'ratio': row['ratio'],
            'winner': row['winner'],
            'n_modes_sr': int(row['n_modes_sr']),
            'params_sr': None,  # À charger depuis fichier complet
            'fit_sr': None,     # À recalculer ou charger
            'params_sir': None,
            'fit_sir': None
        }

        # Note : On devrait recalculer fits ou les stocker, pour l'instant on skip
        print(f"      ⚠️  Fits non disponibles (nécessite recalcul ou stockage)")

    # ========================================================================
    # RÉGIONS (TOUTES)
    # ========================================================================

    print("\n\n📍 RÉGIONS (toutes)")
    print("-" * 80)
    print(f"   Sélectionnées : {len(df_region)} régions")

    for idx, row in df_region.iterrows():
        region_name = row['region']

        print(f"\n   🔍 {region_name} ({row['max_deaths']:.1f} décès/j max)")
        print(f"      ⚠️  Analyse enrichie nécessite stockage fits (à implémenter)")

    # ========================================================================
    # NATIONAL
    # ========================================================================

    print("\n\n📍 NATIONAL (France)")
    print("-" * 80)

    row_nat = df_national.iloc[0]
    print(f"   🇫🇷 France ({row_nat['max_deaths']:.1f} décès/j max)")
    print(f"      ⚠️  Analyse enrichie nécessite stockage fits (à implémenter)")

    print("\n" + "="*80)
    print("⚠️  IMPLÉMENTATION PARTIELLE")
    print("="*80)
    print("\n💡 Pour compléter cette analyse enrichie, il faut :")
    print("   1. Modifier analyse_france_multi_echelle.py pour STOCKER les fits")
    print("   2. Sauvegarder params_sr, fit_sr, params_sir, fit_sir en pickle/npz")
    print("   3. Recharger ici et générer visualisations enrichies")
    print("\n   OU bien : Recalculer fits à la volée (plus lent)")


if __name__ == "__main__":
    main()
