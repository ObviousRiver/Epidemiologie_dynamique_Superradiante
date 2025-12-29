#!/usr/bin/env python3
"""
Test hypothèse fenêtrage sur régions françaises - VRAIES DONNÉES SPF

HYPOTHÈSE (utilisateur):
- L'échec γ ≈ 0.7 régions est dû à window_χ = 14j (zone décroissance)
- Scalogramme montre optimal = 7-10j
- Refaire analyse avec window_χ = 7j sur VRAIES données SPF

DONNÉES:
- Source: Santé Publique France (SPF)
- Fichier: covid-hospit-incid-reg-2023-03-31-18h01.csv
- Variable: incid_rea (entrées réanimation, proxy décès régionaux)
- Période: Vague 1 (2020-03-01 → 2020-07-31)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel


# Régions métropolitaines (noms exacts du CSV SPF)
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


def load_spf_region(region_name, start_date='2020-03-01', end_date='2020-07-31'):
    """
    Charge VRAIES données SPF pour une région.

    Returns:
        DataFrame avec ['date', 'new_rea'] (entrées réanimation)
    """
    # Charger données régionales SPF
    df = pd.read_csv('data/raw/covid-hospit-incid-reg-2023-03-31-18h01.csv',
                     sep=';', parse_dates=['jour'], encoding='latin-1')

    # Filtrer région
    df_reg = df[df['nomReg'] == region_name].copy()

    if len(df_reg) == 0:
        raise ValueError(f"Région '{region_name}' non trouvée")

    # Extraire incid_rea (entrées réanimation)
    df_reg = df_reg[['jour', 'incid_rea']].copy()
    df_reg.columns = ['date', 'new_rea']
    df_reg = df_reg.set_index('date').sort_index()

    # Filtrer période
    df_reg = df_reg.loc[start_date:end_date]

    # Clip négatifs (corrections SPF)
    df_reg['new_rea'] = df_reg['new_rea'].clip(lower=0)

    return df_reg


def calculate_susceptibility(signal, window=7):
    """Calcule χ(t) = variance glissante avec fenêtre OPTIMALE."""
    chi = pd.Series(signal).rolling(window=window, center=True).var()
    return chi.fillna(0).values


def fit_power_law(t_data, chi, t_peak_chi):
    """Fit χ ~ (t_c - t)^(-γ) sur phase montante."""

    # Seuil 10% du max
    chi_max = np.max(chi)
    threshold = 0.1 * chi_max

    # Phase montante
    rising_mask = (chi > threshold) & (t_data < t_peak_chi)

    if np.sum(rising_mask) < 5:
        return None, None, None

    t_fit = t_data[rising_mask]
    chi_fit = chi[rising_mask]

    # Fonction
    def power_law(t, A, gamma, tc):
        return A * (tc - t)**(-gamma)

    try:
        # Initial guess
        p0 = [chi_max, 1.0, t_peak_chi + 2]

        # Bounds
        bounds = ([0.1 * chi_max, 0.1, t_peak_chi],
                 [10 * chi_max, 3.0, t_peak_chi + 20])

        popt, _ = curve_fit(power_law, t_fit, chi_fit, p0=p0, bounds=bounds, maxfev=5000)

        A, gamma, tc = popt

        # R²
        chi_pred = power_law(t_fit, *popt)
        ss_res = np.sum((chi_fit - chi_pred)**2)
        ss_tot = np.sum((chi_fit - np.mean(chi_fit))**2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return gamma, tc, r2

    except:
        return None, None, None


def analyze_region_spf(region_name, window_chi=7, start_date='2020-03-01', end_date='2020-07-31'):
    """
    Analyse γ pour une région SPF avec fenêtre optimale.

    Args:
        region_name: Nom région SPF
        window_chi: Fenêtre χ (7j optimal)
    """
    print(f"\n{'='*70}")
    print(f"Région: {region_name}")
    print(f"Fenêtre χ: {window_chi}j (OPTIMAL)")
    print(f"{'='*70}")

    # 1. Charger VRAIES données SPF
    try:
        df_reg = load_spf_region(region_name, start_date, end_date)
        signal_real = df_reg['new_rea'].values
        dates = df_reg.index
        t_data = np.arange(len(signal_real))

        print(f"  Source: SPF covid-hospit-incid-reg (VRAIES DONNÉES)")
        print(f"  Variable: incid_rea (entrées réanimation)")
        print(f"  Total entrées réa: {np.sum(signal_real):.0f}")
        print(f"  Pic: {np.max(signal_real):.0f} entrées/jour")

    except Exception as e:
        print(f"  ❌ Erreur chargement SPF: {e}")
        return None

    # 2. Fit SR
    print(f"  Fitting SR model...")
    sr_model = SuperRadiantModel(n_modes=3)
    try:
        sr_model.fit(t_data, signal_real)
        signal_sr = sr_model.predict(t_data)
        r2_sr = 1 - np.sum((signal_real - signal_sr)**2) / np.sum((signal_real - np.mean(signal_real))**2)
        print(f"    R²(SR) = {r2_sr:.3f}")
    except Exception as e:
        print(f"    ❌ SR fit failed: {e}")
        return None

    # 3. Susceptibilité avec fenêtre OPTIMALE
    print(f"  Calculating χ(SR) with window={window_chi}j (OPTIMAL)...")
    chi_sr = calculate_susceptibility(signal_sr, window=window_chi)

    # Pic χ
    idx_peak_chi = np.argmax(chi_sr)
    t_peak_chi = t_data[idx_peak_chi]
    chi_max = chi_sr[idx_peak_chi]

    print(f"    χ_max = {chi_max:.2e} at t={t_peak_chi:.0f}j ({dates[idx_peak_chi].date()})")

    # 4. Fit γ
    print(f"  Fitting γ...")
    gamma, tc, r2 = fit_power_law(t_data, chi_sr, t_peak_chi)

    if gamma is not None:
        print(f"    ✅ γ = {gamma:.2f}, t_c = {tc:.1f}j, R² = {r2:.3f}")
    else:
        print(f"    ❌ Fit failed")
        return None

    # 5. Visualisation
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Signal SR
    ax1 = axes[0, 0]
    ax1.plot(dates, signal_real, 'o', alpha=0.5, label='SPF (incid_rea)', markersize=3)
    ax1.plot(dates, signal_sr, '-', linewidth=2, label='SR model', color='red')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Entrées réanimation/jour')
    ax1.set_title(f'{region_name} - Signal SR (R²={r2_sr:.3f})')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Panel 2: χ(SR)
    ax2 = axes[0, 1]
    ax2.plot(dates, chi_sr, '-', linewidth=2, color='purple')
    ax2.axvline(dates[idx_peak_chi], color='red', linestyle='--', alpha=0.5,
                label=f'Pic χ ({dates[idx_peak_chi].date()})')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('χ(SR)')
    ax2.set_title(f'Susceptibilité χ(SR) [window={window_chi}j OPTIMAL]')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Panel 3: Fit γ
    ax3 = axes[1, 0]

    chi_max = np.max(chi_sr)
    threshold = 0.1 * chi_max
    rising_mask = (chi_sr > threshold) & (t_data < t_peak_chi)

    t_fit = t_data[rising_mask]
    chi_fit = chi_sr[rising_mask]

    if gamma is not None:
        def power_law(t, A, gamma, tc):
            return A * (tc - t)**(-gamma)

        chi_pred = power_law(t_fit, chi_max * 0.1, gamma, tc)

        ax3.plot(t_fit, chi_fit, 'o', alpha=0.7, label='χ(SR) phase montante')
        ax3.plot(t_fit, chi_pred, '-', linewidth=2, color='red',
                label=f'Fit: γ={gamma:.2f}, R²={r2:.3f}')
        ax3.set_xlabel('Temps (jours)')
        ax3.set_ylabel('χ(SR)')
        ax3.set_title('Fit χ ~ (t_c - t)^(-γ)')
        ax3.set_yscale('log')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

    # Panel 4: Résumé
    ax4 = axes[1, 1]
    ax4.axis('off')

    summary = f"""
