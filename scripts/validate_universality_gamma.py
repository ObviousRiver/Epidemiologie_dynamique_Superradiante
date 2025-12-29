#!/usr/bin/env python3
"""
Validation Étendue: Universalité de l'Exposant Critique γ

Test sur:
- 19 pays (vague 1)
- Régions françaises
- Départements français

Focus: Mesurer γ dans la PHASE DE MONTÉE (pré-nucléation)
pour détecter l'universalité de la classe critique.

Théorie Landau-Ginzburg:
    χ(t) ~ (t_c - t)^(-γ)    pour t < t_c (montée)

Classes d'universalité attendues:
    γ ≈ 1.0  → Champ moyen
    γ ≈ 1.75 → Ising 2D
    γ ≈ 1.24 → XY model

Si γ constant → Preuve d'universalité
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.stats import linregress
from scipy.optimize import curve_fit
import sys
import os

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel


def load_country_data_direct(country_name):
    """Charge données COVID depuis Johns Hopkins GitHub."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
    df = pd.read_csv(url)
    country_data = df[df['Country/Region'] == country_name]

    if len(country_data) == 0:
        raise ValueError(f"Pays '{country_name}' non trouvé")

    cumul_deaths = country_data.iloc[:, 4:].sum(axis=0)
    result = pd.DataFrame({'deaths': cumul_deaths})
    result.index = pd.to_datetime(result.index, format='%m/%d/%y')
    result['new_deaths'] = result['deaths'].diff().fillna(0).clip(lower=0)

    return result


def calculate_susceptibility(signal, window=14):
    """Calcule χ(t) = variance glissante."""
    chi = pd.Series(signal).rolling(window=window, center=True).var()
    return chi.fillna(0).values


def detect_rising_phase(t_data, chi, t_peak, min_chi_fraction=0.1):
    """
    Détecte automatiquement la phase de montée de χ.

    Commence quand χ dépasse min_chi_fraction × χ_max
    et s'arrête au pic.

    Returns:
        t_start, t_end: Début et fin de la phase de montée
        mask: Masque booléen pour la phase de montée
    """
    chi_max = chi[t_peak] if 0 <= t_peak < len(chi) else np.max(chi)
    threshold = min_chi_fraction * chi_max

    # Trouver où χ dépasse le seuil
    above_threshold = chi > threshold

    if not np.any(above_threshold):
        return None, None, None

    # Première fois au-dessus du seuil
    t_start = np.argmax(above_threshold)

    # Jusqu'au pic
    t_end = t_peak

    # Créer masque
    mask = (t_data >= t_start) & (t_data < t_end) & (chi > 0)

    return t_start, t_end, mask


def fit_power_law_rising_phase(t_data, chi, t_peak, method='optimize'):
    """
    Fit χ(t) ~ (t_c - t)^(-γ) dans la phase de MONTÉE.

    Args:
        t_data: Temps
        chi: Susceptibilité
        t_peak: Index du pic de χ (estimation de t_c)
        method: 'optimize' (curve_fit) ou 'loglog' (régression linéaire)

    Returns:
        gamma: Exposant critique
        t_c: Temps critique optimisé
        r2: Qualité du fit
        fit_info: Dict avec détails
    """
    # Détecter phase de montée
    t_start, t_end, mask = detect_rising_phase(t_data, chi, t_peak)

    if mask is None or np.sum(mask) < 5:
        return None, None, None, None

    t_fit = t_data[mask]
    chi_fit = chi[mask]

    if method == 'optimize':
        # Fit non-linéaire: χ = A × (t_c - t)^(-γ)
        def power_law(t, A, gamma, t_c):
            delta = np.maximum(t_c - t, 0.01)  # Éviter division par 0
            return A * delta**(-gamma)

        try:
            # Initialisation: t_c proche du pic, γ ≈ 1
            p0 = [np.max(chi_fit), 1.0, t_peak + 2]
            bounds = ([0, 0.1, t_peak], [np.inf, 3.0, t_peak + 10])

            popt, pcov = curve_fit(power_law, t_fit, chi_fit, p0=p0, bounds=bounds, maxfev=10000)
            A, gamma, t_c = popt

            # Calculer R²
            chi_pred = power_law(t_fit, *popt)
            ss_res = np.sum((chi_fit - chi_pred)**2)
            ss_tot = np.sum((chi_fit - np.mean(chi_fit))**2)
            r2 = 1 - ss_res / ss_tot

            fit_info = {
                'A': A,
                'gamma': gamma,
                't_c': t_c,
                'r2': r2,
                't_fit': t_fit,
                'chi_fit': chi_fit,
                'chi_pred': chi_pred,
                'method': 'curve_fit'
            }

            return gamma, t_c, r2, fit_info

        except Exception as e:
            print(f"  ⚠️  Curve fit failed: {e}")
            return None, None, None, None

    elif method == 'loglog':
        # Régression log-log avec t_c fixé au pic
        t_c = t_peak
        delta_t = t_c - t_fit
        delta_t = np.maximum(delta_t, 0.1)

        # Exclure points trop proches (log instable)
        valid = delta_t > 0.5
        if np.sum(valid) < 5:
            return None, None, None, None

        log_delta = np.log(delta_t[valid])
        log_chi = np.log(chi_fit[valid])

        slope, intercept, r_value, _, _ = linregress(log_delta, log_chi)
        gamma = -slope  # χ ~ Δt^(-γ) → log(χ) = -γ log(Δt) + const
        r2 = r_value**2

        fit_info = {
            'gamma': gamma,
            't_c': t_c,
            'r2': r2,
            't_fit': t_fit[valid],
            'chi_fit': chi_fit[valid],
            'log_delta': log_delta,
            'log_chi': log_chi,
            'method': 'loglog'
        }

        return gamma, t_c, r2, fit_info


