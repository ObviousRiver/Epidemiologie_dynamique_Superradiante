#!/usr/bin/env python3
"""
Analyse Régionale COVID-19 FRANCE Vague 1 - DONNÉES RÉELLES
============================================================

Version améliorée utilisant les données Santé Publique France par département.

Source: https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4
Fichier: donnees-hospitalieres-covid19.csv

Correspondance Départements → Régions (nouvelle nomenclature 2016):
- Grand Est: 08, 10, 51, 52, 54, 55, 57, 67, 68, 88
- Île-de-France: 75, 77, 78, 91, 92, 93, 94, 95
- Hauts-de-France: 02, 59, 60, 62, 80
- Provence-Alpes-Côte d'Azur: 04, 05, 06, 13, 83, 84
- Auvergne-Rhône-Alpes: 01, 03, 07, 15, 26, 38, 42, 43, 63, 69, 73, 74
- Nouvelle-Aquitaine: 16, 17, 19, 23, 24, 33, 40, 47, 64, 79, 86, 87
- Occitanie: 09, 11, 12, 30, 31, 32, 34, 46, 48, 65, 66, 81, 82
- Bretagne: 22, 29, 35, 56
- Normandie: 14, 27, 50, 61, 76
- Pays de la Loire: 44, 49, 53, 72, 85
- Centre-Val de Loire: 18, 28, 36, 37, 41, 45
- Bourgogne-Franche-Comté: 21, 25, 39, 58, 70, 71, 89, 90
- Corse: 2A, 2B
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import odeint

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (18, 14)


# ============================================================================
# CORRESPONDANCE DÉPARTEMENTS → RÉGIONS
# ============================================================================

REGIONS_MAPPING = {
    'Grand Est': ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
    'Île-de-France': ['75', '77', '78', '91', '92', '93', '94', '95'],
    'Hauts-de-France': ['02', '59', '60', '62', '80'],
    'PACA': ['04', '05', '06', '13', '83', '84'],
    'Auvergne-Rhône-Alpes': ['01', '03', '07', '15', '26', '38', '42', '43', '63', '69', '73', '74'],
    'Nouvelle-Aquitaine': ['16', '17', '19', '23', '24', '33', '40', '47', '64', '79', '86', '87'],
    'Occitanie': ['09', '11', '12', '30', '31', '32', '34', '46', '48', '65', '66', '81', '82'],
    'Bretagne': ['22', '29', '35', '56'],
    'Normandie': ['14', '27', '50', '61', '76'],
    'Pays de la Loire': ['44', '49', '53', '72', '85'],
    'Centre-Val de Loire': ['18', '28', '36', '37', '41', '45'],
    'Bourgogne-Franche-Comté': ['21', '25', '39', '58', '70', '71', '89', '90'],
    'Corse': ['2A', '2B']
}


# ============================================================================
# CHARGEMENT DONNÉES RÉELLES
# ============================================================================

def load_real_data_spf():
    """
    Tente de charger les données réelles depuis Santé Publique France.

    Retourne:
        t_data, regions_dict, national, dates si succès
        None si échec
    """
    url = 'https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4'

    print("📥 Tentative de chargement des données SPF (hospitalisations)...")

    try:
        df = pd.read_csv(url, sep=';', low_memory=False)
        print(f"✅ Données SPF chargées: {len(df):,} lignes")

        # Convertir date
        df['jour'] = pd.to_datetime(df['jour'])

        # Filtrer Vague 1
        wave1 = df[(df['jour'] >= '2020-02-15') & (df['jour'] <= '2020-06-30')]
        print(f"📊 Vague 1: {len(wave1):,} lignes")

        # Convertir dep en string
        wave1 = wave1.copy()
        wave1['dep'] = wave1['dep'].astype(str)

        # Agréger par région et date
        # Utiliser 'hosp' (hospitalisations) ou 'rea' (réanimation) comme métrique
        metric = 'hosp' if 'hosp' in wave1.columns else 'rea'

        regions_data = {}
        dates_range = pd.date_range('2020-02-15', '2020-06-30', freq='D')

        for region_name, depts in REGIONS_MAPPING.items():
            # Filtrer les départements de cette région
            region_df = wave1[wave1['dep'].isin(depts)]

            if len(region_df) > 0:
                # Agréger par date
                daily = region_df.groupby('jour')[metric].sum()

                # Réindexer pour avoir toutes les dates
                daily = daily.reindex(dates_range, fill_value=0)

                # Calculer la dérivée (nouveaux cas/jour) et lisser
                daily_new = daily.diff().fillna(0)
                daily_smooth = daily_new.rolling(window=7, center=True).mean().fillna(0)

                # Normaliser
                if daily_smooth.max() > 0:
                    daily_norm = daily_smooth / daily_smooth.max()
                else:
                    daily_norm = daily_smooth

                regions_data[region_name] = daily_norm.values

        # Calculer la dynamique nationale
        national_df = wave1.groupby('jour')[metric].sum()
        national_df = national_df.reindex(dates_range, fill_value=0)
        national_new = national_df.diff().fillna(0)
        national_smooth = national_new.rolling(window=7, center=True).mean().fillna(0)
        national_norm = national_smooth / national_smooth.max() if national_smooth.max() > 0 else national_smooth

        t_data = np.arange(len(dates_range))

        print(f"✅ Données régionales extraites: {len(regions_data)} régions")
        for region, data in regions_data.items():
            if data.max() > 0:
                print(f"   - {region}: pic={data.max():.3f} au jour {np.argmax(data)}")

        return t_data, regions_data, national_norm.values, dates_range

    except Exception as e:
        print(f"❌ Impossible de charger les données SPF: {e}")
        print(f"   Utilisation des données synthétiques à la place.")
        return None


def generate_synthetic_data():
    """
    Génère des données régionales synthétiques (fallback).
    Basées sur les faits historiques documentés.
    """
    print("📊 Génération de données synthétiques (basées sur faits historiques)...")

    t_data = np.arange(136)

    # Populations régionales (millions)
    pop = {
        'Grand Est': 5.6,
        'Île-de-France': 12.2,
        'Hauts-de-France': 6.0,
        'PACA': 5.1,
        'Auvergne-Rhône-Alpes': 8.0,
        'Nouvelle-Aquitaine': 6.0,
        'Occitanie': 5.9,
    }

    def sech2(t, tau, T, A):
        return A * np.power(1/np.cosh((t - tau) / (2 * T)), 2)

    # Grand Est: Multi-modes (propagation libre)
    ge = (sech2(t_data, 28, 4.5, 0.35) +
          sech2(t_data, 38, 6.0, 0.20) +
          sech2(t_data, 52, 9.0, 0.10))

    # Île-de-France: Bi-modal
    idf = sech2(t_data, 38, 5.5, 0.40) + sech2(t_data, 50, 7.0, 0.15)

    # Hauts-de-France: Pic synchronisé
    hdf = sech2(t_data, 45, 8.0, 0.28)

    # PACA: Pic synchronisé
    paca = sech2(t_data, 48, 7.5, 0.22)

    # Auvergne-Rhône-Alpes: Légèrement décalé
    ara = sech2(t_data, 50, 8.5, 0.25)

    # Nouvelle-Aquitaine: Tardif
    na = sech2(t_data, 52, 9.0, 0.18)

    # Occitanie: Tardif
    occ = sech2(t_data, 54, 9.5, 0.16)

    regions_data = {
        'Grand Est': ge / ge.max(),
        'Île-de-France': idf / idf.max(),
        'Hauts-de-France': hdf / hdf.max(),
        'PACA': paca / paca.max(),
        'Auvergne-Rhône-Alpes': ara / ara.max(),
        'Nouvelle-Aquitaine': na / na.max(),
        'Occitanie': occ / occ.max(),
    }

    # National = superposition pondérée
    total_pop = sum(pop.values())
    national = sum(pop[r] * regions_data[r] for r in regions_data.keys()) / total_pop
    national = national / national.max()

    dates = pd.date_range('2020-02-15', periods=136, freq='D')

    print(f"✅ {len(regions_data)} régions synthétiques générées")

    return t_data, regions_data, national, dates


# ============================================================================
# MODÈLES (identiques au script précédent)
# ============================================================================

def sech_squared(t, A, tau, T):
    """Mode super-radiant sech²."""
    return A * np.power(1/np.cosh((t - tau) / (2 * T)), 2)

def superradiant_model(t, *params):
    """Modèle SR avec N modes."""
    N = len(params) // 3
    y = np.zeros_like(t, dtype=float)
    for i in range(N):
        A, tau, T = params[3*i], params[3*i+1], params[3*i+2]
        y += sech_squared(t, A, tau, T)
    return y

def sir_model_ode(y, t, beta, gamma, N):
    """Système d'équations différentielles SIR."""
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return [dSdt, dIdt, dRdt]

