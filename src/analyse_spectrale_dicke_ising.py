#!/usr/bin/env python3
"""
Analyse Spectrale Dicke-Ising - Susceptibilité Complexe χ(ω)
============================================================

Approche basée sur la physique de la matière condensée pour caractériser
la réponse collective du système épidémique :

1. EXTRACTION SPECTRALE (FFT) :
   - Spectre de puissance |χ(ω)|² (absorption/nouveaux cas)
   - Identification des modes propres (fréquences caractéristiques)

2. RECONSTRUCTION KRAMERS-KRONIG :
   - χ''(ω) : partie imaginaire (absorption, nouveaux cas observés)
   - χ'(ω) : partie réelle (dispersion, latence sociale)
   - Diagramme de Nyquist : χ' vs χ'' (plan complexe)

3. SUSCEPTIBILITÉ DYNAMIQUE :
   - χ_eff(t) : variance glissante (Critical Slowing Down)
   - Calcul de l'exposant critique γ par régression log-log

Interprétation physique :
- χ' > 0 : Système capacitif (latence, inertie sociale, régime SIR)
- χ' < 0 : Système inductif (accélération, synchronisation, régime SR)
- Boucles dans Nyquist : Modes collectifs cohérents (Super-Radiance)

Classes d'universalité :
- γ ≈ 1.0 : Champ moyen (SIR classique)
- γ ≈ 1.24 : Ising 3D (forte corrélation spatiale)
- γ ≈ 1.75 : Ising 2D
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq, ifft
from scipy.stats import linregress
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration
DATA_FILE = "data/covid-hospit-2023-03-31-18h01.csv"
WAVE1_START = "2020-02-15"  # Début élargi pour capturer la montée
WAVE1_END = "2020-06-30"
SAMPLING_RATE = 1.0  # 1 jour^-1


# ============================================================================
# FONCTIONS D'ANALYSE SPECTRALE
# ============================================================================

def analyze_susceptibility_spectrum(t, y_signal, sampling_rate=1.0):
    """
    Effectue l'analyse spectrale pour extraire la susceptibilité complexe
    selon le cadre théorique Dicke-Ising.

    Args:
        t (array): Vecteur temps (jours)
        y_signal (array): Signal épidémique (nouveaux décès quotidiens lissés)
        sampling_rate (float): Fréquence d'échantillonnage (1 jour^-1 par défaut)

    Returns:
        dict: Contient fréquences, spectres (norme, imaginaire, réel) et signaux filtrés.
    """

    # 1. PRÉ-TRAITEMENT
    # Suppression de la composante continue (DC) pour centrer les fluctuations
    y_detrended = y_signal - np.mean(y_signal)

    # Fenêtrage (Hanning) pour réduire les fuites spectrales aux bords
    window = np.hanning(len(y_signal))
    y_windowed = y_detrended * window

    # 2. TRANSFORMÉE DE FOURIER (FFT)
    # Dans la théorie de la réponse linéaire, I(omega) est proportionnel à Chi''(omega) * Force
    # Si l'excitation est un bruit blanc (désordre social constant), alors Spectre ~ Susceptibilité.
    n_fft = 4096  # Zero-padding pour haute résolution fréquentielle
    fft_vals = fft(y_windowed, n=n_fft)
    freqs = fftfreq(n_fft, d=1/sampling_rate)

    # On ne garde que les fréquences positives
    mask = freqs > 0
    freqs = freqs[mask]
    fft_vals = fft_vals[mask]

    # 3. CALCUL DES COMPOSANTES DE LA SUSCEPTIBILITÉ
    # Partie Imaginaire Chi''(omega) ~ Absorption (Nouveaux cas observés)
    # Partie Réelle Chi'(omega) ~ Dispersion (Latence/Retard de phase)

    # Spectre de Puissance (proportionnel à l'absorption d'énergie du champ viral)
    power_spectrum = np.abs(fft_vals)**2

    # Reconstruction complexe
    chi_norm = np.abs(fft_vals)     # Magnitude de la réponse
    chi_imag = np.imag(fft_vals)    # Composante absorptive
    chi_real = np.real(fft_vals)    # Composante dispersive

    return {
        'freqs': freqs,
        'chi_norm': chi_norm,
        'chi_imag': chi_imag,
        'chi_real': chi_real,
        'power': power_spectrum
    }


def calculate_dynamic_susceptibility(t, y_signal, window_size=21):
    """
    Calcule l'évolution temporelle de la susceptibilité intégrée (variance locale).
    Une augmentation soudaine signale l'approche d'un point critique (Critical Slowing Down).

    Selon le théorème fluctuation-dissipation :
    χ_static ∝ variance(I)

    Utilise une fenêtre glissante NON centrée pour capturer la montée vers le point critique.
    """
    susceptibility_t = []
    time_t = []

    for i in range(window_size, len(y_signal)):
        # Fenêtre glissante ARRIÈRE (non centrée)
        segment = y_signal[i-window_size : i]
        # La variance des fluctuations est proportionnelle à la susceptibilité statique Chi(0)
        chi_static_proxy = np.var(segment)
        susceptibility_t.append(chi_static_proxy)
        time_t.append(t[i])

    return np.array(time_t), np.array(susceptibility_t)


def calculate_gamma_from_susceptibility(t_chi, chi, verbose=True):
    """
    Calcule l'exposant critique γ à partir de la susceptibilité dynamique.

    Loi de puissance : χ(t) ∼ |t - t_c|^(-γ)
    Régression : ln(χ) = -γ ln(|t - t_c|) + C

    Args:
        t_chi : array temps (indices ou jours)
        chi : array susceptibilité
        verbose : afficher les résultats

    Returns:
        dict avec gamma, r_squared, t_c, etc.
    """
    # Trouver le point critique (pic de susceptibilité)
    idx_peak = np.argmax(chi)
    t_c = t_chi[idx_peak]
    chi_max = chi[idx_peak]

    # Sélectionner la partie ASCENDANTE (t < t_c)
    mask_ascending = (t_chi < t_c) & (chi > 0)
    t_asc = t_chi[mask_ascending]
    chi_asc = chi[mask_ascending]

    if len(t_asc) < 5:
        if verbose:
            print(f"  ⚠ Régression impossible : seulement {len(t_asc)} points avant le pic")
        return None

    # Distance critique ε = |t - t_c|
    epsilon = np.abs(t_asc - t_c)

    # Filtrer ε = 0
    mask_nonzero = epsilon > 0
    epsilon = epsilon[mask_nonzero]
    chi_asc = chi_asc[mask_nonzero]

    if len(epsilon) < 5:
        if verbose:
            print(f"  ⚠ Régression impossible : seulement {len(epsilon)} points valides")
        return None

    # Régression log-log : ln(χ) = -γ ln(ε) + C
    log_epsilon = np.log(epsilon)
    log_chi = np.log(chi_asc)

    # Vérifier NaN/Inf
    mask_valid = np.isfinite(log_epsilon) & np.isfinite(log_chi)
    log_epsilon = log_epsilon[mask_valid]
    log_chi = log_chi[mask_valid]

    if len(log_epsilon) < 5:
        if verbose:
            print(f"  ⚠ Régression impossible : seulement {len(log_epsilon)} points finis")
        return None

    # Régression linéaire
    slope, intercept, r_value, p_value, std_err = linregress(log_epsilon, log_chi)

    # γ = -slope
    gamma = -slope
    r_squared = r_value**2

    if verbose:
        print(f"\n  Point critique t_c : {t_c:.1f} (χ_max = {chi_max:.2f})")
        print(f"  Exposant γ = {gamma:.3f} ± {std_err:.3f}")
        print(f"  R² = {r_squared:.3f} (p = {p_value:.2e})")
        print(f"  Points de régression : {len(log_epsilon)}")

        # Comparaison avec classes d'universalité
        if gamma > 0:
            if 0.9 < gamma < 1.1:
                print(f"  → Classe : Mean-field (γ ≈ 1.0) ✅")
            elif 1.15 < gamma < 1.35:
                print(f"  → Classe : Ising 3D (γ ≈ 1.24) ✅")
            elif 1.65 < gamma < 1.85:
                print(f"  → Classe : Ising 2D (γ ≈ 1.75) ✅")
            else:
                print(f"  → Classe : Inconnue (γ = {gamma:.3f})")
        else:
            print(f"  → ⚠ γ < 0 : Distance critique mal définie")

    return {
        'gamma': gamma,
        'gamma_err': std_err,
        'r_squared': r_squared,
        'p_value': p_value,
        't_c': t_c,
        'chi_max': chi_max,
        'n_points': len(log_epsilon),
        'epsilon_range': (epsilon.min(), epsilon.max())
    }


# ============================================================================
# CHARGEMENT DES DONNÉES
# ============================================================================

def load_region_data(region_name, dep_codes):
    """
    Charge et agrège les données pour une région française (Vague 1).

    Returns:
        t_data : array temps (jours depuis début)
        y_data : nouveaux décès quotidiens lissés (7j)
        dates : array dates réelles
    """
    print(f"\n{'='*80}")
    print(f"CHARGEMENT DONNÉES : {region_name}")
    print(f"{'='*80}")
    print(f"Départements : {', '.join(dep_codes)}")

    # Charger données SPF
    df_hosp = pd.read_csv(DATA_FILE, sep=';')
    df_hosp['jour'] = pd.to_datetime(df_hosp['jour'])

    # Filtrer région + Vague 1
    df_region = df_hosp[df_hosp['dep'].isin(dep_codes)].copy()
    df_region = df_region[(df_region['jour'] >= WAVE1_START) & (df_region['jour'] <= WAVE1_END)]

    # Agréger par jour (tous départements)
    df_daily = df_region.groupby('jour').agg({
        'dc': 'sum'
    }).reset_index()

    df_daily = df_daily.sort_values('jour').reset_index(drop=True)

    # Calculer nouveaux décès quotidiens
    df_daily['nouveaux_deces'] = df_daily['dc'].diff().fillna(0)

    # Lissage 7 jours (rolling mean centré)
    df_daily['nouveaux_deces_smooth'] = df_daily['nouveaux_deces'].rolling(
        window=7, center=True
    ).mean().fillna(0)

    # Convertir en arrays
    dates = df_daily['jour'].values
    y_data = df_daily['nouveaux_deces_smooth'].values
    t_data = np.arange(len(y_data))  # Temps en jours (indices)

    print(f"Période : {df_daily['jour'].min().strftime('%Y-%m-%d')} → {df_daily['jour'].max().strftime('%Y-%m-%d')}")
    print(f"Points : {len(y_data)} jours")
    print(f"Décès totaux : {df_daily['dc'].iloc[-1]:.0f}")
    print(f"Pic nouveaux décès : {y_data.max():.1f} (jour {t_data[np.argmax(y_data)]}, {dates[np.argmax(y_data)]})")

    return t_data, y_data, dates


# ============================================================================
# VISUALISATIONS
# ============================================================================

def plot_full_analysis(region_name, t_data, y_data, dates, res_spectrum, t_chi, chi):
    """
    Visualisation complète : 4 panels (signal, spectre, Nyquist, susceptibilité)
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    plt.subplots_adjust(hspace=0.3, wspace=0.3)

    # A. Signal Temporel
    ax = axes[0, 0]
    ax.plot(t_data, y_data, 'k-', lw=1.5, label='Nouveaux décès (lissés 7j)')
    ax.set_title(f"1. Signal Temporel I(t) - {region_name}", fontweight='bold', fontsize=13)
    ax.set_xlabel("Temps (jours)", fontsize=11)
    ax.set_ylabel("Nouveaux décès quotidiens", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Marquer le pic
    idx_max = np.argmax(y_data)
    ax.axvline(t_data[idx_max], color='red', linestyle='--', alpha=0.5, label=f'Pic (J{idx_max})')
    ax.text(t_data[idx_max], y_data.max()*1.05, f"J{idx_max}\n{dates[idx_max].astype('datetime64[D]')}",
            ha='center', fontsize=9, color='red')

    # B. Spectre de Puissance (Zoom basses fréquences)
    ax = axes[0, 1]
    freqs = res_spectrum['freqs']
    power = res_spectrum['power']

    # Zoom sur périodes > 3 jours (fréquences < 0.33)
    mask_low_freq = (freqs > 0.005) & (freqs < 0.15)
    f_zoom = freqs[mask_low_freq]
    p_zoom = power[mask_low_freq]

    ax.plot(f_zoom, p_zoom, 'r-', lw=2, label='Spectre mesuré')
    ax.set_title(f"2. Spectre de Puissance |χ(ω)|² - {region_name}", fontweight='bold', fontsize=13)
    ax.set_xlabel("Fréquence (jour⁻¹)", fontsize=11)
    ax.set_ylabel("Puissance spectrale (u.a.)", fontsize=11)
    ax.grid(True, alpha=0.3)

    # Axe secondaire : Période (ticks manuels pour éviter division par zéro)
    secax = ax.twiny()
    secax.set_xlim(ax.get_xlim())

    # Ticks de période manuels
    period_ticks = [100, 50, 33, 25, 20, 14, 10, 7]
    freq_ticks = [1/T for T in period_ticks if 1/T >= f_zoom.min() and 1/T <= f_zoom.max()]
    period_labels = [str(int(1/f)) for f in freq_ticks]

    if len(freq_ticks) > 0:
        secax.set_xticks(freq_ticks)
        secax.set_xticklabels(period_labels)
        secax.set_xlabel('Période (jours)', fontsize=10)

    # Identifier les 3 pics principaux
    if len(p_zoom) > 10:
        peaks_idx = np.argsort(p_zoom)[-3:]
        for idx in peaks_idx:
            if idx < len(f_zoom):
                f_peak = f_zoom[idx]
                T_peak = 1/f_peak
                ax.axvline(x=f_peak, color='b', ls='--', alpha=0.4, lw=1)
                ax.text(f_peak, p_zoom.max()*0.85, f"T≈{T_peak:.0f}j",
                       rotation=90, fontsize=8, color='blue', ha='right')

    ax.legend(fontsize=10)

    # C. Diagramme de Nyquist (Plan Complexe) - Modes Rapides
    ax = axes[1, 0]
    chi_real = res_spectrum['chi_real']
    chi_imag = res_spectrum['chi_imag']

    # Zoom sur modes rapides : 7j < T < 30j → 0.033 < f < 0.14
    mask_rapid = (freqs > 0.033) & (freqs < 0.14)

    if np.sum(mask_rapid) > 5:
        ax.plot(chi_real[mask_rapid], chi_imag[mask_rapid], 'g-', lw=1.5, alpha=0.7)
        ax.scatter(chi_real[mask_rapid][0], chi_imag[mask_rapid][0],
                  color='green', s=80, marker='o', label='Début (f≈0.03)', zorder=5)
        ax.scatter(chi_real[mask_rapid][-1], chi_imag[mask_rapid][-1],
                  color='red', s=80, marker='s', label='Fin (f≈0.14)', zorder=5)

    ax.set_title(f"3. Plan Complexe χ'(ω) vs χ''(ω) - Modes Rapides\n{region_name}",
                fontweight='bold', fontsize=13)
    ax.set_xlabel("χ' : Dispersion (Latence sociale)", fontsize=11)
    ax.set_ylabel("χ'' : Absorption (Nouveaux cas)", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='k', lw=0.5)
    ax.axvline(0, color='k', lw=0.5)
    ax.legend(fontsize=9)

    # Annotation zones
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    ax.text(xlim[0]*0.95, ylim[1]*0.95, "χ' < 0\nInductif\n(SR)",
           fontsize=8, ha='left', va='top', color='purple',
           bbox=dict(boxstyle='round', facecolor='lavender', alpha=0.5))
    ax.text(xlim[1]*0.95, ylim[1]*0.95, "χ' > 0\nCapacitif\n(SIR)",
           fontsize=8, ha='right', va='top', color='blue',
           bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    # D. Susceptibilité Dynamique (Variance Glissante)
    ax = axes[1, 1]
    ax.plot(t_chi, chi, color='purple', lw=2, label='χ_eff(t)')
    ax.set_title(f"4. Susceptibilité Dynamique χ_eff(t) - {region_name}",
                fontweight='bold', fontsize=13)
    ax.set_xlabel("Temps (jours)", fontsize=11)
    ax.set_ylabel("Intensité des fluctuations χ_eff", fontsize=11)
    ax.grid(True, alpha=0.3)

    # Marquer le point critique (pic de susceptibilité)
    idx_chi_max = np.argmax(chi)
    t_c = t_chi[idx_chi_max]
    ax.axvline(t_c, color='red', ls='--', lw=2, label=f'Point critique (t_c ≈ {t_c:.0f}j)')
    ax.scatter(t_c, chi[idx_chi_max], color='red', s=150, marker='*', zorder=5)

    # Marquer le pic de nouveaux décès
    idx_deaths_max = np.argmax(y_data)
    t_deaths = t_data[idx_deaths_max]
    ax.axvline(t_deaths, color='orange', ls=':', lw=2, alpha=0.7,
              label=f'Pic décès (t ≈ {t_deaths:.0f}j)')

    # Avance du signal précurseur
    advance = t_deaths - t_c
    ax.annotate('', xy=(t_c, chi.max()*0.5), xytext=(t_deaths, chi.max()*0.5),
               arrowprops=dict(arrowstyle='<->', color='green', lw=2))
    ax.text((t_c + t_deaths)/2, chi.max()*0.55,
           f'Avance\n{advance:.0f} jours', ha='center', fontsize=10,
           color='green', fontweight='bold')

    ax.legend(fontsize=10, loc='upper left')

    plt.suptitle(f"Analyse Spectrale Dicke-Ising : {region_name}\nVague 1 COVID-19 (Mars-Juin 2020)",
                fontsize=16, fontweight='bold')

    output_file = f"reports/analyse_spectrale_{region_name.replace(' ', '_').lower()}.png"
    Path("reports").mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualisation sauvegardée : {output_file}")
    plt.close()


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

def analyze_region(region_name, dep_codes):
    """
    Pipeline complet d'analyse pour une région.
    """
    print(f"\n{'#'*80}")
    print(f"# ANALYSE SPECTRALE DICKE-ISING : {region_name.upper()}")
    print(f"{'#'*80}")

    # 1. Charger données
    t_data, y_data, dates = load_region_data(region_name, dep_codes)

    # 2. Analyse spectrale (FFT)
    print(f"\n{'='*80}")
    print(f"ANALYSE SPECTRALE (FFT)")
    print(f"{'='*80}")
    res_spectrum = analyze_susceptibility_spectrum(t_data, y_data, sampling_rate=SAMPLING_RATE)

    # Identifier modes principaux
    freqs = res_spectrum['freqs']
    power = res_spectrum['power']
    mask_low = (freqs > 0.005) & (freqs < 0.15)
    if np.sum(mask_low) > 10:
        peaks_idx = np.argsort(power[mask_low])[-3:]
        print(f"\nModes spectraux identifiés (Top 3) :")
        for i, idx in enumerate(peaks_idx[::-1], 1):
            f_peak = freqs[mask_low][idx]
            T_peak = 1/f_peak
            P_peak = power[mask_low][idx]
            print(f"  Mode {i} : f = {f_peak:.4f} jour⁻¹, T ≈ {T_peak:.1f} jours, P = {P_peak:.2e}")

    # 3. Susceptibilité dynamique
    print(f"\n{'='*80}")
    print(f"SUSCEPTIBILITÉ DYNAMIQUE (Variance glissante)")
    print(f"{'='*80}")
    t_chi, chi = calculate_dynamic_susceptibility(t_data, y_data, window_size=14)

    # 4. Calcul de γ
    print(f"\n{'='*80}")
    print(f"CALCUL DE L'EXPOSANT CRITIQUE γ")
    print(f"{'='*80}")
    result_gamma = calculate_gamma_from_susceptibility(t_chi, chi, verbose=True)

    # 5. Visualisation
    plot_full_analysis(region_name, t_data, y_data, dates, res_spectrum, t_chi, chi)

    return {
        'region': region_name,
        't_data': t_data,
        'y_data': y_data,
        'dates': dates,
        'spectrum': res_spectrum,
        't_chi': t_chi,
        'chi': chi,
        'gamma_result': result_gamma
    }


def main():
    """
    Analyse des régions clés : Grand Est et Île-de-France
    """
    regions = {
        'Grand Est': ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
        'Île-de-France': ['75', '77', '78', '91', '92', '93', '94', '95']
    }

    results = {}

    for region_name, dep_codes in regions.items():
        results[region_name] = analyze_region(region_name, dep_codes)

    # Synthèse comparative
    print(f"\n{'#'*80}")
    print(f"# SYNTHÈSE COMPARATIVE")
    print(f"{'#'*80}")

    for region_name, result in results.items():
        gamma_res = result['gamma_result']
        if gamma_res is not None:
            print(f"\n{region_name} :")
            print(f"  γ = {gamma_res['gamma']:.3f} ± {gamma_res['gamma_err']:.3f}")
            print(f"  R² = {gamma_res['r_squared']:.3f}")
            print(f"  Point critique : t_c = {gamma_res['t_c']:.0f} jours")
            print(f"  χ_max = {gamma_res['chi_max']:.2f}")
        else:
            print(f"\n{region_name} : Régression échouée")

    print(f"\n{'#'*80}")
    print(f"# ANALYSE TERMINÉE")
    print(f"{'#'*80}\n")


if __name__ == "__main__":
    main()