Région: {region_name}
{'─'*40}

DONNÉES:
  Source: SPF (VRAIES DONNÉES)
  Variable: incid_rea
  Total entrées réa: {np.sum(signal_real):.0f}
  Pic: {np.max(signal_real):.0f} entrées/jour

MODÈLE SR:
  R²(SR): {r2_sr:.3f}

SUSCEPTIBILITÉ:
  Fenêtre χ: {window_chi}j (OPTIMAL)
  χ_max: {chi_max:.2e}

EXPOSANT CRITIQUE:
  γ = {gamma:.2f}
  t_c = {tc:.1f}j
  R²(fit) = {r2:.3f}

{'─'*40}
COMPARAISON FENÊTRAGE:
  Précédent (w=14j): γ ≈ 0.7
  Optimal (w={window_chi}j): γ = {gamma:.2f}

  {'✅ γ ≈ 2.4 !' if abs(gamma - 2.4) < 0.5 else '⚠️ γ < 2.4'}
    """

    ax4.text(0.05, 0.5, summary, transform=ax4.transAxes,
             fontsize=10, verticalalignment='center', family='monospace')

    plt.suptitle(f'{region_name} - VRAIES DONNÉES SPF - Fenêtre optimale χ={window_chi}j',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()

    # Sauvegarder
    output_dir = 'results/regions_spf_optimal_window'
    os.makedirs(output_dir, exist_ok=True)

    region_slug = region_name.lower().replace(' ', '_').replace("'", '').replace('\'', '')
    filename = f"{output_dir}/{region_slug}_w{window_chi}j_spf.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"  ✅ Figure: {filename}")
    plt.close()

    return {
        'region': region_name,
        'window_chi': window_chi,
        'gamma': gamma,
        'tc': tc,
        'r2_gamma': r2,
        'r2_sr': r2_sr,
        'chi_max': chi_max,
        'total_rea': np.sum(signal_real),
        'peak_rea': np.max(signal_real)
    }


def main():
    print("="*70)
    print("TEST HYPOTHÈSE FENÊTRAGE - RÉGIONS SPF - VRAIES DONNÉES")
    print("="*70)
    print()
    print("Hypothèse (utilisateur):")
    print("  - Échec γ ≈ 0.7 dû à window_χ = 14j (zone décroissance)")
    print("  - Scalogramme: fenêtre optimale = 7-10j")
    print("  - Test: γ devrait augmenter avec w=7j")
    print()
    print("Données:")
    print("  - Source: Santé Publique France (SPF)")
    print("  - Fichier: covid-hospit-incid-reg-2023-03-31-18h01.csv")
    print("  - Variable: incid_rea (entrées réanimation)")
    print("  - 5 régions principales")
    print()

    window_chi_optimal = 7
    results = []

    for region_name in REGIONS_SPF:
        result = analyze_region_spf(region_name, window_chi=window_chi_optimal)
        if result is not None:
            results.append(result)

    # Synthèse
    print()
    print("="*70)
    print(f"SYNTHÈSE - {len(results)} RÉGIONS SPF avec window_χ = {window_chi_optimal}j")
    print("="*70)
    print()

    if len(results) > 0:
        gammas = [r['gamma'] for r in results]
        r2s = [r['r2_gamma'] for r in results]

        gamma_mean = np.mean(gammas)
        gamma_std = np.std(gammas)
        cv = gamma_std / gamma_mean * 100 if gamma_mean > 0 else 0

        print(f"N validés: {len(results)}/{len(REGIONS_SPF)}")
        print()
        print("Résultats par région:")
        print(f"{'Région':<30} {'γ':>6} {'R²':>6} {'Total réa':>10}")
        print("─"*60)
        for r in results:
            print(f"{r['region']:<30} {r['gamma']:>6.2f} {r['r2_gamma']:>6.3f} {r['total_rea']:>10.0f}")
        print("─"*60)
        print(f"{'MOYENNE':<30} {gamma_mean:>6.2f}")
        print(f"{'ÉCART-TYPE':<30} {gamma_std:>6.2f}")
        print(f"{'CV':<30} {cv:>5.1f}%")
        print()

        # Comparaison fenêtrage
        print("COMPARAISON FENÊTRAGE:")
        print()
        print("| Fenêtre χ | γ moyen | σ(γ) | CV | Verdict |")
        print("|-----------|---------|------|--------|---------|")
        print(f"| **14j** (précédent) | 0.71 | 0.32 | 45.9% | ❌ Échec |")
        print(f"| **{window_chi_optimal}j** (optimal) | {gamma_mean:.2f} | {gamma_std:.2f} | {cv:.1f}% | ", end='')

        if abs(gamma_mean - 2.4) < 0.5 and cv < 30:
            print("✅ SUCCÈS! |")
            print()
            print("✅✅✅ HYPOTHÈSE VALIDÉE! ✅✅✅")
            print("   L'échec γ ≈ 0.7 était un ARTEFACT DE FENÊTRAGE")
            print("   Avec fenêtre optimale 7j → γ ≈ 2.4 RETROUVÉ sur RÉGIONS!")
            print("   → Pas de seuil critique de taille système")
            print("   → γ ≈ 2.4 est UNIVERSEL (pays ET régions)")
        elif gamma_mean > 1.5:
            print("⚠️ Partiel |")
            print()
            print("⚠️ AMÉLIORATION PARTIELLE")
            print(f"   γ augmente de 0.7 → {gamma_mean:.2f}")
            print("   Mais reste < 2.4")
            print("   → Fenêtrage important mais pas seul facteur")
        else:
            print("❌ Échec |")
            print()
            print("❌ HYPOTHÈSE REJETÉE")
            print("   γ reste faible même avec fenêtre optimale")
            print("   → Problème de taille système confirmé")
    else:
        print("❌ Aucune région validée")

    print()


if __name__ == "__main__":
    main()
