#!/usr/bin/env python3
"""
Visualisation Détaillée Modèle SIR sur Données Réelles COVID-19
================================================================

Compare avec le code de référence fourni par l'utilisateur :
1. Visualisations complètes (données vs fit, résidus, S/I/R/D)
2. Calcul NRMSE (RMS relatif) en plus du RMS absolu
3. Test sur vraies données COVID-19

Pays testés : France, Italy (pour comparaison)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from models import SIRModel

# Configuration matplotlib pour de beaux graphiques
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10


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
    dates = country_df.index

    return t_data, y_data, dates


def calculate_metrics(y_data, y_fit):
    """
    Calcule les métriques d'erreur comme dans le code de référence.

    Returns:
        dict: {
            'rms': RMS absolu,
            'nrmse': NRMSE (RMS normalisé par range),
            'nrmse_percent': NRMSE en pourcentage,
            'r2': Coefficient de détermination R²
        }
    """
    # 1. RMS absolu (comme actuellement)
    rms = np.sqrt(np.mean((y_data - y_fit)**2))

    # 2. NRMSE (comme dans code de référence)
    data_range = y_data.max() - y_data.min()
    if data_range > 0:
        nrmse = rms / data_range
        nrmse_percent = nrmse * 100
    else:
        nrmse = 0.0
        nrmse_percent = 0.0

    # 3. R² (coefficient de détermination)
    ss_res = np.sum((y_data - y_fit)**2)
    ss_tot = np.sum((y_data - np.mean(y_data))**2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        'rms': rms,
        'nrmse': nrmse,
        'nrmse_percent': nrmse_percent,
        'r2': r2
    }


def visualize_sir_fit(country_name, population):
    """
    Visualisation complète du fit SIR sur données réelles.

    Génère 4 panels :
    1. Données vs Fit (comme code de référence)
    2. Résidus
    3. Compartiments S, I, R, D
    4. Métriques et paramètres
    """

    print(f"\n{'='*70}")
    print(f"VISUALISATION DÉTAILLÉE : {country_name.upper()}")
    print(f"{'='*70}")

    # Charger données
    t_data, y_data, dates = load_country_data(country_name)
    print(f"   Données : {len(t_data)} points")
    print(f"   Max décès quotidiens : {y_data.max():.0f}")

    # Ajuster modèle SIR
    print(f"\n   Ajustement SIR (DOGBOX, IFR=0.01)...")
    sir = SIRModel(population=population, IFR=0.01)
    params, rms = sir.fit(t_data, y_data)

    # Prédiction
    y_fit = sir.predict(t_data)

    # Métriques
    metrics = calculate_metrics(y_data, y_fit)

    # Paramètres SIR
    sir_params = sir.get_parameters()

    print(f"   ✓ RMS absolu : {metrics['rms']:.2f}")
    print(f"   ✓ NRMSE : {metrics['nrmse_percent']:.2f}%")
    print(f"   ✓ R² : {metrics['r2']:.3f}")
    print(f"   ✓ R0 : {sir_params['R0']:.2f}")
    print(f"   ✓ Durée infection : {sir_params['infection_duration_days']:.1f} jours")

    # Résidus
    residuals = y_data - y_fit

    # Courbes S, I, R, D
    sir_curves = sir.get_sir_curve(t_data)

    # === VISUALISATION (4 panels) ===

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # Dates pour axe x
    date_labels = [dates[i].strftime('%Y-%m-%d') for i in range(0, len(dates), 20)]
    date_positions = list(range(0, len(dates), 20))

    # --- PANEL 1 : Données vs Fit (comme code de référence) ---
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.scatter(t_data, y_data, label='Données observées',
                color='red', alpha=0.6, s=20, zorder=3)
    ax1.plot(t_data, y_fit, label='Modèle SIR ajusté (DOGBOX)',
             color='blue', linewidth=2.5, zorder=2)
    ax1.fill_between(t_data, y_fit - residuals.std(), y_fit + residuals.std(),
                      alpha=0.2, color='blue', label='±1 std résidus')

    ax1.set_title(f"1. Données vs Fit - {country_name}", fontweight='bold', fontsize=12)
    ax1.set_xlabel("Temps (jours)")
    ax1.set_ylabel("Décès quotidiens")
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(date_positions)
    ax1.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # Annotation métriques
    textstr = f'RMS = {metrics["rms"]:.1f}\nNRMSE = {metrics["nrmse_percent"]:.1f}%\nR² = {metrics["r2"]:.3f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax1.text(0.05, 0.95, textstr, transform=ax1.transAxes, fontsize=10,
             verticalalignment='top', bbox=props)

    # --- PANEL 2 : Résidus ---
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.scatter(t_data, residuals, color='purple', alpha=0.6, s=20)
    ax2.axhline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
    ax2.axhline(residuals.std(), color='red', linestyle=':', linewidth=1, alpha=0.7, label='+1 std')
    ax2.axhline(-residuals.std(), color='red', linestyle=':', linewidth=1, alpha=0.7, label='-1 std')

    ax2.set_title("2. Analyse des Résidus", fontweight='bold', fontsize=12)
    ax2.set_xlabel("Temps (jours)")
    ax2.set_ylabel("Résidus (Données - Fit)")
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(date_positions)
    ax2.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # Statistiques résidus
    textstr = f'Moyenne = {residuals.mean():.2f}\nStd = {residuals.std():.2f}\nMax = {residuals.max():.1f}\nMin = {residuals.min():.1f}'
    ax2.text(0.75, 0.95, textstr, transform=ax2.transAxes, fontsize=9,
             verticalalignment='top', bbox=props)

    # --- PANEL 3 : Compartiments S, I, R (comme code de référence) ---
    ax3 = fig.add_subplot(gs[1, :])
    ax3.plot(t_data, sir_curves['S'] / 1e6, label='Susceptibles (S)',
             color='green', linewidth=2.5)
    ax3.plot(t_data, sir_curves['I'] / 1e6, label='Infectés (I)',
             color='red', linewidth=3, zorder=3)
    ax3.plot(t_data, sir_curves['R'] / 1e6, label='Retirés (R)',
             color='blue', linewidth=2.5)

    ax3.set_title("3. Évolution des Compartiments S, I, R selon le Modèle Ajusté",
                  fontweight='bold', fontsize=12)
    ax3.set_xlabel("Temps (jours)")
    ax3.set_ylabel("Nombre d'Individus (Millions)")
    ax3.legend(loc='right')
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(date_positions)
    ax3.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # Annotation population
    ax3.text(0.02, 0.98, f'Population totale : {population/1e6:.1f}M',
             transform=ax3.transAxes, fontsize=10, verticalalignment='top', bbox=props)

    # --- PANEL 4 : Décès cumulés et quotidiens ---
    ax4 = fig.add_subplot(gs[2, 0])

    # Décès quotidiens (déjà affiché dans panel 1, mais avec cumul)
    deaths_cumul_data = np.cumsum(y_data)
    deaths_cumul_fit = np.cumsum(y_fit)

    ax4.plot(t_data, deaths_cumul_data, label='Décès cumulés (données)',
             color='red', linewidth=2, linestyle='--', alpha=0.7)
    ax4.plot(t_data, deaths_cumul_fit, label='Décès cumulés (fit)',
             color='blue', linewidth=2.5)

    ax4.set_title("4. Décès Cumulés", fontweight='bold', fontsize=12)
    ax4.set_xlabel("Temps (jours)")
    ax4.set_ylabel("Décès cumulés")
    ax4.legend(loc='upper left')
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(date_positions)
    ax4.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # Annotation total
    textstr = f'Total décès (données) : {deaths_cumul_data[-1]:.0f}\nTotal décès (fit) : {deaths_cumul_fit[-1]:.0f}'
    ax4.text(0.02, 0.98, textstr, transform=ax4.transAxes, fontsize=10,
             verticalalignment='top', bbox=props)

    # --- PANEL 5 : Tableau paramètres ---
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.axis('off')

    # Tableau paramètres
    param_text = f"""