def fit_sir_model(t_data, y_data):
    """Ajuste le modèle SIR aux données."""
    N = 1.0
    I0 = y_data[0] if y_data[0] > 0 else 0.001
    S0 = N - I0
    R0 = 0.0
    y0 = [S0, I0, R0]

    def sir_fit(t, beta, gamma):
        sol = odeint(sir_model_ode, y0, t, args=(beta, gamma, N))
        return sol[:, 1]

    try:
        bounds = ([0.1, 0.01], [2.0, 0.5])
        params, _ = curve_fit(sir_fit, t_data, y_data, p0=[0.5, 0.1],
                             bounds=bounds, maxfev=5000)
        y_fit = sir_fit(t_data, *params)
        rms = np.sqrt(np.mean((y_data - y_fit)**2))
        return params, y_fit, rms
    except:
        return None, None, np.inf

def fit_superradiant(t_data, y_data, n_modes=4):
    """Ajuste le modèle Super-Radiant."""
    p0 = []
    t_max_idx = np.argmax(y_data)
    for i in range(n_modes):
        A = 1.0 / n_modes
        tau = t_max_idx + i * 10
        T = 5.0 + i * 2
        p0.extend([A, tau, T])

    bounds_low = [0.01, 0, 1] * n_modes
    bounds_high = [2.0, len(t_data), 30] * n_modes

    try:
        params, _ = curve_fit(superradiant_model, t_data, y_data,
                             p0=p0, bounds=(bounds_low, bounds_high),
                             maxfev=10000)
        y_fit = superradiant_model(t_data, *params)
        rms = np.sqrt(np.mean((y_data - y_fit)**2))
        return params, y_fit, rms
    except:
        return None, None, np.inf


