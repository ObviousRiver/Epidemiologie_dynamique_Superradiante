#!/usr/bin/env python3
"""
Validation de la Théorie de Nucléation sur le Modèle SR Lui-Même

NOUVELLE APPROCHE:
Au lieu de calculer χ sur les données bruitées, on calcule:
    1. Fit SR sur données
    2. χ sur signal SR reconstruit (lisse)
    3. Comparer γ(données) vs γ(SR)

HYPOTHÈSE:
Si la théorie est cohérente, la somme de solitons SR doit exhiber
naturellement la divergence χ ~ (t_c - t)^(-γ) avant chaque mode.

AVANTAGES:
- Signal lisse (pas de bruit weekend)
- Test de cohérence interne du modèle
- γ universel attendu (propriété mathématique, pas artefact)

DOUBLE VALIDATION:
- Empirique: χ(données réelles) précède pic
- Théorique: χ(modèle SR) diverge comme prédit
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
from scipy.stats import linregress
import sys

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


def fit_power_law_rising_phase(t_data, chi, method='optimize'):
    """
    Fit χ(t) ~ (t_c - t)^(-γ) dans la phase de montée.

    Args:
        t_data: Temps
        chi: Susceptibilité
        method: 'optimize' ou 'loglog'

    Returns:
        gamma, t_c, r2, fit_info
    """
    # Détecter pic de χ
    peaks, _ = find_peaks(chi, prominence=np.std(chi) * 0.3)
    if len(peaks) == 0:
        return None, None, None, None

    peak_idx = peaks[np.argmax(chi[peaks])]
    chi_max = chi[peak_idx]

    # Phase de montée: 10% χ_max jusqu'au pic
    threshold = 0.1 * chi_max
    rising_start = np.argmax(chi > threshold)

    mask = (t_data >= rising_start) & (t_data < peak_idx) & (chi > 0)

    if np.sum(mask) < 5:
        return None, None, None, None

    t_fit = t_data[mask]
    chi_fit = chi[mask]

    if method == 'optimize':
        # Fit χ = A × (t_c - t)^(-γ)
        def power_law(t, A, gamma, t_c):
            delta = np.maximum(t_c - t, 0.01)
            return A * delta**(-gamma)

        try:
            p0 = [np.max(chi_fit), 1.0, peak_idx + 2]
            bounds = ([0, 0.1, peak_idx], [np.inf, 3.0, peak_idx + 10])

            popt, _ = curve_fit(power_law, t_fit, chi_fit, p0=p0, bounds=bounds, maxfev=10000)
            A, gamma, t_c = popt

            chi_pred = power_law(t_fit, *popt)
            ss_res = np.sum((chi_fit - chi_pred)**2)
            ss_tot = np.sum((chi_fit - np.mean(chi_fit))**2)
            r2 = 1 - ss_res / ss_tot

            fit_info = {
                'A': A, 'gamma': gamma, 't_c': t_c, 'r2': r2,
                't_fit': t_fit, 'chi_fit': chi_fit, 'chi_pred': chi_pred
            }

            return gamma, t_c, r2, fit_info

        except:
            return None, None, None, None

    elif method == 'loglog':
        t_c = peak_idx
        delta_t = t_c - t_fit
        delta_t = np.maximum(delta_t, 0.5)

        valid = delta_t > 0.5
        if np.sum(valid) < 5:
            return None, None, None, None

        log_delta = np.log(delta_t[valid])
        log_chi = np.log(chi_fit[valid])

        slope, intercept, r_value, _, _ = linregress(log_delta, log_chi)
        gamma = -slope
        r2 = r_value**2

        fit_info = {
            'gamma': gamma, 't_c': t_c, 'r2': r2,
            't_fit': t_fit[valid], 'chi_fit': chi_fit[valid]
        }

        return gamma, t_c, r2, fit_info


def analyze_double_validation(country, start_date, end_date, window=14):
    """
    Double validation: χ(données) vs χ(SR)

    Returns:
        results: Dict avec métriques pour données ET modèle SR
    """
    # Charger données
    df = load_country_data_direct(country)
    df = df.loc[start_date:end_date]

    if len(df) < 50:
        return None

    t_data = np.arange(len(df))
    deaths_real = df['new_deaths'].values

    # Fit SR
    print(f"  Fitting SR model...")
    sr_model = SuperRadiantModel(n_modes=3)
    try:
        sr_params, sr_rms = sr_model.fit(t_data, deaths_real, maxfev=50000)
        deaths_sr = sr_model.predict(t_data)
        sr_modes = sr_model.get_mode_parameters()
    except Exception as e:
        print(f"    ❌ SR fit failed: {e}")
        return None

    # Calculer χ sur DONNÉES RÉELLES
    print(f"  Computing χ(real data)...")
    chi_real = calculate_susceptibility(deaths_real, window=window)
    gamma_real, tc_real, r2_real, fit_real = fit_power_law_rising_phase(t_data, chi_real)

    # Calculer χ sur MODÈLE SR
    print(f"  Computing χ(SR model)...")
    chi_sr = calculate_susceptibility(deaths_sr, window=window)
    gamma_sr, tc_sr, r2_sr, fit_sr = fit_power_law_rising_phase(t_data, chi_sr)

    # Détecter pics
    peaks_real, _ = find_peaks(deaths_real, prominence=np.std(deaths_real)*0.3)
    peaks_sr, _ = find_peaks(deaths_sr, prominence=np.std(deaths_sr)*0.3)
    peaks_chi_real, _ = find_peaks(chi_real, prominence=np.std(chi_real)*0.3)
    peaks_chi_sr, _ = find_peaks(chi_sr, prominence=np.std(chi_sr)*0.3)

    if len(peaks_real) == 0 or len(peaks_sr) == 0:
        return None

    t_deaths_real = peaks_real[np.argmax(deaths_real[peaks_real])]
    t_deaths_sr = peaks_sr[np.argmax(deaths_sr[peaks_sr])]
    t_chi_real = peaks_chi_real[np.argmax(chi_real[peaks_chi_real])] if len(peaks_chi_real) > 0 else None
    t_chi_sr = peaks_chi_sr[np.argmax(chi_sr[peaks_chi_sr])] if len(peaks_chi_sr) > 0 else None

    # Avances de phase
    delta_t_real = (t_deaths_real - t_chi_real) if t_chi_real is not None else None
    delta_t_sr = (t_deaths_sr - t_chi_sr) if t_chi_sr is not None else None

    results = {
        'country': country,
        'period': f"{start_date} to {end_date}",
        'n_points': len(df),
        # Données réelles
        'gamma_real': gamma_real,
        'r2_real': r2_real,
        't_chi_real': t_chi_real,
        't_deaths_real': t_deaths_real,
        'delta_t_real': delta_t_real,
        # Modèle SR
        'gamma_sr': gamma_sr,
        'r2_sr': r2_sr,
        't_chi_sr': t_chi_sr,
        't_deaths_sr': t_deaths_sr,
        'delta_t_sr': delta_t_sr,
        # SR modes
        'sr_modes': sr_modes,
        'sr_rms': sr_rms,
        # Pour plots
        't_data': t_data,
        'deaths_real': deaths_real,
        'deaths_sr': deaths_sr,
        'chi_real': chi_real,
        'chi_sr': chi_sr,
        'fit_real': fit_real,
        'fit_sr': fit_sr
    }

    return results


def plot_double_validation(results, save_path=None):
    """
    Visualise la double validation: données vs SR.

    4 panneaux:
    1. Données réelles: Signal + χ + fit γ
    2. Modèle SR: Signal + χ + fit γ
    3. Comparaison γ(real) vs γ(SR)
    4. Comparaison Δt(real) vs Δt(SR)
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    t = results['t_data']

    # Panneau 1: Données réelles
    ax = axes[0, 0]
    ax_chi = ax.twinx()

    ax.plot(t, results['deaths_real'], 'k-', linewidth=2, alpha=0.7, label='Décès réels')
    if results['t_deaths_real'] is not None:
        ax.axvline(results['t_deaths_real'], color='red', linestyle='--', linewidth=2,
                   label=f't_pic(I) = {results["t_deaths_real"]}')

    ax_chi.plot(t, results['chi_real'], 'b-', linewidth=2, alpha=0.7, label='χ(réel)')
    if results['t_chi_real'] is not None:
        ax_chi.axvline(results['t_chi_real'], color='blue', linestyle='--', linewidth=2,
                       label=f't_pic(χ) = {results["t_chi_real"]}')
        if results['delta_t_real'] is not None:
            ax_chi.fill_between([results['t_chi_real'], results['t_deaths_real']],
                                0, ax_chi.get_ylim()[1],
                                color='yellow', alpha=0.2)

    gamma_str = f"γ={results['gamma_real']:.2f} (R²={results['r2_real']:.2f})" if results['gamma_real'] else "γ=N/A"
    delta_str = f"Δt={results['delta_t_real']:.0f}j" if results['delta_t_real'] else "Δt=N/A"

    ax.set_xlabel('Jours', fontsize=12)
    ax.set_ylabel('Décès', fontsize=12, color='k')
    ax_chi.set_ylabel('χ (variance)', fontsize=12, color='b')
    ax.set_title(f"DONNÉES RÉELLES\n{gamma_str}, {delta_str}",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left')
    ax_chi.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Panneau 2: Modèle SR
    ax = axes[0, 1]
    ax_chi = ax.twinx()

    ax.plot(t, results['deaths_sr'], 'purple', linewidth=2, alpha=0.7, label='SR fit')
    if results['t_deaths_sr'] is not None:
        ax.axvline(results['t_deaths_sr'], color='red', linestyle='--', linewidth=2,
                   label=f't_pic(I) = {results["t_deaths_sr"]}')

    ax_chi.plot(t, results['chi_sr'], 'orange', linewidth=2, alpha=0.7, label='χ(SR)')
    if results['t_chi_sr'] is not None:
        ax_chi.axvline(results['t_chi_sr'], color='orange', linestyle='--', linewidth=2,
                       label=f't_pic(χ) = {results["t_chi_sr"]}')
        if results['delta_t_sr'] is not None:
            ax_chi.fill_between([results['t_chi_sr'], results['t_deaths_sr']],
                                0, ax_chi.get_ylim()[1],
                                color='yellow', alpha=0.2)

    gamma_str = f"γ={results['gamma_sr']:.2f} (R²={results['r2_sr']:.2f})" if results['gamma_sr'] else "γ=N/A"
    delta_str = f"Δt={results['delta_t_sr']:.0f}j" if results['delta_t_sr'] else "Δt=N/A"

    ax.set_xlabel('Jours', fontsize=12)
    ax.set_ylabel('Décès (SR)', fontsize=12, color='purple')
    ax_chi.set_ylabel('χ (variance)', fontsize=12, color='orange')
    ax.set_title(f"MODÈLE SR (LISSE)\n{gamma_str}, {delta_str}",
                 fontsize=14, fontweight='bold')
    ax.legend(loc='upper left')
    ax_chi.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    # Panneau 3: Fit loi de puissance (données)
    ax = axes[1, 0]
    if results['fit_real'] is not None and 'chi_pred' in results['fit_real']:
        fit = results['fit_real']
        ax.plot(fit['t_fit'], fit['chi_fit'], 'bo', markersize=6, alpha=0.6, label='Données')
        ax.plot(fit['t_fit'], fit['chi_pred'], 'r-', linewidth=2,
                label=f"χ ~ (t_c - t)^(-{fit['gamma']:.2f})")
        ax.set_xlabel('Temps', fontsize=12)
        ax.set_ylabel('χ', fontsize=12)
        ax.set_title(f'Fit Loi de Puissance (Données Réelles)\nR²={fit["r2"]:.3f}',
                     fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'Fit données réelles: ÉCHEC', ha='center', va='center',
                transform=ax.transAxes, fontsize=14)

    # Panneau 4: Fit loi de puissance (SR)
    ax = axes[1, 1]
    if results['fit_sr'] is not None and 'chi_pred' in results['fit_sr']:
        fit = results['fit_sr']
        ax.plot(fit['t_fit'], fit['chi_fit'], 'o', color='orange', markersize=6, alpha=0.6,
                label='SR χ')
        ax.plot(fit['t_fit'], fit['chi_pred'], 'purple', linewidth=2,
                label=f"χ ~ (t_c - t)^(-{fit['gamma']:.2f})")
        ax.set_xlabel('Temps', fontsize=12)
        ax.set_ylabel('χ', fontsize=12)
        ax.set_title(f'Fit Loi de Puissance (Modèle SR)\nR²={fit["r2"]:.3f}',
                     fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'Fit SR: ÉCHEC', ha='center', va='center',
                transform=ax.transAxes, fontsize=14)

    plt.suptitle(f"{results['country']} - {results['period']}\n"
                 f"Double Validation: Données Réelles vs Modèle SR",
                 fontsize=16, fontweight='bold')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"    ✅ Figure sauvegardée: {save_path}")

    return fig


