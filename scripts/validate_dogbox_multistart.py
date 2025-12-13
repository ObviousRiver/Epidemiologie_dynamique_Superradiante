#!/usr/bin/env python3
"""
Validation DOGBOX avec Multi-Start
===================================

Teste DOGBOX avec 10 initialisations différentes pour vérifier :
1. Convergence vers le même minimum (reproductibilité)
2. Stabilité de la solution
3. Variance des paramètres (β, γ, I0, scale)

Pays testés : France, Italy, USA, Canada
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.integrate import odeint


class SIRMultiStart:
    """SIR avec tests multi-start pour validation."""

    def __init__(self, population, IFR=0.01):
        self.N = population
        self.IFR = IFR

    def _sir_equations(self, y, t, beta, gamma):
        S, I, R = y
        dS = -beta * S * I / self.N
        dI = beta * S * I / self.N - gamma * I
        dR = gamma * I
        return np.array([dS, dI, dR])

    def _sir_fit_deaths(self, t, beta, gamma, I0, scale):
        S0 = self.N - I0
        R0 = 0
        y0 = (S0, I0, R0)
        sol = odeint(self._sir_equations, y0, t, args=(beta, gamma))
        I_t = sol[:, 1]
        deaths = self.IFR * gamma * I_t * scale
        return deaths

    def fit_with_init(self, t_data, y_data, p0):
        """Fit DOGBOX avec initialisation spécifique."""
        bounds_lower = [0.01, 0.01, 1, 0.01]
        bounds_upper = [5.0, 1.0, self.N / 100, 100.0]

        try:
            params, cov = curve_fit(
                self._sir_fit_deaths,
                t_data,
                y_data,
                p0=p0,
                bounds=(bounds_lower, bounds_upper),
                method='dogbox',
                maxfev=10000
            )

            y_fit = self._sir_fit_deaths(t_data, *params)
            rms = np.sqrt(np.mean((y_data - y_fit)**2))

            beta, gamma, I0, scale = params
            R0 = beta / gamma
            duration = 1 / gamma

            return {
                'success': True,
                'rms': rms,
                'beta': beta,
                'gamma': gamma,
                'I0': I0,
                'scale': scale,
                'R0': R0,
                'duration': duration
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


def load_country_data(country_name):
    """Charge les données COVID-19."""
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

    return t_data, y_data


def generate_initializations(n_init=10):
    """
    Génère n_init initialisations différentes couvrant l'espace des paramètres.

    Stratégie :
    - Beta : [0.1, 0.3, 0.5, 1.0, 2.0]
    - Gamma : [0.05, 0.1, 0.2, 0.5]
    - I0 : [100, 500, 1000, 5000, 10000]
    - Scale : [0.5, 1.0, 2.0, 5.0]
    """
    np.random.seed(42)  # Reproductibilité

    initializations = []

    # Initialisation 1 : Standard (référence)
    initializations.append([0.3, 0.1, 1000, 1.0])

    # Initialisations 2-10 : Exploration systématique
    beta_values = [0.1, 0.5, 1.0, 2.0, 0.2, 0.4, 0.7, 1.5, 3.0]
    gamma_values = [0.05, 0.2, 0.5, 0.1, 0.15, 0.3, 0.4, 0.7, 0.8]
    I0_values = [100, 500, 5000, 10000, 200, 2000, 7000, 50, 20000]
    scale_values = [0.5, 2.0, 5.0, 1.0, 0.2, 0.8, 3.0, 10.0, 0.1]

    for i in range(min(n_init - 1, 9)):
        initializations.append([
            beta_values[i],
            gamma_values[i],
            I0_values[i],
            scale_values[i]
        ])

    return initializations[:n_init]


def validate_country(country_name, population):
    """Valide DOGBOX avec multi-start."""

    print(f"\n{'='*70}")
    print(f"VALIDATION MULTI-START : {country_name.upper()}")
    print(f"{'='*70}")

    # Charger données
    t_data, y_data = load_country_data(country_name)
    print(f"   Données : {len(t_data)} points, max={y_data.max():.1f} décès/jour")

    sir = SIRMultiStart(population=population, IFR=0.01)

    # Générer 10 initialisations
    initializations = generate_initializations(10)

    print(f"\n   📊 TEST MULTI-START : 10 initialisations différentes")
    print(f"   {'─'*66}")

    results = []

    for i, p0 in enumerate(initializations, 1):
        result = sir.fit_with_init(t_data, y_data, p0)

        if result['success']:
            print(f"      Init {i:2d} : RMS={result['rms']:6.2f} | "
                  f"R0={result['R0']:5.2f} | Durée={result['duration']:5.1f}j")
            results.append(result)
        else:
            print(f"      Init {i:2d} : ❌ Échec ({result['error']})")

    # Analyse des résultats
    if len(results) >= 2:
        df = pd.DataFrame(results)

        print(f"\n   📈 ANALYSE STATISTIQUE ({len(results)}/10 succès)")
        print(f"   {'─'*66}")

        # RMS
        rms_min = df['rms'].min()
        rms_max = df['rms'].max()
        rms_mean = df['rms'].mean()
        rms_std = df['rms'].std()
        rms_cv = (rms_std / rms_mean) * 100  # Coefficient de variation

        print(f"\n   RMS:")
        print(f"      • Minimum  : {rms_min:.2f}")
        print(f"      • Maximum  : {rms_max:.2f}")
        print(f"      • Moyenne  : {rms_mean:.2f}")
        print(f"      • Std Dev  : {rms_std:.2f}")
        print(f"      • CV       : {rms_cv:.1f}%")

        # R0
        R0_min = df['R0'].min()
        R0_max = df['R0'].max()
        R0_mean = df['R0'].mean()
        R0_std = df['R0'].std()
        R0_cv = (R0_std / R0_mean) * 100

        print(f"\n   R0 (Nombre de reproduction):")
        print(f"      • Minimum  : {R0_min:.2f}")
        print(f"      • Maximum  : {R0_max:.2f}")
        print(f"      • Moyenne  : {R0_mean:.2f}")
        print(f"      • Std Dev  : {R0_std:.2f}")
        print(f"      • CV       : {R0_cv:.1f}%")

        # Durée infection
        dur_min = df['duration'].min()
        dur_max = df['duration'].max()
        dur_mean = df['duration'].mean()
        dur_std = df['duration'].std()
        dur_cv = (dur_std / dur_mean) * 100

        print(f"\n   Durée infection (jours):")
        print(f"      • Minimum  : {dur_min:.1f}")
        print(f"      • Maximum  : {dur_max:.1f}")
        print(f"      • Moyenne  : {dur_mean:.1f}")
        print(f"      • Std Dev  : {dur_std:.1f}")
        print(f"      • CV       : {dur_cv:.1f}%")

        # Verdict stabilité
        print(f"\n   📊 VERDICT STABILITÉ:")

        # Critères de stabilité
        stable_rms = rms_cv < 5.0
        stable_R0 = R0_cv < 10.0
        stable_dur = dur_cv < 15.0

        if stable_rms and stable_R0 and stable_dur:
            print(f"      ✅ TRÈS STABLE")
            print(f"         - RMS CV < 5% : {rms_cv:.1f}%")
            print(f"         - R0 CV < 10% : {R0_cv:.1f}%")
            print(f"         - Durée CV < 15% : {dur_cv:.1f}%")
            print(f"         → DOGBOX converge toujours vers le même minimum")
            stability = "TRÈS STABLE"
        elif stable_rms:
            print(f"      ⚠️  STABLE (RMS) mais variance paramètres")
            print(f"         - RMS CV : {rms_cv:.1f}% ✅")
            print(f"         - R0 CV : {R0_cv:.1f}%")
            print(f"         - Durée CV : {dur_cv:.1f}%")
            print(f"         → Même qualité fit mais paramètres variés")
            stability = "STABLE"
        else:
            print(f"      ⚠️  INSTABLE - Multiples minima locaux")
            print(f"         - RMS CV : {rms_cv:.1f}%")
            print(f"         - R0 CV : {R0_cv:.1f}%")
            print(f"         - Durée CV : {dur_cv:.1f}%")
            print(f"         → Attention : Choisir meilleur RMS")
            stability = "INSTABLE"

        # Identifier le meilleur fit
        best_idx = df['rms'].idxmin()
        best = df.loc[best_idx]

        print(f"\n   🏆 MEILLEUR FIT:")
        print(f"      RMS = {best['rms']:.2f}")
        print(f"      R0 = {best['R0']:.2f}")
        print(f"      Durée = {best['duration']:.1f} jours")

        return {
            'country': country_name,
            'n_success': len(results),
            'rms_min': rms_min,
            'rms_cv': rms_cv,
            'R0_mean': R0_mean,
            'R0_cv': R0_cv,
            'duration_mean': dur_mean,
            'duration_cv': dur_cv,
            'stability': stability,
            'best_rms': best['rms'],
            'best_R0': best['R0'],
            'best_duration': best['duration']
        }
    else:
        print(f"\n   ❌ Pas assez de succès pour analyse statistique")
        return None


def main():
    """Point d'entrée principal."""

    print(f"\n{'#'*70}")
    print(f"#  VALIDATION DOGBOX AVEC MULTI-START")
    print(f"#  Objectif : Vérifier robustesse et reproductibilité DOGBOX")
    print(f"{'#'*70}")
    print(f"\n   Méthode : 10 initialisations différentes par pays")
    print(f"   Critère stabilité : CV < 5% (RMS), < 10% (R0), < 15% (Durée)")

    countries = {
        'France': 67.0e6,
        'Italy': 60.0e6,
        'US': 331.0e6,
        'Canada': 38.0e6
    }

    all_results = {}

    for country, pop in countries.items():
        result = validate_country(country, pop)
        if result is not None:
            all_results[country] = result

    # Synthèse globale
    print(f"\n{'='*70}")
    print(f"SYNTHÈSE GLOBALE")
    print(f"{'='*70}\n")

    print("| Pays     | Succès | RMS CV  | R0 CV   | Durée CV | Stabilité      |")
    print("|----------|--------|---------|---------|----------|----------------|")

    for country, res in all_results.items():
        print(f"| {country:<8} | {res['n_success']}/10  | "
              f"{res['rms_cv']:5.1f}% | "
              f"{res['R0_cv']:5.1f}% | "
              f"{res['duration_cv']:6.1f}% | "
              f"{res['stability']:<14} |")

    print(f"\n{'='*70}")
    print(f"CONCLUSION")
    print(f"{'='*70}\n")

    stable_count = sum(1 for r in all_results.values() if r['stability'] in ['TRÈS STABLE', 'STABLE'])

    print(f"Pays TRÈS STABLE ou STABLE : {stable_count}/{len(all_results)}")
    print("")

    if stable_count == len(all_results):
        print("✅ DOGBOX est ROBUSTE et REPRODUCTIBLE pour tous les pays")
        print("   → Convergence systématique vers le même minimum")
        print("   → Résultats fiables quelque soit l'initialisation")
        print("   → Validation complète réussie")
    elif stable_count >= len(all_results) * 0.75:
        print("✅ DOGBOX est ROBUSTE pour la majorité des pays")
        print("   → Convergence stable dans la plupart des cas")
        print("   → Quelques pays nécessitent attention sur initialisation")
    else:
        print("⚠️  DOGBOX montre variabilité sur plusieurs pays")
        print("   → Recommandation : Utiliser meilleur RMS parmi multi-start")
        print("   → Ou considérer optimisation globale pour pays instables")

    print("")


if __name__ == "__main__":
    main()