# ============================================================================
# ANALYSE
# ============================================================================

def analyze_region(region_name, t_data, y_data, n_modes=2):
    """Analyse une région: SR vs SIR."""
    print(f"\n{'='*70}")
    print(f"🔍 Analyse: {region_name}")
    print(f"{'='*70}")

    sr_params, sr_fit, sr_rms = fit_superradiant(t_data, y_data, n_modes=n_modes)
    sir_params, sir_fit, sir_rms = fit_sir_model(t_data, y_data)

    if sr_rms < np.inf and sir_rms < np.inf:
        ratio = sir_rms / sr_rms if sr_rms > 1e-6 else 0
        winner = "SR" if ratio > 1.0 else "SIR"

        print(f"\n📊 Résultats:")
        print(f"   RMS Super-Radiant: {sr_rms:.4f}")
        print(f"   RMS SIR:           {sir_rms:.4f}")
        print(f"   Ratio SIR/SR:      {ratio:.2f}x")
        print(f"   🏆 Gagnant:         {winner}")

        if sr_params is not None and n_modes > 0:
            print(f"\n🎯 Modes Super-Radiant détectés:")
            for i in range(n_modes):
                A = sr_params[3*i]
                tau = sr_params[3*i+1]
                T = sr_params[3*i+2]
                if A > 0.05:
                    print(f"   Mode {i+1}: τ={tau:5.1f}j, T={T:4.1f}j, A={A:.3f}")

        return {
            'region': region_name,
            'sr_rms': sr_rms,
            'sir_rms': sir_rms,
            'ratio': ratio,
            'winner': winner,
            'sr_params': sr_params,
            'sr_fit': sr_fit,
            'sir_fit': sir_fit
        }

    return None


# ============================================================================
# VISUALISATION
# ============================================================================

