#!/usr/bin/env python3
"""
Validation Exposant Critique γ - Classes d'Universalité
========================================================

Calcule l'exposant critique γ de la susceptibilité pour les 19 pays analysés.

Théorie :
- Transition de phase : χ(t) ∼ |t - t_c|^(-γ)
- Classes d'universalité :
  * Ising 3D : γ = 1.24 (interactions courte portée, 3D)
  * Mean-field : γ = 1.0 (interactions longue portée)
  * Percolation 3D : γ = 1.80 (propagation par contact)

Hypothèse COVID-19 : Classe Ising 3D (interactions sociales locales)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')

# ============================================================================
# LISTE DES PAYS À ANALYSER
# ============================================================================

COUNTRIES = {
    # Europe
    'Austria': 9e6,
    'Belgium': 11.5e6,
    'Denmark': 5.8e6,
    'Finland': 5.5e6,
    'France': 67e6,
    'Germany': 83e6,
    'Ireland': 5e6,
    'Italy': 60e6,
    'Netherlands': 17.5e6,
    'Norway': 5.4e6,
    'Portugal': 10e6,
    'Spain': 47e6,
    'Sweden': 10e6,
    'Switzerland': 8.7e6,
    'United Kingdom': 67e6,
    # Amérique du Nord
    'US': 331e6,
    'Canada': 38e6,
    # Océanie
    'Australia': 26e6,
    'New Zealand': 5e6,
}

# ============================================================================
# CHARGEMENT DONNÉES JHU
# ============================================================================

def load_country_data(country_name, start_date='2020-02-15', end_date='2020-06-30'):
    """
    Charge les données JHU pour un pays.

    Returns:
        t_data, y_data (décès quotidiens lissés), dates
    """
    url = f'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'

    try:
        df = pd.read_csv(url)

        # Filtrer pays
        country_df = df[df['Country/Region'] == country_name]

        if len(country_df) == 0:
            print(f"⚠️  Pays non trouvé : {country_name}")
            return None, None, None

        # Somme toutes les régions du pays
        death_series = country_df.iloc[:, 4:].sum(axis=0)

        # Convertir index en dates
        dates = pd.to_datetime(death_series.index, format='%m/%d/%y')
        death_series.index = dates

        # Filtrer Vague 1
        death_series = death_series[(death_series.index >= start_date) & (death_series.index <= end_date)]

        # Décès quotidiens
        daily_deaths = death_series.diff().fillna(0)

        # Lisser 7 jours
        daily_smooth = daily_deaths.rolling(window=7, center=True).mean().fillna(0)
        daily_smooth = daily_smooth.clip(lower=0)

        t_data = np.arange(len(daily_smooth))
        y_data = daily_smooth.values

        return t_data, y_data, daily_smooth.index

    except Exception as e:
        print(f"❌ Erreur chargement {country_name} : {e}")
        return None, None, None


# ============================================================================
# CALCUL SUSCEPTIBILITÉ χ(t)
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


# ============================================================================
# EXTRACTION EXPOSANT γ
# ============================================================================

def extract_gamma(t_chi, chi, visualize=False, country_name=""):
    """
    Extrait l'exposant critique γ par régression log-log.

    Méthode :
    1. Identifier t_c (pic de susceptibilité)
    2. Prendre phase ascendante (t < t_c)
    3. Régresser log(χ) vs log(|t - t_c|)
    4. Pente = -γ

    Returns:
        gamma, t_c, R²
    """
    if len(chi) == 0 or np.max(chi) < 1e-6:
        return np.nan, np.nan, np.nan

    # 1. Identifier t_c (pic)
    t_c_idx = np.argmax(chi)
    t_c = t_chi[t_c_idx]
    chi_max = chi[t_c_idx]

    print(f"   t_c = {t_c:.0f} jours, χ_max = {chi_max:.1f}")

    # 2. Phase ascendante (avant pic)
    ascending = (t_chi < t_c) & (t_chi > t_c - 30)  # 30 jours avant pic

    if np.sum(ascending) < 5:
        print(f"   ⚠️  Pas assez de points en phase ascendante ({np.sum(ascending)})")
        return np.nan, t_c, np.nan

    t_asc = t_chi[ascending]
    chi_asc = chi[ascending]

    # Filtrer χ > 0
    valid = chi_asc > 1e-6
    t_asc = t_asc[valid]
    chi_asc = chi_asc[valid]

    if len(t_asc) < 5:
        print(f"   ⚠️  Pas assez de points valides ({len(t_asc)})")
        return np.nan, t_c, np.nan

    # 3. Distance au point critique
    epsilon = np.abs(t_asc - t_c)

    # Logarithmes
    log_epsilon = np.log(epsilon)
    log_chi = np.log(chi_asc)

    # 4. Régression linéaire
    slope, intercept, r_value, p_value, std_err = linregress(log_epsilon, log_chi)

    gamma = -slope  # χ ∼ ε^(-γ) → log(χ) = -γ log(ε) + const
    R2 = r_value**2

    print(f"   γ = {gamma:.3f} ± {std_err:.3f}, R² = {R2:.3f}")

    # Visualisation (optionnel)
    if visualize:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Panel 1: Susceptibilité temporelle
        ax1 = axes[0]
        ax1.plot(t_chi, chi, 'b-', linewidth=2, label='χ(t)')
        ax1.axvline(t_c, color='red', linestyle='--', label=f't_c = {t_c:.0f} j')
        ax1.scatter(t_asc, chi_asc, color='green', s=50, zorder=5, label='Phase ascendante')
        ax1.set_xlabel('Temps (jours depuis 15/02/2020)', fontsize=11)
        ax1.set_ylabel('Susceptibilité χ(t)', fontsize=11)
        ax1.set_title(f'{country_name} - Susceptibilité Dynamique', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Panel 2: Régression log-log
        ax2 = axes[1]
        ax2.scatter(log_epsilon, log_chi, color='green', s=50, alpha=0.7, label='Données')

        # Droite de fit
        log_eps_fit = np.linspace(log_epsilon.min(), log_epsilon.max(), 100)
        log_chi_fit = slope * log_eps_fit + intercept
        ax2.plot(log_eps_fit, log_chi_fit, 'r-', linewidth=2,
                label=f'Fit: γ = {gamma:.3f} ± {std_err:.3f}')

        ax2.set_xlabel('log(ε) = log(|t - t_c|)', fontsize=11)
        ax2.set_ylabel('log(χ)', fontsize=11)
        ax2.set_title(f'{country_name} - Régression Power Law\nγ = {gamma:.3f}, R² = {R2:.3f}',
                     fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'results/gamma_{country_name.replace(" ", "_")}.png', dpi=200, bbox_inches='tight')
        plt.close()

    return gamma, t_c, R2


# ============================================================================
# ANALYSE MULTI-PAYS
# ============================================================================

def analyze_all_countries(visualize_top=5):
    """
    Analyse γ pour tous les pays.

    Args:
        visualize_top: Nombre de pays à visualiser (top γ)

    Returns:
        DataFrame avec résultats
    """
    print("="*80)
    print("🔬 VALIDATION EXPOSANT CRITIQUE γ - UNIVERSALITÉ")
    print("="*80)

    results = []

    for i, (country_name, population) in enumerate(COUNTRIES.items(), 1):
        print(f"\n[{i}/{len(COUNTRIES)}] {country_name}")
        print("-" * 70)

        # Charger données
        t_data, y_data, dates = load_country_data(country_name)

        if t_data is None or len(y_data) == 0 or np.max(y_data) < 1.0:
            print(f"   ⚠️  Données insuffisantes")
            continue

        # Calculer susceptibilité
        t_chi, chi = calculate_susceptibility(y_data, window=21)

        # Extraire γ
        gamma, t_c, R2 = extract_gamma(t_chi, chi, visualize=False, country_name=country_name)

        if not np.isnan(gamma):
            results.append({
                'Country': country_name,
                'Population': population,
                'Max_Deaths': np.max(y_data),
                'gamma': gamma,
                't_c': t_c,
                'R2': R2
            })

    # DataFrame résultats
    df = pd.DataFrame(results)

    # Trier par γ
    df = df.sort_values('gamma', ascending=False)

    print("\n" + "="*80)
    print("📊 RÉSULTATS")
    print("="*80)
    print(df.to_string(index=False))

    # Statistiques γ
    print("\n" + "="*80)
    print("📈 STATISTIQUES γ")
    print("="*80)

    print(f"   Nombre de pays : {len(df)}")
    print(f"   Moyenne γ : {df['gamma'].mean():.3f}")
    print(f"   Médiane γ : {df['gamma'].median():.3f}")
    print(f"   Écart-type γ : {df['gamma'].std():.3f}")
    print(f"   Min γ : {df['gamma'].min():.3f} ({df.loc[df['gamma'].idxmin(), 'Country']})")
    print(f"   Max γ : {df['gamma'].max():.3f} ({df.loc[df['gamma'].idxmax(), 'Country']})")

    # Comparaison classes d'universalité
    print("\n" + "="*80)
    print("🎯 CLASSES D'UNIVERSALITÉ")
    print("="*80)

    gamma_mean = df['gamma'].mean()
    gamma_median = df['gamma'].median()

    print(f"   Ising 3D (théorie) : γ = 1.24")
    print(f"   Mean-field (théorie) : γ = 1.00")
    print(f"   Percolation 3D (théorie) : γ = 1.80")
    print()
    print(f"   COVID-19 (observé) :")
    print(f"      Moyenne : γ = {gamma_mean:.3f}")
    print(f"      Médiane : γ = {gamma_median:.3f}")

    # Distance aux classes
    dist_ising = abs(gamma_median - 1.24)
    dist_meanfield = abs(gamma_median - 1.00)
    dist_percolation = abs(gamma_median - 1.80)

    print()
    print(f"   Distance à Ising 3D : {dist_ising:.3f}")
    print(f"   Distance à Mean-field : {dist_meanfield:.3f}")
    print(f"   Distance à Percolation 3D : {dist_percolation:.3f}")

    if dist_ising < dist_meanfield and dist_ising < dist_percolation:
        print(f"\n   ✅ Classe d'universalité COVID-19 : **ISING 3D** (γ ≈ 1.24)")
    elif dist_meanfield < dist_ising:
        print(f"\n   ✅ Classe d'universalité COVID-19 : **MEAN-FIELD** (γ ≈ 1.00)")
    else:
        print(f"\n   ✅ Classe d'universalité COVID-19 : **PERCOLATION 3D** (γ ≈ 1.80)")

    # Visualiser top pays
    if visualize_top > 0:
        print(f"\n📊 Génération visualisations ({visualize_top} pays)...")

        for idx in range(min(visualize_top, len(df))):
            country = df.iloc[idx]['Country']

            # Recharger données
            t_data, y_data, dates = load_country_data(country)
            t_chi, chi = calculate_susceptibility(y_data, window=21)

            # Visualiser
            extract_gamma(t_chi, chi, visualize=True, country_name=country)

        print(f"   ✅ Visualisations sauvegardées : results/gamma_*.png")

    # Histogramme γ
    plot_gamma_histogram(df)

    return df


def plot_gamma_histogram(df):
    """Histogramme des γ avec classes d'universalité."""

    fig, ax = plt.subplots(figsize=(12, 7))

    # Histogramme
    ax.hist(df['gamma'], bins=15, color='steelblue', alpha=0.7, edgecolor='black', label='COVID-19 (observé)')

    # Lignes classes d'universalité
    ax.axvline(1.24, color='red', linestyle='--', linewidth=2, label='Ising 3D (γ = 1.24)')
    ax.axvline(1.00, color='green', linestyle='--', linewidth=2, label='Mean-field (γ = 1.00)')
    ax.axvline(1.80, color='purple', linestyle='--', linewidth=2, label='Percolation 3D (γ = 1.80)')

    # Médiane observée
    median_gamma = df['gamma'].median()
    ax.axvline(median_gamma, color='orange', linestyle='-', linewidth=3,
              label=f'Médiane observée (γ = {median_gamma:.3f})')

    ax.set_xlabel('Exposant critique γ', fontsize=13)
    ax.set_ylabel('Nombre de pays', fontsize=13)
    ax.set_title('Distribution Exposant Critique γ - 19 Pays (Vague 1 COVID-19)\nValidation Classes d\'Universalité',
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('results/gamma_distribution.png', dpi=200, bbox_inches='tight')
    plt.close()

    print(f"\n   ✅ Histogramme sauvegardé : results/gamma_distribution.png")


# ============================================================================
# MAIN
# ============================================================================

def main():
    import os
    os.makedirs('results', exist_ok=True)

    # Analyser tous les pays
    df_results = analyze_all_countries(visualize_top=5)

    # Sauvegarder résultats
    df_results.to_csv('results/gamma_results.csv', index=False)
    print(f"\n✅ Résultats sauvegardés : results/gamma_results.csv")

    print("\n" + "="*80)
    print("✅ ANALYSE TERMINÉE")
    print("="*80)


if __name__ == "__main__":
    main()
