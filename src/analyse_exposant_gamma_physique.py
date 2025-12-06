#!/usr/bin/env python3
"""
Analyse de l'exposant critique γ (susceptibilité) - Méthode Physique
=====================================================================

Méthode correcte basée sur la physique des transitions de phase :
- Distance critique : ε = |t - t_c| où t_c est le pic de variance
- Susceptibilité : χ(t) = variance glissante des NOUVEAUX DÉCÈS (lissés 7j)
- Loi de puissance : χ(t) ∼ |t - t_c|^(-γ)
- Régression log-log sur la partie ASCENDANTE : ln(χ) = -γ ln(ε) + C

IMPORTANT : Utilise les DÉCÈS ('dc') comme dans l'analyse originale,
pas les hospitalisations ('hosp'). Les nouveaux décès sont lissés sur
7 jours (rolling mean) pour réduire le bruit, puis la variance glissante
est calculée sur cette série lissée.

L'exposant γ doit être POSITIF et comparable aux classes d'universalité :
- Ising 3D : γ ≈ 1.24
- Mean-field : γ = 1.0
- Ising 2D : γ ≈ 1.75
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configuration
DATA_FILE = "data/covid-hospit-2023-03-31-18h01.csv"
WAVE1_START = "2020-03-18"
WAVE1_END = "2020-06-30"
WINDOW_SIZE = 7  # Fenêtre pour variance glissante
MIN_POINTS_REGRESSION = 10  # Minimum de points pour régression valide

def load_department_data(df_hosp, dep_code):
    """
    Charge les données d'un département pour la Vague 1
    """
    df_dep = df_hosp[df_hosp['dep'] == dep_code].copy()
    df_dep = df_dep[(df_dep['jour'] >= WAVE1_START) & (df_dep['jour'] <= WAVE1_END)]

    # Agréger par jour (tous sexes)
    df_daily = df_dep.groupby('jour').agg({
        'hosp': 'sum',
        'rea': 'sum',
        'dc': 'sum'
    }).reset_index()

    df_daily['jour'] = pd.to_datetime(df_daily['jour'])
    df_daily = df_daily.sort_values('jour')

    # Calculer les nouveaux décès quotidiens (comme dans l'analyse originale)
    df_daily['nouveaux_deces'] = df_daily['dc'].diff().fillna(0)

    # Lissage sur 7 jours (rolling mean) pour réduire le bruit
    df_daily['nouveaux_deces_smooth'] = df_daily['nouveaux_deces'].rolling(window=7, center=True).mean().fillna(0)

    return df_daily

def calculate_rolling_variance(cases, window=7):
    """
    Calcule la variance glissante (susceptibilité χ)
    """
    return pd.Series(cases).rolling(window=window, center=False).var()

def find_variance_peak(variance_series):
    """
    Identifie le pic de variance (point critique t_c)
    Retourne l'index du pic
    """
    # Nettoyer les NaN
    clean_variance = variance_series.dropna()
    if len(clean_variance) == 0:
        return None

    peak_idx = clean_variance.idxmax()
    return peak_idx

def calculate_gamma_exponent(time_array, variance_array, peak_idx):
    """
    Calcule l'exposant γ par régression log-log sur la partie ASCENDANTE

    Paramètres :
    - time_array : array des jours (indices)
    - variance_array : χ(t)
    - peak_idx : indice du pic de variance (t_c)

    Retourne :
    - gamma : exposant critique
    - r_squared : qualité du fit
    - n_points : nombre de points utilisés
    - epsilon_range : plage de ε utilisée
    """
    # Sélectionner UNIQUEMENT la partie ascendante (t < t_c)
    mask_ascending = (time_array < peak_idx) & (variance_array > 0)

    t_asc = time_array[mask_ascending]
    chi_asc = variance_array[mask_ascending]

    if len(t_asc) < MIN_POINTS_REGRESSION:
        return None, None, 0, None

    # Distance critique : ε = |t - t_c|
    epsilon = np.abs(t_asc - peak_idx)

    # Filtrer ε = 0 (point critique lui-même)
    mask_nonzero = epsilon > 0
    epsilon = epsilon[mask_nonzero]
    chi_asc = chi_asc[mask_nonzero]

    if len(epsilon) < MIN_POINTS_REGRESSION:
        return None, None, 0, None

    # Régression log-log : ln(χ) = -γ ln(ε) + C
    log_epsilon = np.log(epsilon)
    log_chi = np.log(chi_asc)

    # Vérifier qu'il n'y a pas de NaN/Inf
    mask_valid = np.isfinite(log_epsilon) & np.isfinite(log_chi)
    log_epsilon = log_epsilon[mask_valid]
    log_chi = log_chi[mask_valid]

    if len(log_epsilon) < MIN_POINTS_REGRESSION:
        return None, None, 0, None

    # Régression linéaire
    slope, intercept, r_value, p_value, std_err = linregress(log_epsilon, log_chi)

    # γ = -slope (car ln(χ) = -γ ln(ε) + C)
    gamma = -slope
    r_squared = r_value**2

    epsilon_range = (epsilon.min(), epsilon.max())

    return gamma, r_squared, len(log_epsilon), epsilon_range

def analyze_all_departments():
    """
    Analyse tous les départements métropolitains
    """
    print("=" * 80)
    print("ANALYSE DE L'EXPOSANT CRITIQUE γ - MÉTHODE PHYSIQUE")
    print("=" * 80)
    print()
    print("Méthode :")
    print("  • Susceptibilité χ(t) = variance glissante (fenêtre 7 jours)")
    print("  • Point critique t_c = jour du pic de variance")
    print("  • Distance critique ε = |t - t_c|")
    print("  • Régression log-log (partie ascendante) : ln(χ) = -γ ln(ε) + C")
    print()
    print("Attendu : γ > 0 et γ ≈ 1.0-1.5 pour système social complexe")
    print("=" * 80)
    print()

    # Charger données
    print(f"Chargement des données : {DATA_FILE}")
    df_hosp = pd.read_csv(DATA_FILE, sep=';')
    df_hosp['jour'] = pd.to_datetime(df_hosp['jour'])

    # Liste des départements métropolitains
    departments = sorted([d for d in df_hosp['dep'].unique() if isinstance(d, str) and d.isdigit() and int(d) < 96])

    print(f"Départements à analyser : {len(departments)}")
    print()

    results = []

    for dep in departments:
        try:
            # Charger données départementales
            df_dep = load_department_data(df_hosp, dep)

            if len(df_dep) < 30:  # Données insuffisantes
                continue

            # Calculer variance glissante (susceptibilité)
            df_dep['variance'] = calculate_rolling_variance(df_dep['nouveaux_deces_smooth'], window=WINDOW_SIZE)

            # Trouver pic de variance (point critique)
            peak_idx = find_variance_peak(df_dep['variance'])

            if peak_idx is None:
                continue

            peak_day = df_dep.loc[peak_idx, 'jour']

            # Calculer γ
            time_array = np.arange(len(df_dep))
            variance_array = df_dep['variance'].values

            gamma, r_squared, n_points, epsilon_range = calculate_gamma_exponent(
                time_array, variance_array, peak_idx
            )

            if gamma is None:
                continue

            # Pic de nouveaux décès (pour comparaison)
            cases_peak_idx = df_dep['nouveaux_deces_smooth'].idxmax()
            cases_peak_day = df_dep.loc[cases_peak_idx, 'jour']

            # Avance temporelle du pic de variance
            advance_days = (cases_peak_day - peak_day).days

            results.append({
                'departement': dep,
                'gamma': gamma,
                'r_squared': r_squared,
                'n_points': n_points,
                'epsilon_min': epsilon_range[0] if epsilon_range else None,
                'epsilon_max': epsilon_range[1] if epsilon_range else None,
                'pic_variance_jour': peak_day,
                'pic_cas_jour': cases_peak_day,
                'avance_jours': advance_days,
                'chi_max': df_dep['variance'].max()
            })

        except Exception as e:
            print(f"  ⚠ Erreur {dep}: {e}")
            continue

    return pd.DataFrame(results)

def analyze_specific_regions(df_hosp):
    """
    Analyse détaillée pour Grand Est et Île-de-France
    """
    regions = {
        'Grand Est': ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
        'Île-de-France': ['75', '77', '78', '91', '92', '93', '94', '95']
    }

    print("\n" + "=" * 80)
    print("ANALYSE DÉTAILLÉE DES RÉGIONS GRAND EST ET ÎLE-DE-FRANCE")
    print("=" * 80)

    for region_name, dep_codes in regions.items():
        print(f"\n{region_name}")
        print("-" * 80)

        # Agréger les données régionales
        df_region = df_hosp[df_hosp['dep'].isin(dep_codes)].copy()
        df_region = df_region[(df_region['jour'] >= WAVE1_START) & (df_region['jour'] <= WAVE1_END)]

        df_daily = df_region.groupby('jour').agg({
            'hosp': 'sum',
            'rea': 'sum',
            'dc': 'sum'
        }).reset_index()

        df_daily['jour'] = pd.to_datetime(df_daily['jour'])
        df_daily = df_daily.sort_values('jour').reset_index(drop=True)

        # Calculer les nouveaux décès quotidiens (comme dans l'analyse originale)
        df_daily['nouveaux_deces'] = df_daily['dc'].diff().fillna(0)

        # Lissage sur 7 jours (rolling mean) pour réduire le bruit
        df_daily['nouveaux_deces_smooth'] = df_daily['nouveaux_deces'].rolling(window=7, center=True).mean().fillna(0)

        # Variance glissante
        df_daily['variance'] = calculate_rolling_variance(df_daily['nouveaux_deces_smooth'], window=WINDOW_SIZE)

        # Pic de variance
        peak_idx = find_variance_peak(df_daily['variance'])
        peak_day = df_daily.loc[peak_idx, 'jour']

        print(f"  Point critique (pic variance) : {peak_day.strftime('%Y-%m-%d')} (J{peak_idx})")

        # Calculer γ
        time_array = np.arange(len(df_daily))
        variance_array = df_daily['variance'].values

        gamma, r_squared, n_points, epsilon_range = calculate_gamma_exponent(
            time_array, variance_array, peak_idx
        )

        if gamma is not None:
            print(f"  Exposant γ = {gamma:.3f} (R² = {r_squared:.3f}, {n_points} points)")
            print(f"  Plage ε : [{epsilon_range[0]:.1f}, {epsilon_range[1]:.1f}] jours")
        else:
            print(f"  ⚠ Régression échouée (données insuffisantes)")

        # Pic de décès
        deaths_peak_idx = df_daily['nouveaux_deces_smooth'].idxmax()
        deaths_peak_day = df_daily.loc[deaths_peak_idx, 'jour']
        advance_days = (deaths_peak_day - peak_day).days

        print(f"  Pic des décès : {deaths_peak_day.strftime('%Y-%m-%d')} (J{deaths_peak_idx})")
        print(f"  Avance du signal : +{advance_days} jours")

def plot_results(df_results):
    """
    Visualise les résultats de l'analyse
    """
    if len(df_results) == 0:
        print("Aucun résultat à visualiser")
        return

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Analyse de l'Exposant Critique γ (Méthode Physique)\n" +
                 f"Vague 1 - {len(df_results)} départements métropolitains",
                 fontsize=16, fontweight='bold')

    # A. Distribution de γ
    ax = axes[0, 0]
    gamma_values = df_results['gamma']
    ax.hist(gamma_values, bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
    ax.axvline(gamma_values.median(), color='red', linestyle='--', linewidth=2,
               label=f'Médiane = {gamma_values.median():.3f}')
    ax.axvline(1.24, color='orange', linestyle=':', linewidth=2, label='Ising 3D (γ=1.24)')
    ax.axvline(1.0, color='purple', linestyle=':', linewidth=2, label='Mean-field (γ=1.0)')
    ax.set_xlabel('Exposant γ', fontsize=12, fontweight='bold')
    ax.set_ylabel('Nombre de départements', fontsize=12, fontweight='bold')
    ax.set_title('A. Distribution de l\'exposant critique γ', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    # Statistiques
    stats_text = f"Moyenne : {gamma_values.mean():.3f} ± {gamma_values.std():.3f}\n"
    stats_text += f"Médiane : {gamma_values.median():.3f}\n"
    stats_text += f"Min : {gamma_values.min():.3f} | Max : {gamma_values.max():.3f}"
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # B. Qualité du fit (R²)
    ax = axes[0, 1]
    r2_values = df_results['r_squared']
    ax.hist(r2_values, bins=30, color='#A23B72', alpha=0.7, edgecolor='black')
    ax.axvline(r2_values.median(), color='red', linestyle='--', linewidth=2,
               label=f'Médiane = {r2_values.median():.3f}')
    ax.set_xlabel('Coefficient R²', fontsize=12, fontweight='bold')
    ax.set_ylabel('Nombre de départements', fontsize=12, fontweight='bold')
    ax.set_title('B. Qualité du fit log-log', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    # C. γ vs R² (validation)
    ax = axes[1, 0]
    scatter = ax.scatter(df_results['gamma'], df_results['r_squared'],
                        c=df_results['n_points'], cmap='viridis',
                        s=100, alpha=0.6, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('Exposant γ', fontsize=12, fontweight='bold')
    ax.set_ylabel('R²', fontsize=12, fontweight='bold')
    ax.set_title('C. Corrélation γ vs qualité du fit', fontsize=13, fontweight='bold')
    ax.axvline(1.24, color='orange', linestyle=':', alpha=0.5, label='Ising 3D')
    ax.axvline(1.0, color='purple', linestyle=':', alpha=0.5, label='Mean-field')
    ax.axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='R² = 0.5')
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Nombre de points', fontsize=10)

    # D. Avance temporelle du pic de variance
    ax = axes[1, 1]
    advance_values = df_results['avance_jours']
    ax.hist(advance_values, bins=30, color='#F18F01', alpha=0.7, edgecolor='black')
    ax.axvline(advance_values.median(), color='red', linestyle='--', linewidth=2,
               label=f'Médiane = {advance_values.median():.0f} jours')
    ax.set_xlabel('Avance du pic de variance (jours)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Nombre de départements', fontsize=12, fontweight='bold')
    ax.set_title('D. Signal précurseur : avance temporelle', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    output_file = "reports/exposant_gamma_physique.png"
    Path("reports").mkdir(exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualisation sauvegardée : {output_file}")
    plt.close()

def main():
    """
    Pipeline principal
    """
    # Analyser tous les départements
    df_results = analyze_all_departments()

    if len(df_results) == 0:
        print("Aucun département analysé avec succès")
        return

    # Statistiques globales
    print("\n" + "=" * 80)
    print("RÉSULTATS GLOBAUX")
    print("=" * 80)
    print(f"\nDépartements analysés : {len(df_results)}/96")
    print(f"\nExposant γ (susceptibilité critique) :")
    print(f"  • Moyenne : {df_results['gamma'].mean():.3f} ± {df_results['gamma'].std():.3f}")
    print(f"  • Médiane : {df_results['gamma'].median():.3f}")
    print(f"  • Plage : [{df_results['gamma'].min():.3f}, {df_results['gamma'].max():.3f}]")

    # Vérifier que γ > 0
    negative_gamma = (df_results['gamma'] < 0).sum()
    print(f"\n  • Départements avec γ < 0 : {negative_gamma} ({negative_gamma/len(df_results)*100:.1f}%)")
    print(f"  • Départements avec γ > 0 : {len(df_results) - negative_gamma} ({(1-negative_gamma/len(df_results))*100:.1f}%)")

    # Comparaison avec classes d'universalité
    print(f"\nComparaison avec classes d'universalité connues :")
    print(f"  • Ising 3D : γ = 1.24")
    print(f"  • Mean-field : γ = 1.0")
    print(f"  • Ising 2D : γ = 1.75")

    # Qualité du fit
    print(f"\nQualité du fit (R²) :")
    print(f"  • Moyenne : {df_results['r_squared'].mean():.3f}")
    print(f"  • Médiane : {df_results['r_squared'].median():.3f}")
    good_fit = (df_results['r_squared'] > 0.5).sum()
    print(f"  • Départements avec R² > 0.5 : {good_fit} ({good_fit/len(df_results)*100:.1f}%)")

    # Signal précurseur
    print(f"\nSignal précurseur (avance du pic de variance) :")
    print(f"  • Médiane : +{df_results['avance_jours'].median():.0f} jours")
    print(f"  • Plage : [{df_results['avance_jours'].min():.0f}, {df_results['avance_jours'].max():.0f}] jours")

    # Sauvegarder résultats
    output_csv = "data/resultats_gamma_physique.csv"
    df_results.to_csv(output_csv, index=False)
    print(f"\n✓ Résultats sauvegardés : {output_csv}")

    # Analyse régionale détaillée
    df_hosp = pd.read_csv(DATA_FILE, sep=';')
    df_hosp['jour'] = pd.to_datetime(df_hosp['jour'])
    analyze_specific_regions(df_hosp)

    # Visualisation
    plot_results(df_results)

    print("\n" + "=" * 80)
    print("ANALYSE TERMINÉE")
    print("=" * 80)

if __name__ == "__main__":
    main()