def analyze_case(name, t_data, deaths, label="", window=14):
    """
    Analyse un cas (pays, région, département).

    Returns:
        Dict avec résultats incluant γ, Δt, etc.
    """
    if len(deaths) < window * 3:
        return None

    # Calculer χ
    chi = calculate_susceptibility(deaths, window=window)

    # Détecter pics
    peaks_chi, _ = find_peaks(chi, prominence=np.std(chi) * 0.3)
    peaks_deaths, _ = find_peaks(deaths, prominence=np.std(deaths) * 0.3)

    if len(peaks_chi) == 0 or len(peaks_deaths) == 0:
        return None

    # Pic principal = plus fort
    idx_chi = peaks_chi[np.argmax(chi[peaks_chi])]
    idx_deaths = peaks_deaths[np.argmax(deaths[peaks_deaths])]

    t_chi = t_data[idx_chi]
    t_deaths = t_data[idx_deaths]
    delta_t = t_deaths - t_chi

    # Fit loi de puissance dans phase de montée
    gamma_opt, t_c_opt, r2_opt, fit_opt = fit_power_law_rising_phase(
        t_data, chi, idx_chi, method='optimize'
    )

    gamma_log, t_c_log, r2_log, fit_log = fit_power_law_rising_phase(
        t_data, chi, idx_chi, method='loglog'
    )

    # Prendre le meilleur fit
    if gamma_opt is not None and gamma_log is not None:
        if r2_opt > r2_log:
            gamma, t_c, r2, fit_info = gamma_opt, t_c_opt, r2_opt, fit_opt
        else:
            gamma, t_c, r2, fit_info = gamma_log, t_c_log, r2_log, fit_log
    elif gamma_opt is not None:
        gamma, t_c, r2, fit_info = gamma_opt, t_c_opt, r2_opt, fit_opt
    elif gamma_log is not None:
        gamma, t_c, r2, fit_info = gamma_log, t_c_log, r2_log, fit_log
    else:
        gamma, t_c, r2, fit_info = None, None, None, None

    # Fit SR pour contexte
    try:
        sr_model = SuperRadiantModel(n_modes=3)
        sr_params, sr_rms = sr_model.fit(t_data, deaths, maxfev=30000)
        sr_modes = sr_model.get_mode_parameters()
        main_mode = max(sr_modes, key=lambda m: m['A'])
        tau = main_mode['T']
    except:
        tau = None

    results = {
        'name': name,
        'label': label,
        't_chi': t_chi,
        't_deaths': t_deaths,
        'delta_t': delta_t,
        'delta_t_normalized': delta_t / tau if tau else None,
        'gamma': gamma,
        't_c': t_c,
        'r2_gamma': r2,
        'tau': tau,
        'chi_max': chi[idx_chi],
        'deaths_max': deaths[idx_deaths],
        'n_points': len(deaths),
        'prediction_verified': delta_t > 0,
        'fit_info': fit_info,
        # Pour analyse
        't_data': t_data,
        'deaths': deaths,
        'chi': chi,
        'idx_chi': idx_chi,
        'idx_deaths': idx_deaths
    }

    return results


