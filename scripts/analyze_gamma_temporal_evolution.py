#!/usr/bin/env python3
"""
Analyse de l'évolution temporelle de γ(t) avec fenêtre glissante.

Approche: Calculer γ localement en chaque point du temps en utilisant une fenêtre
glissante, similaire au calcul d'une dérivée numérique.

Objectif: Observer si γ a un extremum ou une évolution caractéristique au cours
du processus épidémique.
"""

import sys
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from scipy.optimize import curve_fit
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
    """Calcule χ(t) = variance glissante."""
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


def compute_gamma_sliding_window(t_data, chi, window_size=30, step=5):
    """
    Calcule γ(t) avec fenêtre glissante.

    Args:
        t_data: Temps (array)
        chi: Susceptibilité (array)
        window_size: Largeur de la fenêtre (en points)
        step: Pas de déplacement de la fenêtre

    Returns:
        t_centers: Temps du centre de chaque fenêtre
        gammas: γ mesuré dans chaque fenêtre
        r2s: R² de chaque fit
    """
    t_centers = []
    gammas = []
    r2s = []

    n = len(t_data)

    for start_idx in range(0, n - window_size, step):
        end_idx = start_idx + window_size

        # Extraire fenêtre
        t_window = t_data[start_idx:end_idx]
        chi_window = chi[start_idx:end_idx]

        # Recentrer t sur cette fenêtre
        t_window = t_window - t_window[0]

        # Fit γ local
        gamma, tc, r2, _ = fit_power_law(t_window, chi_window)

        if gamma is not None and r2 is not None and r2 > 0.5:
            t_center = t_data[start_idx + window_size // 2]
            t_centers.append(t_center)
            gammas.append(gamma)
            r2s.append(r2)

    return np.array(t_centers), np.array(gammas), np.array(r2s)


def analyze_country_gamma_evolution(country, start_date, end_date,
                                     window_chi=14, window_gamma=30, step_gamma=5):
    """
    Analyse complète de l'évolution temporelle de γ pour un pays.

    Args:
        country: Nom du pays
        start_date, end_date: Période d'analyse
        window_chi: Fenêtre pour calcul χ
        window_gamma: Fenêtre pour calcul γ(t)
        step_gamma: Pas de la fenêtre glissante
    """
    print(f"\n{'='*80}")
    print(f"Analyse évolution temporelle γ(t): {country}")
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
        sr_success = False
        return None

    # 3. Calculer χ sur SR
    print(f"  Computing χ(SR model)...")
    chi_sr = calculate_susceptibility(deaths_sr, window=window_chi)

    # 4. γ global (référence)
    print(f"  Computing global γ...")
    gamma_global, tc_global, r2_global, _ = fit_power_law(t_data, chi_sr)

    if gamma_global is not None:
        print(f"    γ_global = {gamma_global:.2f} (R² = {r2_global:.2f})")
    else:
        print(f"    ❌ Global fit failed")
        return None

    # 5. γ(t) avec fenêtre glissante
    print(f"  Computing γ(t) with sliding window...")
    print(f"    Window size: {window_gamma} points")
    print(f"    Step: {step_gamma} points")

    t_centers, gammas, r2s = compute_gamma_sliding_window(
        t_data, chi_sr,
        window_size=window_gamma,
        step=step_gamma
    )

    print(f"    → {len(gammas)} fenêtres analysées")

    if len(gammas) == 0:
        print(f"    ❌ No valid windows")
        return None

    # 6. Statistiques γ(t)
    print(f"\n  📊 Statistiques γ(t):")
    print(f"    Moyenne: {np.mean(gammas):.2f} ± {np.std(gammas):.2f}")
    print(f"    Range: [{np.min(gammas):.2f}, {np.max(gammas):.2f}]")
    print(f"    Médiane: {np.median(gammas):.2f}")

    # Détecter extremum
    idx_max = np.argmax(gammas)
    idx_min = np.argmin(gammas)

    print(f"\n  📍 Extremums:")
    print(f"    γ_max = {gammas[idx_max]:.2f} à t = {t_centers[idx_max]:.0f}j")
    print(f"    γ_min = {gammas[idx_min]:.2f} à t = {t_centers[idx_min]:.0f}j")

    # 7. Visualisation
    print(f"\n  Plotting results...")

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # Panel 1: Données + SR
    ax1 = axes[0]
    ax1.plot(dates, deaths_real, 'o-', alpha=0.5, label='Données réelles', markersize=3)
    ax1.plot(dates, deaths_sr, '-', linewidth=2, label='SR model', color='red')
    ax1.set_ylabel('Décès quotidiens')
    ax1.set_title(f'{country} - Données et modèle SR')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Panel 2: χ(SR)
    ax2 = axes[1]
    ax2.plot(dates, chi_sr, '-', linewidth=2, color='purple')
    ax2.axhline(y=np.max(chi_sr) * 0.1, color='gray', linestyle='--', alpha=0.5, label='Seuil 10%')
    ax2.set_ylabel('χ(SR)')
    ax2.set_title(f'Susceptibilité χ(SR) - γ_global = {gamma_global:.2f}')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Panel 3: γ(t) évolution temporelle
    ax3 = axes[2]

    # Convertir t_centers en dates
    dates_centers = [dates[0] + timedelta(days=int(t)) for t in t_centers]

    # Colorier par R²
    scatter = ax3.scatter(dates_centers, gammas, c=r2s, cmap='viridis',
                         s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax3.plot(dates_centers, gammas, '-', alpha=0.3, color='gray')

    # γ global
    ax3.axhline(y=gamma_global, color='red', linestyle='--', linewidth=2,
                label=f'γ_global = {gamma_global:.2f}')

    # Extremums
    ax3.plot(dates_centers[idx_max], gammas[idx_max], 'r*', markersize=15,
            label=f'γ_max = {gammas[idx_max]:.2f}')
    ax3.plot(dates_centers[idx_min], gammas[idx_min], 'b*', markersize=15,
            label=f'γ_min = {gammas[idx_min]:.2f}')

    ax3.set_ylabel('γ(t)')
    ax3.set_xlabel('Date')
    ax3.set_title(f'Évolution temporelle de γ(t) - Fenêtre glissante (taille={window_gamma}j, pas={step_gamma}j)')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax3)
    cbar.set_label('R² du fit local')

    plt.tight_layout()

    # Sauvegarder
    output_dir = "results/gamma_temporal_evolution"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{output_dir}/{country.lower().replace(' ', '_')}_gamma_evolution.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"    ✅ Figure sauvegardée: {filename}")
    plt.close()

    return {
        'country': country,
        'gamma_global': gamma_global,
        'r2_global': r2_global,
        't_centers': t_centers,
        'dates_centers': dates_centers,
        'gammas': gammas,
        'r2s': r2s,
        'gamma_mean': np.mean(gammas),
        'gamma_std': np.std(gammas),
        'gamma_max': gammas[idx_max],
        'gamma_min': gammas[idx_min],
        't_max': t_centers[idx_max],
        't_min': t_centers[idx_min],
    }


