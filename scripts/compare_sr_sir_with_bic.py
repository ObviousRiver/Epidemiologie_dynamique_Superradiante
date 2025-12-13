#!/usr/bin/env python3
"""
Comparaison SR vs SIR avec BIC (Bayesian Information Criterion)
================================================================

Le BIC pénalise la complexité du modèle :
    BIC = n * ln(RSS/n) + k * ln(n)

où :
- n = nombre de points de données
- RSS = somme des carrés des résidus (= n * RMS²)
- k = nombre de paramètres

RÈGLE : Plus petit BIC = meilleur modèle (compromis fit + parcimonie)

Comparaison avec ratio RMS simple :
- Ratio RMS : Ne pénalise PAS la complexité → Favorise modèle complexe
- BIC : Pénalise complexité → Favorise modèle parcimonieux SI fit similaire
"""

import sys
sys.path.insert(0, 'src/core')

import numpy as np
import pandas as pd
from models import SuperRadiantModel, SIRModel

# ====================================================================
#                    FONCTION CALCUL BIC
# ====================================================================

def calculate_bic(y_data, y_fit, k):
    """
    Calcule le Bayesian Information Criterion (BIC).

    Args:
        y_data (array): Données observées
        y_fit (array): Prédictions du modèle
        k (int): Nombre de paramètres du modèle

    Returns:
        dict: {
            'bic': BIC value,
            'rss': Residual Sum of Squares,
            'n': Number of data points,
            'k': Number of parameters
        }
    """
    n = len(y_data)
    residuals = y_data - y_fit
    rss = np.sum(residuals**2)

    # BIC = n * ln(RSS/n) + k * ln(n)
    if rss > 0:
        bic = n * np.log(rss / n) + k * np.log(n)
    else:
        bic = -np.inf  # Fit parfait (impossible en pratique)

    return {
        'bic': bic,
        'rss': rss,
        'n': n,
        'k': k
    }

# ====================================================================
#                    CHARGEMENT DONNÉES
# ====================================================================