def test_19_countries():
    """Test sur les 19 pays européens."""
    countries = [
        'France', 'Italy', 'Spain', 'United Kingdom', 'Germany',
        'Belgium', 'Netherlands', 'Switzerland', 'Portugal', 'Austria',
        'Sweden', 'Norway', 'Denmark', 'Finland', 'Ireland',
        'Greece', 'Poland', 'Romania', 'Czechia'
    ]

    results = []

    print("="*80)
    print("TEST SUR 19 PAYS EUROPÉENS - Vague 1")
    print("="*80)
    print()

    for country in countries:
        print(f"⏳ {country}...", end=" ")

        try:
            df = load_country_data_direct(country)

            # Vague 1: Mars-Juin 2020
            df_wave = df.loc['2020-03-01':'2020-07-31']

            if len(df_wave) < 50:
                print(f"Pas assez de données ({len(df_wave)} points)")
                continue

            t_data = np.arange(len(df_wave))
            deaths = df_wave['new_deaths'].values

            result = analyze_case(country, t_data, deaths, label="Wave 1")

            if result is None:
                print("❌ Échec détection")
                continue

            results.append(result)

            # Afficher résumé
            status = "✅" if result['prediction_verified'] else "❌"
            gamma_str = f"γ={result['gamma']:.2f} (R²={result['r2_gamma']:.2f})" if result['gamma'] else "γ=N/A"
            print(f"{status} Δt={result['delta_t']:.0f}j, {gamma_str}")

        except Exception as e:
            print(f"❌ Erreur: {e}")

    return results


def test_french_regions():
    """Test sur régions françaises (données SPF si disponibles)."""
    # Pour l'instant, retourner vide - à implémenter avec données régionales
    print("\n⚠️  Test régions françaises: données régionales à charger")
    return []


