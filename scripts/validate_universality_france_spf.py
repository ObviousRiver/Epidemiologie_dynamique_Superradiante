#!/usr/bin/env python3
"""
Validation de l'Universalité γ_soliton sur Données Françaises SPF

OBJECTIF:
Tester l'universalité de γ_soliton ≈ 2.4 à toutes les échelles:
- Départements français (~100)
- Régions françaises (13)
- France nationale

HYPOTHÈSE CLÉE:
Si γ est vraiment universel, on peut l'utiliser pour PRÉDIRE t_c:
    χ(t) = A × (t_c - t)^(-γ_universel)
Avec γ = 2.4 fixe, on fit seulement (A, t_c) → prédiction précoce!

MÉTHODOLOGIE:
1. Charger données SPF (départements/régions)
2. Pour chaque entité:
   a) Fit SR model sur nouveaux décès
   b) Calculer χ(SR) sur signal lisse
   c) Mesurer γ(SR) en phase de montée
3. Vérifier universalité multi-échelle
4. Tester prédiction t_c avec γ fixe
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from scipy.optimize import curve_fit
import sys
import os

sys.path.insert(0, 'src/core')
from models import SuperRadiantModel


def load_spf_departements(dep_code, start_date='2020-03-01', end_date='2020-07-31'):
    """
    Charge données SPF pour un département.

    Args:
        dep_code: Code département ('01', '75', etc.)
        start_date: Date début
        end_date: Date fin

    Returns:
        DataFrame avec colonnes ['date', 'new_deaths']
    """
    # Charger données brutes SPF
    df = pd.read_csv('data/raw/covid-hospit-incid-2023-03-31-18h01.csv',
                     sep=';', parse_dates=['jour'])

    # Filtrer département
    df_dep = df[df['dep'] == dep_code].copy()

    if len(df_dep) == 0:
        return None

    # Extraire incid_dc (nouveaux décès)
    df_dep = df_dep[['jour', 'incid_dc']].copy()
    df_dep.columns = ['date', 'new_deaths']
    df_dep = df_dep.set_index('date')

    # Filtrer période
    df_dep = df_dep.loc[start_date:end_date]

    # Clip négatifs (corrections SPF)
    df_dep['new_deaths'] = df_dep['new_deaths'].clip(lower=0)

    return df_dep


def load_spf_regions(region_name, start_date='2020-03-01', end_date='2020-07-31'):
    """
    Charge données SPF pour une région.

    Args:
        region_name: Nom région ('Île-de-France', etc.)
        start_date: Date début
        end_date: Date fin

    Returns:
        DataFrame avec colonnes ['date', 'incid_rea'] (proxy décès)
    """
    # Charger données régionales SPF (encoding latin-1 pour caractères français)
    df = pd.read_csv('data/raw/covid-hospit-incid-reg-2023-03-31-18h01.csv',
                     sep=';', parse_dates=['jour'], encoding='latin-1')

    # Filtrer région
    df_reg = df[df['nomReg'] == region_name].copy()

    if len(df_reg) == 0:
        return None

    # Extraire incid_rea (entrées réanimation, meilleur proxy que décès pour régions)
    df_reg = df_reg[['jour', 'incid_rea']].copy()
    df_reg.columns = ['date', 'new_rea']
    df_reg = df_reg.set_index('date')

    # Filtrer période
    df_reg = df_reg.loc[start_date:end_date]

    # Clip négatifs
    df_reg['new_rea'] = df_reg['new_rea'].clip(lower=0)

    return df_reg


def calculate_susceptibility(signal, window=14, normalize=True):
    """
    Calcule χ(t) = variance glissante.

    Args:
        signal: Signal temporel
        window: Fenêtre de variance glissante
        normalize: Si True, normalise le signal avant calcul (INVARIANCE D'ÉCHELLE)

    Returns:
        chi: Susceptibilité
    """
    # NORMALISATION (invariance d'échelle des phénomènes critiques)
    if normalize:
        signal_max = np.max(signal)
        if signal_max > 0:
            signal = signal / signal_max  # Normaliser entre 0 et 1
        else:
            return np.zeros_like(signal)

    # Variance glissante
    chi = pd.Series(signal).rolling(window=window, center=True).var()
    return chi.fillna(0).values


def fit_power_law_rising_phase(t_data, chi, gamma_fixed=None):
    """
    Fit χ(t) ~ (t_c - t)^(-γ) dans la phase de montée.

    Args:
        t_data: Temps
        chi: Susceptibilité
        gamma_fixed: Si fourni, impose γ fixe et fit seulement (A, t_c)

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

    if gamma_fixed is not None:
        # Fit avec γ fixe (prédiction)
        def power_law_fixed_gamma(t, A, t_c):
            delta = np.maximum(t_c - t, 0.01)
            return A * delta**(-gamma_fixed)

        try:
            p0 = [np.max(chi_fit), peak_idx + 2]
            bounds = ([0, peak_idx], [np.inf, peak_idx + 10])

            popt, _ = curve_fit(power_law_fixed_gamma, t_fit, chi_fit,
                               p0=p0, bounds=bounds, maxfev=10000)
            A, t_c = popt
            gamma = gamma_fixed  # Imposé

            chi_pred = power_law_fixed_gamma(t_fit, *popt)
            ss_res = np.sum((chi_fit - chi_pred)**2)
            ss_tot = np.sum((chi_fit - np.mean(chi_fit))**2)
            r2 = 1 - ss_res / ss_tot

            fit_info = {
                'A': A, 'gamma': gamma, 't_c': t_c, 'r2': r2,
                't_fit': t_fit, 'chi_fit': chi_fit, 'chi_pred': chi_pred,
                'method': 'fixed_gamma'
            }

            return gamma, t_c, r2, fit_info

        except:
            return None, None, None, None

    else:
        # Fit standard (γ libre)
        def power_law(t, A, gamma, t_c):
            delta = np.maximum(t_c - t, 0.01)
            return A * delta**(-gamma)

        try:
            p0 = [np.max(chi_fit), 1.0, peak_idx + 2]
            bounds = ([0, 0.1, peak_idx], [np.inf, 3.5, peak_idx + 10])

            popt, _ = curve_fit(power_law, t_fit, chi_fit,
                               p0=p0, bounds=bounds, maxfev=10000)
            A, gamma, t_c = popt

            chi_pred = power_law(t_fit, *popt)
            ss_res = np.sum((chi_fit - chi_pred)**2)
            ss_tot = np.sum((chi_fit - np.mean(chi_fit))**2)
            r2 = 1 - ss_res / ss_tot

            fit_info = {
                'A': A, 'gamma': gamma, 't_c': t_c, 'r2': r2,
                't_fit': t_fit, 'chi_fit': chi_fit, 'chi_pred': chi_pred,
                'method': 'free_gamma'
            }

            return gamma, t_c, r2, fit_info

        except:
            return None, None, None, None


def analyze_entity(name, data, entity_type='departement', window=14, gamma_universel=None):
    """
    Analyse une entité (département/région).

    Args:
        name: Nom entité
        data: DataFrame avec signal temporel
        entity_type: 'departement' ou 'region'
        window: Fenêtre susceptibilité
        gamma_universel: Si fourni, teste prédiction avec γ fixe

    Returns:
        results: Dict avec métriques
    """
    if data is None or len(data) < 50:
        return None

    t_data = np.arange(len(data))

    if entity_type == 'departement':
        signal = data['new_deaths'].values
    elif entity_type == 'region':
        signal = data['new_rea'].values
    else:
        return None

    # Filtrer signal trop faible (départements avec trop peu de décès)
    total_signal = np.sum(signal)
    max_signal = np.max(signal)

    if entity_type == 'departement':
        # Départements: minimum 50 décès total ET pic > 3
        if total_signal < 50 or max_signal < 3:
            return None
    elif entity_type == 'region':
        # Régions: minimum 100 entrées réa total
        if total_signal < 100:
            return None

    # Fit SR
    sr_model = SuperRadiantModel(n_modes=3)
    try:
        sr_params, sr_rms = sr_model.fit(t_data, signal, maxfev=50000)
        signal_sr = sr_model.predict(t_data)
        sr_modes = sr_model.get_mode_parameters()
    except:
        return None

    # FENÊTRE ADAPTATIVE basée sur τ_moyen des modes SR
    # Justification: τ définit l'échelle temporelle caractéristique
    # → window doit s'adapter (invariance d'échelle temporelle)
    if len(sr_modes) > 0:
        tau_values = [mode['T'] for mode in sr_modes if mode['T'] > 0]
        if len(tau_values) > 0:
            tau_mean = np.mean(tau_values)
            window_adaptive = max(7, int(2.0 * tau_mean))  # Fenêtre = 2×τ (minimum 7j)
        else:
            window_adaptive = window
    else:
        window_adaptive = window

    # Calculer χ sur SR (avec NORMALISATION + fenêtre adaptative)
    chi_sr = calculate_susceptibility(signal_sr, window=window_adaptive, normalize=True)

    # Mesurer γ (libre)
    gamma_sr, tc_sr, r2_sr, fit_sr = fit_power_law_rising_phase(t_data, chi_sr)

    # Test prédiction avec γ universel
    if gamma_universel is not None:
        gamma_pred, tc_pred, r2_pred, fit_pred = fit_power_law_rising_phase(
            t_data, chi_sr, gamma_fixed=gamma_universel
        )
    else:
        gamma_pred, tc_pred, r2_pred = None, None, None

    # Extraire τ_moyen pour info
    tau_mean_value = tau_mean if len(sr_modes) > 0 and len(tau_values) > 0 else None

    results = {
        'name': name,
        'type': entity_type,
        'n_points': len(data),
        'total_signal': np.sum(signal),
        # Modèle SR
        'gamma_sr': gamma_sr,
        'tc_sr': tc_sr,
        'r2_sr': r2_sr,
        'sr_rms': sr_rms,
        'tau_mean': tau_mean_value,
        'window_used': window_adaptive,
        # Prédiction avec γ fixe
        'gamma_pred': gamma_pred,
        'tc_pred': tc_pred,
        'r2_pred': r2_pred,
        # Comparaison
        'delta_tc': abs(tc_sr - tc_pred) if (tc_sr and tc_pred) else None,
        'delta_r2': abs(r2_sr - r2_pred) if (r2_sr and r2_pred) else None
    }

    return results


def main():
    """Validation universalité γ_soliton sur données françaises SPF."""

    print("="*80)
    print("VALIDATION UNIVERSALITÉ γ_soliton - DONNÉES FRANÇAISES SPF")
    print("="*80)
    print()
    print("Hypothèse: γ ≈ 2.4 universel à toutes les échelles")
    print("Test: Départements + Régions françaises (vague 1)")
    print()
    print("INNOVATIONS MÉTHODOLOGIQUES:")
    print("  1. NORMALISATION des signaux SR: I_norm = I_SR / max(I_SR)")
    print("     → Invariance d'échelle (amplitude)")
    print("  2. FENÊTRE ADAPTATIVE: window = 2 × τ_moyen(modes SR)")
    print("     → Invariance d'échelle (temps)")
    print("  Justification: γ ne doit dépendre NI de l'amplitude NI de l'échelle temporelle")
    print()

    # Constante universelle (issue des 19 pays)
    GAMMA_UNIVERSEL = 2.39

    # Log file
    log_file = '/tmp/universality_france_spf.log'
    log = open(log_file, 'w')

    def log_print(msg):
        print(msg)
        log.write(msg + '\n')
        log.flush()

    all_results = []

    # ===== DÉPARTEMENTS =====
    log_print("\n" + "="*80)
    log_print("PHASE 1: DÉPARTEMENTS FRANÇAIS")
    log_print("="*80)

    # Liste départements métropole + DOM
    departements = [f"{i:02d}" for i in range(1, 96)] + ['971', '972', '973', '974', '976']

    # Exclure départements sans données ou Corse (20)
    exclude = ['20']
    departements = [d for d in departements if d not in exclude]

    log_print(f"\nTest sur {len(departements)} départements...")

    for i, dep in enumerate(departements):
        if (i+1) % 10 == 0:
            log_print(f"  Progression: {i+1}/{len(departements)}...")

        try:
            df_dep = load_spf_departements(dep, '2020-03-01', '2020-07-31')

            results = analyze_entity(
                name=f"Dep-{dep}",
                data=df_dep,
                entity_type='departement',
                window=14,
                gamma_universel=GAMMA_UNIVERSEL
            )

            if results is not None:
                all_results.append(results)

        except Exception as e:
            # Skip silencieusement les départements sans données
            pass

    # ===== RÉGIONS =====
    log_print("\n" + "="*80)
    log_print("PHASE 2: RÉGIONS FRANÇAISES")
    log_print("="*80)

    regions = [
        'Île-de-France', 'Auvergne-Rhône-Alpes', 'Hauts-de-France',
        'Grand Est', 'Provence-Alpes-Côte d\'Azur', 'Occitanie',
        'Nouvelle-Aquitaine', 'Bretagne', 'Normandie', 'Pays de la Loire',
        'Bourgogne-Franche-Comté', 'Centre-Val de Loire', 'Corse'
    ]

    log_print(f"\nTest sur {len(regions)} régions...")

    for reg in regions:
        try:
            df_reg = load_spf_regions(reg, '2020-03-01', '2020-07-31')

            results = analyze_entity(
                name=reg,
                data=df_reg,
                entity_type='region',
                window=14,
                gamma_universel=GAMMA_UNIVERSEL
            )

            if results is not None:
                all_results.append(results)

        except Exception as e:
            log_print(f"  ⚠️ {reg}: {e}")

    # ===== SYNTHÈSE =====
    if len(all_results) == 0:
        log_print("\n❌ Aucun résultat valide")
        log.close()
        return

    log_print("\n" + "="*80)
    log_print("SYNTHÈSE MULTI-ÉCHELLE")
    log_print("="*80)

    # Séparer départements et régions
    results_dep = [r for r in all_results if r['type'] == 'departement']
    results_reg = [r for r in all_results if r['type'] == 'region']

    log_print(f"\n✅ {len(results_dep)} départements validés")
    log_print(f"✅ {len(results_reg)} régions validées")
    log_print(f"✅ {len(all_results)} entités TOTAL")

    # Rapport fenêtres adaptatives
    windows_dep = [r['window_used'] for r in results_dep if r['window_used'] is not None]
    windows_reg = [r['window_used'] for r in results_reg if r['window_used'] is not None]
    tau_dep = [r['tau_mean'] for r in results_dep if r['tau_mean'] is not None]
    tau_reg = [r['tau_mean'] for r in results_reg if r['tau_mean'] is not None]

    log_print("\n📏 FENÊTRES ADAPTATIVES:")
    if len(windows_dep) > 0:
        log_print(f"  Départements: window = {np.mean(windows_dep):.1f} ± {np.std(windows_dep):.1f} jours")
        log_print(f"                τ_moyen = {np.mean(tau_dep):.1f} ± {np.std(tau_dep):.1f} jours")
    if len(windows_reg) > 0:
        log_print(f"  Régions:      window = {np.mean(windows_reg):.1f} ± {np.std(windows_reg):.1f} jours")
        log_print(f"                τ_moyen = {np.mean(tau_reg):.1f} ± {np.std(tau_reg):.1f} jours")

    # Statistiques γ(SR) libre
    gammas_dep = [r['gamma_sr'] for r in results_dep if r['gamma_sr'] and 0.1 < r['gamma_sr'] < 3.5]
    gammas_reg = [r['gamma_sr'] for r in results_reg if r['gamma_sr'] and 0.1 < r['gamma_sr'] < 3.5]
    gammas_all = gammas_dep + gammas_reg

    log_print("\n📊 EXPOSANT CRITIQUE γ(SR) - Mesure Libre:")
    log_print(f"  DÉPARTEMENTS: N={len(gammas_dep)}")
    if len(gammas_dep) > 0:
        log_print(f"    γ moyen: {np.mean(gammas_dep):.2f} ± {np.std(gammas_dep):.2f}")
        log_print(f"    CV: {np.std(gammas_dep)/np.mean(gammas_dep)*100:.1f}%")
        log_print(f"    Range: [{np.min(gammas_dep):.2f}, {np.max(gammas_dep):.2f}]")

    log_print(f"\n  RÉGIONS: N={len(gammas_reg)}")
    if len(gammas_reg) > 0:
        log_print(f"    γ moyen: {np.mean(gammas_reg):.2f} ± {np.std(gammas_reg):.2f}")
        log_print(f"    CV: {np.std(gammas_reg)/np.mean(gammas_reg)*100:.1f}%")
        log_print(f"    Range: [{np.min(gammas_reg):.2f}, {np.max(gammas_reg):.2f}]")

    log_print(f"\n  TOUTES ÉCHELLES: N={len(gammas_all)}")
    if len(gammas_all) > 0:
        log_print(f"    γ moyen: {np.mean(gammas_all):.2f} ± {np.std(gammas_all):.2f}")
        log_print(f"    CV: {np.std(gammas_all)/np.mean(gammas_all)*100:.1f}%")
        log_print(f"    Range: [{np.min(gammas_all):.2f}, {np.max(gammas_all):.2f}]")

    # Test universalité multi-échelle
    cv_all = np.std(gammas_all) / np.mean(gammas_all) if len(gammas_all) > 10 else np.inf

    log_print("\n🔬 TEST UNIVERSALITÉ MULTI-ÉCHELLE:")
    if cv_all < 0.25:
        log_print(f"  ✅ UNIVERSALITÉ CONFIRMÉE (CV={cv_all*100:.1f}% < 25%)")
        log_print(f"  → γ_soliton valide de l'échelle départementale à régionale!")
    elif cv_all < 0.35:
        log_print(f"  ✅ UNIVERSALITÉ PROBABLE (CV={cv_all*100:.1f}% < 35%)")
    else:
        log_print(f"  ⚠️  Dispersion élevée (CV={cv_all*100:.1f}% > 35%)")

    # Comparaison avec 19 pays
    gamma_pays = 2.39
    gamma_france = np.mean(gammas_all)
    log_print(f"\n📐 COHÉRENCE PAYS ↔ FRANCE:")
    log_print(f"  γ(19 pays européens): {gamma_pays:.2f} ± 0.50")
    log_print(f"  γ(France multi-échelle): {gamma_france:.2f} ± {np.std(gammas_all):.2f}")
    log_print(f"  Δγ: {abs(gamma_pays - gamma_france):.2f}")
    if abs(gamma_pays - gamma_france) < 0.3:
        log_print(f"  ✅ EXCELLENTE cohérence internationale!")

    # Prédiction avec γ fixe
    r2_pred_all = [r['r2_pred'] for r in all_results if r['r2_pred'] is not None]
    r2_sr_all = [r['r2_sr'] for r in all_results if r['r2_sr'] is not None]

    log_print("\n🎯 TEST PRÉDICTION avec γ = 2.39 FIXE:")
    log_print(f"  N entités testées: {len(r2_pred_all)}")
    if len(r2_pred_all) > 0:
        log_print(f"  R² moyen (γ fixe): {np.mean(r2_pred_all):.3f}")
        log_print(f"  R² moyen (γ libre): {np.mean(r2_sr_all):.3f}")
        log_print(f"  Δ R²: {abs(np.mean(r2_sr_all) - np.mean(r2_pred_all)):.3f}")

        if abs(np.mean(r2_sr_all) - np.mean(r2_pred_all)) < 0.05:
            log_print(f"  ✅ γ fixe AUSSI BON que γ libre!")
            log_print(f"  → On peut PRÉDIRE t_c avec γ=2.39 universel!")

    # Conclusion
    log_print("\n" + "="*80)
    log_print("CONCLUSION")
    log_print("="*80)

    if cv_all < 0.3 and len(gammas_all) >= 20:
        log_print("✅ UNIVERSALITÉ γ_soliton VALIDÉE À TOUTES LES ÉCHELLES!")
        log_print(f"   γ_France = {np.mean(gammas_all):.2f} ± {np.std(gammas_all):.2f} (CV={cv_all*100:.1f}%)")
        log_print("   → Départements, régions, pays: MÊME classe d'universalité")
        log_print("   → γ ≈ 2.4 est une CONSTANTE FONDAMENTALE des épidémies solitoniques")
        log_print("\n💡 APPLICATION:")
        log_print("   On peut maintenant PRÉDIRE t_c en temps réel:")
        log_print("   1. Mesurer χ(t) pendant la montée")
        log_print("   2. Fitter χ = A × (t_c - t)^(-2.39) avec γ FIXE")
        log_print("   3. Obtenir t_c AVANT le pic!")
    else:
        log_print(f"⚠️  {len(gammas_all)} mesures, CV={cv_all*100:.1f}%")
        log_print("   Besoin de plus de données pour conclure définitivement")

    log_print(f"\n📁 Log: {log_file}")
    log_print(f"📁 Résultats: {len(all_results)} entités analysées")

    # Sauvegarder résultats CSV
    results_df = pd.DataFrame(all_results)
    output_csv = 'results/universality_france_spf.csv'
    results_df.to_csv(output_csv, index=False)
    log_print(f"📁 CSV: {output_csv}")

    log.close()


if __name__ == '__main__':
    main()
