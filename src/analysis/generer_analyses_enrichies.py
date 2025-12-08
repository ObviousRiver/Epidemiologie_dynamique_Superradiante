#!/usr/bin/env python3
"""
Générateur Analyses Enrichies France
=====================================

Génère les visualisations enrichies (susceptibilité, spectre, Nyquist, résidus)
pour les territoires sélectionnés.

Stratégie :
- Recalcule fits à la volée (plus simple que stockage)
- Sélection intelligente basée sur seuil décès
- Départements : > 15 décès/jour (statistique robuste)
- Régions : toutes (données suffisantes)
- National : complet

Output : PNG par territoire dans results/france_enriched/
"""

import sys
sys.path.append('src')

from analyse_france_multi_echelle import (
    load_spf_data, extract_departement_deaths, extract_region_deaths,
    extract_national_deaths, fit_superradiant, SIRModel
)
from analyse_france_enrichie import (
    plot_enriched_analysis, calculate_susceptibility, extract_gamma
)

import numpy as np
import pandas as pd
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

SEUIL_DEPT = 15.0  # Décès/jour minimum pour départements
OUTPUT_DIR = 'results/france_enriched'

# Départements et régions clés à analyser prioritairement
DEPTS_PRIORITAIRES = ['75', '92', '93', '94', '67', '68', '13', '69', '33', '59']
REGIONS_PRIORITAIRES = ['Île-de-France', 'Grand Est', 'Hauts-de-France',
                        'Provence-Alpes-Côte d\'Azur', 'Auvergne-Rhône-Alpes']

# ============================================================================
# ANALYSE COMPLÈTE D'UN TERRITOIRE
# ============================================================================

def analyze_territory_full(t_data, y_data, location_name, population):
    """
    Analyse complète avec recalcul fits.

    Returns:
        result dict complet avec fits
    """
    max_deaths = np.max(y_data)

    # Fit SR
    params_sr3, fit_sr3, rms_sr3 = fit_superradiant(t_data, y_data, n_modes=3, max_value=max_deaths)
    params_sr4, fit_sr4, rms_sr4 = fit_superradiant(t_data, y_data, n_modes=4, max_value=max_deaths)

    if rms_sr3 <= rms_sr4:
        params_sr, fit_sr, rms_sr, n_modes_sr = params_sr3, fit_sr3, rms_sr3, 3
    else:
        params_sr, fit_sr, rms_sr, n_modes_sr = params_sr4, fit_sr4, rms_sr4, 4

    # Fit SIR
    sir = SIRModel(population=population, IFR=0.01)
    params_sir, fit_sir, rms_sir = sir.fit(t_data, y_data)

    if rms_sir == np.inf:
        params_sir = None
        fit_sir = None

    # Ratio
    ratio = rms_sir / rms_sr if rms_sr > 0 and rms_sir < np.inf else np.nan
    winner = "SR" if ratio > 1.0 else "SIR"

    # Susceptibilité
    t_chi, chi = calculate_susceptibility(y_data, window=21)
    gamma, t_c, R2_gamma = extract_gamma(t_chi, chi)

    result = {
        'location': location_name,
        'population': population,
        'max_deaths': max_deaths,
        'rms_sr': rms_sr,
        'rms_sir': rms_sir,
        'ratio': ratio,
        'winner': winner,
        'n_modes_sr': n_modes_sr,
        'params_sr': params_sr,
        'fit_sr': fit_sr,
        'params_sir': params_sir,
        'fit_sir': fit_sir,
        'gamma': gamma,
        't_c_gamma': t_c,
        'R2_gamma': R2_gamma
    }

    return result


# ============================================================================
# GÉNÉRATION ANALYSES ENRICHIES
# ============================================================================

