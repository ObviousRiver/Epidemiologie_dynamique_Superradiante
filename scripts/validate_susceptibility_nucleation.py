#!/usr/bin/env python3
"""
Validation de la Théorie de Nucléation du Soliton via Susceptibilité

Ce script teste la prédiction théorique Sine-Gordon:
    t_pic(χ) < t_pic(I)

où χ est la susceptibilité dynamique (variance glissante) et I l'intensité
épidémique (nouveaux décès).

Basé sur la théorie:
- Avant nucléation: χ diverge (instabilité modulationnelle)
- Pic de χ: Point de bascule critique (formation du soliton)
- Après: χ chute (structure rigide établie)
- Pic épidémique: Arrive APRÈS (propagation du soliton)

Référence théorique:
    χ(t) ~ 1/|t - t_nucléation|^γ (divergence critique)
    Δt = t_pic(I) - t_pic(χ) > 0 (avance de phase)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.stats import pearsonr
import sys

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel


def load_country_data_direct(country_name):
    """
    Charge les données COVID depuis Johns Hopkins GitHub (sans API Kaggle).

    Args:
        country_name: Nom du pays

    Returns:
        DataFrame avec colonnes 'new_deaths' et index datetime
    """
    # URL Johns Hopkins
    url_deaths = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    # Charger
    df = pd.read_csv(url_deaths)

    # Filtrer pays
    country_data = df[df['Country/Region'] == country_name]

    if len(country_data) == 0:
        raise ValueError(f"Pays '{country_name}' non trouvé")

    # Agréger sur provinces si nécessaire
    cumul_deaths = country_data.iloc[:, 4:].sum(axis=0)

    # Créer DataFrame avec dates
    result = pd.DataFrame({'deaths': cumul_deaths})
    result.index = pd.to_datetime(result.index, format='%m/%d/%y')

    # Calculer nouveaux décès
    result['new_deaths'] = result['deaths'].diff().fillna(0)
    result['new_deaths'] = result['new_deaths'].clip(lower=0)  # Pas de valeurs négatives

    return result


def calculate_susceptibility(signal, window=14):
    """
    Calcule la susceptibilité dynamique χ(t) = variance glissante.

    Théorie: χ ∝ ⟨(δφ)²⟩ (théorème fluctuation-dissipation)

    Args:
        signal: Série temporelle (nouveaux cas/décès)
        window: Largeur de fenêtre glissante (jours)

    Returns:
        chi: Susceptibilité χ(t)
    """
    chi = pd.Series(signal).rolling(window=window, center=True).var()
    return chi.fillna(0).values


def detect_peak_times(t_data, signal, prominence_factor=0.5):
    """
    Détecte le temps du pic principal dans un signal.

    Args:
        t_data: Temps
        signal: Signal
        prominence_factor: Facteur pour seuil de prominence

    Returns:
        t_peak: Temps du pic principal (None si pas trouvé)
        peak_idx: Index du pic
    """
    if len(signal) == 0 or np.all(signal == 0):
        return None, None

    # Détecter les pics
    peaks, properties = find_peaks(
        signal,
        prominence=np.std(signal) * prominence_factor,
        distance=10
    )

    if len(peaks) == 0:
        # Prendre le maximum global si pas de pic détecté
        peak_idx = np.argmax(signal)
        return t_data[peak_idx], peak_idx

    # Prendre le pic le plus fort
    strongest_peak_idx = peaks[np.argmax(properties['prominences'])]
    return t_data[strongest_peak_idx], strongest_peak_idx


def analyze_nucleation_timing(country_name, start_date, end_date, window=14):
    """
    Analyse le timing de nucléation pour une vague donnée.

    Mesure:
        - t_pic(χ): Temps du pic de susceptibilité
        - t_pic(I): Temps du pic épidémique
        - Δt = t_pic(I) - t_pic(χ): Avance de phase

    Prédiction théorique: Δt > 0 (susceptibilité précède épidémie)

    Args:
        country_name: Nom du pays
        start_date: Date début vague
        end_date: Date fin vague
        window: Fenêtre susceptibilité

    Returns:
        results: Dictionnaire avec timing, Δt, et métriques
    """
    # Charger données
    df = load_country_data_direct(country_name)
    df = df.loc[start_date:end_date]

    if len(df) < window * 2:
        print(f"⚠️  Pas assez de données pour {country_name} ({len(df)} points)")
        return None

    t_data = np.arange(len(df))
    deaths = df['new_deaths'].values

    # Calculer susceptibilité χ(t)
    chi = calculate_susceptibility(deaths, window=window)

    # Détecter pics
    t_chi, idx_chi = detect_peak_times(t_data, chi)
    t_deaths, idx_deaths = detect_peak_times(t_data, deaths)

    if t_chi is None or t_deaths is None:
        print(f"⚠️  Impossible de détecter les pics pour {country_name}")
        return None

    # Calculer avance de phase
    delta_t = t_deaths - t_chi

    # Fit SuperRadiant pour contexte
    sr_model = SuperRadiantModel(n_modes=3)
    sr_params, sr_rms = sr_model.fit(t_data, deaths, maxfev=50000)
    sr_modes = sr_model.get_mode_parameters()

    # Trouver le mode principal (plus forte amplitude)
    main_mode = max(sr_modes, key=lambda m: m['A'])
    tau_soliton = main_mode['T']  # Largeur temporelle du soliton

    results = {
        'country': country_name,
        'period': f"{start_date} to {end_date}",
        't_chi': t_chi,
        't_deaths': t_deaths,
        'delta_t': delta_t,
        'delta_t_normalized': delta_t / tau_soliton if tau_soliton > 0 else None,
        'chi_max': chi[idx_chi] if idx_chi is not None else 0,
        'deaths_max': deaths[idx_deaths] if idx_deaths is not None else 0,
        'tau_soliton': tau_soliton,
        'n_points': len(df),
        'prediction_verified': delta_t > 0,
        # Pour analyse
        't_data': t_data,
        'deaths': deaths,
        'chi': chi,
        'idx_chi': idx_chi,
        'idx_deaths': idx_deaths
    }

    return results


def test_power_law_divergence(t_data, chi, t_nucleation, window=10):
    """
    Test si χ(t) ~ 1/|t - t_nucleation|^γ près de la nucléation.

    Args:
        t_data: Temps
        chi: Susceptibilité
        t_nucleation: Temps de nucléation estimé (pic de χ)
        window: Fenêtre autour de t_nucleation

    Returns:
        gamma: Exposant critique (si fit valide)
        r2: Qualité du fit
    """
    # Sélectionner région autour de la nucléation (avant le pic)
    mask = (t_data >= t_nucleation - window) & (t_data < t_nucleation)
    mask &= (chi > 0)  # Éviter log(0)

    if np.sum(mask) < 5:
        return None, None

    t_fit = t_data[mask]
    chi_fit = chi[mask]

    # Fit log-log: log(χ) = -γ log(|t - t_nuc|) + const
    delta_t = np.abs(t_fit - t_nucleation)
    delta_t = np.maximum(delta_t, 0.1)  # Éviter division par 0

    # Régression linéaire en log-log
    from scipy.stats import linregress
    slope, intercept, r_value, _, _ = linregress(np.log(delta_t), np.log(chi_fit))

    gamma = -slope
    r2 = r_value**2

    return gamma, r2


def plot_nucleation_analysis(results, save_path=None):
    """
    Visualise l'analyse de nucléation.

    Panneau 1: Signal et susceptibilité avec pics marqués
    Panneau 2: Zoom sur la région critique
    Panneau 3: Test loi de puissance (log-log)
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    t = results['t_data']
    deaths = results['deaths']
    chi = results['chi']
    t_chi = results['t_chi']
    t_deaths = results['t_deaths']
    delta_t = results['delta_t']

    # Panneau 1: Vue d'ensemble
    ax1 = axes[0]
    ax1_twin = ax1.twinx()

    ax1.plot(t, deaths, 'k-', linewidth=2, label='Décès (I)', alpha=0.7)
    ax1.axvline(t_deaths, color='red', linestyle='--', linewidth=2,
                label=f't_pic(I) = {t_deaths:.1f}')
    ax1.set_ylabel('Nouveaux décès', fontsize=12, color='k')
    ax1.tick_params(axis='y', labelcolor='k')

    ax1_twin.plot(t, chi, 'b-', linewidth=2, label='Susceptibilité (χ)', alpha=0.7)
    ax1_twin.axvline(t_chi, color='blue', linestyle='--', linewidth=2,
                     label=f't_pic(χ) = {t_chi:.1f}')
    ax1_twin.fill_between([t_chi, t_deaths], 0, ax1_twin.get_ylim()[1],
                           color='yellow', alpha=0.2,
                           label=f'Δt = {delta_t:.1f}j')
    ax1_twin.set_ylabel('Susceptibilité χ (variance)', fontsize=12, color='b')
    ax1_twin.tick_params(axis='y', labelcolor='b')

    ax1.set_xlabel('Jours depuis début vague', fontsize=12)
    ax1.set_title(f"{results['country']} - {results['period']}\n"
                  f"Δt = {delta_t:.1f}j, τ_soliton = {results['tau_soliton']:.1f}j, "
                  f"Δt/τ = {results['delta_t_normalized']:.2f}",
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)

    # Panneau 2: Zoom région critique
    ax2 = axes[1]
    window = int(2 * results['tau_soliton'])
    t_min = max(0, int(t_chi - window))
    t_max = min(len(t), int(t_deaths + window))

    ax2_twin = ax2.twinx()
    ax2.plot(t[t_min:t_max], deaths[t_min:t_max], 'k-', linewidth=2, alpha=0.7)
    ax2.axvline(t_deaths, color='red', linestyle='--', linewidth=2)
    ax2.set_ylabel('Décès', color='k')
    ax2.tick_params(axis='y', labelcolor='k')

    ax2_twin.plot(t[t_min:t_max], chi[t_min:t_max], 'b-', linewidth=2, alpha=0.7)
    ax2_twin.axvline(t_chi, color='blue', linestyle='--', linewidth=2)
    ax2_twin.fill_between([t_chi, t_deaths], 0, ax2_twin.get_ylim()[1],
                           color='yellow', alpha=0.2)
    ax2_twin.set_ylabel('χ', color='b')
    ax2_twin.tick_params(axis='y', labelcolor='b')

    ax2.set_xlabel('Jours', fontsize=12)
    ax2.set_title('Zoom sur Région Critique (Nucléation)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Panneau 3: Test loi de puissance
    ax3 = axes[2]
    gamma, r2 = test_power_law_divergence(t, chi, t_chi, window=int(results['tau_soliton']))

    if gamma is not None:
        # Préparation données pour plot
        window = int(results['tau_soliton'])
        mask = (t >= t_chi - window) & (t < t_chi) & (chi > 0)
        t_fit = t[mask]
        chi_fit = chi[mask]
        delta_t_fit = np.abs(t_fit - t_chi)
        delta_t_fit = np.maximum(delta_t_fit, 0.1)

        ax3.loglog(delta_t_fit, chi_fit, 'bo', markersize=8, alpha=0.6,
                   label='Données')

        # Fit théorique
        t_theory = np.linspace(0.1, window, 100)
        chi_theory = (t_theory)**(-gamma) * np.exp(gamma * np.log(delta_t_fit[0]) + np.log(chi_fit[0]))
        ax3.loglog(t_theory, chi_theory, 'r-', linewidth=2,
                   label=f'χ ~ Δt^(-{gamma:.2f}), R²={r2:.3f}')

        ax3.set_xlabel('|t - t_nucléation| (jours)', fontsize=12)
        ax3.set_ylabel('χ (variance)', fontsize=12)
        ax3.set_title(f'Test Loi de Puissance: χ(t) ~ 1/|t - t_nuc|^γ\n'
                      f'γ = {gamma:.2f} (théorie: γ > 0 pour divergence critique)',
                      fontsize=12, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3, which='both')
    else:
        ax3.text(0.5, 0.5, 'Pas assez de données pour test loi de puissance',
                 ha='center', va='center', transform=ax3.transAxes, fontsize=14)
        ax3.set_xlabel('|t - t_nucléation|')
        ax3.set_ylabel('χ')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"✅ Figure sauvegardée: {save_path}")

    return fig


