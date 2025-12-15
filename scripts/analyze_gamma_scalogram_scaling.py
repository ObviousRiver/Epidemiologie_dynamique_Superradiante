#!/usr/bin/env python3
"""
Scalogramme γ(t, window_χ) - Méthode Rigoureuse par Scaling

MÉTHODOLOGIE CORRIGÉE:
Pour chaque temps t avant le pic de χ:
  1. Calculer χ(t, w) pour différents window_χ = [2, 3, ..., w_max]
  2. Régression log-log : log(χ) vs log(w)
     → log(χ) = log(A) - γ(t) × log(w)
     → Pente = -γ(t)
  3. Contrainte: ne pas dépasser t_pic (sinon mélange avant/après pic)

AVANTAGES:
- Régression linéaire robuste (2 paramètres)
- Séparation claire A et γ
- Calcul purement local (pas de t_c à deviner)
- Interprétation: scaling critique en échelle

DONNÉES:
- France nationale (SPF)
- 13 régions métropolitaines (SPF)
- Variable: incid_rea (entrées réanimation, proxy décès)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm, Normalize
from scipy.stats import linregress
import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel


# Régions métropolitaines SPF
REGIONS_SPF = [
    'Ile-de-France',
    'Grand-Est',
    'Auvergne-Rhône-Alpes',
    'Hauts-de-France',
    'Provence-Alpes-Côte d\'Azur',
    'Occitanie',
    'Nouvelle-Aquitaine',
    'Pays de la Loire',
    'Bretagne',
    'Normandie',
    'Bourgogne-Franche-Comté',
    'Centre-Val de Loire',
    'Corse'
]


def load_spf_national(start_date='2020-03-01', end_date='2020-07-31'):
    """Charge données France nationale (agrégation toutes régions)."""
    df = pd.read_csv('data/raw/covid-hospit-incid-reg-2023-03-31-18h01.csv',
                     sep=';', parse_dates=['jour'], encoding='latin-1')

    # Agréger toutes les régions métropolitaines
    df_metro = df[df['nomReg'].isin(REGIONS_SPF)].copy()

    # Somme par jour
    df_nat = df_metro.groupby('jour')['incid_rea'].sum().reset_index()
    df_nat.columns = ['date', 'new_rea']
    df_nat = df_nat.set_index('date').sort_index()

    # Filtrer période
    df_nat = df_nat.loc[start_date:end_date]
    df_nat['new_rea'] = df_nat['new_rea'].clip(lower=0)

    return df_nat


def load_spf_region(region_name, start_date='2020-03-01', end_date='2020-07-31'):
    """Charge données région SPF."""
    df = pd.read_csv('data/raw/covid-hospit-incid-reg-2023-03-31-18h01.csv',
                     sep=';', parse_dates=['jour'], encoding='latin-1')

    df_reg = df[df['nomReg'] == region_name].copy()
    if len(df_reg) == 0:
        raise ValueError(f"Région '{region_name}' non trouvée")

    df_reg = df_reg[['jour', 'incid_rea']].copy()
    df_reg.columns = ['date', 'new_rea']
    df_reg = df_reg.set_index('date').sort_index()

    df_reg = df_reg.loc[start_date:end_date]
    df_reg['new_rea'] = df_reg['new_rea'].clip(lower=0)

    return df_reg


def calculate_susceptibility(signal, window):
    """Calcule χ(t) = variance glissante sur signal SR."""
    chi = pd.Series(signal).rolling(window=window, center=True).var()
    return chi.fillna(0).values


def compute_gamma_scalogram_scaling(t_data, signal_sr, dates,
                                     window_chi_values=list(range(2, 21)),
                                     min_points_regression=3,
                                     debug=False):
    """
    Calcule γ(t, window_χ) par méthode de scaling.

    Pour chaque t:
      - Calculer χ(t, w) pour différents w
      - Régression log(χ) vs log(w) → pente = -γ(t)

    Args:
        t_data: Temps (array)
        signal_sr: Signal SR (array)
        dates: Dates correspondantes
        window_chi_values: Liste window_χ à tester
        min_points_regression: Nombre min de points pour régression valide

    Returns:
        scalogram: dict avec structure γ(t), R²(t), etc.
    """
    n = len(t_data)

    # Calculer χ pour tous les window_χ
    print("  Calcul χ(t, window_χ)...")
    chi_curves = {}
    for w in window_chi_values:
        chi_curves[w] = calculate_susceptibility(signal_sr, window=w)

    # Trouver pic global χ_max (référence pour contrainte)
    chi_max_global = 0
    t_pic_global = 0
    for w, chi in chi_curves.items():
        peak_idx = np.argmax(chi)
        if chi[peak_idx] > chi_max_global:
            chi_max_global = chi[peak_idx]
            t_pic_global = t_data[peak_idx]

    print(f"    t_pic(χ_max) = {t_pic_global:.0f}j ({dates[int(t_pic_global)].date()})")

    # Scalogramme : pour chaque t, régression log-log
    print("  Régression γ(t) par scaling...")

    t_centers = []
    gammas = []
    r2s = []
    n_points_fit = []

    # Balayage temporel avec step=1j
    for t_center_idx in range(0, n):
        t_center = t_data[t_center_idx]

        # Contrainte: ne pas dépasser t_pic (avec petite marge)
        # Pour chaque window_χ, vérifier que t_center + w/2 < t_pic + marge
        margin = 5  # jours de marge après pic

        chi_values = []
        w_values = []

        for w in window_chi_values:
            # Contrainte locale: fenêtre ne doit pas trop dépasser pic
            if t_center + w/2 >= t_pic_global + margin:
                continue

            # Vérifier que χ > 0 (sinon log impossible)
            chi_val = chi_curves[w][t_center_idx]
            if chi_val <= 0:
                continue

            chi_values.append(chi_val)
            w_values.append(w)

        # Debug pour premier t qui a des points
        if debug and len(w_values) >= min_points_regression and len(t_centers) == 0:
            print(f"    DEBUG t={t_center:.0f}: {len(w_values)} windows valides")
            print(f"      w = {w_values}")
            print(f"      χ = {[f'{c:.2e}' for c in chi_values]}")

        # Régression log-log si assez de points
        if len(w_values) >= min_points_regression:
            log_w = np.log(w_values)
            log_chi = np.log(chi_values)

            # Régression linéaire
            slope, intercept, r_value, p_value, std_err = linregress(log_w, log_chi)

            gamma = -slope  # γ = -pente
            r2 = r_value**2

            # Debug: afficher premier gamma
            if debug and len(t_centers) == 0:
                print(f"    FIRST FIT: γ={gamma:.3f}, R²={r2:.3f}, slope={slope:.3f}")

            # Filtrer fits aberrants (assouplir temporairement)
            if -3.0 <= gamma <= 3.0 and r2 > 0.3:
                t_centers.append(t_center)
                gammas.append(gamma)
                r2s.append(r2)
                n_points_fit.append(len(w_values))

    print(f"    {len(gammas)} points γ valides")

    return {
        't_centers': np.array(t_centers),
        'gammas': np.array(gammas),
        'r2s': np.array(r2s),
        'n_points': np.array(n_points_fit),
        't_pic_global': t_pic_global,
        'chi_curves': chi_curves,
        'dates': dates
    }


def plot_scalogram(scalogram, signal_sr, entity_name, output_dir):
    """Génère figure scalogramme + analyses."""

    t_centers = scalogram['t_centers']
    gammas = scalogram['gammas']
    r2s = scalogram['r2s']
    n_points = scalogram['n_points']
    t_pic = scalogram['t_pic_global']
    dates = scalogram['dates']

    if len(gammas) == 0:
        print(f"    ⚠️  Pas de points γ valides pour {entity_name}")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Signal SR
    ax1 = axes[0, 0]
    ax1.plot(dates, signal_sr, '-', linewidth=2, color='red', label='SR model')
    ax1.axvline(dates[int(t_pic)], color='purple', linestyle='--',
                alpha=0.5, label=f'Pic χ (t={t_pic:.0f}j)')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Entrées réanimation/jour')
    ax1.set_title(f'{entity_name} - Signal SR')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Panel 2: γ(t) avec code couleur R²
    ax2 = axes[0, 1]
    scatter = ax2.scatter(t_centers, gammas, c=r2s, cmap='viridis',
                         s=50, alpha=0.7, vmin=0.5, vmax=1.0)
    ax2.axhline(y=2.4, color='red', linestyle='--', linewidth=2,
                alpha=0.5, label='γ = 2.4 (référence)')
    ax2.axvline(x=t_pic, color='purple', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Temps (jours)')
    ax2.set_ylabel('γ (exposant critique)')
    ax2.set_title('γ(t) par méthode scaling log-log')
    ax2.set_ylim([0, 3.5])
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax2, label='R² régression')

    # Panel 3: Nombre de points par fit
    ax3 = axes[1, 0]
    ax3.plot(t_centers, n_points, 'o-', color='steelblue', alpha=0.7)
    ax3.axvline(x=t_pic, color='purple', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Temps (jours)')
    ax3.set_ylabel('Nb points window_χ utilisés')
    ax3.set_title('Contrainte triangulaire (moins de points près du pic)')
    ax3.grid(True, alpha=0.3)

    # Panel 4: Distribution γ
    ax4 = axes[1, 1]
    ax4.hist(gammas, bins=20, color='steelblue', alpha=0.7, edgecolor='black')
    ax4.axvline(x=2.4, color='red', linestyle='--', linewidth=2, label='γ = 2.4')
    ax4.axvline(x=np.mean(gammas), color='orange', linestyle='-', linewidth=2,
                label=f'Moyenne: {np.mean(gammas):.2f}')
    ax4.set_xlabel('γ')
    ax4.set_ylabel('Nombre de points temporels')
    ax4.set_title('Distribution γ')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # Statistiques
    gamma_mean = np.mean(gammas)
    gamma_std = np.std(gammas)
    gamma_med = np.median(gammas)
    r2_mean = np.mean(r2s)

    plt.suptitle(f'{entity_name} - Scalogramme Scaling\nγ = {gamma_mean:.2f} ± {gamma_std:.2f} (médiane: {gamma_med:.2f}, R²: {r2_mean:.3f})',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()

    # Sauvegarder
    entity_slug = entity_name.lower().replace(' ', '_').replace("'", '')
    filename = f"{output_dir}/{entity_slug}_scalogram_scaling.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"    ✅ {filename}")
    plt.close()

    return {
        'entity': entity_name,
        'gamma_mean': gamma_mean,
        'gamma_std': gamma_std,
        'gamma_median': gamma_med,
        'r2_mean': r2_mean,
        'n_points': len(gammas)
    }


def analyze_entity(entity_name, data_loader, output_dir):
    """Analyse complète scalogramme pour une entité (France ou région)."""

    print(f"\n{'='*70}")
    print(f"Entité: {entity_name}")
    print(f"{'='*70}")

    # 1. Charger données
    try:
        df = data_loader()
        signal_real = df['new_rea'].values
        dates = df.index
        t_data = np.arange(len(signal_real))

        print(f"  Total entrées réa: {np.sum(signal_real):.0f}")
        print(f"  Pic: {np.max(signal_real):.0f} entrées/jour")

    except Exception as e:
        print(f"  ❌ Erreur chargement: {e}")
        return None

    # 2. Fit SR
    print(f"  Fit SR model...")
    sr_model = SuperRadiantModel(n_modes=3)
    try:
        sr_model.fit(t_data, signal_real)
        signal_sr = sr_model.predict(t_data)
        r2_sr = 1 - np.sum((signal_real - signal_sr)**2) / np.sum((signal_real - np.mean(signal_real))**2)
        print(f"    R²(SR) = {r2_sr:.3f}")
    except Exception as e:
        print(f"    ❌ SR fit failed: {e}")
        return None

    # 3. Scalogramme scaling
    print(f"  Scalogramme γ(t) par scaling...")
    scalogram = compute_gamma_scalogram_scaling(t_data, signal_sr, dates, debug=True)

    if len(scalogram['gammas']) == 0:
        print(f"    ❌ Aucun point γ valide")
        return None

    # 4. Visualisation
    print(f"  Génération figure...")
    result = plot_scalogram(scalogram, signal_sr, entity_name, output_dir)

    return result


def main():
    print("="*70)
    print("SCALOGRAMME γ(t) - MÉTHODE SCALING RIGOUREUSE")
    print("="*70)
    print()
    print("Méthodologie:")
    print("  - Pour chaque t: χ(t, w) calculé pour w ∈ [2..20]j")
    print("  - Régression log(χ) vs log(w) → pente = -γ(t)")
    print("  - Contrainte: ne pas dépasser t_pic (triangularité)")
    print("  - Résolution temporelle: 1 jour")
    print()
    print("Données:")
    print("  - Source: SPF (VRAIES DONNÉES)")
    print("  - Variable: incid_rea (entrées réanimation)")
    print("  - France nationale + 13 régions métropolitaines")
    print()

    output_dir = 'results/scalogram_scaling_spf'
    os.makedirs(output_dir, exist_ok=True)

    results = []

    # France nationale
    result = analyze_entity(
        'France Nationale',
        lambda: load_spf_national(),
        output_dir
    )
    if result:
        results.append(result)

    # Régions
    for region_name in REGIONS_SPF:
        result = analyze_entity(
            region_name,
            lambda r=region_name: load_spf_region(r),
            output_dir
        )
        if result:
            results.append(result)

    # Synthèse
    print()
    print("="*70)
    print(f"SYNTHÈSE - {len(results)} entités validées")
    print("="*70)
    print()

    if len(results) > 0:
        print(f"{'Entité':<30} {'γ moyen':>10} {'σ(γ)':>8} {'γ médian':>10} {'R²':>6} {'N pts':>6}")
        print("─"*80)

        for r in results:
            print(f"{r['entity']:<30} {r['gamma_mean']:>10.2f} {r['gamma_std']:>8.2f} "
                  f"{r['gamma_median']:>10.2f} {r['r2_mean']:>6.3f} {r['n_points']:>6d}")

        print("─"*80)

        # Stats globales
        all_gammas = [r['gamma_mean'] for r in results]
        gamma_global_mean = np.mean(all_gammas)
        gamma_global_std = np.std(all_gammas)

        print(f"{'GLOBAL':<30} {gamma_global_mean:>10.2f} {gamma_global_std:>8.2f}")
        print()

        # Analyse
        n_near_24 = sum(1 for g in all_gammas if abs(g - 2.4) < 0.5)
        frac_near_24 = n_near_24 / len(all_gammas)

        print(f"Entités avec γ ≈ 2.4 (±0.5): {n_near_24}/{len(results)} ({frac_near_24:.1%})")
        print()

        if frac_near_24 > 0.5:
            print("✅ Comportement critique γ ≈ 2.4 observé sur majorité des entités")
        elif frac_near_24 > 0.3:
            print("⚠️  Comportement γ ≈ 2.4 partiel (minorité significative)")
        else:
            print("❌ Comportement γ ≈ 2.4 rare ou absent")

        print()
        print(f"Résultats dans: {output_dir}/")

    else:
        print("❌ Aucune entité validée")


if __name__ == "__main__":
    main()
