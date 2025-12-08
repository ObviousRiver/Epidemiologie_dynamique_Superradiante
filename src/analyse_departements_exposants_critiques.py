#!/usr/bin/env python3
"""
Analyse Départementale - Extraction des Exposants Critiques
============================================================

Analyse granularité maximale: 96 départements métropolitains
Objectif: Extraire les exposants critiques de la transition de phase SR↔SIR

Théorie des transitions de phase:
- Susceptibilité: χ ∼ |r|^(-γ)
- Paramètre d'ordre: M ∼ |r|^β
- Longueur de corrélation: ξ ∼ |r|^(-ν)

Où r = distance au point critique ≈ (RMS_SIR - RMS_SR) / RMS_SR

Vague 1 (fév-juin 2020): La plus "neutre" (pas de vaccination, confinement uniforme tardif)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import odeint
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
DATA_PATH = "data/covid-hospit-2023-03-31-18h01.csv"

# Départements métropolitains (exclure DOM: 971-976, 2A, 2B)
DEPARTEMENTS_METRO = [f"{i:02d}" for i in range(1, 96)] + ['2A', '2B']
DEPARTEMENTS_METRO.remove('20')  # N'existe pas (scindé en 2A, 2B)

# --- MODÈLES ---

def sech_squared(t, A, tau, T):
    """Mode super-radiant sech²."""
    return A * np.power(1/np.cosh((t - tau) / (2 * T)), 2)

def model_sr(t, A, tau, T):
    """Modèle SR mono-mode (pour départements individuels)."""
    return sech_squared(t, A, tau, T)

def fit_sr_model(t, y):
    """Ajuste le modèle SR."""
    if len(y) == 0 or max(y) == 0:
        return None, None, np.inf, None

    p0 = [max(y), t[np.argmax(y)], 10.0]
    try:
        popt, _ = curve_fit(model_sr, t, y, p0=p0, maxfev=10000,
                           bounds=([0, 0, 1], [2*max(y), len(t), 30]))
        y_fit = model_sr(t, *popt)
        rms = np.sqrt(np.mean((y - y_fit)**2))
        return popt, y_fit, rms, popt  # A, tau, T
    except:
        return None, None, np.inf, None

def model_sir(y, t, N, beta, gamma):
    """Système SIR."""
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return dSdt, dIdt, dRdt

def fit_sir_model(t, y, population=1e6):
    """Ajuste le modèle SIR."""
    if len(y) == 0 or max(y) == 0:
        return None, None, np.inf

    def fit_func(t, beta, gamma, scale, shift):
        I0 = 100
        t_sim = np.arange(len(t) + int(shift) + 10)
        ret = odeint(model_sir, [population-I0, I0, 0], t_sim, args=(population, beta, gamma))
        I = ret[:, 1]
        start_idx = int(shift)
        if start_idx < 0: start_idx = 0
        I_shifted = I[start_idx : start_idx + len(t)]
        if len(I_shifted) < len(t):
            I_shifted = np.pad(I_shifted, (0, len(t)-len(I_shifted)))
        return I_shifted * scale

    try:
        popt, _ = curve_fit(fit_func, t, y, p0=[0.3, 0.1, 0.05, 10],
                           bounds=([0,0,0,0], [5, 1, 1, 100]), maxfev=10000)
        y_fit = fit_func(t, *popt)
        rms = np.sqrt(np.mean((y - y_fit)**2))
        return popt, y_fit, rms
    except:
        return None, None, np.inf

# --- CHARGEMENT DONNÉES ---

def load_department_data(df, dep_code):
    """
    Extrait les données d'un département pour Vague 1.

    Returns:
        t, y, dates ou None si pas de données
    """
    # Filtrer département et sexe=0 (tous)
    mask = (df['dep'] == dep_code) & (df['sexe'] == 0)
    df_dep = df[mask].copy()

    if len(df_dep) == 0:
        return None

    # Grouper par jour et sommer
    df_dep = df_dep.groupby('jour')['dc'].sum().reset_index().sort_values('jour')

    # Nouveaux décès quotidiens
    df_dep['new_dc'] = df_dep['dc'].diff().fillna(0)

    # Lissage 7 jours
    df_dep['smooth_dc'] = df_dep['new_dc'].rolling(window=7, center=True).mean().fillna(0)

    # Filtrer Vague 1
    mask_v1 = (df_dep['jour'] >= '2020-03-18') & (df_dep['jour'] <= '2020-06-30')
    df_v1 = df_dep[mask_v1]

    if len(df_v1) < 10:  # Besoin d'au moins 10 points
        return None

    t = np.arange(len(df_v1))
    y = df_v1['smooth_dc'].values
    dates = df_v1['jour'].values

    # Vérifier qu'il y a un signal significatif
    if max(y) < 1.0:  # Moins de 1 décès/jour en moyenne
        return None

    return t, y, dates

# --- ANALYSE DÉPARTEMENTALE ---

def analyze_all_departments():
    """
    Analyse tous les départements métropolitains.
    Retourne DataFrame avec résultats par département.
    """
    print("="*80)
    print("🇫🇷 ANALYSE DÉPARTEMENTALE - Extraction Exposants Critiques")
    print("="*80)
    print(f"\n📊 Chargement données: {DATA_PATH}")

    # Charger données
    df = pd.read_csv(DATA_PATH, sep=';', low_memory=False)
    df['jour'] = pd.to_datetime(df['jour'])
    print(f"✅ {len(df):,} lignes chargées")

    print(f"\n🔍 Analyse {len(DEPARTEMENTS_METRO)} départements métropolitains...")

    results = []

    for dep in DEPARTEMENTS_METRO:
        data = load_department_data(df, dep)

        if data is None:
            print(f"   ⊗ {dep}: Pas de données suffisantes")
            continue

        t, y, dates = data

        # Fit SR
        sr_params, sr_fit, sr_rms, sr_full = fit_sr_model(t, y)

        # Fit SIR
        sir_params, sir_fit, sir_rms = fit_sir_model(t, y, population=5e5)

        if sr_rms < np.inf and sir_rms < np.inf and sr_rms > 0:
            ratio = sir_rms / sr_rms
            winner = "SR" if ratio > 1.0 else "SIR"

            # Distance au point critique
            r = (sir_rms - sr_rms) / sr_rms  # > 0 si SR gagne, < 0 si SIR gagne

            # Variance glissante (susceptibilité)
            variance = pd.Series(y).rolling(14, center=True).var().fillna(0)
            max_variance = np.max(variance)
            idx_variance_peak = np.argmax(variance)
            idx_epidemic_peak = np.argmax(y)
            delay_variance = idx_epidemic_peak - idx_variance_peak

            # Paramètres SR
            if sr_full is not None:
                A, tau, T = sr_full
            else:
                A, tau, T = 0, 0, 0

            result = {
                'dep': dep,
                'rms_sr': sr_rms,
                'rms_sir': sir_rms,
                'ratio': ratio,
                'winner': winner,
                'r': r,  # Distance au point critique
                'max_variance': max_variance,  # Susceptibilité χ
                'variance_peak_day': idx_variance_peak,
                'epidemic_peak_day': idx_epidemic_peak,
                'delay_variance': delay_variance,
                'A': A,  # Amplitude (paramètre d'ordre)
                'tau': tau,  # Temporalité
                'T': T,  # Largeur temporelle (longueur de corrélation)
                'max_deaths': np.max(y)
            }

            results.append(result)

            status = "✓" if winner == "SR" else "✗"
            print(f"   {status} {dep}: {winner} {ratio:.2f}x, r={r:+.2f}, χ={max_variance:.2f}, Δt={delay_variance:+2d}j")

    df_results = pd.DataFrame(results)
    print(f"\n✅ {len(df_results)} départements analysés avec succès")

    return df_results

# --- ANALYSE DES EXPOSANTS CRITIQUES ---

def calculate_critical_exponents(df_results):
    """
    Calcule les exposants critiques de la transition de phase.

    Théorie:
    - Susceptibilité: χ ∼ |r|^(-γ)  → log(χ) = -γ log(|r|) + const
    - Paramètre d'ordre: A ∼ |r|^β  → log(A) = β log(|r|) + const
    - Longueur corrélation: T ∼ |r|^(-ν) → log(T) = -ν log(|r|) + const
    """
    print("\n" + "="*80)
    print("📊 CALCUL DES EXPOSANTS CRITIQUES")
    print("="*80)

    # Filtrer données valides (r != 0, variance > 0)
    df = df_results[(df_results['r'].abs() > 0.01) &
                    (df_results['max_variance'] > 0) &
                    (df_results['A'] > 0) &
                    (df_results['T'] > 0)].copy()

    print(f"\n📈 {len(df)} départements avec données valides pour régression")

    # Logarithmes
    log_r = np.log(df['r'].abs())
    log_chi = np.log(df['max_variance'])
    log_A = np.log(df['A'])
    log_T = np.log(df['T'])

    # Régressions linéaires
    # 1. Exposant γ (susceptibilité)
    slope_gamma, intercept_gamma, r_gamma, p_gamma, stderr_gamma = linregress(log_r, log_chi)
    gamma = -slope_gamma  # Car χ ∼ |r|^(-γ)

    # 2. Exposant β (paramètre d'ordre)
    slope_beta, intercept_beta, r_beta, p_beta, stderr_beta = linregress(log_r, log_A)
    beta = slope_beta  # A ∼ |r|^β

    # 3. Exposant ν (longueur de corrélation)
    slope_nu, intercept_nu, r_nu, p_nu, stderr_nu = linregress(log_r, log_T)
    nu = -slope_nu  # T ∼ |r|^(-ν)

    print("\n🎯 EXPOSANTS CRITIQUES ESTIMÉS:")
    print(f"   γ (susceptibilité):       {gamma:.3f} ± {stderr_gamma:.3f} (R²={r_gamma**2:.3f}, p={p_gamma:.2e})")
    print(f"   β (paramètre d'ordre):    {beta:.3f} ± {stderr_beta:.3f} (R²={r_beta**2:.3f}, p={p_beta:.2e})")
    print(f"   ν (longueur corrélation): {nu:.3f} ± {stderr_nu:.3f} (R²={r_nu**2:.3f}, p={p_nu:.2e})")

    # Comparaison avec classes d'universalité connues
    print("\n📚 Comparaison avec classes d'universalité théoriques:")
    print(f"   Ising 2D:      γ=1.75, β=0.125, ν=1.0")
    print(f"   Ising 3D:      γ=1.24, β=0.326, ν=0.63")
    print(f"   Percolation:   γ=1.80, β=0.14,  ν=0.88")
    print(f"   Champ moyen:   γ=1.00, β=0.50,  ν=0.50")

    # Relations de scaling
    print("\n🔬 Relations de scaling:")
    alpha = 2 - nu * 3  # Exposant chaleur spécifique (dimension d=3 pour espace+temps?)
    delta = 1 + gamma / beta  # Relation Widom

    print(f"   α (chaleur spécifique): {alpha:.3f}")
    print(f"   δ (isotherme critique): {delta:.3f}")
    print(f"   Relation Rushbrooke: α + 2β + γ = 2 → {alpha + 2*beta + gamma:.3f} (attendu: 2)")
    print(f"   Relation Widom: δ = 1 + γ/β → {delta:.3f}")

    return {
        'gamma': gamma,
        'beta': beta,
        'nu': nu,
        'stderr_gamma': stderr_gamma,
        'stderr_beta': stderr_beta,
        'stderr_nu': stderr_nu,
        'r_gamma': r_gamma,
        'r_beta': r_beta,
        'r_nu': r_nu,
        'p_gamma': p_gamma,
        'p_beta': p_beta,
        'p_nu': p_nu,
        'log_r': log_r,
        'log_chi': log_chi,
        'log_A': log_A,
        'log_T': log_T,
        'slope_gamma': slope_gamma,
        'intercept_gamma': intercept_gamma,
        'slope_beta': slope_beta,
        'intercept_beta': intercept_beta,
        'slope_nu': slope_nu,
        'intercept_nu': intercept_nu
    }

# --- VISUALISATION ---

def plot_critical_exponents(df_results, exponents):
    """Visualise les lois de puissance et exposants critiques."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle('Exposants Critiques de la Transition de Phase SR↔SIR\n' +
                 'Analyse 96 Départements Français - Vague 1 COVID-19',
                 fontsize=14, fontweight='bold')

    # Données filtrées
    df = df_results[(df_results['r'].abs() > 0.01) &
                    (df_results['max_variance'] > 0) &
                    (df_results['A'] > 0) &
                    (df_results['T'] > 0)].copy()

    log_r = np.log(df['r'].abs())
    log_chi = np.log(df['max_variance'])
    log_A = np.log(df['A'])
    log_T = np.log(df['T'])

    # Couleurs par gagnant
    colors = ['blue' if w == 'SR' else 'red' for w in df['winner']]

    # 1. Susceptibilité χ ∼ |r|^(-γ)
    ax1 = axes[0, 0]
    ax1.scatter(log_r, log_chi, c=colors, alpha=0.6, s=50)
    # Ligne de régression
    x_fit = np.linspace(log_r.min(), log_r.max(), 100)
    y_fit = exponents['slope_gamma'] * x_fit + exponents['intercept_gamma']
    ax1.plot(x_fit, y_fit, 'k--', linewidth=2,
            label=f"γ = {exponents['gamma']:.3f} ± {exponents['stderr_gamma']:.3f}\nR² = {exponents['r_gamma']**2:.3f}")
    ax1.set_xlabel('log(|r|) où r = (RMS_SIR - RMS_SR) / RMS_SR', fontsize=10)
    ax1.set_ylabel('log(χ) où χ = variance glissante max', fontsize=10)
    ax1.set_title('A. Susceptibilité: χ ∼ |r|^(-γ)', fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 2. Paramètre d'ordre A ∼ |r|^β
    ax2 = axes[0, 1]
    ax2.scatter(log_r, log_A, c=colors, alpha=0.6, s=50)
    y_fit = exponents['slope_beta'] * x_fit + exponents['intercept_beta']
    ax2.plot(x_fit, y_fit, 'k--', linewidth=2,
            label=f"β = {exponents['beta']:.3f} ± {exponents['stderr_beta']:.3f}\nR² = {exponents['r_beta']**2:.3f}")
    ax2.set_xlabel('log(|r|)', fontsize=10)
    ax2.set_ylabel('log(A) où A = amplitude mode SR', fontsize=10)
    ax2.set_title('B. Paramètre d\'ordre: A ∼ |r|^β', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    # 3. Longueur de corrélation T ∼ |r|^(-ν)
    ax3 = axes[1, 0]
    ax3.scatter(log_r, log_T, c=colors, alpha=0.6, s=50)
    y_fit = exponents['slope_nu'] * x_fit + exponents['intercept_nu']
    ax3.plot(x_fit, y_fit, 'k--', linewidth=2,
            label=f"ν = {exponents['nu']:.3f} ± {exponents['stderr_nu']:.3f}\nR² = {exponents['r_nu']**2:.3f}")
    ax3.set_xlabel('log(|r|)', fontsize=10)
    ax3.set_ylabel('log(T) où T = largeur temporelle mode SR', fontsize=10)
    ax3.set_title('C. Longueur de corrélation: T ∼ |r|^(-ν)', fontsize=11, fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)

    # 4. Distribution des ratios SR/SIR
    ax4 = axes[1, 1]
    ratios_sr = df_results[df_results['winner'] == 'SR']['ratio']
    ratios_sir = df_results[df_results['winner'] == 'SIR']['ratio']

    ax4.hist(ratios_sr, bins=30, alpha=0.6, color='blue', label=f'SR gagne ({len(ratios_sr)} dép.)')
    ax4.hist(ratios_sir, bins=30, alpha=0.6, color='red', label=f'SIR gagne ({len(ratios_sir)} dép.)')
    ax4.axvline(1.0, color='black', linestyle='--', linewidth=2, label='Point critique (ratio=1.0)')
    ax4.set_xlabel('Ratio RMS_SIR / RMS_SR', fontsize=10)
    ax4.set_ylabel('Nombre de départements', fontsize=10)
    ax4.set_title('D. Distribution des Régimes par Département', fontsize=11, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('/home/user/Epid-miologie/reports/exposants_critiques_departements.png',
                dpi=300, bbox_inches='tight')
    print(f"\n💾 Graphique sauvegardé: reports/exposants_critiques_departements.png")

# --- MAIN ---

def main():
    # 1. Analyser tous les départements
    df_results = analyze_all_departments()

    # Sauvegarder résultats
    df_results.to_csv('/home/user/Epid-miologie/data/resultats_departements_wave1.csv', index=False)
    print(f"\n💾 Résultats sauvegardés: data/resultats_departements_wave1.csv")

    # 2. Calculer exposants critiques
    exponents = calculate_critical_exponents(df_results)

    # 3. Visualiser
    plot_critical_exponents(df_results, exponents)

    # 4. Statistiques descriptives
    print("\n" + "="*80)
    print("📊 STATISTIQUES DESCRIPTIVES")
    print("="*80)

    n_sr = len(df_results[df_results['winner'] == 'SR'])
    n_sir = len(df_results[df_results['winner'] == 'SIR'])

    print(f"\n🏆 Régimes dominants:")
    print(f"   SR gagne: {n_sr} départements ({100*n_sr/len(df_results):.1f}%)")
    print(f"   SIR gagne: {n_sir} départements ({100*n_sir/len(df_results):.1f}%)")

    print(f"\n📈 Ratios RMS_SIR / RMS_SR:")
    print(f"   Médiane: {df_results['ratio'].median():.2f}")
    print(f"   Moyenne: {df_results['ratio'].mean():.2f}")
    print(f"   Min: {df_results['ratio'].min():.2f} (département {df_results.loc[df_results['ratio'].idxmin(), 'dep']})")
    print(f"   Max: {df_results['ratio'].max():.2f} (département {df_results.loc[df_results['ratio'].idxmax(), 'dep']})")

    print(f"\n⏱️  Délai variance → pic épidémique:")
    delays = df_results['delay_variance']
    print(f"   Médiane: {delays.median():.0f} jours")
    print(f"   Moyenne: {delays.mean():.1f} ± {delays.std():.1f} jours")
    print(f"   Min: {delays.min():.0f} jours")
    print(f"   Max: {delays.max():.0f} jours")

    print("\n" + "="*80)

if __name__ == "__main__":
    main()
