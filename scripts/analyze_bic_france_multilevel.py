#!/usr/bin/env python3
"""
Analyse BIC France Multi-Niveaux : Départements, Régions, National
==================================================================

Calcule le BIC (Bayesian Information Criterion) pour l'analyse France
à trois échelles géographiques :
- Départements (n=85)
- Régions (n=12)
- National (n=1)

Basé sur les résultats existants dans results/france_*_consolidee.csv

BIC = n * ln(RSS/n) + k * ln(n)
où :
- n = nombre de points temporels (137 jours: 2020-02-15 à 2020-06-30)
- RSS = n * RMS²
- k = nombre de paramètres (SR: 3*n_modes, SIR: 4)
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ====================================================================
#                    CONFIGURATION
# ====================================================================

N_POINTS = 137  # Période 2020-02-15 à 2020-06-30 (cohérent avec analyse 19 pays)

FILES = {
    'departments': 'results/france_departements_consolidee.csv',
    'regions': 'results/france_regions_consolidee.csv',
    'national': 'results/france_national_consolidee.csv'
}

# ====================================================================
#                    FONCTIONS
# ====================================================================

def calculate_bic(rms, n_points, k):
    """Calcule le BIC à partir du RMS."""
    rss = n_points * (rms ** 2)
    if rss > 0:
        bic = n_points * np.log(rss / n_points) + k * np.log(n_points)
    else:
        bic = -np.inf
    return bic

def analyze_level(file_path, level_name, entity_col):
    """Analyse un niveau géographique."""

    print(f"\n{'='*70}")
    print(f"ANALYSE BIC : {level_name.upper()}")
    print(f"{'='*70}")

    # Chargement données
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"   ❌ Fichier introuvable : {file_path}")
        return None

    n_entities = len(df)
    print(f"   Entités : {n_entities}")
    print(f"   Points temporels (assumés) : {N_POINTS}")

    # Calcul BIC pour chaque entité
    results = []

    for idx, row in df.iterrows():
        entity_name = row[entity_col] if entity_col in row else f"Entity_{idx}"
        rms_sr = row['rms_sr']
        rms_sir = row['rms_sir']
        ratio_rms = row['ratio']
        n_modes = row['n_modes_sr']

        # Calcul BIC
        k_sr = 3 * n_modes
        k_sir = 4

        bic_sr = calculate_bic(rms_sr, N_POINTS, k_sr)
        bic_sir = calculate_bic(rms_sir, N_POINTS, k_sir)
        delta_bic = bic_sir - bic_sr

        # Détermination gagnant BIC
        if abs(delta_bic) < 2:
            bic_winner = "Equiv"
            bic_strength = "Faible"
        elif abs(delta_bic) < 6:
            bic_winner = "SR" if delta_bic > 0 else "SIR"
            bic_strength = "Positive"
        elif abs(delta_bic) < 10:
            bic_winner = "SR" if delta_bic > 0 else "SIR"
            bic_strength = "Forte"
        else:
            bic_winner = "SR" if delta_bic > 0 else "SIR"
            bic_strength = "Très forte"

        # Détermination gagnant RMS
        rms_winner = "SR" if ratio_rms > 1 else "SIR"

        # Accord/désaccord
        if bic_winner == "Equiv":
            agreement = "Neutre"
        elif bic_winner == rms_winner:
            agreement = "Accord"
        else:
            agreement = "Désaccord"

        results.append({
            'entity': entity_name,
            'rms_sr': rms_sr,
            'rms_sir': rms_sir,
            'ratio_rms': ratio_rms,
            'n_modes': n_modes,
            'k_sr': k_sr,
            'k_sir': k_sir,
            'bic_sr': bic_sr,
            'bic_sir': bic_sir,
            'delta_bic': delta_bic,
            'rms_winner': rms_winner,
            'bic_winner': bic_winner,
            'bic_strength': bic_strength,
            'agreement': agreement
        })

    df_results = pd.DataFrame(results)

    # Statistiques globales
    print(f"\n📊 STATISTIQUES GLOBALES :")

    # Ratio RMS
    sr_wins_rms = (df_results['ratio_rms'] > 1).sum()
    sir_wins_rms = (df_results['ratio_rms'] < 1).sum()

    print(f"\n   Ratio RMS :")
    print(f"   - SR gagne : {sr_wins_rms}/{n_entities} ({sr_wins_rms/n_entities*100:.1f}%)")
    print(f"   - SIR gagne : {sir_wins_rms}/{n_entities} ({sir_wins_rms/n_entities*100:.1f}%)")

    # BIC
    sr_wins_bic = (df_results['bic_winner'] == 'SR').sum()
    sir_wins_bic = (df_results['bic_winner'] == 'SIR').sum()
    equiv_bic = (df_results['bic_winner'] == 'Equiv').sum()

    print(f"\n   BIC (|ΔBIC| > 2) :")
    print(f"   - SR gagne : {sr_wins_bic}/{n_entities} ({sr_wins_bic/n_entities*100:.1f}%)")
    print(f"   - SIR gagne : {sir_wins_bic}/{n_entities} ({sir_wins_bic/n_entities*100:.1f}%)")
    print(f"   - Équivalents : {equiv_bic}/{n_entities} ({equiv_bic/n_entities*100:.1f}%)")

    # Accord/désaccord
    accord = (df_results['agreement'] == 'Accord').sum()
    desaccord = (df_results['agreement'] == 'Désaccord').sum()
    neutre = (df_results['agreement'] == 'Neutre').sum()

    total_decidable = n_entities - neutre
    if total_decidable > 0:
        print(f"\n   Accord RMS ↔ BIC :")
        print(f"   - Accord : {accord}/{total_decidable} ({accord/total_decidable*100:.1f}%)")
        print(f"   - Désaccord : {desaccord}/{total_decidable} ({desaccord/total_decidable*100:.1f}%)")

    # ΔBIC extrêmes
    if len(df_results) > 0:
        max_delta_row = df_results.loc[df_results['delta_bic'].idxmax()]
        min_delta_row = df_results.loc[df_results['delta_bic'].idxmin()]

        print(f"\n   ΔBIC extrêmes :")
        print(f"   - Plus favorable SR : {max_delta_row['entity']} (ΔBIC = +{max_delta_row['delta_bic']:.1f})")
        print(f"   - Plus favorable SIR : {min_delta_row['entity']} (ΔBIC = {min_delta_row['delta_bic']:.1f})")

    # Cas de désaccord
    if desaccord > 0:
        print(f"\n   ⚠️  Cas de désaccord RMS ≠ BIC :")
        desaccord_df = df_results[df_results['agreement'] == 'Désaccord']
        for _, row in desaccord_df.head(5).iterrows():  # Limiter à 5 exemples
            print(f"      {row['entity']} : RMS dit {row['rms_winner']} ({row['ratio_rms']:.2f}×), "
                  f"BIC dit {row['bic_winner']} (ΔBIC={row['delta_bic']:+.1f})")
        if len(desaccord_df) > 5:
            print(f"      ... et {len(desaccord_df) - 5} autres")

    return df_results

# ====================================================================
#                    ANALYSE PRINCIPALE
# ====================================================================

if __name__ == '__main__':
    print("="*70)
    print("ANALYSE BIC FRANCE MULTI-NIVEAUX")
    print("Départements, Régions, National - COVID-19 Vague 1")
    print("="*70)

    all_results = {}

    # Départements
    df_dep = analyze_level(FILES['departments'], 'Départements', 'departement')
    if df_dep is not None:
        all_results['departments'] = df_dep
        df_dep.to_csv('results_bic_france_departments.csv', index=False)
        print(f"\n   ✅ Résultats sauvegardés : results_bic_france_departments.csv")

    # Régions
    df_reg = analyze_level(FILES['regions'], 'Régions', 'region')
    if df_reg is not None:
        all_results['regions'] = df_reg
        df_reg.to_csv('results_bic_france_regions.csv', index=False)
        print(f"\n   ✅ Résultats sauvegardés : results_bic_france_regions.csv")

    # National
    df_nat = analyze_level(FILES['national'], 'National', 'pays')
    if df_nat is not None:
        all_results['national'] = df_nat
        df_nat.to_csv('results_bic_france_national.csv', index=False)
        print(f"\n   ✅ Résultats sauvegardés : results_bic_france_national.csv")

    # ====================================================================
    #                    SYNTHÈSE COMPARATIVE
    # ====================================================================

    print("\n" + "="*70)
    print("SYNTHÈSE COMPARATIVE MULTI-NIVEAUX")
    print("="*70)

    print("\n| Niveau | Entités | SR gagne (RMS) | SR gagne (BIC) | Accord RMS↔BIC |")
    print("|--------|---------|----------------|----------------|----------------|")

    for level_name, df in all_results.items():
        n_entities = len(df)
        sr_wins_rms = (df['ratio_rms'] > 1).sum()
        sr_wins_bic = (df['bic_winner'] == 'SR').sum()
        accord = (df['agreement'] == 'Accord').sum()
        neutre = (df['agreement'] == 'Neutre').sum()
        total_decidable = n_entities - neutre

        level_display = level_name.capitalize()
        accord_pct = f"{accord/total_decidable*100:.1f}%" if total_decidable > 0 else "N/A"

        print(f"| {level_display:<10} | {n_entities:>7} | {sr_wins_rms:>6}/{n_entities:>2} ({sr_wins_rms/n_entities*100:>5.1f}%) | "
              f"{sr_wins_bic:>6}/{n_entities:>2} ({sr_wins_bic/n_entities*100:>5.1f}%) | {accord_pct:>14} |")

    print("\n" + "="*70)
    print("✅ ANALYSE COMPLÈTE TERMINÉE")
    print("="*70)

    print("\n📌 OBSERVATION CLÉS :")
    print("   - Ratio RMS : Ne considère QUE la qualité du fit")
    print("   - BIC : Compromis entre fit ET parcimonie (pénalise k paramètres)")
    print("   - Si accord élevé (>90%) : Les deux critères cohérents")
    print("   - Si désaccord : BIC suggère que SR surparamétr ou SIR sous-paramétré")
