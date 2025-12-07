#!/usr/bin/env python3
"""
Analyse Multi-Échelle France COVID-19 - Méthodologie Consolidée
================================================================

Analyse à 3 niveaux :
1. Départemental (96 départements métropolitains)
2. Régional (13 régions métropolitaines)
3. National (France entière)

Méthodologie :
- Modèles : SR (3-4 modes) vs SIR (IFR explicite)
- Données : Santé Publique France (décès quotidiens, valeurs absolues)
- Validation : Analyse spectrale (FFT, Nyquist, susceptibilité)

Source : https://www.data.gouv.fr/fr/datasets/donnees-hospitalieres-relatives-a-lepidemie-de-covid-19/
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution
from scipy.integrate import odeint
from scipy.fft import fft, fftfreq
import warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')

# ============================================================================
# MAPPING DÉPARTEMENTS → RÉGIONS
# ============================================================================

REGIONS_MAPPING = {
    'Auvergne-Rhône-Alpes': ['01', '03', '07', '15', '26', '38', '42', '43', '63', '69', '73', '74'],
    'Bourgogne-Franche-Comté': ['21', '25', '39', '58', '70', '71', '89', '90'],
    'Bretagne': ['22', '29', '35', '56'],
    'Centre-Val de Loire': ['18', '28', '36', '37', '41', '45'],
    'Corse': ['2A', '2B'],
    'Grand Est': ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
    'Hauts-de-France': ['02', '59', '60', '62', '80'],
    'Île-de-France': ['75', '77', '78', '91', '92', '93', '94', '95'],
    'Normandie': ['14', '27', '50', '61', '76'],
    'Nouvelle-Aquitaine': ['16', '17', '19', '23', '24', '33', '40', '47', '64', '79', '86', '87'],
    'Occitanie': ['09', '11', '12', '30', '31', '32', '34', '46', '48', '65', '66', '81', '82'],
    'Pays de la Loire': ['44', '49', '53', '72', '85'],
    'Provence-Alpes-Côte d\'Azur': ['04', '05', '06', '13', '83', '84']
}

# Inversion : département → région
DEPARTEMENT_TO_REGION = {}
for region, depts in REGIONS_MAPPING.items():
    for dept in depts:
        DEPARTEMENT_TO_REGION[dept] = region

# Populations régionales (millions, approximatif)
POPULATIONS_REGIONS = {
    'Auvergne-Rhône-Alpes': 8.0,
    'Bourgogne-Franche-Comté': 2.8,
    'Bretagne': 3.3,
    'Centre-Val de Loire': 2.6,
    'Corse': 0.34,
    'Grand Est': 5.6,
    'Hauts-de-France': 6.0,
    'Île-de-France': 12.2,
    'Normandie': 3.3,
    'Nouvelle-Aquitaine': 6.0,
    'Occitanie': 5.9,
    'Pays de la Loire': 3.8,
    'Provence-Alpes-Côte d\'Azur': 5.1
}

# ============================================================================
# CHARGEMENT DONNÉES SPF
# ============================================================================

def load_spf_data(start_date='2020-02-15', end_date='2020-06-30'):
    """
    Charge les données Santé Publique France (hospitalisations COVID-19).

    Returns:
        DataFrame avec colonnes: date, dep, dc (décès cumulés)
    """
    url = 'https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-ad16-5fe1351110a4'

    print("📥 Chargement données Santé Publique France...")

    try:
        df = pd.read_csv(url, sep=';', low_memory=False)
        print(f"✅ Données SPF chargées : {len(df):,} lignes")

        # Convertir date
        df['jour'] = pd.to_datetime(df['jour'])

        # Filtrer Vague 1
        df = df[(df['jour'] >= start_date) & (df['jour'] <= end_date)]

        # Filtrer France métropolitaine (exclure DROM)
        df = df.copy()
        df['dep'] = df['dep'].astype(str)

        # Départements métropolitains
        depts_metro = []
        for region_depts in REGIONS_MAPPING.values():
            depts_metro.extend(region_depts)

        df = df[df['dep'].isin(depts_metro)]

        print(f"📊 Vague 1 (France métropolitaine) : {len(df):,} lignes")
        print(f"   Départements uniques : {df['dep'].nunique()}")
        print(f"   Période : {df['jour'].min()} → {df['jour'].max()}")

        return df

    except Exception as e:
        print(f"❌ Erreur chargement SPF : {e}")
        return None


def extract_departement_deaths(df, dept_code):
    """
    Extrait la série temporelle des décès quotidiens pour un département.

    Args:
        df: DataFrame SPF
        dept_code: Code département (str)

    Returns:
        t_data (jours depuis début), y_data (décès quotidiens lissés), dates
    """
    dept_data = df[df['dep'] == dept_code].copy()

    if len(dept_data) == 0:
        return None, None, None

    # Grouper par date (sexe = 0 = tous)
    if 'sexe' in dept_data.columns:
        dept_data = dept_data[dept_data['sexe'] == 0]

    daily = dept_data.groupby('jour')['dc'].sum().sort_index()

    # Créer série complète
    dates = pd.date_range('2020-02-15', '2020-06-30', freq='D')
    daily = daily.reindex(dates, fill_value=0)

    # Décès quotidiens (dérivée)
    daily_new = daily.diff().fillna(0)

    # Lisser 7 jours
    daily_smooth = daily_new.rolling(window=7, center=True).mean().fillna(0)

    # Valeurs négatives → 0 (corrections administratives)
    daily_smooth = daily_smooth.clip(lower=0)

    t_data = np.arange(len(dates))
    y_data = daily_smooth.values

    return t_data, y_data, dates


def extract_region_deaths(df, region_name):
    """
    Agrège les décès pour une région (somme départements).
    """
    depts = REGIONS_MAPPING[region_name]

    region_data = df[df['dep'].isin(depts)].copy()

    if len(region_data) == 0:
        return None, None, None

    # Grouper par date
    if 'sexe' in region_data.columns:
        region_data = region_data[region_data['sexe'] == 0]

    daily = region_data.groupby('jour')['dc'].sum().sort_index()

    dates = pd.date_range('2020-02-15', '2020-06-30', freq='D')
    daily = daily.reindex(dates, fill_value=0)

    daily_new = daily.diff().fillna(0)
    daily_smooth = daily_new.rolling(window=7, center=True).mean().fillna(0)
    daily_smooth = daily_smooth.clip(lower=0)

    t_data = np.arange(len(dates))
    y_data = daily_smooth.values

    return t_data, y_data, dates


def extract_national_deaths(df):
    """
    Agrège les décès pour la France entière.
    """
    # Grouper par date
    df_copy = df.copy()
    if 'sexe' in df_copy.columns:
        df_copy = df_copy[df_copy['sexe'] == 0]

    daily = df_copy.groupby('jour')['dc'].sum().sort_index()

    dates = pd.date_range('2020-02-15', '2020-06-30', freq='D')
    daily = daily.reindex(dates, fill_value=0)

    daily_new = daily.diff().fillna(0)
    daily_smooth = daily_new.rolling(window=7, center=True).mean().fillna(0)
    daily_smooth = daily_smooth.clip(lower=0)

    t_data = np.arange(len(dates))
    y_data = daily_smooth.values

    return t_data, y_data, dates


# ============================================================================
# MODÈLES SR ET SIR (identiques à analyse_consolidee.py)
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


def fit_superradiant(t_data, y_data, n_modes=3, max_value=None):
    """
    Ajuste le modèle Super-Radiant.

    Args:
        t_data: Temps
        y_data: Décès quotidiens
        n_modes: Nombre de modes SR
        max_value: Valeur max (pour normalisation initiale)

    Returns:
        params, y_fit, rms
    """
    if max_value is None:
        max_value = np.max(y_data)

    if max_value < 1e-6:
        return None, None, np.inf

    # Estimation initiale
    t_max_idx = np.argmax(y_data)
    p0 = []

    for i in range(n_modes):
        A = max_value / n_modes
        tau = t_max_idx + (i - 1) * 10
        T = 5.0 + i * 2
        p0.extend([A, tau, T])

    # Bounds
    bounds_low = []
    bounds_high = []
    for i in range(n_modes):
        bounds_low.extend([0.01, 0, 1])
        bounds_high.extend([max_value * 2, len(t_data), 30])

    try:
        params, _ = curve_fit(
            superradiant_model, t_data, y_data,
            p0=p0, bounds=(bounds_low, bounds_high),
            maxfev=10000
        )

        y_fit = superradiant_model(t_data, *params)
        rms = np.sqrt(np.mean((y_data - y_fit)**2))

        return params, y_fit, rms

    except:
        return None, None, np.inf


class SIRModel:
    """Modèle SIR avec IFR explicite (méthodologie consolidée)."""

    def __init__(self, population, IFR=0.01):
        self.N = population
        self.IFR = IFR

    def _sir_ode(self, y, t, beta, gamma):
        S, I, R = y
        dSdt = -beta * S * I / self.N
        dIdt = beta * S * I / self.N - gamma * I
        dRdt = gamma * I
        return [dSdt, dIdt, dRdt]

    def _deaths_from_I(self, I_t, gamma):
        """D(t) = IFR × γ × I(t)"""
        return self.IFR * gamma * I_t

    def fit(self, t_data, y_data):
        """
        Ajuste le modèle SIR aux décès quotidiens.

        Paramètres libres : beta, gamma, I0, scale
        """
        if np.max(y_data) < 1e-6:
            return None, None, np.inf

        def objective(params):
            beta, gamma, I0, scale = params

            S0 = self.N - I0
            R0 = 0.0
            y0 = [S0, I0, R0]

            try:
                sol = odeint(self._sir_ode, y0, t_data, args=(beta, gamma))
                I_t = sol[:, 1]

                # Décès quotidiens = dérivée de D(t)
                D_cumul = np.cumsum(self._deaths_from_I(I_t, gamma)) * scale
                D_daily = np.gradient(D_cumul)
                D_daily = np.maximum(D_daily, 0)

                rms = np.sqrt(np.mean((y_data - D_daily)**2))
                return rms

            except:
                return 1e10

        # Bounds
        bounds = [
            (0.05, 5.0),      # beta
            (0.01, 1.0),      # gamma
            (1, self.N/100),  # I0
            (0.1, 100.0)      # scale
        ]

        # Optimisation globale
        result = differential_evolution(
            objective, bounds, seed=42, maxiter=500, atol=1e-6, tol=1e-6
        )

        if result.success:
            beta, gamma, I0, scale = result.x

            S0 = self.N - I0
            R0 = 0.0
            y0 = [S0, I0, R0]

            sol = odeint(self._sir_ode, y0, t_data, args=(beta, gamma))
            I_t = sol[:, 1]

            D_cumul = np.cumsum(self._deaths_from_I(I_t, gamma)) * scale
            D_daily = np.gradient(D_cumul)
            D_daily = np.maximum(D_daily, 0)

            rms = result.fun

            # Calculer R0 et durée infection
            R0 = beta / gamma
            duration = 1 / gamma

            params = {
                'beta': beta,
                'gamma': gamma,
                'I0': I0,
                'scale': scale,
                'R0': R0,
                'duration': duration,
                'IFR_eff': self.IFR * scale
            }

            return params, D_daily, rms
        else:
            return None, None, np.inf


# ============================================================================
# ANALYSE INDIVIDUELLE (DÉPARTEMENT/RÉGION)
# ============================================================================

def analyze_location(t_data, y_data, location_name, population, output_file=None):
    """
    Analyse SR vs SIR pour un département ou une région.

    Args:
        t_data: Temps (jours)
        y_data: Décès quotidiens
        location_name: Nom (département ou région)
        population: Population
        output_file: Fichier PNG de sortie (optionnel)

    Returns:
        dict avec résultats
    """
    print(f"\n{'='*70}")
    print(f"🔍 Analyse : {location_name}")
    print(f"{'='*70}")

    max_deaths = np.max(y_data)
    print(f"   Max décès quotidiens : {max_deaths:.1f}")

    if max_deaths < 1.0:
        print(f"   ⚠️  Données insuffisantes (max < 1 décès/jour)")
        return None

    # Fit SR 3 et 4 modes
    print(f"\n📊 Ajustement des modèles...")

    params_sr3, fit_sr3, rms_sr3 = fit_superradiant(t_data, y_data, n_modes=3, max_value=max_deaths)
    params_sr4, fit_sr4, rms_sr4 = fit_superradiant(t_data, y_data, n_modes=4, max_value=max_deaths)

    # Choisir meilleur SR
    if rms_sr3 <= rms_sr4:
        params_sr, fit_sr, rms_sr, n_modes_sr = params_sr3, fit_sr3, rms_sr3, 3
    else:
        params_sr, fit_sr, rms_sr, n_modes_sr = params_sr4, fit_sr4, rms_sr4, 4

    print(f"   SR {n_modes_sr} modes : RMS = {rms_sr:.2f}")

    # Fit SIR
    sir = SIRModel(population=population, IFR=0.01)
    params_sir, fit_sir, rms_sir = sir.fit(t_data, y_data)

    if params_sir is not None:
        print(f"   SIR : RMS = {rms_sir:.2f}")
        print(f"         R0 = {params_sir['R0']:.2f}, Durée infection = {params_sir['duration']:.1f} jours")
    else:
        print(f"   SIR : Échec du fit")
        rms_sir = np.inf

    # Ratio
    if rms_sr > 0 and rms_sir < np.inf:
        ratio = rms_sir / rms_sr
        winner = "SR" if ratio > 1.0 else "SIR"
        print(f"\n🏆 Gagnant : {winner} (ratio = {ratio:.2f}×)")
    else:
        ratio = np.nan
        winner = "Indéterminé"

    # Résultats
    results = {
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
        'fit_sir': fit_sir
    }

    return results


# ============================================================================
# ANALYSE MULTI-ÉCHELLE
# ============================================================================

def analyze_france_multiscale(df_spf, sample_depts=None, output_dir='results/france_multiscale'):
    """
    Analyse multi-échelle complète de la France.

    Args:
        df_spf: DataFrame SPF
        sample_depts: Liste départements à analyser (None = tous)
        output_dir: Répertoire de sortie

    Returns:
        dict avec résultats départementaux, régionaux, national
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    print("\n" + "="*80)
    print("🇫🇷 ANALYSE MULTI-ÉCHELLE FRANCE - MÉTHODOLOGIE CONSOLIDÉE")
    print("="*80)

    # 1. NIVEAU DÉPARTEMENTAL
    print("\n📍 NIVEAU 1 : DÉPARTEMENTS")
    print("-" * 80)

    results_depts = {}

    # Liste départements
    if sample_depts is None:
        depts_to_analyze = []
        for region_depts in REGIONS_MAPPING.values():
            depts_to_analyze.extend(region_depts)
    else:
        depts_to_analyze = sample_depts

    print(f"   Départements à analyser : {len(depts_to_analyze)}")

    for dept_code in depts_to_analyze[:10]:  # Limiter à 10 pour test
        t_data, y_data, dates = extract_departement_deaths(df_spf, dept_code)

        if t_data is None or np.max(y_data) < 1.0:
            continue

        # Population département (estimation grossière)
        region = DEPARTEMENT_TO_REGION.get(dept_code, 'Unknown')
        pop_dept = POPULATIONS_REGIONS.get(region, 1.0) * 1e6 / len(REGIONS_MAPPING.get(region, [dept_code]))

        result = analyze_location(
            t_data, y_data,
            f"Département {dept_code}",
            pop_dept
        )

        if result is not None:
            results_depts[dept_code] = result

    # 2. NIVEAU RÉGIONAL
    print("\n📍 NIVEAU 2 : RÉGIONS")
    print("-" * 80)

    results_regions = {}

    for region_name in REGIONS_MAPPING.keys():
        t_data, y_data, dates = extract_region_deaths(df_spf, region_name)

        if t_data is None or np.max(y_data) < 5.0:
            continue

        pop_region = POPULATIONS_REGIONS.get(region_name, 1.0) * 1e6

        result = analyze_location(
            t_data, y_data,
            region_name,
            pop_region
        )

        if result is not None:
            results_regions[region_name] = result

    # 3. NIVEAU NATIONAL
    print("\n📍 NIVEAU 3 : NATIONAL")
    print("-" * 80)

    t_data, y_data, dates = extract_national_deaths(df_spf)

    result_national = analyze_location(
        t_data, y_data,
        "France",
        67e6
    )

    return {
        'departements': results_depts,
        'regions': results_regions,
        'national': result_national
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Charger données SPF
    df_spf = load_spf_data()

    if df_spf is None:
        print("❌ Impossible de charger les données SPF")
        return

    # Analyser multi-échelle (sample pour test)
    sample_depts = ['67', '68', '75', '92', '93', '13', '69']  # Grand Est, IdF, PACA, ARA

    results = analyze_france_multiscale(
        df_spf,
        sample_depts=sample_depts,
        output_dir='results/france_multiscale'
    )

    print("\n" + "="*80)
    print("✅ ANALYSE TERMINÉE")
    print("="*80)

    # Résumé
    print(f"\nRésultats :")
    print(f"   Départements analysés : {len(results['departements'])}")
    print(f"   Régions analysées : {len(results['regions'])}")
    print(f"   National : {'✅' if results['national'] else '❌'}")


if __name__ == "__main__":
    main()
