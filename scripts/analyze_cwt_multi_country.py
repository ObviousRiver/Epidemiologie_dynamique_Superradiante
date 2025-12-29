"""
Test CWT amélioré sur UK, Norway, Sweden.

Compare les 3 modèles (SR, SIR, CWT) sur les 3 pays extrêmes pour validation croisée.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel, SIRModel, CWTModel

# Métadonnées pays
COUNTRIES = {
    'United Kingdom': {'name': 'UK', 'pop': 67e6, 'color': '#FF6B6B'},
    'Norway': {'name': 'Norway', 'pop': 5.4e6, 'color': '#4ECDC4'},
    'Sweden': {'name': 'Sweden', 'pop': 10.3e6, 'color': '#FFE66D'}
}


def load_country_data(country_name):
    """Charge les données COVID-19 pour un pays."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"

    df = pd.read_csv(url)
    country_data = df[df['Country/Region'] == country_name]

    cumul_cases = country_data.iloc[:, 4:].sum(axis=0)
    df_country = pd.DataFrame({'cases': cumul_cases})
    df_country.index = pd.to_datetime(df_country.index, format='%m/%d/%y')
    df_country = df_country.loc['2020-02-15':'2020-06-30']

    new_cases = df_country['cases'].diff().fillna(0)
    new_cases[new_cases < 0] = 0

    return np.arange(len(new_cases)), new_cases.values, new_cases.index


def analyze_country(country_name, t_data, y_data, n_modes=3):
    """Analyse un pays avec SR, SIR, CWT."""
    results = {}
    meta = COUNTRIES[country_name]

    # SR
    print(f"  SR...")
    sr_model = SuperRadiantModel(n_modes=n_modes)
    sr_params, sr_rms = sr_model.fit(t_data, y_data, maxfev=100000)
    sr_fit = sr_model.predict(t_data)

    residuals_sr = y_data - sr_fit
    r2_sr = 1 - (np.sum(residuals_sr**2) / np.sum((y_data - np.mean(y_data))**2))

    results['SR'] = {
        'rms': sr_rms,
        'r2': r2_sr,
        'fit': sr_fit,
        'model': sr_model
    }

    # SIR
    print(f"  SIR...")
    sir_model = SIRModel(population=meta['pop'])
    sir_model.fit(t_data, y_data)
    sir_fit = sir_model.predict(t_data)
    sir_quality = sir_model.get_fit_quality(t_data, y_data)

    results['SIR'] = {
        'rms': sir_quality['rms'],
        'r2': sir_quality['r2'],
        'fit': sir_fit,
        'R0': sir_model.get_parameters()['R0']
    }

    # CWT amélioré
    print(f"  CWT (amélioré)...")
    cwt_model = CWTModel(n_modes=n_modes, threshold_factor=1.2, min_time_separation=8)
    cwt_rms = cwt_model.fit(t_data, y_data)
    cwt_fit = cwt_model.predict(t_data)
    cwt_quality = cwt_model.get_fit_quality(t_data, y_data)

    results['CWT'] = {
        'rms': cwt_quality['rms'],
        'r2': cwt_quality['r2'],
        'fit': cwt_fit,
        'n_modes_detected': len(cwt_model.get_mode_parameters())
    }

    # Comparaison SR-CWT
    try:
        comparison = cwt_model.compare_with_sr_modes(sr_model)
        results['comparison'] = comparison
    except:
        results['comparison'] = None

    return results


def main():
    print("="*80)
    print("TEST CWT AMÉLIORÉ : UK, NORWAY, SWEDEN")
    print("="*80 + "\n")

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results', 'cwt_multi_country')
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    all_results = {}

    for country_name, meta in COUNTRIES.items():
        print(f"\n📊 {country_name} ({meta['name']})...")
        t_data, y_data, dates = load_country_data(country_name)
        print(f"  ✅ {len(y_data)} points chargés")

        results = analyze_country(country_name, t_data, y_data, n_modes=3)
        all_results[country_name] = {
            't_data': t_data,
            'y_data': y_data,
            'dates': dates,
            **results
        }

        # Afficher résumé
        print(f"  📈 RMS: SR={results['SR']['rms']:.0f}, SIR={results['SIR']['rms']:.0f}, CWT={results['CWT']['rms']:.0f}")
        print(f"  📈 R²:  SR={results['SR']['r2']:.3f}, SIR={results['SIR']['r2']:.3f}, CWT={results['CWT']['r2']:.3f}")
        print(f"  🔬 Modes CWT détectés: {results['CWT']['n_modes_detected']}")

    # Créer tableau comparatif
    summary = []
    for country_name in COUNTRIES.keys():
        r = all_results[country_name]
        summary.append({
            'Country': COUNTRIES[country_name]['name'],
            'SR_RMS': r['SR']['rms'],
            'SR_R2': r['SR']['r2'],
            'SIR_RMS': r['SIR']['rms'],
            'SIR_R2': r['SIR']['r2'],
            'SIR_R0': r['SIR']['R0'],
            'CWT_RMS': r['CWT']['rms'],
            'CWT_R2': r['CWT']['r2'],
            'CWT_Modes': r['CWT']['n_modes_detected'],
            'Best_Model': 'SR' if r['SR']['rms'] < min(r['SIR']['rms'], r['CWT']['rms']) else ('SIR' if r['SIR']['rms'] < r['CWT']['rms'] else 'CWT')
        })

    df = pd.DataFrame(summary)
    csv_path = os.path.join(output_dir, 'cwt_multi_country_summary.csv')
    df.to_csv(csv_path, index=False)

    print("\n" + "="*80)
    print("TABLEAU RÉCAPITULATIF")
    print("="*80)
    print(df.to_string(index=False))

    print(f"\n✅ Résultats sauvegardés: {csv_path}")

    # Figure comparative
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, (country_name, meta) in enumerate(COUNTRIES.items()):
        r = all_results[country_name]
        ax = axes[idx]

        ax.plot(r['t_data'], r['y_data'], 'o', color='black', markersize=3, alpha=0.6, label='Data')
        ax.plot(r['t_data'], r['SR']['fit'], '-', color='#FF6B6B', linewidth=2, label=f"SR (R²={r['SR']['r2']:.3f})")
        ax.plot(r['t_data'], r['SIR']['fit'], '--', color='purple', linewidth=2, label=f"SIR (R²={r['SIR']['r2']:.3f})")
        ax.plot(r['t_data'], r['CWT']['fit'], '-.', color='#4ECDC4', linewidth=2, label=f"CWT (R²={r['CWT']['r2']:.3f})")

        ax.set_title(f"{meta['name']}: SR vs SIR vs CWT Improved", fontweight='bold')
        ax.set_xlabel('Days since 15/02/2020')
        ax.set_ylabel('New cases')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'cwt_multi_country_comparison.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"✅ Figure sauvegardée: {fig_path}")

    return all_results


if __name__ == '__main__':
    main()
