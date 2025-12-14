#!/usr/bin/env python3
"""
Analyse 2D de γ(t, window): Scalogramme temporel-fenêtrage

Approche: Calculer γ en fonction de:
  - t: position temporelle (fenêtre glissante)
  - window: largeur de fenêtre (7j, 14j, 21j, 28j, 40j, 60j, ...)

Objectif: Chercher "îlots" dimensionnels, minima/maxima locaux, structure répétitive.

Méthodologie:
  1. Modèle SR (SANS normalisation - brut)
  2. γ(t, window) pour différentes fenêtres
  3. Heatmap 2D temps × fenêtre
  4. Repérage t_pic(χ), t_pic(I), Δt
  5. Détection patterns répétitifs
"""

import sys
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from datetime import datetime, timedelta
from scipy.optimize import curve_fit
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

# Import SR model
sys.path.insert(0, 'src/core')
from models import SuperRadiantModel


def load_country_data(country_name, start_date, end_date):
    """Charge les données COVID pour un pays depuis Johns Hopkins GitHub."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
    df = pd.read_csv(url)
    country_data = df[df['Country/Region'] == country_name]

    if len(country_data) == 0:
        raise ValueError(f"Pays '{country_name}' non trouvé")

    # Agréger sur les provinces si nécessaire
    cumul_deaths = country_data.iloc[:, 4:].sum(axis=0)
    result = pd.DataFrame({'deaths': cumul_deaths})
    result.index = pd.to_datetime(result.index, format='%m/%d/%y')
    result['new_deaths'] = result['deaths'].diff().fillna(0).clip(lower=0)

    # Filtrer par dates
    mask = (result.index >= pd.Timestamp(start_date)) & (result.index <= pd.Timestamp(end_date))
    result_filtered = result[mask]

    return {
        'dates': result_filtered.index,
        'deaths': result_filtered['new_deaths'].values,
        't': np.arange(len(result_filtered))
    }


def calculate_susceptibility(signal, window=14):
    """Calcule χ(t) = variance glissante (SANS normalisation)."""
    chi = pd.Series(signal).rolling(window=window, center=True).var()
    return chi.fillna(0).values


def fit_power_law(t, chi):
    """
    Fit loi de puissance χ(t) = A × (t_c - t)^(-γ) sur phase montante.

    Returns:
        gamma, t_c, R², fit_params ou None si échec
    """
    if len(t) < 5 or np.max(chi) == 0:
        return None, None, None, None

    # Détecter pic
    peak_idx = np.argmax(chi)
    if peak_idx < 3:  # Pas assez de points avant le pic
        return None, None, None, None

    # Phase montante jusqu'au pic
    threshold = 0.1 * chi[peak_idx]
    rising_mask = (chi[:peak_idx] > threshold)

    if np.sum(rising_mask) < 3:
        return None, None, None, None

    # Extraire phase montante
    t_rising = t[:peak_idx][rising_mask]
    chi_rising = chi[:peak_idx][rising_mask]

    if len(t_rising) < 3:
        return None, None, None, None

    # Modèle: χ = A × (t_c - t)^(-γ)
    def power_law(t, A, gamma, t_c):
        with np.errstate(all='ignore'):
            result = A * np.power(np.maximum(t_c - t, 1e-10), -gamma)
            return np.where(t < t_c, result, 1e10)

    # Fit
    try:
        # Initialisation
        t_c_init = t[peak_idx] + 2
        gamma_init = 1.0
        A_init = np.median(chi_rising)

        bounds = ([0, 0.1, t[peak_idx]], [np.inf, 3.0, t[peak_idx] + 10])

        popt, _ = curve_fit(
            power_law, t_rising, chi_rising,
            p0=[A_init, gamma_init, t_c_init],
            bounds=bounds,
            maxfev=2000
        )

        A_fit, gamma_fit, tc_fit = popt

        # R²
        chi_pred = power_law(t_rising, *popt)
        ss_res = np.sum((chi_rising - chi_pred)**2)
        ss_tot = np.sum((chi_rising - np.mean(chi_rising))**2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return gamma_fit, tc_fit, r2, popt

    except:
        return None, None, None, None


def compute_gamma_2d_scalogram(t_data, signal_sr,
                                window_chi_values=[7, 10, 14, 21, 28, 40, 60],
                                window_gamma=30,
                                step_gamma=5,
                                normalize=False):
    """
    Calcule γ(t, window_χ) pour différentes fenêtres χ.

    Args:
        t_data: Temps (array)
        signal_sr: Signal SR reconstruit (array)
        window_chi_values: Liste de fenêtres pour χ (en jours)
        window_gamma: Taille fenêtre pour fit γ local
        step_gamma: Pas de déplacement
        normalize: Si True, normalise signal_sr avant calcul χ (intensité uniquement)

    Returns:
        scalogram: dict avec structure γ(t, window)
    """
    # Normalisation en intensité (optionnelle)
    if normalize:
        signal_max = np.max(signal_sr)
        if signal_max > 0:
            signal_sr = signal_sr / signal_max
        else:
            print("    ⚠️  Signal SR max = 0, normalisation impossible")
            normalize = False
    scalogram = {
        'windows': window_chi_values,
        'gamma_maps': {},  # {window: (t_centers, gammas, r2s)}
        'chi_curves': {},  # {window: chi}
        'chi_peaks': {},   # {window: (t_peak, chi_peak)}
    }

    n = len(t_data)

    for window_chi in window_chi_values:
        print(f"    window_χ = {window_chi}j...", end=' ')

        # Calculer χ avec cette fenêtre
        chi = calculate_susceptibility(signal_sr, window=window_chi)

        # Détecter pic χ
        peak_idx = np.argmax(chi)
        t_peak_chi = t_data[peak_idx]
        chi_peak = chi[peak_idx]

        scalogram['chi_curves'][window_chi] = chi
        scalogram['chi_peaks'][window_chi] = (t_peak_chi, chi_peak)

        # Calculer γ(t) avec fenêtre glissante
        t_centers = []
        gammas = []
        r2s = []

        for start_idx in range(0, n - window_gamma, step_gamma):
            end_idx = start_idx + window_gamma

            # Extraire fenêtre
            t_window = t_data[start_idx:end_idx]
            chi_window = chi[start_idx:end_idx]

            # Recentrer t sur cette fenêtre
            t_window_rel = t_window - t_window[0]

            # Fit γ local
            gamma, tc, r2, _ = fit_power_law(t_window_rel, chi_window)

            if gamma is not None and r2 is not None and r2 > 0.5:
                t_center = t_data[start_idx + window_gamma // 2]
                t_centers.append(t_center)
                gammas.append(gamma)
                r2s.append(r2)

        scalogram['gamma_maps'][window_chi] = (
            np.array(t_centers),
            np.array(gammas),
            np.array(r2s)
        )

        print(f"{len(gammas)} points γ")

    return scalogram


def analyze_temporal_markers(t_data, deaths_sr, scalogram):
    """
    Repère les temps caractéristiques:
      - t_pic(I): pic épidémique (SR)
      - t_pic(χ): pic de susceptibilité (pour chaque window)
      - Δt = t_pic(I) - t_pic(χ)

    Returns:
        markers: dict avec repères temporels
    """
    markers = {}

    # Pic épidémique (SR)
    peak_idx_I = np.argmax(deaths_sr)
    t_peak_I = t_data[peak_idx_I]
    I_peak = deaths_sr[peak_idx_I]

    markers['t_peak_I'] = t_peak_I
    markers['I_peak'] = I_peak

    # Pics χ pour chaque fenêtre
    markers['chi_peaks'] = {}
    markers['delta_t'] = {}

    for window_chi in scalogram['windows']:
        t_peak_chi, chi_peak = scalogram['chi_peaks'][window_chi]
        delta_t = t_peak_I - t_peak_chi

        markers['chi_peaks'][window_chi] = {
            't_peak': t_peak_chi,
            'chi_peak': chi_peak,
            'delta_t': delta_t
        }
        markers['delta_t'][window_chi] = delta_t

    return markers


def plot_2d_scalogram(country, dates, t_data, deaths_sr, scalogram, markers, output_dir):
    """
    Visualisation scalogramme 2D γ(t, window).
    """
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # Panel 1: Signal SR
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(dates, deaths_sr, '-', linewidth=2, color='red', label='SR model')
    ax1.axvline(x=dates[int(markers['t_peak_I'])], color='red', linestyle='--',
                linewidth=2, alpha=0.7, label=f't_pic(I) = {dates[int(markers["t_peak_I"])].strftime("%Y-%m-%d")}')
    ax1.set_ylabel('Décès quotidiens (SR)')
    ax1.set_title(f'{country} - Signal SR et repères temporels')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Panel 2: χ(t) pour différentes fenêtres
    ax2 = fig.add_subplot(gs[1, :])
    colors = plt.cm.viridis(np.linspace(0, 1, len(scalogram['windows'])))

    for i, window_chi in enumerate(scalogram['windows']):
        chi = scalogram['chi_curves'][window_chi]
        t_peak_chi, _ = scalogram['chi_peaks'][window_chi]

        ax2.plot(dates, chi, '-', linewidth=1.5, color=colors[i],
                alpha=0.7, label=f'window={window_chi}j')
        ax2.axvline(x=dates[int(t_peak_chi)], color=colors[i],
                   linestyle=':', linewidth=1, alpha=0.5)

    ax2.axvline(x=dates[int(markers['t_peak_I'])], color='red',
               linestyle='--', linewidth=2, alpha=0.7, label='t_pic(I)')
    ax2.set_ylabel('χ(t)')
    ax2.set_title('Susceptibilité χ(t) pour différentes fenêtres')
    ax2.legend(loc='upper right', fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Panel 3: Heatmap γ(t, window) - SCALOGRAMME
    ax3 = fig.add_subplot(gs[2, :])

    # Construire grille pour heatmap
    windows_grid = []
    t_centers_grid = []
    gamma_values = []

    for window_chi in scalogram['windows']:
        t_centers, gammas, r2s = scalogram['gamma_maps'][window_chi]

        for t_c, gamma in zip(t_centers, gammas):
            windows_grid.append(window_chi)
            t_centers_grid.append(t_c)
            gamma_values.append(gamma)

    if len(gamma_values) > 0:
        # Convertir en dates
        dates_centers = [dates[0] + timedelta(days=int(t)) for t in t_centers_grid]

        # Scatter avec colormap
        scatter = ax3.scatter(dates_centers, windows_grid, c=gamma_values,
                             cmap='RdYlBu_r', s=50, alpha=0.8,
                             vmin=0, vmax=3.0, edgecolors='black', linewidth=0.3)

        # Pic épidémique
        ax3.axvline(x=dates[int(markers['t_peak_I'])], color='red',
                   linestyle='--', linewidth=2, alpha=0.7)

        # Pics χ pour chaque fenêtre
        for window_chi in scalogram['windows']:
            t_peak_chi, _ = scalogram['chi_peaks'][window_chi]
            ax3.plot(dates[int(t_peak_chi)], window_chi, 'r*',
                    markersize=12, markeredgecolor='black', markeredgewidth=0.5)

        ax3.set_ylabel('Fenêtre χ (jours)')
        ax3.set_xlabel('Date')
        ax3.set_title('SCALOGRAMME γ(t, window) - Analyse 2D temps × fenêtrage')

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('γ(t, window)', fontsize=10)

    # Panel 4: Δt(window) - Écart temporel pic(I) - pic(χ)
    ax4 = fig.add_subplot(gs[3, 0])

    delta_t_values = [markers['delta_t'][w] for w in scalogram['windows']]

    ax4.plot(scalogram['windows'], delta_t_values, 'o-', linewidth=2,
            markersize=8, color='purple')
    ax4.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax4.set_xlabel('Fenêtre χ (jours)')
    ax4.set_ylabel('Δt = t_pic(I) - t_pic(χ) (jours)')
    ax4.set_title('Écart temporel entre pics')
    ax4.grid(True, alpha=0.3)

    # Panel 5: γ_mean(window) - Moyenne de γ par fenêtre
    ax5 = fig.add_subplot(gs[3, 1])

    gamma_means = []
    gamma_stds = []

    for window_chi in scalogram['windows']:
        _, gammas, _ = scalogram['gamma_maps'][window_chi]
        if len(gammas) > 0:
            gamma_means.append(np.mean(gammas))
            gamma_stds.append(np.std(gammas))
        else:
            gamma_means.append(np.nan)
            gamma_stds.append(np.nan)

    ax5.errorbar(scalogram['windows'], gamma_means, yerr=gamma_stds,
                fmt='o-', linewidth=2, markersize=8, color='orange',
                capsize=5, capthick=2)
    ax5.axhline(y=2.4, color='red', linestyle='--', linewidth=2,
               alpha=0.7, label='γ ≈ 2.4 (référence)')
    ax5.set_xlabel('Fenêtre χ (jours)')
    ax5.set_ylabel('γ_mean')
    ax5.set_title('γ moyen en fonction de la fenêtre')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    plt.suptitle(f'{country} - Scalogramme γ(t, window) et repères temporels',
                fontsize=14, fontweight='bold')

    # Sauvegarder
    filename = f"{output_dir}/{country.lower().replace(' ', '_')}_scalogram_2d.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"    ✅ Figure sauvegardée: {filename}")
    plt.close()


def analyze_country_scalogram(country, start_date, end_date,
                               window_chi_values=[7, 10, 14, 21, 28, 40, 60],
                               window_gamma=30,
                               step_gamma=5,
                               normalize=False):
    """
    Analyse scalogramme 2D γ(t, window) pour un pays.

    Args:
        normalize: Si True, normalise SR en intensité avant calcul χ
    """
    norm_str = "NORMALISÉ" if normalize else "BRUT"
    print(f"\n{'='*80}")
    print(f"Analyse scalogramme 2D: {country} [{norm_str}]")
    print(f"{'='*80}")

    # 1. Charger données
    print(f"  Loading data...")
    data = load_country_data(country, start_date, end_date)
    t_data = data['t']
    deaths_real = data['deaths']
    dates = data['dates']

    # 2. Fit SR
    print(f"  Fitting SR model...")
    sr_model = SuperRadiantModel(n_modes=3)
    try:
        sr_model.fit(t_data, deaths_real)
        deaths_sr = sr_model.predict(t_data)
        sr_success = True
    except Exception as e:
        print(f"    ❌ SR fit failed: {e}")
        return None

    # 3. Scalogramme γ(t, window_χ) avec option normalisation
    norm_msg = "SR normalisé I/max" if normalize else "SR brut"
    print(f"  Computing γ(t, window) scalogram [{norm_msg}]...")
    print(f"    Fenêtres χ testées: {window_chi_values}")
    print(f"    Fenêtre γ: {window_gamma}j, pas: {step_gamma}j")

    scalogram = compute_gamma_2d_scalogram(
        t_data, deaths_sr,
        window_chi_values=window_chi_values,
        window_gamma=window_gamma,
        step_gamma=step_gamma,
        normalize=normalize
    )

    # 4. Repérage temporel
    print(f"  Analyzing temporal markers...")
    markers = analyze_temporal_markers(t_data, deaths_sr, scalogram)

    print(f"\n  📍 Repères temporels:")
    print(f"    t_pic(I) = {dates[int(markers['t_peak_I'])].strftime('%Y-%m-%d')} (pic épidémique)")

    for window_chi in window_chi_values:
        info = markers['chi_peaks'][window_chi]
        print(f"    t_pic(χ, w={window_chi:2d}j) = {dates[int(info['t_peak'])].strftime('%Y-%m-%d')}, "
              f"Δt = {info['delta_t']:+5.1f}j")

    # 5. Statistiques γ par fenêtre
    print(f"\n  📊 Statistiques γ par fenêtre:")
    for window_chi in window_chi_values:
        _, gammas, _ = scalogram['gamma_maps'][window_chi]
        if len(gammas) > 0:
            print(f"    window={window_chi:2d}j: γ = {np.mean(gammas):.2f} ± {np.std(gammas):.2f}, "
                  f"range=[{np.min(gammas):.2f}, {np.max(gammas):.2f}]")
        else:
            print(f"    window={window_chi:2d}j: aucun point γ valide")

    # 6. Visualisation
    print(f"\n  Plotting scalogram...")
    suffix = "_normalized" if normalize else "_raw"
    output_dir = f"results/gamma_scalogram_2d{suffix}"
    os.makedirs(output_dir, exist_ok=True)

    plot_2d_scalogram(country, dates, t_data, deaths_sr, scalogram, markers, output_dir)

    return {
        'country': country,
        'scalogram': scalogram,
        'markers': markers,
        'dates': dates,
        't_data': t_data,
        'deaths_sr': deaths_sr
    }


def main():
    print("="*80)
    print("ANALYSE SCALOGRAMME 2D: γ(t, window) - COMPARAISON BRUT vs NORMALISÉ")
    print("="*80)
    print()
    print("Méthodologie:")
    print("  - Modèle SR: deux versions testées")
    print("    * BRUT: Signal SR sans modification")
    print("    * NORMALISÉ: Signal SR / max(SR) pour comparaison inter-pays")
    print("  - χ(t) calculé pour différentes fenêtres")
    print("  - γ(t) extrait par fenêtre glissante")
    print("  - Heatmap 2D temps × fenêtre (scalogramme)")
    print("  - Repérage t_pic(I), t_pic(χ), Δt")
    print("  - Comparaison systématique brut vs normalisé")
    print()

    # 19 pays européens - Vague 1
    test_cases = [
        ("Italy", "2020-02-15", "2020-08-31"),
        ("France", "2020-02-15", "2020-08-31"),
        ("United Kingdom", "2020-02-15", "2020-08-31"),
        ("Spain", "2020-02-15", "2020-08-31"),
        ("Germany", "2020-02-15", "2020-08-31"),
        ("Belgium", "2020-02-15", "2020-08-31"),
        ("Netherlands", "2020-02-15", "2020-08-31"),
        ("Switzerland", "2020-02-15", "2020-08-31"),
        ("Portugal", "2020-02-15", "2020-08-31"),
        ("Austria", "2020-02-15", "2020-08-31"),
        ("Sweden", "2020-02-15", "2020-08-31"),
        ("Norway", "2020-02-15", "2020-08-31"),
        ("Denmark", "2020-02-15", "2020-08-31"),
        ("Finland", "2020-02-15", "2020-08-31"),
        ("Ireland", "2020-02-15", "2020-08-31"),
        ("Greece", "2020-02-15", "2020-08-31"),
        ("Poland", "2020-02-15", "2020-08-31"),
        ("Romania", "2020-02-15", "2020-08-31"),
        ("Czechia", "2020-02-15", "2020-08-31"),
    ]

    # Paramètres - ZOOM sur zone critique [2-20j] par pas de 1j
    WINDOW_CHI_VALUES = list(range(2, 21))  # [2, 3, 4, ..., 19, 20]
    WINDOW_GAMMA = 30  # Fenêtre pour fit γ local
    STEP_GAMMA = 3     # Pas de déplacement

    print(f"Paramètres - ZOOM haute résolution:")
    print(f"  - {len(test_cases)} pays européens")
    print(f"  - Fenêtres χ: {len(WINDOW_CHI_VALUES)} valeurs [{WINDOW_CHI_VALUES[0]}-{WINDOW_CHI_VALUES[-1]}j]")
    print(f"  - Fenêtre fit γ: {WINDOW_GAMMA}j, pas: {STEP_GAMMA}j")
    print()

    # RUN 1: SR BRUT
    print(f"\n{'#'*80}")
    print(f"# RUN 1: SR BRUT (sans normalisation)")
    print(f"{'#'*80}\n")

    results_raw = []
    for country, start, end in test_cases:
        result = analyze_country_scalogram(
            country, start, end,
            window_chi_values=WINDOW_CHI_VALUES,
            window_gamma=WINDOW_GAMMA,
            step_gamma=STEP_GAMMA,
            normalize=False
        )
        if result is not None:
            results_raw.append(result)

    # RUN 2: SR NORMALISÉ
    print(f"\n{'#'*80}")
    print(f"# RUN 2: SR NORMALISÉ (I_SR / max)")
    print(f"{'#'*80}\n")

    results_normalized = []
    for country, start, end in test_cases:
        result = analyze_country_scalogram(
            country, start, end,
            window_chi_values=WINDOW_CHI_VALUES,
            window_gamma=WINDOW_GAMMA,
            step_gamma=STEP_GAMMA,
            normalize=True
        )
        if result is not None:
            results_normalized.append(result)

    # Synthèse comparative
    print(f"\n{'='*80}")
    print(f"SYNTHÈSE COMPARATIVE - {len(results_raw)} pays")
    print(f"{'='*80}\n")

    print(f"✅ Scalogrammes générés:")
    print(f"  - SR BRUT: results/gamma_scalogram_2d_raw/*.png ({len(results_raw)} pays)")
    print(f"  - SR NORMALISÉ: results/gamma_scalogram_2d_normalized/*.png ({len(results_normalized)} pays)")
    print()
    print(f"📊 Pour comparer:")
    print(f"  - Plateau optimal identifié pour chaque pays")
    print(f"  - Variation γ(window) brut vs normalisé")
    print(f"  - Δt(window) robustesse testée")
    print()
    print(f"→ Analyser les figures pour identifier patterns universels vs spécificités")


if __name__ == "__main__":
    main()