def main():
    print("="*80)
    print("🔬 GÉNÉRATION ANALYSES ENRICHIES FRANCE")
    print("="*80)

    # Créer répertoire output
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Charger données SPF
    df_spf = load_spf_data()

    if df_spf is None:
        print("❌ Impossible de charger données SPF")
        return

    # Charger résultats existants pour sélection
    df_dept = pd.read_csv('results/france_departements_consolidee.csv')
    df_region = pd.read_csv('results/france_regions_consolidee.csv')

    # ========================================================================
    # 1. DÉPARTEMENTS SÉLECTIONNÉS
    # ========================================================================

    print(f"\n📍 DÉPARTEMENTS (seuil > {SEUIL_DEPT} décès/jour)")
    print("-" * 80)

    # Sélection départements
    df_dept_selected = df_dept[
        (df_dept['max_deaths'] > SEUIL_DEPT) |
        (df_dept['departement'].isin(DEPTS_PRIORITAIRES))
    ].copy()

    print(f"   Sélectionnés : {len(df_dept_selected)} départements")
    print(f"   (dont {len([d for d in DEPTS_PRIORITAIRES if d in df_dept_selected['departement'].values])} prioritaires)")

    for idx, row in df_dept_selected.iterrows():
        dept_code = row['departement']
        is_priority = dept_code in DEPTS_PRIORITAIRES
        marker = "⭐" if is_priority else "  "

        print(f"\n{marker} 🔍 Département {dept_code} ({row['max_deaths']:.1f} décès/j max)")

        # Charger données
        t_data, y_data, dates = extract_departement_deaths(df_spf, dept_code)

        if t_data is None or len(t_data) < 50:
            print(f"      ⚠️  Données insuffisantes")
            continue

        # Estimer population
        region = next((r for r, depts in {
            'Île-de-France': ['75', '77', '78', '91', '92', '93', '94', '95'],
            'Grand Est': ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
            # ... autres régions
        }.items() if dept_code in depts), None)

        pop_dept = row['population'] if 'population' in row else 500000

        # Analyse complète
        print(f"      Recalcul fits...")
        result = analyze_territory_full(t_data, y_data, f"Département {dept_code}", pop_dept)

        # Générer visualisation
        output_file = os.path.join(OUTPUT_DIR, f"dept_{dept_code}_enriched.png")
        plot_enriched_analysis(f"Département {dept_code}", t_data, y_data, result, output_file)

        print(f"      ✅ Ratio SR/SIR : {result['ratio']:.2f}×, γ = {result['gamma']:.3f}")

    # ========================================================================
    # 2. RÉGIONS PRIORITAIRES
    # ========================================================================

    print(f"\n\n📍 RÉGIONS PRIORITAIRES ({len(REGIONS_PRIORITAIRES)})")
    print("-" * 80)

    df_region_selected = df_region[df_region['region'].isin(REGIONS_PRIORITAIRES)].copy()

    for idx, row in df_region_selected.iterrows():
        region_name = row['region']

        print(f"\n⭐ 🔍 {region_name} ({row['max_deaths']:.1f} décès/j max)")

        # Charger données
        t_data, y_data, dates = extract_region_deaths(df_spf, region_name)

        if t_data is None:
            print(f"      ⚠️  Données insuffisantes")
            continue

        pop_region = row['population'] if 'population' in row else 5e6

        # Analyse complète
        print(f"      Recalcul fits...")
        result = analyze_territory_full(t_data, y_data, region_name, pop_region)

        # Générer visualisation
        safe_name = region_name.replace(' ', '_').replace("'", '_').replace('-', '_')
        output_file = os.path.join(OUTPUT_DIR, f"region_{safe_name}_enriched.png")
        plot_enriched_analysis(region_name, t_data, y_data, result, output_file)

        print(f"      ✅ Ratio SR/SIR : {result['ratio']:.2f}×, γ = {result['gamma']:.3f}")

    # ========================================================================
    # 3. NATIONAL (France entière)
    # ========================================================================

    print(f"\n\n📍 NATIONAL (France)")
    print("-" * 80)

    t_data, y_data, dates = extract_national_deaths(df_spf)

    if t_data is not None:
        print(f"   🇫🇷 France (max {np.max(y_data):.1f} décès/j)")
        print(f"      Recalcul fits...")

        result = analyze_territory_full(t_data, y_data, "France", 67e6)

        output_file = os.path.join(OUTPUT_DIR, "france_national_enriched.png")
        plot_enriched_analysis("France (National)", t_data, y_data, result, output_file)

        print(f"      ✅ Ratio SR/SIR : {result['ratio']:.2f}×, γ = {result['gamma']:.3f}")

    print("\n" + "="*80)
    print("✅ GÉNÉRATION ANALYSES ENRICHIES TERMINÉE")
    print("="*80)
    print(f"\n📂 Résultats : {OUTPUT_DIR}/")
    print(f"   - Départements : {len(df_dept_selected)} visualisations")
    print(f"   - Régions : {len(df_region_selected)} visualisations")
    print(f"   - National : 1 visualisation")


if __name__ == "__main__":
    main()