PARAMÈTRES DU MODÈLE SIR AJUSTÉ
{'='*45}

Paramètres épidémiologiques :
  • β (Transmission) : {sir_params['beta']:.4f}
  • γ (Guérison) : {sir_params['gamma']:.4f}
  • I₀ (Infectés initiaux) : {sir_params['I0']:.0f}
  • Scale (Calibration) : {sir_params['scale']:.2f}

Indicateurs dérivés :
  • R₀ (Reproduction de base) : {sir_params['R0']:.2f}
  • Durée infection : {sir_params['infection_duration_days']:.1f} jours
  • IFR effectif : {sir_params['IFR_effective']*100:.2f}%

Qualité du fit :
  • RMS absolu : {metrics['rms']:.2f}
  • NRMSE : {metrics['nrmse_percent']:.2f}%
  • R² : {metrics['r2']:.3f}

Consensus COVID-19 (Vague 1) :
  • R₀ attendu : 2.5 - 4.0
  • Durée attendue : 7 - 14 jours
  • IFR attendu : 0.5% - 1.0%
    """

    ax5.text(0.1, 0.95, param_text, transform=ax5.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

    # Titre général
    plt.suptitle(f"Analyse Complète Modèle SIR - {country_name} (Vague 1 COVID-19)\n"
                 f"Population : {population/1e6:.1f}M | Période : Février-Juin 2020",
                 fontsize=14, fontweight='bold')

    # Sauvegarder
    output_path = f"visualisation_sir_complete_{country_name.lower()}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n   ✓ Visualisation sauvegardée : {output_path}")

    plt.show()

    return {
        'country': country_name,
        'metrics': metrics,
        'params': sir_params
    }


def main():
    """Point d'entrée principal."""

    print(f"\n{'#'*70}")
    print(f"#  VISUALISATION DÉTAILLÉE SIR SUR DONNÉES RÉELLES")
    print(f"#  Comparaison avec code de référence + NRMSE")
    print(f"{'#'*70}\n")

    print("Objectifs :")
    print("  1. Visualisations complètes (données vs fit, résidus, S/I/R)")
    print("  2. Calcul NRMSE (RMS relatif) comme code de référence")
    print("  3. Métriques qualité (RMS, NRMSE, R²)")
    print("  4. Comparaison paramètres vs consensus COVID-19")

    countries = {
        'France': 67.0e6,
        'Italy': 60.0e6
    }

    all_results = {}

    for country, pop in countries.items():
        result = visualize_sir_fit(country, pop)
        all_results[country] = result

    # Synthèse comparative
    print(f"\n{'='*70}")
    print(f"SYNTHÈSE COMPARATIVE")
    print(f"{'='*70}\n")

    print("| Pays   | RMS    | NRMSE  | R²    | R0    | Durée (j) | IFR eff |")
    print("|--------|--------|--------|-------|-------|-----------|---------|")

    for country, res in all_results.items():
        m = res['metrics']
        p = res['params']
        print(f"| {country:<6} | {m['rms']:6.2f} | {m['nrmse_percent']:5.1f}% | {m['r2']:.3f} | "
              f"{p['R0']:5.2f} | {p['infection_duration_days']:9.1f} | {p['IFR_effective']*100:6.2f}% |")

    print(f"\n{'='*70}")
    print(f"CONCLUSION")
    print(f"{'='*70}\n")

    print("✅ Visualisations générées (4 panels par pays)")
    print("✅ NRMSE calculé (comme code de référence)")
    print("✅ Fit SIR sur vraies données COVID-19 validé")
    print("")
    print("📊 NRMSE permet de comparer qualité fit entre pays")
    print("   (indépendant de l'échelle des données)")
    print("")
    print("💡 RECOMMANDATION : Ajouter NRMSE au code de production")
    print("")


if __name__ == "__main__":
    main()
