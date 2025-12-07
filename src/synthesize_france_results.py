#!/usr/bin/env python3
"""
Synthèse Résultats France Multi-Échelle
========================================

Analyse les résultats CSV et génère une synthèse markdown comparant
avec les prédictions conceptuelles.
"""

import pandas as pd
import numpy as np

# Chargement des résultats
df_dept = pd.read_csv('results/france_departements_consolidee.csv')
df_region = pd.read_csv('results/france_regions_consolidee.csv')
df_national = pd.read_csv('results/france_national_consolidee.csv')

print("="*80)
print("📊 SYNTHÈSE RÉSULTATS FRANCE MULTI-ÉCHELLE")
print("="*80)

print(f"\n✅ Données chargées:")
print(f"   - {len(df_dept)} départements")
print(f"   - {len(df_region)} régions")
print(f"   - 1 national (France)")

# ============================================================================
# 1. STATISTIQUES DÉPARTEMENTALES
# ============================================================================

print("\n" + "="*80)
print("📍 NIVEAU DÉPARTEMENTAL (n={})".format(len(df_dept)))
print("="*80)

# Régime dominant
sr_count = (df_dept['winner'] == 'SR').sum()
sir_count = (df_dept['winner'] == 'SIR').sum()
print(f"\n🏆 Régime dominant:")
print(f"   SR gagne : {sr_count}/{len(df_dept)} ({100*sr_count/len(df_dept):.1f}%)")
print(f"   SIR gagne : {sir_count}/{len(df_dept)} ({100*sir_count/len(df_dept):.1f}%)")

# Ratios SR/SIR
print(f"\n📊 Ratios RMS_SIR / RMS_SR:")
print(f"   Médiane : {df_dept['ratio'].median():.2f}×")
print(f"   Moyenne : {df_dept['ratio'].mean():.2f}× ± {df_dept['ratio'].std():.2f}")
print(f"   Min : {df_dept['ratio'].min():.2f}× ({df_dept.loc[df_dept['ratio'].idxmin(), 'departement']})")
print(f"   Max : {df_dept['ratio'].max():.2f}× ({df_dept.loc[df_dept['ratio'].idxmax(), 'departement']})")

# Exposants critiques γ
df_dept_gamma = df_dept[df_dept['gamma'].notna()]
print(f"\n📈 Exposants critiques γ (n={len(df_dept_gamma)}):")
print(f"   Médiane : {df_dept_gamma['gamma'].median():.3f}")
print(f"   Moyenne : {df_dept_gamma['gamma'].mean():.3f} ± {df_dept_gamma['gamma'].std():.3f}")
print(f"   Min : {df_dept_gamma['gamma'].min():.3f} ({df_dept_gamma.loc[df_dept_gamma['gamma'].idxmin(), 'departement']})")
print(f"   Max : {df_dept_gamma['gamma'].max():.3f} ({df_dept_gamma.loc[df_dept_gamma['gamma'].idxmax(), 'departement']})")

# Top 10 γ
print(f"\n🔝 Top 10 départements (γ le plus élevé):")
top10_gamma = df_dept_gamma.nlargest(10, 'gamma')[['departement', 'gamma', 'R2_gamma', 'ratio']]
for idx, row in top10_gamma.iterrows():
    print(f"   {row['departement']}: γ = {row['gamma']:.3f}, R² = {row['R2_gamma']:.3f}, ratio = {row['ratio']:.2f}×")

# Départements clés prédits (foyers COVID)
print(f"\n🎯 Départements clés (foyers COVID-19 prédits):")
key_depts = ['67', '68', '75', '92', '93', '94', '13', '69', '60']
for dept in key_depts:
    if dept in df_dept['departement'].values:
        row = df_dept[df_dept['departement'] == dept].iloc[0]
        print(f"   {dept}: ratio = {row['ratio']:.2f}×, γ = {row['gamma']:.3f}, R² = {row['R2_gamma']:.3f}")
    else:
        print(f"   {dept}: ⚠️  Pas de données suffisantes")

# ============================================================================
# 2. STATISTIQUES RÉGIONALES
# ============================================================================

print("\n" + "="*80)
print("📍 NIVEAU RÉGIONAL (n={})".format(len(df_region)))
print("="*80)

# Régime dominant
sr_count_reg = (df_region['winner'] == 'SR').sum()
sir_count_reg = (df_region['winner'] == 'SIR').sum()
print(f"\n🏆 Régime dominant:")
print(f"   SR gagne : {sr_count_reg}/{len(df_region)} ({100*sr_count_reg/len(df_region):.1f}%)")
print(f"   SIR gagne : {sir_count_reg}/{len(df_region)} ({100*sir_count_reg/len(df_region):.1f}%)")

# Ratios SR/SIR
print(f"\n📊 Ratios RMS_SIR / RMS_SR:")
print(f"   Médiane : {df_region['ratio'].median():.2f}×")
print(f"   Moyenne : {df_region['ratio'].mean():.2f}× ± {df_region['ratio'].std():.2f}")

# Exposants critiques γ
df_region_gamma = df_region[df_region['gamma'].notna()]
print(f"\n📈 Exposants critiques γ (n={len(df_region_gamma)}):")
print(f"   Médiane : {df_region_gamma['gamma'].median():.3f}")
print(f"   Moyenne : {df_region_gamma['gamma'].mean():.3f} ± {df_region_gamma['gamma'].std():.3f}")

# Classement régions
print(f"\n🔝 Classement régions par ratio SR/SIR:")
df_region_sorted = df_region.sort_values('ratio', ascending=False)
for idx, row in df_region_sorted.iterrows():
    print(f"   {row['region']:30s}: {row['ratio']:.2f}× (γ = {row['gamma']:.3f}, R² = {row['R2_gamma']:.3f})")

# ============================================================================
# 3. NIVEAU NATIONAL
# ============================================================================

print("\n" + "="*80)
print("📍 NIVEAU NATIONAL")
print("="*80)

row_nat = df_national.iloc[0]
print(f"\n🇫🇷 France:")
print(f"   Ratio SR/SIR : {row_nat['ratio']:.2f}×")
print(f"   Gagnant : {row_nat['winner']}")
print(f"   Exposant γ : {row_nat['gamma']:.3f} (R² = {row_nat['R2_gamma']:.3f})")
print(f"   Max décès/jour : {row_nat['max_deaths']:.1f}")
print(f"   Modes SR : {row_nat['n_modes_sr']}")

# ============================================================================
# 4. COMPARAISON AVEC LES 19 PAYS
# ============================================================================

print("\n" + "="*80)
print("📊 COMPARAISON FRANCE vs 19 PAYS")
print("="*80)

# Charger résultats gamma 19 pays
try:
    df_19pays = pd.read_csv('results/gamma_results.csv')

    gamma_france_nat = row_nat['gamma']
    gamma_19pays_median = df_19pays['gamma'].median()
    gamma_france_pays = df_19pays[df_19pays['Country'] == 'France']['gamma'].iloc[0] if 'France' in df_19pays['Country'].values else np.nan

    print(f"\n📈 Exposant γ:")
    print(f"   France national (SPF) : {gamma_france_nat:.3f}")
    print(f"   France pays (JHU) : {gamma_france_pays:.3f}")
    print(f"   Médiane 19 pays : {gamma_19pays_median:.3f}")
    print(f"   Écart : {gamma_france_nat - gamma_19pays_median:+.3f}")

except:
    print("\n⚠️  Fichier gamma_results.csv non trouvé")

print("\n" + "="*80)
print("✅ SYNTHÈSE TERMINÉE")
print("="*80)
