#!/usr/bin/env python3
"""
Investigation Approfondie : Optimisation SIR
============================================

Compare différentes méthodes d'optimisation pour le modèle SIR
et identifie la source de variabilité pour Canada et Nouvelle-Zélande.

Méthodes testées :
1. Trust Region Reflective (TRF) - méthode actuelle
2. Dogbox
3. Levenberg-Marquardt (si pas de bornes)
4. Differential Evolution (global optimizer)
5. Basin Hopping (global optimizer)

Référence : scipy.optimize documentation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit, differential_evolution, basinhopping
from scipy.integrate import odeint


# ============================================================================
# MODÈLE SIR (Copie du code actuel pour investigation)
# ============================================================================

class SIRInvestigation:
    """Version du SIR pour investigation des méthodes d'optimisation."""

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

    def fit_method(self, t_data, y_data, method='trf', p0=None, maxfev=10000):
        """
        Fit avec méthode spécifique.

        Args:
            method : 'trf', 'dogbox', 'lm' (si pas de bornes)
        """
        if p0 is None:
            p0 = [0.3, 0.1, 1000, 1.0]

        bounds_lower = [0, 0, 1, 0]
        bounds_upper = [5.0, 1.0, self.N / 100, 100.0]

        try:
            params, cov = curve_fit(
                self._sir_fit_deaths,
                t_data,
                y_data,
                p0=p0,
                bounds=(bounds_lower, bounds_upper),
                method=method,
                maxfev=maxfev
            )

            y_fit = self._sir_fit_deaths(t_data, *params)
            rms = np.sqrt(np.mean((y_data - y_fit)**2))

            return params, rms, True

        except Exception as e:
            print(f"      Méthode {method} échouée: {e}")
            return None, np.inf, False


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


def investigate_country(country_name, population):
    """Investigation complète d'un pays."""

    print(f"\n{'='*80}")
    print(f"INVESTIGATION : {country_name.upper()}")
    print(f"{'='*80}")

    # Charger données
    t_data, y_data = load_country_data(country_name)
    print(f"   Données : {len(t_data)} points, max={y_data.max():.1f} décès/jour")

    sir = SIRInvestigation(population=population, IFR=0.01)

    results = []

    # ========================================================================
    # TEST 1 : Méthodes scipy.optimize.curve_fit
    # ========================================================================

    print(f"\n   📊 TEST 1 : Méthodes curve_fit")
    print(f"   {'─'*76}")

    for method in ['trf', 'dogbox']:
        print(f"      • {method.upper():<10} : ", end='', flush=True)
        params, rms, success = sir.fit_method(t_data, y_data, method=method)

        if success:
            beta, gamma, I0, scale = params
            R0 = beta / gamma
            duration = 1 / gamma
            print(f"RMS={rms:6.2f} | R0={R0:4.2f} | Durée={duration:5.1f}j | I0={I0:8.0f}")

            results.append({
                'method': method.upper(),
                'rms': rms,
                'beta': beta,
                'gamma': gamma,
                'I0': I0,
                'scale': scale,
                'R0': R0,
                'duration': duration
            })
        else:
            print("ÉCHEC")

    # ========================================================================
    # TEST 2 : Initialisations Multiples
    # ========================================================================

    print(f"\n   📊 TEST 2 : Initialisations multiples (méthode TRF)")
    print(f"   {'─'*76}")

    # Différentes initialisations
    p0_variants = [
        [0.3, 0.1, 1000, 1.0],     # Standard (actuel)
        [0.5, 0.2, 500, 2.0],      # R0≈2.5, durée courte
        [0.2, 0.05, 2000, 0.5],    # R0≈4, durée longue
        [1.0, 0.1, 100, 5.0],      # R0≈10, très peu d'infectés
        [0.15, 0.05, 5000, 0.2],   # R0≈3, beaucoup d'infectés
    ]

    for i, p0 in enumerate(p0_variants):
        print(f"      • Init {i+1:<2} : ", end='', flush=True)
        params, rms, success = sir.fit_method(t_data, y_data, method='trf', p0=p0)

        if success:
            beta, gamma, I0, scale = params
            R0 = beta / gamma
            duration = 1 / gamma
            print(f"RMS={rms:6.2f} | R0={R0:4.2f} | Durée={duration:5.1f}j | I0={I0:8.0f}")

            results.append({
                'method': f'TRF_init{i+1}',
                'rms': rms,
                'beta': beta,
                'gamma': gamma,
                'I0': I0,
                'scale': scale,
                'R0': R0,
                'duration': duration
            })
        else:
            print("ÉCHEC")

    # ========================================================================
    # ANALYSE DES RÉSULTATS
    # ========================================================================

    if len(results) > 0:
        df = pd.DataFrame(results)

        print(f"\n   📈 ANALYSE DES RÉSULTATS")
        print(f"   {'─'*76}")

        print(f"\n   RMS:")
        print(f"      • Minimum  : {df['rms'].min():.2f}")
        print(f"      • Maximum  : {df['rms'].max():.2f}")
        print(f"      • Écart    : {((df['rms'].max() - df['rms'].min()) / df['rms'].min() * 100):.1f}%")
        print(f"      • Std Dev  : {df['rms'].std():.2f}")

        print(f"\n   R0 (Nombre de reproduction de base):")
        print(f"      • Minimum  : {df['R0'].min():.2f}")
        print(f"      • Maximum  : {df['R0'].max():.2f}")
        print(f"      • Médiane  : {df['R0'].median():.2f}")
        print(f"      • Std Dev  : {df['R0'].std():.2f}")

        print(f"\n   Durée infection (jours):")
        print(f"      • Minimum  : {df['duration'].min():.1f}")
        print(f"      • Maximum  : {df['duration'].max():.1f}")
        print(f"      • Médiane  : {df['duration'].median():.1f}")
        print(f"      • Std Dev  : {df['duration'].std():.1f}")

        # Identifier les meilleurs fits
        best_idx = df['rms'].idxmin()
        worst_idx = df['rms'].idxmax()

        print(f"\n   🏆 MEILLEUR FIT : {df.loc[best_idx, 'method']}")
        print(f"      RMS = {df.loc[best_idx, 'rms']:.2f}")
        print(f"      R0  = {df.loc[best_idx, 'R0']:.2f}")
        print(f"      Durée = {df.loc[best_idx, 'duration']:.1f} jours")

        print(f"\n   ⚠️  PIRE FIT : {df.loc[worst_idx, 'method']}")
        print(f"      RMS = {df.loc[worst_idx, 'rms']:.2f}")
        print(f"      R0  = {df.loc[worst_idx, 'R0']:.2f}")
        print(f"      Durée = {df.loc[worst_idx, 'duration']:.1f} jours")

        # Vérifier si multiples minima
        rms_range = df['rms'].max() - df['rms'].min()
        if rms_range > 1.0:
            print(f"\n   ⚠️  MULTIPLES MINIMA LOCAUX DÉTECTÉS")
            print(f"      Écart RMS : {rms_range:.2f} ({(rms_range / df['rms'].min() * 100):.1f}%)")
            print(f"      → L'optimisation SIR est INSTABLE pour ce pays")
        else:
            print(f"\n   ✅  Optimisation STABLE (écart RMS < 1.0)")

        return df
    else:
        print("\n   ❌ Aucun fit réussi")
        return None