def main():
    """Test double validation sur quelques pays clés."""
    import os

    print("="*80)
    print("DOUBLE VALIDATION: χ(DONNÉES) vs χ(MODÈLE SR)")
    print("="*80)
    print()
    print("Hypothèse: Si théorie cohérente, χ(SR) doit diverger comme prédit")
    print("Avantage: Signal SR lisse → γ plus robuste")
    print()

    test_cases = [
        {'country': 'France', 'start': '2020-02-15', 'end': '2020-06-30'},
        {'country': 'Italy', 'start': '2020-02-20', 'end': '2020-06-30'},
        {'country': 'United Kingdom', 'start': '2020-03-01', 'end': '2020-07-31'},
        {'country': 'Sweden', 'start': '2020-03-01', 'end': '2020-08-31'},
        {'country': 'Spain', 'start': '2020-03-01', 'end': '2020-06-30'},
    ]

    all_results = []

    os.makedirs('results/nucleation_sr_validation', exist_ok=True)

    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Analyse: {test['country']}")
        print(f"{'='*60}")

        try:
            results = analyze_double_validation(
                test['country'],
                test['start'],
                test['end'],
                window=14
            )

            if results is None:
                print(f"  ❌ Échec analyse")
                continue

            all_results.append(results)

            # Afficher résumé
            print(f"\n📊 Résultats:")
            print(f"  DONNÉES RÉELLES:")
            print(f"    γ = {results['gamma_real']:.2f}" if results['gamma_real'] else "    γ = N/A")
            print(f"    R² = {results['r2_real']:.2f}" if results['r2_real'] else "    R² = N/A")
            print(f"    Δt = {results['delta_t_real']:.0f}j" if results['delta_t_real'] else "    Δt = N/A")

            print(f"  MODÈLE SR:")
            print(f"    γ = {results['gamma_sr']:.2f}" if results['gamma_sr'] else "    γ = N/A")
            print(f"    R² = {results['r2_sr']:.2f}" if results['r2_sr'] else "    R² = N/A")
            print(f"    Δt = {results['delta_t_sr']:.0f}j" if results['delta_t_sr'] else "    Δt = N/A")

            # Cohérence?
            if results['gamma_real'] and results['gamma_sr']:
                diff = abs(results['gamma_sr'] - results['gamma_real'])
                print(f"\n  📐 Cohérence γ(SR) vs γ(real): Δγ = {diff:.2f}")
                if diff < 0.5:
                    print(f"     ✅ EXCELLENTE cohérence (Δγ < 0.5)")
                elif diff < 1.0:
                    print(f"     ✅ BONNE cohérence (Δγ < 1.0)")
                else:
                    print(f"     ⚠️  Cohérence partielle (Δγ > 1.0)")

            # Générer figure
            save_path = f"results/nucleation_sr_validation/{test['country'].lower().replace(' ', '_')}_double_validation.png"
            plot_double_validation(results, save_path=save_path)

        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            import traceback
            traceback.print_exc()

    # Synthèse
    if len(all_results) == 0:
        print("\n❌ Aucun résultat valide")
        return

    print("\n" + "="*80)
    print("SYNTHÈSE GLOBALE")
    print("="*80)

    gammas_real = [r['gamma_real'] for r in all_results if r['gamma_real'] is not None and 0.1 < r['gamma_real'] < 3.0]
    gammas_sr = [r['gamma_sr'] for r in all_results if r['gamma_sr'] is not None and 0.1 < r['gamma_sr'] < 3.0]

    print(f"\n📊 Exposants γ:")
    print(f"  DONNÉES RÉELLES: N={len(gammas_real)}")
    if len(gammas_real) > 0:
        print(f"    γ moyen: {np.mean(gammas_real):.2f} ± {np.std(gammas_real):.2f}")
        print(f"    CV: {np.std(gammas_real)/np.mean(gammas_real)*100:.1f}%")

    print(f"\n  MODÈLE SR: N={len(gammas_sr)}")
    if len(gammas_sr) > 0:
        print(f"    γ moyen: {np.mean(gammas_sr):.2f} ± {np.std(gammas_sr):.2f}")
        print(f"    CV: {np.std(gammas_sr)/np.mean(gammas_sr)*100:.1f}%")

    # Test universalité
    if len(gammas_sr) >= 3:
        cv_sr = np.std(gammas_sr) / np.mean(gammas_sr)
        cv_real = np.std(gammas_real) / np.mean(gammas_real) if len(gammas_real) >= 3 else np.inf

        print(f"\n🔬 Test Universalité:")
        print(f"  χ(SR) plus universel que χ(real)? {cv_sr < cv_real}")
        if cv_sr < 0.2:
            print(f"  ✅ UNIVERSALITÉ CONFIRMÉE sur χ(SR) (CV={cv_sr*100:.1f}%)")
        elif cv_sr < cv_real:
            print(f"  ✅ χ(SR) améliore l'universalité (CV: {cv_sr*100:.1f}% < {cv_real*100:.1f}%)")
        else:
            print(f"  ⚠️  Pas d'amélioration claire")

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)

    if len(gammas_sr) >= 3:
        cv = np.std(gammas_sr) / np.mean(gammas_sr)
        gamma_mean = np.mean(gammas_sr)

        if cv < 0.3:
            print("✅ Le modèle SR exhibe NATURELLEMENT la divergence critique!")
            print(f"   γ(SR) = {gamma_mean:.2f} ± {np.std(gammas_sr):.2f}")
            print("   → Cohérence interne de la théorie VALIDÉE")
            print("   → La somme de solitons diverge comme prédit")
        else:
            print("⚠️  Divergence observée mais dispersion élevée")
            print(f"   γ(SR) = {gamma_mean:.2f} ± {np.std(gammas_sr):.2f}")
    else:
        print("❌ Pas assez de mesures pour conclure")


if __name__ == '__main__':
    main()