def main():
    """
    Test de validation de la théorie de nucléation sur plusieurs pays/vagues.
    """
    print("="*80)
    print("VALIDATION THÉORIE NUCLÉATION SOLITON - SUSCEPTIBILITÉ PRÉCURSEUR")
    print("="*80)
    print()
    print("Prédiction théorique Sine-Gordon:")
    print("  χ(t) diverge avant nucléation → Pic χ → Formation soliton → Pic épidémique")
    print("  ⟹  t_pic(χ) < t_pic(I)")
    print()

    # Cas tests
    test_cases = [
        {'country': 'France', 'start': '2020-02-15', 'end': '2020-06-30', 'label': 'Vague 1'},
        {'country': 'Italy', 'start': '2020-02-20', 'end': '2020-06-30', 'label': 'Vague 1'},
        {'country': 'United Kingdom', 'start': '2020-03-01', 'end': '2020-07-31', 'label': 'Vague 1'},
        {'country': 'Spain', 'start': '2020-03-01', 'end': '2020-06-30', 'label': 'Vague 1'},
        {'country': 'Sweden', 'start': '2020-03-01', 'end': '2020-08-31', 'label': 'Vague 1'},
    ]

    all_results = []

    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Analyse: {test['country']} - {test['label']}")
        print(f"{'='*60}")

        try:
            results = analyze_nucleation_timing(
                test['country'],
                test['start'],
                test['end'],
                window=14
            )

            if results is None:
                continue

            all_results.append(results)

            # Afficher résultats
            print(f"\n📊 Résultats:")
            print(f"  t_pic(χ) = {results['t_chi']:.1f} jours")
            print(f"  t_pic(I) = {results['t_deaths']:.1f} jours")
            print(f"  Δt = t_pic(I) - t_pic(χ) = {results['delta_t']:.1f} jours")
            print(f"  Δt/τ (normalisé) = {results['delta_t_normalized']:.2f}")
            print(f"  τ_soliton = {results['tau_soliton']:.1f} jours")

            # Verdict
            if results['prediction_verified']:
                print(f"  ✅ PRÉDICTION VÉRIFIÉE: χ précède bien le pic épidémique!")
            else:
                print(f"  ❌ PRÉDICTION NON VÉRIFIÉE: χ arrive APRÈS le pic")

            # Test loi de puissance
            gamma, r2 = test_power_law_divergence(
                results['t_data'],
                results['chi'],
                results['t_chi'],
                window=int(results['tau_soliton'])
            )

            if gamma is not None:
                print(f"\n🔬 Test divergence critique:")
                print(f"  γ = {gamma:.2f} (attendu: γ > 0)")
                print(f"  R² = {r2:.3f}")
                if gamma > 0 and r2 > 0.5:
                    print(f"  ✅ Compatible avec divergence χ ~ 1/|t-t_nuc|^γ")
                else:
                    print(f"  ⚠️  Loi de puissance peu évidente")

            # Générer figure
            save_path = f"results/nucleation_validation/{test['country'].lower().replace(' ', '_')}_{test['label'].lower().replace(' ', '_')}.png"
            import os
            os.makedirs('results/nucleation_validation', exist_ok=True)
            plot_nucleation_analysis(results, save_path=save_path)

        except Exception as e:
            print(f"❌ Erreur pour {test['country']}: {e}")
            import traceback
            traceback.print_exc()

    # Synthèse
    print("\n" + "="*80)
    print("SYNTHÈSE - VALIDATION MULTI-PAYS")
    print("="*80)

    if len(all_results) == 0:
        print("❌ Aucun résultat valide")
        return

    verified = sum(1 for r in all_results if r['prediction_verified'])
    total = len(all_results)

    print(f"\nTaux de vérification: {verified}/{total} ({100*verified/total:.1f}%)")
    print(f"\nStatistiques Δt (avance de phase):")

    delta_ts = [r['delta_t'] for r in all_results]
    print(f"  Moyenne: {np.mean(delta_ts):.1f} ± {np.std(delta_ts):.1f} jours")
    print(f"  Médiane: {np.median(delta_ts):.1f} jours")
    print(f"  Min/Max: {np.min(delta_ts):.1f} / {np.max(delta_ts):.1f} jours")

    # Corrélation Δt vs τ
    delta_ts_normalized = [r['delta_t_normalized'] for r in all_results if r['delta_t_normalized'] is not None]
    if len(delta_ts_normalized) > 0:
        print(f"\nΔt/τ (normalisé):")
        print(f"  Moyenne: {np.mean(delta_ts_normalized):.2f} ± {np.std(delta_ts_normalized):.2f}")
        print(f"  Médiane: {np.median(delta_ts_normalized):.2f}")

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    if verified / total >= 0.8:
        print("✅ La prédiction théorique est FORTEMENT VALIDÉE:")
        print("   Le pic de susceptibilité χ précède systématiquement le pic épidémique,")
        print("   confirmant la théorie de nucléation du soliton Sine-Gordon.")
    elif verified / total >= 0.5:
        print("⚠️  La prédiction est PARTIELLEMENT VALIDÉE:")
        print("   La majorité des cas confirme χ précurseur, mais des exceptions existent.")
    else:
        print("❌ La prédiction n'est PAS validée sur ces données.")

    print()
    print("Fichiers générés: results/nucleation_validation/*.png")


if __name__ == '__main__':
    main()
