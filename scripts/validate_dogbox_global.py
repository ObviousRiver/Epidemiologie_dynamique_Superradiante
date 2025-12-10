#!/usr/bin/env python3
"""
Validation DOGBOX avec Optimisation Globale
============================================

Compare DOGBOX avec differential_evolution (optimisation globale garantie)
sur 4 pays clés pour valider que DOGBOX trouve les bons minima.

Pays testés :
- France : Référence stable
- Italy : Amélioration -72% avec DOGBOX
- USA : Basculement SR→SIR avec DOGBOX (-81%)
- Canada : Amélioration -76% avec DOGBOX
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
from scipy.integrate import odeint


class SIRGlobalOptimization:
    """SIR avec optimisation globale pour validation."""

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

    def fit_global(self, t_data, y_data, maxiter=100, seed=42):
        """
        Optimisation globale avec differential_evolution.

        Args:
            maxiter : Nombre d'itérations (100 = rapide, 1000 = exhaustif)
            seed : Graine aléatoire pour reproductibilité
        """
        bounds = [
            (0.01, 5.0),          # beta
            (0.01, 1.0),          # gamma
            (1, self.N / 100),    # I0
            (0.01, 100.0)         # scale
        ]

        def objective(params):
            try:
                y_fit = self._sir_fit_deaths(t_data, *params)
                return np.sqrt(np.mean((y_data - y_fit)**2))
            except:
                return np.inf

        print(f"      Optimisation globale (maxiter={maxiter}, seed={seed})...")

        result = differential_evolution(
            objective,
            bounds,
            maxiter=maxiter,
            seed=seed,
            workers=1,  # Pas de parallélisation pour éviter problèmes ODE
            atol=0.01,
            tol=0.01
        )

        beta, gamma, I0, scale = result.x
        rms = result.fun

        return result.x, rms, result.success


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


def validate_country(country_name, population, rms_dogbox):
    """Valide DOGBOX avec optimisation globale."""

    print(f"\n{'='*70}")
    print(f"VALIDATION : {country_name.upper()}")
    print(f"{'='*70}")

    # Charger données
    t_data, y_data = load_country_data(country_name)
    print(f"   Données : {len(t_data)} points, max={y_data.max():.1f} décès/jour")
    print(f"   RMS DOGBOX (référence) : {rms_dogbox:.2f}")

    sir = SIRGlobalOptimization(population=population, IFR=0.01)

    results = []

    # Test 1 : differential_evolution rapide (100 iter)
    print(f"\n   📊 TEST 1 : differential_evolution (rapide)")
    params, rms, success = sir.fit_global(t_data, y_data, maxiter=100, seed=42)

    if success:
        beta, gamma, I0, scale = params
        R0 = beta / gamma
        duration = 1 / gamma
        diff_dogbox = rms - rms_dogbox
        pct_diff = (diff_dogbox / rms_dogbox) * 100

        print(f"      RMS = {rms:.2f} (DOGBOX: {rms_dogbox:.2f}, Δ={diff_dogbox:+.2f}, {pct_diff:+.1f}%)")
        print(f"      R0 = {R0:.2f}, Durée = {duration:.1f}j")

        results.append({
            'method': 'DiffEvo_100',
            'rms': rms,
            'diff_dogbox': diff_dogbox,
            'pct_diff': pct_diff,
            'R0': R0,
            'duration': duration
        })
    else:
        print(f"      ❌ Échec")

    # Test 2 : differential_evolution exhaustif (300 iter)
    print(f"\n   📊 TEST 2 : differential_evolution (exhaustif)")
    params, rms, success = sir.fit_global(t_data, y_data, maxiter=300, seed=42)

    if success:
        beta, gamma, I0, scale = params
        R0 = beta / gamma
        duration = 1 / gamma
        diff_dogbox = rms - rms_dogbox
        pct_diff = (diff_dogbox / rms_dogbox) * 100

        print(f"      RMS = {rms:.2f} (DOGBOX: {rms_dogbox:.2f}, Δ={diff_dogbox:+.2f}, {pct_diff:+.1f}%)")
        print(f"      R0 = {R0:.2f}, Durée = {duration:.1f}j")

        results.append({
            'method': 'DiffEvo_300',
            'rms': rms,
            'diff_dogbox': diff_dogbox,
            'pct_diff': pct_diff,
            'R0': R0,
            'duration': duration
        })
    else:
        print(f"      ❌ Échec")

    # Analyse
    if len(results) > 0:
        df = pd.DataFrame(results)

        print(f"\n   📈 ANALYSE")
        print(f"      Meilleur global : RMS = {df['rms'].min():.2f}")
        print(f"      DOGBOX         : RMS = {rms_dogbox:.2f}")

        best_global = df['rms'].min()
        if abs(best_global - rms_dogbox) / rms_dogbox < 0.05:
            print(f"\n      ✅ DOGBOX = OPTIMAL (écart < 5%)")
            print(f"         DOGBOX trouve le vrai minimum global !")
        elif best_global < rms_dogbox:
            diff = rms_dogbox - best_global
            pct = (diff / rms_dogbox) * 100
            print(f"\n      ⚠️  Global trouve mieux que DOGBOX")
            print(f"         Différence : -{diff:.2f} ({pct:.1f}%)")
            print(f"         DOGBOX sous-optimal pour ce pays")
        else:
            diff = best_global - rms_dogbox
            pct = (diff / rms_dogbox) * 100
            print(f"\n      ✅ DOGBOX MEILLEUR que global")
            print(f"         Différence : +{diff:.2f} ({pct:.1f}%)")
            print(f"         DOGBOX trouve meilleur minimum !")

        return df
    else:
        print(f"\n   ❌ Aucun test réussi")
        return None


def main():
    """Point d'entrée principal."""

    print(f"\n{'#'*70}")
    print(f"#  VALIDATION DOGBOX AVEC OPTIMISATION GLOBALE")
    print(f"#  Objectif : Vérifier que DOGBOX trouve les bons minima")
    print(f"{'#'*70}")

    # RMS DOGBOX de référence (résultats précédents)
    countries = {
        'France': {'pop': 67.0e6, 'rms_dogbox': 31.35},
        'Italy': {'pop': 60.0e6, 'rms_dogbox': 20.55},
        'US': {'pop': 331.0e6, 'rms_dogbox': 52.44},
        'Canada': {'pop': 38.0e6, 'rms_dogbox': 6.35}
    }

    all_results = {}

    for country, info in countries.items():
        results = validate_country(country, info['pop'], info['rms_dogbox'])
        if results is not None:
            all_results[country] = results

    # Synthèse globale
    print(f"\n{'='*70}")
    print(f"SYNTHÈSE GLOBALE")
    print(f"{'='*70}\n")

    for country, df in all_results.items():
        best_diff = df['pct_diff'].min()
        if abs(best_diff) < 5:
            status = "✅ OPTIMAL"
        elif best_diff < 0:
            status = f"⚠️ Sous-optimal ({best_diff:.1f}%)"
        else:
            status = f"✅ Meilleur (+{best_diff:.1f}%)"

        print(f"{country:<10} : {status}")

    print(f"\n{'='*70}")
    print(f"CONCLUSION")
    print(f"{'='*70}\n")

    print("Si tous pays ont status '✅ OPTIMAL' :")
    print("→ DOGBOX trouve les vrais minima globaux")
    print("→ Résultats validés, on peut utiliser DOGBOX en confiance")
    print("")
    print("Si certains pays '⚠️ Sous-optimal' :")
    print("→ Considérer differential_evolution pour ces pays")
    print("→ Ou augmenter maxfev de DOGBOX")
    print("")


if __name__ == "__main__":
    main()
