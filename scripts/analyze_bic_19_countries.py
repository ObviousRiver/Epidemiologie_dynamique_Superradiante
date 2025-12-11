#!/usr/bin/env python3
"""
Analyse BIC Complète : 19 Pays - Super-Radiant vs SIR
=======================================================

Calcule le BIC (Bayesian Information Criterion) pour tous les 19 pays
de notre étude comparative COVID-19 Vague 1.

BIC = n * ln(RSS/n) + k * ln(n)
- Pénalise la complexité du modèle
- Plus petit BIC = meilleur modèle

Résultats sauvegardés dans : results_bic_19_countries.csv
"""

import sys
sys.path.insert(0, 'src/core')

import numpy as np
import pandas as pd
from models import SuperRadiantModel, SIRModel
import warnings
warnings.filterwarnings('ignore')

# ====================================================================
#                    CONFIGURATION 19 PAYS
# ====================================================================

COUNTRIES = [
    # Nom pays, Population, N_modes SR optimal
    ('France', 67e6, 4),
    ('Italy', 60e6, 4),
    ('Germany', 83e6, 4),
    ('Spain', 47e6, 4),
    ('United Kingdom', 67e6, 4),  # JHU dataset uses 'United Kingdom'
    ('Belgium', 11.5e6, 3),
    ('Netherlands', 17.5e6, 4),
    ('Switzerland', 8.7e6, 4),
    ('Austria', 9e6, 3),
    ('Portugal', 10e6, 3),
    ('Sweden', 10e6, 3),
    ('Norway', 5.4e6, 3),
    ('Denmark', 5.8e6, 3),
    ('Finland', 5.5e6, 3),
    ('Ireland', 5e6, 3),
    ('Canada', 38e6, 4),
    ('US', 331e6, 4),  # 'US' est le nom dans JHU dataset
    ('Australia', 26e6, 3),
    ('New Zealand', 5e6, 2),
]

# ====================================================================
#                    FONCTIONS UTILITAIRES
# ====================================================================

def calculate_bic(y_data, y_fit, k):
    """Calcule le Bayesian Information Criterion (BIC)."""
    n = len(y_data)
    residuals = y_data - y_fit
    rss = np.sum(residuals**2)

    if rss > 0:
        bic = n * np.log(rss / n) + k * np.log(n)
    else:
        bic = -np.inf

    return bic, rss, n