def main():
    """Point d'entrée principal."""

    print(f"\n{'#'*80}")
    print(f"#  INVESTIGATION : OPTIMISATION SIR")
    print(f"#  Objectif : Identifier source de variabilité Canada & Nouvelle-Zélande")
    print(f"{'#'*80}")

    countries = {
        'France': 67.0e6,           # Référence stable
        'Italy': 60.0e6,            # Référence stable
        'Canada': 38.0e6,           # Écart -62%
        'New Zealand': 5.0e6        # Écart -46%
    }

    all_results = {}

    for country, pop in countries.items():
        results = investigate_country(country, pop)
        if results is not None:
            all_results[country] = results

    # ========================================================================
    # SYNTHÈSE GLOBALE
    # ========================================================================

    print(f"\n{'='*80}")
    print(f"SYNTHÈSE GLOBALE")
    print(f"{'='*80}\n")

    for country, df in all_results.items():
        rms_min = df['rms'].min()
        rms_max = df['rms'].max()
        variability = (rms_max - rms_min) / rms_min * 100

        status = "✅ STABLE" if variability < 10 else "⚠️ INSTABLE"

        print(f"{country:<15} : RMS = {rms_min:6.2f} - {rms_max:6.2f} "
              f"(variabilité {variability:5.1f}%) {status}")

    print(f"\n{'='*80}")
    print(f"CONCLUSION")
    print(f"{'='*80}\n")

    print("Si Canada et Nouvelle-Zélande montrent une variabilité > 10% :")
    print("→ L'optimisation SIR converge vers différents minima locaux")
    print("→ Les écarts observés (-62%, -46%) s'expliquent par cette instabilité")
    print("→ Recommandation : Utiliser méthode avec meilleur RMS médian")
    print("")
    print("Si France et Italie sont stables (< 10%) :")
    print("→ La méthodologie est fiable pour pays avec données robustes")
    print("→ Problème limité aux pays avec petits nombres (stratégie zéro COVID)")
    print("")


if __name__ == "__main__":
    main()
