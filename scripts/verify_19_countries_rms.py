#!/usr/bin/env python3
"""
Script de Vérification RMS - 19 Pays
=====================================

Relance les analyses pour les 19 pays et compare avec les valeurs du document consolidé.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'analysis'))

import numpy as np
import pandas as pd
from datetime import datetime
from models import SuperRadiantModel, SIRModel

# Liste des 19 pays à analyser
COUNTRIES_EU = [
    'Netherlands', 'Switzerland', 'Italy', 'Germany', 'Ireland',
    'Belgium', 'Austria', 'Finland', 'Norway', 'Denmark',
    'France', 'Portugal', 'Spain', 'Sweden', 'United Kingdom'
]

COUNTRIES_ANGLO = ['Canada', 'US', 'New Zealand', 'Australia']

ALL_COUNTRIES = COUNTRIES_EU + COUNTRIES_ANGLO

# Populations (millions)
POPULATIONS = {
    'Austria': 8.9e6, 'Belgium': 11.5e6, 'Denmark': 5.8e6, 'Finland': 5.5e6,
    'France': 67.0e6, 'Germany': 83.0e6, 'Ireland': 5.0e6, 'Italy': 60.0e6,
    'Netherlands': 17.4e6, 'Norway': 5.4e6, 'Portugal': 10.3e6, 'Spain': 47.0e6,
    'Sweden': 10.3e6, 'Switzerland': 8.6e6, 'United Kingdom': 67.0e6,
    'Canada': 38.0e6, 'US': 331.0e6, 'New Zealand': 5.0e6, 'Australia': 26.0e6
}

# Valeurs consolidées du document de référence (pour comparaison)
REFERENCE_VALUES = {
    'Netherlands': {'rms_sr': 2.58, 'rms_sir': 26.27, 'ratio': 10.2},
    'Switzerland': {'rms_sr': 0.55, 'rms_sir': 4.64, 'ratio': 8.4},
    'Italy': {'rms_sr': 10.11, 'rms_sir': 74.01, 'ratio': 7.3},
    'Germany': {'rms_sr': 5.00, 'rms_sir': 26.86, 'ratio': 5.4},
    'Ireland': {'rms_sr': 2.46, 'rms_sir': 7.02, 'ratio': 2.9},
    'Belgium': {'rms_sr': 7.96, 'rms_sir': 21.74, 'ratio': 2.7},
    'Austria': {'rms_sr': 0.75, 'rms_sir': 2.03, 'ratio': 2.7},
    'Finland': {'rms_sr': 0.36, 'rms_sir': 0.93, 'ratio': 2.6},
    'Norway': {'rms_sr': 0.32, 'rms_sir': 0.79, 'ratio': 2.5},
    'Denmark': {'rms_sr': 0.55, 'rms_sir': 1.19, 'ratio': 2.2},
    'France': {'rms_sr': 22.58, 'rms_sir': 46.94, 'ratio': 2.1},
    'Portugal': {'rms_sr': 1.05, 'rms_sir': 2.01, 'ratio': 1.9},
    'Spain': {'rms_sr': 28.44, 'rms_sir': 41.71, 'ratio': 1.5},
    'Sweden': {'rms_sr': 4.52, 'rms_sir': 6.65, 'ratio': 1.5},
    'United Kingdom': {'rms_sr': 18.79, 'rms_sir': 8.51, 'ratio': 0.45},
    'Canada': {'rms_sr': 3.69, 'rms_sir': 26.92, 'ratio': 7.3},
    'US': {'rms_sr': 68.20, 'rms_sir': 281.98, 'ratio': 4.13},
    'New Zealand': {'rms_sr': 0.07, 'rms_sir': 0.31, 'ratio': 4.4},
    'Australia': {'rms_sr': 0.18, 'rms_sir': 0.50, 'ratio': 2.8}
}

WAVE1_START = '2020-02-15'
WAVE1_END = '2020-06-30'


def load_country_data(country_name):
    """Charge les données COVID-19 d'un pays."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    try:
        df = pd.read_csv(url)
        country_data = df[df['Country/Region'] == country_name].iloc[:, 4:].sum(axis=0)
        country_df = pd.DataFrame({'deaths': country_data})
        country_df.index = pd.to_datetime(country_df.index)
        country_df = country_df.loc[WAVE1_START:WAVE1_END]

        # Décès quotidiens
        daily_deaths = country_df['deaths'].diff().fillna(0).clip(lower=0)
        daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

        t_data = np.arange(len(daily_deaths_smooth))
        y_data = daily_deaths_smooth.values

        return t_data, y_data
    except Exception as e:
        print(f"   ❌ Erreur {country_name}: {e}")
        return None, None