def plot_regional_analysis(t_data, regions, national, dates, results, data_source):
    """Visualise l'analyse régionale complète."""

    fig = plt.figure(figsize=(18, 14))

    # Sélectionner top 5 régions par amplitude
    top_regions = sorted(regions.items(),
                        key=lambda x: np.max(x[1]),
                        reverse=True)[:5]

    n_regions = len(top_regions)

    colors = plt.cm.tab10(np.linspace(0, 0.9, n_regions))
    region_colors = {name: colors[i] for i, (name, _) in enumerate(top_regions)}

    # Titre
    fig.suptitle(f'🇫🇷 Analyse Régionale France - Vague 1 COVID-19\n' +
                 f'Données: {data_source}',
                 fontsize=16, fontweight='bold')

    # 1. Superposition
    ax1 = plt.subplot(3, 3, (1, 3))
    for region_name, y_data in top_regions:
        ax1.plot(dates, y_data, label=region_name,
                color=region_colors[region_name], linewidth=2, alpha=0.7)
    ax1.plot(dates, national, 'k-', linewidth=3, label='National', alpha=0.8)
    ax1.set_ylabel('Incidence Normalisée', fontsize=11)
    ax1.set_title('A. Superposition des Dynamiques Régionales',
                 fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', framealpha=0.9)
    ax1.grid(True, alpha=0.3)
    ax1.axvline(pd.Timestamp('2020-03-17'), color='red',
               linestyle='--', alpha=0.5, linewidth=2)
    ax1.text(pd.Timestamp('2020-03-17'), ax1.get_ylim()[1]*0.95,
            ' Confinement', fontsize=9, color='red')

    # 2-6. Analyses régionales
    valid_results = [r for r in results if r and r['region'] in [n for n, _ in top_regions]]

    for idx, result in enumerate(valid_results[:5]):
        row = 1 + idx // 3
        col = idx % 3
        ax = plt.subplot(3, 3, 4 + idx)

        region_name = result['region']
        y_data = regions[region_name]

        ax.plot(t_data, y_data, 'o', color=region_colors[region_name],
               markersize=3, alpha=0.6, label='Données')

        if result['sr_fit'] is not None:
            ax.plot(t_data, result['sr_fit'], '-', color='#9b59b6',
                   linewidth=2.5, label=f'SR (RMS={result["sr_rms"]:.3f})')
        if result['sir_fit'] is not None:
            ax.plot(t_data, result['sir_fit'], '--', color='#e67e22',
                   linewidth=2, label=f'SIR (RMS={result["sir_rms"]:.3f})')

        ax.set_title(f'{result["region"]} - {result["winner"]} ({result["ratio"]:.2f}x)',
                    fontsize=10, fontweight='bold')
        ax.set_xlabel('Jours depuis 15/02/2020', fontsize=9)
        ax.set_ylabel('Incidence', fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = '/home/user/Epid-miologie/reports/france_regional_real_data.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n💾 Graphique sauvegardé: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*80)
    print("🇫🇷 ANALYSE RÉGIONALE FRANCE - DONNÉES RÉELLES (si disponibles)")
    print("="*80)

    # Tenter de charger données réelles
    real_data = load_real_data_spf()

    if real_data is not None:
        t_data, regions, national, dates = real_data
        data_source = "Santé Publique France (données réelles)"
        print("✅ Utilisation des DONNÉES RÉELLES")
    else:
        t_data, regions, national, dates = generate_synthetic_data()
        data_source = "Synthétiques (basées sur faits historiques)"
        print("⚠️  Utilisation des DONNÉES SYNTHÉTIQUES")

    print(f"\n📊 Configuration:")
    print(f"   Période: {dates[0].strftime('%d/%m/%Y')} - {dates[-1].strftime('%d/%m/%Y')}")
    print(f"   Nombre de jours: {len(t_data)}")
    print(f"   Régions analysées: {len(regions)}")

    # Analyser chaque région
    results = []
    region_modes = {
        'Grand Est': 3,
        'Île-de-France': 2,
        'Hauts-de-France': 2,
        'PACA': 2,
        'Auvergne-Rhône-Alpes': 2,
        'Nouvelle-Aquitaine': 2,
        'Occitanie': 2
    }

    for region_name, y_data in regions.items():
        if np.max(y_data) > 0.01:  # Seulement si données significatives
            n_modes = region_modes.get(region_name, 2)
            result = analyze_region(region_name, t_data, y_data, n_modes=n_modes)
            if result:
                results.append(result)

    # Visualisation
    print("\n" + "="*70)
    print("📊 Création de la visualisation...")
    print("="*70)
    plot_regional_analysis(t_data, regions, national, dates, results, data_source)

    # Conclusions
    print("\n" + "="*80)
    print("🎯 RÉSUMÉ")
    print("="*80)

    for result in sorted(results, key=lambda r: r['ratio'], reverse=True):
        print(f"  {result['region']:25s} - {result['winner']:3s} gagne {result['ratio']:6.2f}x")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