def main():
    """Validation étendue avec analyse d'universalité."""
    print("="*80)
    print("VALIDATION UNIVERSALITÉ EXPOSANT CRITIQUE γ")
    print("="*80)
    print()
    print("Hypothèse: γ constant à travers pays/régions (universalité)")
    print("Classes attendues: γ≈1.0 (champ moyen), γ≈1.75 (Ising 2D)")
    print()

    # Test 19 pays
    results_countries = test_19_countries()

    # Test régions françaises (TODO)
    results_regions = test_french_regions()

    # Combiner
    all_results = results_countries + results_regions

    if len(all_results) == 0:
        print("\n❌ Aucun résultat valide")
        return

    # Analyse statistique
    print("\n" + "="*80)
    print("ANALYSE STATISTIQUE GLOBALE")
    print("="*80)

    # Δt statistics
    verified = sum(1 for r in all_results if r['prediction_verified'])
    total = len(all_results)
    delta_ts = [r['delta_t'] for r in all_results]

    print(f"\n📊 Validation t_pic(χ) < t_pic(I):")
    print(f"  Taux de succès: {verified}/{total} ({100*verified/total:.1f}%)")
    print(f"  Δt moyen: {np.mean(delta_ts):.1f} ± {np.std(delta_ts):.1f} jours")
    print(f"  Δt médian: {np.median(delta_ts):.1f} jours")

    # γ statistics
    gammas = [r['gamma'] for r in all_results if r['gamma'] is not None and 0.1 < r['gamma'] < 3.0]
    r2s = [r['r2_gamma'] for r in all_results if r['r2_gamma'] is not None]

    print(f"\n🔬 Exposant Critique γ:")
    print(f"  Nombre de mesures valides: {len(gammas)}/{total}")

    if len(gammas) > 0:
        print(f"  γ moyen: {np.mean(gammas):.2f} ± {np.std(gammas):.2f}")
        print(f"  γ médian: {np.median(gammas):.2f}")
        print(f"  γ min/max: {np.min(gammas):.2f} / {np.max(gammas):.2f}")
        print(f"  Écart-type relatif: {np.std(gammas)/np.mean(gammas)*100:.1f}%")
        print(f"  R² moyen: {np.mean(r2s):.3f}")

        # Test universalité: CV < 20% ?
        cv = np.std(gammas) / np.mean(gammas)
        if cv < 0.2:
            print(f"\n  ✅ UNIVERSALITÉ CONFIRMÉE (CV={cv*100:.1f}% < 20%)")
            print(f"     γ ≈ {np.mean(gammas):.2f} est universel!")
        else:
            print(f"\n  ⚠️  Universalité partielle (CV={cv*100:.1f}% > 20%)")

        # Identification classe
        gamma_mean = np.mean(gammas)
        if 0.8 < gamma_mean < 1.2:
            print(f"  🎯 Classe d'universalité: CHAMP MOYEN (γ≈1.0)")
        elif 1.5 < gamma_mean < 2.0:
            print(f"  🎯 Classe d'universalité: ISING 2D (γ≈1.75)")
        elif 1.0 < gamma_mean < 1.5:
            print(f"  🎯 Classe d'universalité: XY MODEL? (γ≈1.24)")
        else:
            print(f"  ❓ Classe d'universalité: NON IDENTIFIÉE")

    # Sauvegarder résultats
    os.makedirs('results/universality_analysis', exist_ok=True)

    # CSV
    df_results = pd.DataFrame([{
        'name': r['name'],
        'label': r['label'],
        't_chi': r['t_chi'],
        't_deaths': r['t_deaths'],
        'delta_t': r['delta_t'],
        'gamma': r['gamma'],
        'r2_gamma': r['r2_gamma'],
        't_c': r['t_c'],
        'tau': r['tau'],
        'verified': r['prediction_verified']
    } for r in all_results])

    df_results.to_csv('results/universality_analysis/results_19_countries.csv', index=False)
    print(f"\n✅ Résultats sauvegardés: results/universality_analysis/results_19_countries.csv")

    # Histogramme γ
    if len(gammas) > 0:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Histogramme
        ax1.hist(gammas, bins=15, edgecolor='black', alpha=0.7)
        ax1.axvline(np.mean(gammas), color='red', linestyle='--', linewidth=2,
                    label=f'Moyenne: γ={np.mean(gammas):.2f}')
        ax1.axvline(1.0, color='blue', linestyle=':', linewidth=2, label='Champ moyen (γ=1.0)')
        ax1.axvline(1.75, color='green', linestyle=':', linewidth=2, label='Ising 2D (γ=1.75)')
        ax1.set_xlabel('Exposant critique γ', fontsize=12)
        ax1.set_ylabel('Fréquence', fontsize=12)
        ax1.set_title(f'Distribution de γ (N={len(gammas)})', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # γ vs Δt
        gammas_plot = [r['gamma'] for r in all_results if r['gamma'] is not None]
        deltas_plot = [r['delta_t'] for r in all_results if r['gamma'] is not None]

        ax2.scatter(deltas_plot, gammas_plot, s=100, alpha=0.6, edgecolors='black')
        ax2.axhline(np.mean(gammas), color='red', linestyle='--', linewidth=2, alpha=0.5)
        ax2.set_xlabel('Avance de phase Δt (jours)', fontsize=12)
        ax2.set_ylabel('Exposant γ', fontsize=12)
        ax2.set_title('γ vs Δt (indépendance?)', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('results/universality_analysis/gamma_distribution.png', dpi=150)
        print(f"✅ Figure sauvegardée: results/universality_analysis/gamma_distribution.png")

    # Conclusion
    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)

    if len(gammas) >= 10 and cv < 0.3:
        print("✅ UNIVERSALITÉ DE γ CONFIRMÉE")
        print(f"   Exposant critique: γ = {np.mean(gammas):.2f} ± {np.std(gammas):.2f}")
        print("   → Preuve d'une classe d'universalité commune")
        print("   → Indépendant de la géographie, population, politique")
    elif len(gammas) >= 5:
        print("⚠️  UNIVERSALITÉ PARTIELLE")
        print(f"   γ variable: {np.mean(gammas):.2f} ± {np.std(gammas):.2f}")
        print("   → Possible effet de taille finie ou hétérogénéités")
    else:
        print("❌ DONNÉES INSUFFISANTES pour conclure sur l'universalité")
        print(f"   Seulement {len(gammas)} mesures de γ valides")


if __name__ == '__main__':
    main()