def analyze_country(country_name):
    """Analyse un pays et retourne les RMS SR et SIR."""
    print(f"\n{'='*60}")
    print(f"Analyse : {country_name}")
    print(f"{'='*60}")

    # Charger données
    t_data, y_data = load_country_data(country_name)
    if t_data is None:
        return None

    population = POPULATIONS.get(country_name, 60e6)
    print(f"   Population : {population/1e6:.1f}M")
    print(f"   Points de données : {len(t_data)}")

    # Ajuster SR (tester 3 et 4 modes)
    rms_sr_best = np.inf
    best_n_modes = None

    for n_modes in [3, 4]:
        try:
            sr = SuperRadiantModel(n_modes=n_modes)
            params_sr, rms_sr = sr.fit(t_data, y_data)
            print(f"   SR {n_modes} modes : RMS = {rms_sr:.2f}")
            if rms_sr < rms_sr_best:
                rms_sr_best = rms_sr
                best_n_modes = n_modes
        except Exception as e:
            print(f"   SR {n_modes} modes : Échec ({e})")

    # Ajuster SIR
    try:
        sir = SIRModel(population=population, IFR=0.01)
        params_sir, rms_sir = sir.fit(t_data, y_data)
        print(f"   SIR : RMS = {rms_sir:.2f}")
    except Exception as e:
        print(f"   SIR : Échec ({e})")
        rms_sir = np.inf

    # Calculer ratio
    if rms_sr_best < np.inf and rms_sir < np.inf:
        ratio = rms_sir / rms_sr_best
    else:
        ratio = np.nan

    print(f"\n   → RMS SR (best {best_n_modes} modes) : {rms_sr_best:.2f}")
    print(f"   → RMS SIR : {rms_sir:.2f}")
    print(f"   → Ratio SIR/SR : {ratio:.2f}×")

    return {
        'country': country_name,
        'rms_sr': rms_sr_best,
        'rms_sir': rms_sir,
        'ratio': ratio,
        'n_modes': best_n_modes
    }


def compare_with_reference(results):
    """Compare les résultats obtenus avec les valeurs de référence."""
    print(f"\n{'='*80}")
    print("COMPARAISON AVEC VALEURS DE RÉFÉRENCE")
    print(f"{'='*80}\n")

    comparison = []

    for res in results:
        if res is None:
            continue

        country = res['country']
        ref = REFERENCE_VALUES.get(country)

        if ref is None:
            continue

        # Écarts relatifs
        delta_sr = ((res['rms_sr'] - ref['rms_sr']) / ref['rms_sr']) * 100
        delta_sir = ((res['rms_sir'] - ref['rms_sir']) / ref['rms_sir']) * 100
        delta_ratio = ((res['ratio'] - ref['ratio']) / ref['ratio']) * 100

        comparison.append({
            'country': country,
            'rms_sr_calc': res['rms_sr'],
            'rms_sr_ref': ref['rms_sr'],
            'delta_sr': delta_sr,
            'rms_sir_calc': res['rms_sir'],
            'rms_sir_ref': ref['rms_sir'],
            'delta_sir': delta_sir,
            'ratio_calc': res['ratio'],
            'ratio_ref': ref['ratio'],
            'delta_ratio': delta_ratio
        })

    # Créer DataFrame pour affichage
    df = pd.DataFrame(comparison)

    # Afficher résultats
    print("| Pays | RMS SR | RMS SIR | Ratio | Δ SR (%) | Δ SIR (%) | Δ Ratio (%) | Status |")
    print("|------|--------|---------|-------|----------|-----------|-------------|--------|")

    for _, row in df.iterrows():
        # Vérification : écart < 10% = ✅, sinon ⚠️
        status = '✅' if abs(row['delta_ratio']) < 10 else '⚠️'

        print(f"| {row['country'][:12]:<12} | "
              f"{row['rms_sr_calc']:5.2f} | "
              f"{row['rms_sir_calc']:6.2f} | "
              f"{row['ratio_calc']:4.2f}× | "
              f"{row['delta_sr']:+6.1f}% | "
              f"{row['delta_sir']:+6.1f}% | "
              f"{row['delta_ratio']:+7.1f}% | "
              f"{status} |")

    # Statistiques globales
    print(f"\n{'='*80}")
    print("STATISTIQUES GLOBALES")
    print(f"{'='*80}\n")

    print(f"Écart moyen SR   : {df['delta_sr'].abs().mean():.1f}%")
    print(f"Écart moyen SIR  : {df['delta_sir'].abs().mean():.1f}%")
    print(f"Écart moyen Ratio: {df['delta_ratio'].abs().mean():.1f}%")
    print(f"\nNombre de pays avec écart ratio < 10% : {(df['delta_ratio'].abs() < 10).sum()}/{len(df)}")

    # Sauvegarder résultats
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"verification_rms_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    print(f"\n✓ Résultats sauvegardés : {output_file}")

    return df


def main():
    """Point d'entrée principal."""
    print(f"\n{'#'*80}")
    print("VÉRIFICATION RMS - 19 PAYS COVID-19")
    print(f"{'#'*80}")
    print(f"\nDate : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pays à analyser : {len(ALL_COUNTRIES)}")
    print(f"Période : {WAVE1_START} → {WAVE1_END}\n")

    results = []

    # Analyser tous les pays
    for country in ALL_COUNTRIES:
        result = analyze_country(country)
        results.append(result)

    # Comparer avec référence
    compare_with_reference(results)

    print(f"\n{'#'*80}")
    print("VÉRIFICATION TERMINÉE")
    print(f"{'#'*80}\n")


if __name__ == "__main__":
    main()