def load_country_data(country_name):
    """Charge les données COVID-19 pour un pays."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    df = pd.read_csv(url)
    country_data = df[df['Country/Region'] == country_name].iloc[:, 4:].sum(axis=0)
    country_df = pd.DataFrame({'deaths': country_data})
    country_df.index = pd.to_datetime(country_df.index)
    country_df = country_df.loc['2020-02-15':'2020-06-30']

    daily_deaths = country_df['deaths'].diff().fillna(0).clip(lower=0)
    daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

    t_data = np.arange(len(daily_deaths_smooth))
    y_data = daily_deaths_smooth.values
    dates = country_df.index

    return t_data, y_data, dates, country_df['deaths'].iloc[-1]

# ====================================================================
#                    COMPARAISON PAYS
# ====================================================================

def compare_country(country_name, population, n_modes=4):
    """Compare SR vs SIR avec BIC pour un pays."""

    print(f"\n{'='*70}")
    print(f"ANALYSE : {country_name.upper()}")
    print(f"{'='*70}")

    # Chargement données
    t_data, y_data, dates, total_deaths = load_country_data(country_name)
    print(f"   Données : {len(t_data)} points")
    print(f"   Décès totaux : {total_deaths:.0f}")
    print(f"   Max décès quotidiens : {y_data.max():.0f}")

    # --- MODÈLE SUPER-RADIANT ---
    print(f"\n📊 Modèle Super-Radiant ({n_modes} modes)...")
    sr_model = SuperRadiantModel(n_modes=n_modes)
    params_sr, rms_sr = sr_model.fit(t_data, y_data)
    y_fit_sr = sr_model.predict(t_data)

    # Nombre de paramètres SR : 3 * n_modes (A, tau, T pour chaque mode)
    k_sr = 3 * n_modes

    # Calcul BIC SR
    bic_sr_data = calculate_bic(y_data, y_fit_sr, k_sr)

    # Calcul NRMSE SR
    data_range = y_data.max() - y_data.min()
    nrmse_sr = (rms_sr / data_range) * 100 if data_range > 0 else 0.0

    # Calcul R² SR
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r2_sr = 1 - (bic_sr_data['rss'] / ss_tot) if ss_tot > 0 else 0.0

    print(f"   ✓ RMS absolu : {rms_sr:.2f}")
    print(f"   ✓ NRMSE : {nrmse_sr:.2f}%")
    print(f"   ✓ R² : {r2_sr:.3f}")
    print(f"   ✓ BIC (k={k_sr}) : {bic_sr_data['bic']:.2f}")

    # --- MODÈLE SIR ---
    print(f"\n🦠 Modèle SIR (DOGBOX)...")
    sir_model = SIRModel(population=population, IFR=0.01)
    params_sir, rms_sir = sir_model.fit(t_data, y_data)
    y_fit_sir = sir_model.predict(t_data)

    # Nombre de paramètres SIR : 4 (beta, gamma, I0, scale)
    k_sir = 4

    # Calcul BIC SIR
    bic_sir_data = calculate_bic(y_data, y_fit_sir, k_sir)

    # Calcul NRMSE SIR
    nrmse_sir = (rms_sir / data_range) * 100 if data_range > 0 else 0.0

    # Calcul R² SIR
    r2_sir = 1 - (bic_sir_data['rss'] / ss_tot) if ss_tot > 0 else 0.0

    # Paramètres SIR
    sir_params = sir_model.get_parameters()

    print(f"   ✓ RMS absolu : {rms_sir:.2f}")
    print(f"   ✓ NRMSE : {nrmse_sir:.2f}%")
    print(f"   ✓ R² : {r2_sir:.3f}")
    print(f"   ✓ BIC (k={k_sir}) : {bic_sir_data['bic']:.2f}")
    print(f"   ✓ R0 : {sir_params['R0']:.2f}")
    print(f"   ✓ Durée infection : {sir_params['infection_duration_days']:.1f} jours")

    # --- COMPARAISON ---
    print(f"\n{'='*70}")
    print(f"COMPARAISON : {country_name.upper()}")
    print(f"{'='*70}")

    # 1. Ratio RMS traditionnel (notre approche actuelle)
    ratio_rms = rms_sir / rms_sr
    print(f"\n📐 RATIO RMS (approche actuelle) :")
    print(f"   Ratio SIR/SR : {ratio_rms:.2f}×")
    if ratio_rms > 1:
        print(f"   → SR gagne (SIR {ratio_rms:.2f}× pire)")
    else:
        print(f"   → SIR gagne (SR {1/ratio_rms:.2f}× pire)")

    # 2. BIC (approche plus rigoureuse)
    delta_bic = bic_sir_data['bic'] - bic_sr_data['bic']
    print(f"\n📊 BIC (approche rigoureuse, pénalise complexité) :")
    print(f"   BIC SIR (k={k_sir}) : {bic_sir_data['bic']:.2f}")
    print(f"   BIC SR (k={k_sr}) : {bic_sr_data['bic']:.2f}")
    print(f"   ΔBIC (SIR - SR) : {delta_bic:+.2f}")

    # Interprétation ΔBIC (règle empirique Kass & Raftery 1995)
    print(f"\n   Interprétation ΔBIC (Kass & Raftery 1995) :")
    if abs(delta_bic) < 2:
        strength = "Faible (≈ équivalents)"
        winner = "Aucun"
    elif abs(delta_bic) < 6:
        strength = "Positive"
        winner = "SIR" if delta_bic > 0 else "SR"
    elif abs(delta_bic) < 10:
        strength = "Forte"
        winner = "SIR" if delta_bic > 0 else "SR"
    else:
        strength = "Très forte"
        winner = "SIR" if delta_bic > 0 else "SR"

    if winner != "Aucun":
        print(f"   → Evidence {strength.lower()} pour {winner}")
    else:
        print(f"   → {strength} : Modèles équivalents")

    # 3. Synthèse
    print(f"\n🎯 SYNTHÈSE :")

    # Accord ou désaccord ?
    ratio_conclusion = "SR" if ratio_rms > 1 else "SIR"
    bic_conclusion = "SR" if delta_bic > 0 else "SIR" if abs(delta_bic) >= 2 else "Aucun"

    print(f"   Ratio RMS → {ratio_conclusion} gagne")
    print(f"   BIC       → {bic_conclusion} gagne" if bic_conclusion != "Aucun" else "   BIC       → Modèles équivalents")

    if ratio_conclusion == bic_conclusion and bic_conclusion != "Aucun":
        print(f"   ✅ ACCORD : {ratio_conclusion} clairement meilleur")
    elif bic_conclusion == "Aucun":
        print(f"   ⚖️  NUANCÉ : BIC suggère modèles équivalents (compromis complexité/fit)")
    else:
        print(f"   ⚠️  DÉSACCORD : Ratio RMS favorise {ratio_conclusion}, BIC favorise {bic_conclusion}")
        print(f"       → BIC pénalise SR ({k_sr} paramètres) vs SIR ({k_sir} paramètres)")

    return {
        'country': country_name,
        'rms_sr': rms_sr,
        'rms_sir': rms_sir,
        'nrmse_sr': nrmse_sr,
        'nrmse_sir': nrmse_sir,
        'r2_sr': r2_sr,
        'r2_sir': r2_sir,
        'bic_sr': bic_sr_data['bic'],
        'bic_sir': bic_sir_data['bic'],
        'k_sr': k_sr,
        'k_sir': k_sir,
        'ratio_rms': ratio_rms,
        'delta_bic': delta_bic
    }

# ====================================================================
#                    ANALYSE MULTI-PAYS
# ====================================================================

if __name__ == '__main__':
    countries = [
        ('France', 67e6),
        ('Italy', 60e6),
        ('UK', 67e6),
        ('USA', 331e6),
        ('Germany', 83e6),
    ]

    results = []
    for country, pop in countries:
        result = compare_country(country, pop, n_modes=4)
        results.append(result)

    # Tableau récapitulatif
    print(f"\n{'='*70}")
    print("TABLEAU RÉCAPITULATIF : BIC vs RATIO RMS")
    print(f"{'='*70}")

    df = pd.DataFrame(results)
    print(f"\n| Pays | Ratio SIR/SR | ΔBIC | Conclusion Ratio | Conclusion BIC |")
    print(f"|------|--------------|------|------------------|----------------|")

    for _, row in df.iterrows():
        ratio_str = f"{row['ratio_rms']:.2f}×"
        delta_bic_str = f"{row['delta_bic']:+.1f}"

        ratio_winner = "SR" if row['ratio_rms'] > 1 else "SIR"
        bic_winner = "SR" if row['delta_bic'] > 0 else "SIR" if abs(row['delta_bic']) >= 2 else "≈"

        print(f"| {row['country']:8s} | {ratio_str:>12s} | {delta_bic_str:>4s} | {ratio_winner:>16s} | {bic_winner:>14s} |")

    print(f"\n📌 OBSERVATION CLÉS :")
    print(f"   - Ratio RMS : Ne considère QUE la qualité du fit")
    print(f"   - BIC : Compromis entre fit ET parcimonie (pénalise k paramètres)")
    print(f"   - SR a {results[0]['k_sr']} paramètres vs SIR {results[0]['k_sir']} paramètres")
    print(f"   - Si ΔBIC < 2 : Modèles équivalents malgré ratio RMS différent")