def load_country_data(country_name):
    """Charge les données COVID-19 pour un pays."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    df = pd.read_csv(url)
    country_data = df[df['Country/Region'] == country_name].iloc[:, 4:].sum(axis=0)

    if len(country_data) == 0:
        return None, None, None, None

    country_df = pd.DataFrame({'deaths': country_data})
    country_df.index = pd.to_datetime(country_df.index)
    country_df = country_df.loc['2020-02-15':'2020-06-30']

    daily_deaths = country_df['deaths'].diff().fillna(0).clip(lower=0)
    daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

    t_data = np.arange(len(daily_deaths_smooth))
    y_data = daily_deaths_smooth.values
    dates = country_df.index
    total_deaths = country_df['deaths'].iloc[-1]

    return t_data, y_data, dates, total_deaths

def analyze_country_bic(country_name, population, n_modes=4):
    """Analyse complète SR vs SIR avec BIC pour un pays."""

    print(f"\n{'='*70}")
    print(f"ANALYSE BIC : {country_name.upper()}")
    print(f"{'='*70}")

    # Chargement données
    t_data, y_data, dates, total_deaths = load_country_data(country_name)

    if t_data is None:
        print(f"   ❌ ERREUR : Pays '{country_name}' introuvable dans dataset JHU")
        return None

    if y_data.max() < 1.0:
        print(f"   ⚠️  SKIP : Données insuffisantes (max décès quotidiens < 1)")
        return None

    print(f"   Données : {len(t_data)} points, max décès : {y_data.max():.0f}/jour")

    # --- MODÈLE SUPER-RADIANT ---
    print(f"\n   📊 SR ({n_modes} modes)...", end=' ')
    try:
        sr_model = SuperRadiantModel(n_modes=n_modes)
        params_sr, rms_sr = sr_model.fit(t_data, y_data)
        y_fit_sr = sr_model.predict(t_data)

        k_sr = 3 * n_modes
        bic_sr, rss_sr, n = calculate_bic(y_data, y_fit_sr, k_sr)

        data_range = y_data.max() - y_data.min()
        nrmse_sr = (rms_sr / data_range) * 100 if data_range > 0 else 0.0

        ss_tot = np.sum((y_data - np.mean(y_data))**2)
        r2_sr = 1 - (rss_sr / ss_tot) if ss_tot > 0 else 0.0

        print(f"RMS={rms_sr:.2f}, NRMSE={nrmse_sr:.2f}%, R²={r2_sr:.3f}, BIC={bic_sr:.2f}")
        success_sr = True

    except Exception as e:
        print(f"❌ ÉCHEC : {e}")
        success_sr = False
        rms_sr = nrmse_sr = r2_sr = bic_sr = k_sr = np.nan

    # --- MODÈLE SIR ---
    print(f"   🦠 SIR (DOGBOX)...", end=' ')
    try:
        sir_model = SIRModel(population=population, IFR=0.01)
        params_sir, rms_sir = sir_model.fit(t_data, y_data)
        y_fit_sir = sir_model.predict(t_data)

        k_sir = 4  # beta, gamma, I0, scale
        bic_sir, rss_sir, n = calculate_bic(y_data, y_fit_sir, k_sir)

        nrmse_sir = (rms_sir / data_range) * 100 if data_range > 0 else 0.0
        r2_sir = 1 - (rss_sir / ss_tot) if ss_tot > 0 else 0.0

        sir_params = sir_model.get_parameters()

        print(f"RMS={rms_sir:.2f}, NRMSE={nrmse_sir:.2f}%, R²={r2_sir:.3f}, BIC={bic_sir:.2f}")
        print(f"              R0={sir_params['R0']:.2f}, Durée={sir_params['infection_duration_days']:.1f}j")
        success_sir = True

    except Exception as e:
        print(f"❌ ÉCHEC : {e}")
        success_sir = False
        rms_sir = nrmse_sir = r2_sir = bic_sir = k_sir = np.nan
        sir_params = {'R0': np.nan, 'infection_duration_days': np.nan}

    if not (success_sr and success_sir):
        print(f"   ⚠️  SKIP : Au moins un modèle a échoué")
        return None

    # --- COMPARAISON ---
    ratio_rms = rms_sir / rms_sr
    delta_bic = bic_sir - bic_sr

    print(f"\n   🎯 COMPARAISON :")
    print(f"      Ratio SIR/SR : {ratio_rms:.2f}×", end='')
    if ratio_rms > 1:
        print(f" → SR gagne")
    else:
        print(f" → SIR gagne")

    print(f"      ΔBIC (SIR-SR) : {delta_bic:+.2f}", end='')

    # Interprétation ΔBIC
    if abs(delta_bic) < 2:
        bic_winner = "Équivalents"
        strength = "Faible"
    elif abs(delta_bic) < 6:
        bic_winner = "SIR" if delta_bic > 0 else "SR"
        strength = "Positive"
    elif abs(delta_bic) < 10:
        bic_winner = "SIR" if delta_bic > 0 else "SR"
        strength = "Forte"
    else:
        bic_winner = "SIR" if delta_bic > 0 else "SR"
        strength = "Très forte"

    if bic_winner != "Équivalents":
        print(f" → Evidence {strength.lower()} pour {bic_winner}")
    else:
        print(f" → Modèles équivalents")

    # Retour résultats structurés
    return {
        'country': country_name,
        'population': population,
        'n_modes': n_modes,
        'total_deaths': total_deaths,
        'max_daily_deaths': y_data.max(),
        # SR
        'rms_sr': rms_sr,
        'nrmse_sr': nrmse_sr,
        'r2_sr': r2_sr,
        'bic_sr': bic_sr,
        'k_sr': k_sr,
        # SIR
        'rms_sir': rms_sir,
        'nrmse_sir': nrmse_sir,
        'r2_sir': r2_sir,
        'bic_sir': bic_sir,
        'k_sir': k_sir,
        'R0': sir_params['R0'],
        'duration_days': sir_params['infection_duration_days'],
        # Comparaison
        'ratio_rms': ratio_rms,
        'delta_bic': delta_bic,
        'bic_winner': bic_winner,
        'bic_strength': strength
    }

# ====================================================================
#                    ANALYSE COMPLÈTE 19 PAYS
# ====================================================================

if __name__ == '__main__':
    print("="*70)
    print("ANALYSE BIC COMPLÈTE : 19 PAYS")
    print("Super-Radiant vs SIR - COVID-19 Vague 1 (Fév-Juin 2020)")
    print("="*70)

    results = []

    for country, pop, n_modes in COUNTRIES:
        result = analyze_country_bic(country, pop, n_modes)
        if result is not None:
            results.append(result)

    # Sauvegarde résultats
    df = pd.DataFrame(results)
    df.to_csv('results_bic_19_countries.csv', index=False)
    print(f"\n✅ Résultats sauvegardés : results_bic_19_countries.csv")

    # ====================================================================
    #                    TABLEAU RÉCAPITULATIF
    # ====================================================================

    print("\n" + "="*70)
    print("TABLEAU RÉCAPITULATIF : BIC vs RATIO RMS")
    print("="*70)

    # Tri par ΔBIC décroissant (plus favorable SR en haut)
    df_sorted = df.sort_values('delta_bic', ascending=False)

    print(f"\n{'Pays':<15} {'Ratio':>8} {'ΔBIC':>8} {'RMS Conclusion':>16} {'BIC Conclusion':>20}")
    print("-" * 70)

    for _, row in df_sorted.iterrows():
        ratio_str = f"{row['ratio_rms']:.2f}×"
        delta_bic_str = f"{row['delta_bic']:+.1f}"

        rms_winner = "SR gagne" if row['ratio_rms'] > 1 else "SIR gagne"
        bic_conclusion = f"{row['bic_winner']} ({row['bic_strength'].lower()})"

        print(f"{row['country']:<15} {ratio_str:>8} {delta_bic_str:>8} {rms_winner:>16} {bic_conclusion:>20}")

    # ====================================================================
    #                    STATISTIQUES GLOBALES
    # ====================================================================

    print("\n" + "="*70)
    print("STATISTIQUES GLOBALES")
    print("="*70)

    n_countries = len(df)

    # Ratio RMS
    sr_wins_rms = (df['ratio_rms'] > 1).sum()
    sir_wins_rms = (df['ratio_rms'] < 1).sum()

    # BIC
    sr_wins_bic = (df['delta_bic'] > 2).sum()  # ΔBIC > 2 → SR gagne
    sir_wins_bic = (df['delta_bic'] < -2).sum()  # ΔBIC < -2 → SIR gagne
    equiv_bic = (abs(df['delta_bic']) <= 2).sum()  # |ΔBIC| ≤ 2 → Équivalents

    print(f"\n📊 VERDICT RATIO RMS :")
    print(f"   SR gagne : {sr_wins_rms}/{n_countries} pays ({sr_wins_rms/n_countries*100:.1f}%)")
    print(f"   SIR gagne : {sir_wins_rms}/{n_countries} pays ({sir_wins_rms/n_countries*100:.1f}%)")

    print(f"\n📊 VERDICT BIC (|ΔBIC| > 2) :")
    print(f"   SR gagne : {sr_wins_bic}/{n_countries} pays ({sr_wins_bic/n_countries*100:.1f}%)")
    print(f"   SIR gagne : {sir_wins_bic}/{n_countries} pays ({sir_wins_bic/n_countries*100:.1f}%)")
    print(f"   Équivalents : {equiv_bic}/{n_countries} pays ({equiv_bic/n_countries*100:.1f}%)")

    # Accord/désaccord
    df['rms_winner'] = df['ratio_rms'].apply(lambda x: 'SR' if x > 1 else 'SIR')
    df['bic_winner_simple'] = df['delta_bic'].apply(
        lambda x: 'SR' if x > 2 else ('SIR' if x < -2 else 'Equiv')
    )

    accord = ((df['rms_winner'] == df['bic_winner_simple']) & (df['bic_winner_simple'] != 'Equiv')).sum()
    desaccord = ((df['rms_winner'] != df['bic_winner_simple']) & (df['bic_winner_simple'] != 'Equiv')).sum()

    print(f"\n🔍 ACCORD RATIO RMS ↔ BIC :")
    print(f"   Accord : {accord}/{n_countries - equiv_bic} pays ({accord/(n_countries - equiv_bic)*100:.1f}%)")
    print(f"   Désaccord : {desaccord}/{n_countries - equiv_bic} pays ({desaccord/(n_countries - equiv_bic)*100:.1f}%)")

    # ΔBIC extrêmes
    max_delta_bic_row = df.loc[df['delta_bic'].idxmax()]
    min_delta_bic_row = df.loc[df['delta_bic'].idxmin()]

    print(f"\n🏆 ΔBIC EXTRÊMES :")
    print(f"   Plus favorable SR : {max_delta_bic_row['country']} (ΔBIC = +{max_delta_bic_row['delta_bic']:.1f})")
    print(f"   Plus favorable SIR : {min_delta_bic_row['country']} (ΔBIC = {min_delta_bic_row['delta_bic']:.1f})")

    print("\n" + "="*70)
    print("✅ ANALYSE COMPLÈTE TERMINÉE")
    print("="*70)