def main():
    print("="*80)
    print("ANALYSE ÉVOLUTION TEMPORELLE DE γ(t)")
    print("="*80)
    print()
    print("Méthodologie:")
    print("  - Fenêtre glissante temporelle (comme dérivée numérique)")
    print("  - Calcul de γ local dans chaque fenêtre")
    print("  - Observation de l'évolution γ(t)")
    print("  - Recherche d'extremums, patterns caractéristiques")
    print()

    # Pays tests
    test_cases = [
        ("Italy", "2020-02-15", "2020-08-31"),
        ("United Kingdom", "2020-02-15", "2020-08-31"),
        ("France", "2020-02-15", "2020-08-31"),
        ("Spain", "2020-02-15", "2020-08-31"),
        ("Germany", "2020-02-15", "2020-08-31"),
    ]

    # Paramètres fenêtres
    WINDOW_CHI = 14  # Fenêtre variance glissante pour χ
    WINDOW_GAMMA = 40  # Fenêtre pour calcul γ (à ajuster)
    STEP_GAMMA = 5  # Pas de déplacement

    print(f"Paramètres fenêtres:")
    print(f"  - window_χ = {WINDOW_CHI} jours (variance glissante)")
    print(f"  - window_γ = {WINDOW_GAMMA} jours (fit local)")
    print(f"  - step = {STEP_GAMMA} jours (déplacement)")
    print()

    results = []

    for country, start, end in test_cases:
        result = analyze_country_gamma_evolution(
            country, start, end,
            window_chi=WINDOW_CHI,
            window_gamma=WINDOW_GAMMA,
            step_gamma=STEP_GAMMA
        )

        if result is not None:
            results.append(result)

    # Synthèse
    if len(results) > 0:
        print(f"\n{'='*80}")
        print(f"SYNTHÈSE - {len(results)} PAYS ANALYSÉS")
        print(f"{'='*80}\n")

        print(f"{'Pays':<20} {'γ_global':<10} {'γ_mean(t)':<12} {'γ_max':<10} {'γ_min':<10} {'Range'}")
        print("-" * 80)

        for r in results:
            gamma_range = r['gamma_max'] - r['gamma_min']
            print(f"{r['country']:<20} {r['gamma_global']:>6.2f}     "
                  f"{r['gamma_mean']:>6.2f}±{r['gamma_std']:<4.2f} "
                  f"{r['gamma_max']:>6.2f}     {r['gamma_min']:>6.2f}     {gamma_range:>6.2f}")

        print()
        print("Observations:")
        print("  - γ_global: Exposant mesuré sur toute la période")
        print("  - γ_mean(t): Moyenne des γ locaux (fenêtre glissante)")
        print("  - γ_max, γ_min: Extremums de γ(t)")
        print("  - Range: Amplitude de variation de γ au cours du temps")
        print()
        print(f"📁 Figures: results/gamma_temporal_evolution/*.png")


if __name__ == "__main__":
    main()
