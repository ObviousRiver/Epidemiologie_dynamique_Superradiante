#!/usr/bin/env python3
"""
Analyse FFT Comparative : Données Réelles vs Fit SR
====================================================

Objectif : Valider le fit SR dans le domaine fréquentiel en comparant :
- FFT(données réelles) : résolution standard, spectre anguleux
- FFT(fit SR interpolé) : résolution fine, pics bien définis

Méthode :
1. Données réelles (137 points) → zero-padding à 256 (2^8)
2. Fit SR → interpolation à 2048 points (2^11)
3. Fenêtrage de Hanning pour réduire les effets de bord
4. Identification automatique des pics dominants
5. Superposition graphique + export CSV

Auteur : Analyse automatisée
Date : 12 décembre 2025
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, windows
from pathlib import Path
import sys

# Ajouter le répertoire src/core au path (éviter __init__.py qui importe Kaggle)
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'core'))

from models import SuperRadiantModel

# Configuration
DATA_DIR = Path(__file__).parent.parent / 'data'
RESULTS_DIR = Path(__file__).parent.parent / 'results'
OUTPUT_DIR = Path(__file__).parent.parent / 'results' / 'fft_analysis'

# Créer répertoire output
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Paramètres FFT
N_REAL_FFT = 256        # 2^8 : zero-padding pour données réelles
N_SR_FFT = 2048         # 2^11 : interpolation fine pour fit SR
WINDOW_TYPE = 'hann'    # Fenêtre de Hanning


def load_france_data():
    """Charge les données de décès quotidiens France (JHU dataset depuis GitHub)."""

    # URL GitHub JHU CSSE
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    print(f"  Téléchargement depuis GitHub JHU CSSE...")
    df = pd.read_csv(url)

    # Extraire France
    france = df[df['Country/Region'] == 'France']

    if len(france) == 0:
        raise ValueError("France non trouvée dans le dataset")

    # Sommer toutes les lignes France (régions d'outre-mer possibles)
    cumul_deaths = france.iloc[:, 4:].sum(axis=0)

    # Créer DataFrame avec dates
    france_df = pd.DataFrame({'deaths': cumul_deaths})
    france_df.index = pd.to_datetime(france_df.index)

    # Filtrer période vague 1 : 15 fév - 30 juin 2020
    start_date = '2020-02-15'
    end_date = '2020-06-30'
    france_df = france_df.loc[start_date:end_date]

    # Convertir en décès quotidiens
    daily_deaths = france_df['deaths'].diff().fillna(0).clip(lower=0)

    # Lissage 7 jours (comme dans les autres scripts)
    daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

    t_data = np.arange(len(daily_deaths_smooth))
    y_data = daily_deaths_smooth.values

    print(f"✓ Données France chargées : {len(y_data)} points")
    print(f"  Période : {france_df.index.min().date()} à {france_df.index.max().date()}")
    print(f"  Max décès quotidiens (lissé 7j) : {y_data.max():.1f}")

    return t_data, y_data


def fit_sr_model(t_data, y_data, n_modes=4):
    """Ajuste le modèle SR sur les données et retourne les paramètres."""

    print(f"  Ajustement SR avec {n_modes} modes...")

    # Créer et ajuster modèle SR
    sr_model = SuperRadiantModel(n_modes=n_modes)
    fitted_params, rms = sr_model.fit(t_data, y_data)

    # Extraire paramètres (format bloc : [A1...An, tau1...taun, T1...Tn])
    params = []
    for i in range(n_modes):
        A = fitted_params[i]
        tau = fitted_params[n_modes + i]
        T = fitted_params[2*n_modes + i]
        params.append({'A': A, 'tau': tau, 'T': T})

    print(f"✓ Fit SR terminé : RMS = {rms:.2f}")
    for i, p in enumerate(params, 1):
        print(f"  Mode {i}: A={p['A']:.2f}, τ={p['tau']:.1f}j, T={p['T']:.1f}j")

    return params, n_modes


def compute_sr_fit(t_array, params):
    """Calcule le fit SR sur un array de temps donné."""

    y_fit = np.zeros_like(t_array, dtype=float)

    for p in params:
        # Formule sech² de Dicke
        x = (t_array - p['tau']) / (2.0 * p['T'])
        y_fit += p['A'] * (1.0 / np.cosh(x))**2

    return y_fit


def apply_hanning_window(signal):
    """Applique fenêtre de Hanning au signal."""
    window = windows.hann(len(signal))
    return signal * window


def compute_fft_spectrum(signal, dt=1.0, n_fft=None, apply_window=True):
    """
    Calcule le spectre FFT d'un signal.

    Args:
        signal: Signal temporel
        dt: Pas de temps (jours)
        n_fft: Taille FFT (avec zero-padding si > len(signal))
        apply_window: Appliquer fenêtre de Hanning

    Returns:
        freqs: Fréquences (1/jours)
        spectrum: Amplitude du spectre
    """

    # Retirer la moyenne (detrending) pour éliminer composante DC
    signal_detrended = signal - np.mean(signal)

    # Appliquer fenêtrage
    if apply_window:
        signal_windowed = apply_hanning_window(signal_detrended)
    else:
        signal_windowed = signal_detrended.copy()

    # Zero-padding si nécessaire
    if n_fft is None:
        n_fft = len(signal_windowed)

    # FFT
    spectrum = fft(signal_windowed, n=n_fft)
    freqs = fftfreq(n_fft, d=dt)

    # Ne garder que fréquences positives
    positive_mask = freqs >= 0
    freqs = freqs[positive_mask]
    spectrum = np.abs(spectrum[positive_mask])

    return freqs, spectrum


def identify_peaks(freqs, spectrum, prominence_factor=0.1, min_distance=5):
    """
    Identifie les pics dominants dans le spectre FFT.

    Args:
        freqs: Fréquences
        spectrum: Amplitudes
        prominence_factor: Seuil de prominence (fraction du max)
        min_distance: Distance minimale entre pics (en points)

    Returns:
        peak_freqs: Fréquences des pics
        peak_amps: Amplitudes des pics
        peak_periods: Périodes correspondantes (jours)
    """

    # Trouver pics avec prominence
    prominence = prominence_factor * spectrum.max()
    peaks, properties = find_peaks(spectrum, prominence=prominence, distance=min_distance)

    # Trier par amplitude décroissante
    sorted_idx = np.argsort(properties['prominences'])[::-1]
    peaks = peaks[sorted_idx]

    # Limiter aux 5 pics les plus importants
    peaks = peaks[:5]

    peak_freqs = freqs[peaks]
    peak_amps = spectrum[peaks]

    # Calculer périodes (éviter division par zéro)
    peak_periods = np.where(peak_freqs > 1e-6, 1.0 / peak_freqs, np.inf)

    return peak_freqs, peak_amps, peak_periods


def plot_fft_comparison(freqs_real, spectrum_real, freqs_sr, spectrum_sr,
                        peaks_real, peaks_sr, entity_name="France"):
    """
    Génère le graphique de comparaison des spectres FFT.

    Args:
        freqs_real: Fréquences données réelles
        spectrum_real: Spectre données réelles
        freqs_sr: Fréquences fit SR
        spectrum_sr: Spectre fit SR
        peaks_real: (freqs, amps, periods) pics données réelles
        peaks_sr: (freqs, amps, periods) pics fit SR
        entity_name: Nom de l'entité analysée
    """

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # ========== Graphique 1 : Spectres superposés (échelle linéaire) ==========

    ax1.plot(freqs_real, spectrum_real, 'b-', alpha=0.6, linewidth=1.5,
             label='FFT Données Réelles (137 pts → 256 FFT)')
    ax1.plot(freqs_sr, spectrum_sr, 'r-', alpha=0.8, linewidth=1.2,
             label='FFT Fit SR (2048 pts)')

    # Marquer les pics
    if len(peaks_real[0]) > 0:
        ax1.plot(peaks_real[0], peaks_real[1], 'bo', markersize=8,
                label=f'Pics Réels ({len(peaks_real[0])})')

        # Annoter les pics réels
        for f, a, T in zip(peaks_real[0], peaks_real[1], peaks_real[2]):
            if T < 1000:  # Éviter périodes infinies
                ax1.annotate(f'T={T:.1f}j', xy=(f, a), xytext=(5, 5),
                           textcoords='offset points', fontsize=8, color='blue')

    if len(peaks_sr[0]) > 0:
        ax1.plot(peaks_sr[0], peaks_sr[1], 'rs', markersize=8,
                label=f'Pics SR Fit ({len(peaks_sr[0])})')

        # Annoter les pics SR
        for f, a, T in zip(peaks_sr[0], peaks_sr[1], peaks_sr[2]):
            if T < 1000:
                ax1.annotate(f'T={T:.1f}j', xy=(f, a), xytext=(5, -15),
                           textcoords='offset points', fontsize=8, color='red')

    ax1.set_xlabel('Fréquence (1/jours)', fontsize=12)
    ax1.set_ylabel('Amplitude FFT', fontsize=12)
    ax1.set_title(f'Comparaison Spectres FFT : {entity_name} (Échelle Linéaire)',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 0.15)  # Limiter à fréquences pertinentes

    # ========== Graphique 2 : Spectres superposés (échelle log) ==========

    ax2.semilogy(freqs_real, spectrum_real + 1e-3, 'b-', alpha=0.6, linewidth=1.5,
                 label='FFT Données Réelles')
    ax2.semilogy(freqs_sr, spectrum_sr + 1e-3, 'r-', alpha=0.8, linewidth=1.2,
                 label='FFT Fit SR')

    # Marquer les pics (échelle log)
    if len(peaks_real[0]) > 0:
        ax2.semilogy(peaks_real[0], peaks_real[1] + 1e-3, 'bo', markersize=8)

    if len(peaks_sr[0]) > 0:
        ax2.semilogy(peaks_sr[0], peaks_sr[1] + 1e-3, 'rs', markersize=8)

    ax2.set_xlabel('Fréquence (1/jours)', fontsize=12)
    ax2.set_ylabel('Amplitude FFT (échelle log)', fontsize=12)
    ax2.set_title(f'Comparaison Spectres FFT : {entity_name} (Échelle Logarithmique)',
                  fontsize=14, fontweight='bold')
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3, which='both')
    ax2.set_xlim(0, 0.15)

    plt.tight_layout()

    # Sauvegarder
    output_path = OUTPUT_DIR / f'fft_comparison_{entity_name.lower().replace(" ", "_")}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Graphique sauvegardé : {output_path}")

    plt.close()


def export_peaks_csv(peaks_real, peaks_sr, entity_name="France"):
    """
    Exporte les pics identifiés dans un CSV.

    Args:
        peaks_real: (freqs, amps, periods) pics données réelles
        peaks_sr: (freqs, amps, periods) pics fit SR
        entity_name: Nom de l'entité
    """

    # Construire DataFrame
    rows = []

    # Pics réels
    for i, (f, a, T) in enumerate(zip(peaks_real[0], peaks_real[1], peaks_real[2]), 1):
        rows.append({
            'entity': entity_name,
            'source': 'Données Réelles',
            'peak_rank': i,
            'frequency_per_day': f,
            'period_days': T if T < 1000 else np.nan,
            'amplitude': a
        })

    # Pics SR
    for i, (f, a, T) in enumerate(zip(peaks_sr[0], peaks_sr[1], peaks_sr[2]), 1):
        rows.append({
            'entity': entity_name,
            'source': 'Fit SR',
            'peak_rank': i,
            'frequency_per_day': f,
            'period_days': T if T < 1000 else np.nan,
            'amplitude': a
        })

    df = pd.DataFrame(rows)

    # Sauvegarder
    output_path = OUTPUT_DIR / f'fft_peaks_{entity_name.lower().replace(" ", "_")}.csv'
    df.to_csv(output_path, index=False, float_format='%.6f')
    print(f"✓ Pics FFT exportés : {output_path}")

    return df


def main():
    """Fonction principale : analyse FFT France nationale."""

    print("="*70)
    print("ANALYSE FFT COMPARATIVE : FRANCE NATIONALE")
    print("Validation du Fit SR dans le Domaine Fréquentiel")
    print("="*70)
    print()

    # ========== 1. Charger données réelles ==========
    print("📥 CHARGEMENT DONNÉES RÉELLES")
    print("-" * 70)

    t_data, y_data = load_france_data()
    dt = 1.0  # 1 jour entre chaque point
    n_points = len(y_data)

    print(f"  Δt = {dt} jour")
    print(f"  Durée totale = {n_points} jours")
    print()

    # ========== 2. Ajuster modèle SR ==========
    print("🔧 AJUSTEMENT MODÈLE SR")
    print("-" * 70)

    sr_params, n_modes = fit_sr_model(t_data, y_data, n_modes=4)
    print()

    # ========== 3. Générer fit SR sur grille fine ==========
    print("🔧 GÉNÉRATION FIT SR (GRILLE FINE)")
    print("-" * 70)

    # Grille fine : 2048 points sur même durée
    t_sr_fine = np.linspace(0, n_points - 1, N_SR_FFT)
    y_sr_fine = compute_sr_fit(t_sr_fine, sr_params)
    dt_sr_fine = t_sr_fine[1] - t_sr_fine[0]

    print(f"  Grille SR : {N_SR_FFT} points (2^11)")
    print(f"  Δt interpolé = {dt_sr_fine:.4f} jours")
    print(f"  Résolution fréquentielle ≈ {1.0/(N_SR_FFT*dt_sr_fine):.6f} jour⁻¹")
    print()

    # ========== 4. Calculer FFT données réelles ==========
    print("📊 FFT DONNÉES RÉELLES")
    print("-" * 70)

    freqs_real, spectrum_real = compute_fft_spectrum(
        y_data, dt=dt, n_fft=N_REAL_FFT, apply_window=True
    )

    print(f"  Fenêtrage : Hanning")
    print(f"  Taille FFT : {N_REAL_FFT} (2^8, zero-padding)")
    print(f"  Résolution fréquentielle = {freqs_real[1]:.6f} jour⁻¹")
    print(f"  Plage fréquences : [{freqs_real.min():.6f}, {freqs_real.max():.6f}] jour⁻¹")
    print(f"  Max amplitude = {spectrum_real.max():.2f} à f={freqs_real[spectrum_real.argmax()]:.6f} jour⁻¹")

    # Debug : afficher le top 5 des amplitudes
    top_indices = np.argsort(spectrum_real)[-5:][::-1]
    print(f"  Top 5 amplitudes :")
    for idx in top_indices:
        print(f"    f={freqs_real[idx]:.6f} jour⁻¹, T={1/freqs_real[idx] if freqs_real[idx] > 0 else np.inf:.1f}j, Amp={spectrum_real[idx]:.1f}")
    print()

    # ========== 5. Calculer FFT fit SR ==========
    print("📊 FFT FIT SR")
    print("-" * 70)

    freqs_sr, spectrum_sr = compute_fft_spectrum(
        y_sr_fine, dt=dt_sr_fine, n_fft=N_SR_FFT, apply_window=True
    )

    print(f"  Fenêtrage : Hanning")
    print(f"  Taille FFT : {N_SR_FFT} (2^11)")
    print(f"  Résolution fréquentielle = {freqs_sr[1]:.6f} jour⁻¹")
    print(f"  Plage fréquences : [{freqs_sr.min():.6f}, {freqs_sr.max():.6f}] jour⁻¹")
    print(f"  Max amplitude = {spectrum_sr.max():.2f} à f={freqs_sr[spectrum_sr.argmax()]:.6f} jour⁻¹")

    # Debug : afficher le top 5 des amplitudes
    top_indices_sr = np.argsort(spectrum_sr)[-5:][::-1]
    print(f"  Top 5 amplitudes :")
    for idx in top_indices_sr:
        print(f"    f={freqs_sr[idx]:.6f} jour⁻¹, T={1/freqs_sr[idx] if freqs_sr[idx] > 0 else np.inf:.1f}j, Amp={spectrum_sr[idx]:.1f}")
    print()

    # ========== 6. Identifier pics dominants ==========
    print("🔍 IDENTIFICATION PICS DOMINANTS")
    print("-" * 70)

    # Pics données réelles (seuil abaissé pour mieux détecter)
    peak_freqs_real, peak_amps_real, peak_periods_real = identify_peaks(
        freqs_real, spectrum_real, prominence_factor=0.02, min_distance=2
    )

    print(f"📌 Pics Données Réelles ({len(peak_freqs_real)} identifiés) :")
    for i, (f, a, T) in enumerate(zip(peak_freqs_real, peak_amps_real, peak_periods_real), 1):
        if T < 1000:
            print(f"   {i}. f={f:.5f} jour⁻¹, T={T:.1f}j, Amp={a:.1f}")
        else:
            print(f"   {i}. f={f:.5f} jour⁻¹, T=∞, Amp={a:.1f}")

    print()

    # Pics fit SR (seuil abaissé pour mieux détecter)
    peak_freqs_sr, peak_amps_sr, peak_periods_sr = identify_peaks(
        freqs_sr, spectrum_sr, prominence_factor=0.02, min_distance=5
    )

    print(f"📌 Pics Fit SR ({len(peak_freqs_sr)} identifiés) :")
    for i, (f, a, T) in enumerate(zip(peak_freqs_sr, peak_amps_sr, peak_periods_sr), 1):
        if T < 1000:
            print(f"   {i}. f={f:.5f} jour⁻¹, T={T:.1f}j, Amp={a:.1f}")
        else:
            print(f"   {i}. f={f:.5f} jour⁻¹, T=∞, Amp={a:.1f}")

    print()

    # ========== 7. Comparer avec paramètres SR théoriques ==========
    print("🔬 COMPARAISON AVEC PARAMÈTRES SR THÉORIQUES")
    print("-" * 70)

    print("Paramètres SR (domaine temporel) :")
    for i, p in enumerate(sr_params, 1):
        T_param = p['T']
        f_theor = 1.0 / (4.0 * T_param)  # Fréquence caractéristique sech²
        print(f"  Mode {i}: T={T_param:.1f}j → f_théorique ≈ {f_theor:.5f} jour⁻¹")

    print()
    print("✓ Les pics FFT devraient être proches de ces fréquences théoriques")
    print()

    # ========== 8. Générer visualisations ==========
    print("📈 GÉNÉRATION GRAPHIQUES")
    print("-" * 70)

    peaks_real = (peak_freqs_real, peak_amps_real, peak_periods_real)
    peaks_sr = (peak_freqs_sr, peak_amps_sr, peak_periods_sr)

    plot_fft_comparison(
        freqs_real, spectrum_real,
        freqs_sr, spectrum_sr,
        peaks_real, peaks_sr,
        entity_name="France"
    )

    print()

    # ========== 9. Exporter CSV ==========
    print("💾 EXPORT RÉSULTATS")
    print("-" * 70)

    df_peaks = export_peaks_csv(peaks_real, peaks_sr, entity_name="France")

    print()
    print("="*70)
    print("✅ ANALYSE FFT TERMINÉE")
    print("="*70)
    print(f"📁 Répertoire outputs : {OUTPUT_DIR}")
    print()


if __name__ == "__main__":
    main()
