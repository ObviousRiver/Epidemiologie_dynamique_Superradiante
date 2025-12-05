#!/usr/bin/env python3
"""
Analyse COVID-19 Finlande - Première Vague
Comparaison Super-Radiant (sech²) vs SIR Standard

CAS TEST CRITIQUE: Finlande vs Suède
- Culture scandinave identique
- Géographie similaire
- MAIS stratégies COVID opposées:
  * Finlande: Confinement strict précoce (12 mars 2020)
  * Suède: Mesures volontaires uniquement

Période: Février-Juin 2020
Source: Johns Hopkins University CSSE COVID-19 Data Repository
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Imports locaux
from models import SuperRadiantModel, SIRModel

# ============================================================================
# DONNÉES FINLANDE
# ============================================================================

def load_finland_data_github():
    """Télécharge les données COVID-19 Finlande depuis GitHub JHU CSSE."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    print("📥 Téléchargement des données Finlande depuis GitHub JHU CSSE...")
    try:
        df = pd.read_csv(url)
        # Finlande - somme de toutes les régions
        finland_data = df[df['Country/Region'] == 'Finland'].iloc[:, 4:].sum(axis=0)
        finland = pd.DataFrame({'deaths': finland_data})
        finland.index = pd.to_datetime(finland.index)

        # Filtrer Vague 1
        start_date = '2020-02-15'
        end_date = '2020-06-30'
        finland = finland.loc[start_date:end_date]

        # Calculer décès quotidiens
        daily_deaths = finland['deaths'].diff().fillna(0)
        daily_deaths = daily_deaths.clip(lower=0)  # Enlever valeurs négatives

        # Lissage sur 7 jours
        daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

        # Normalisation
        max_deaths_raw = daily_deaths_smooth.max()
        normalized = daily_deaths_smooth / max_deaths_raw

        # Préparer données pour ajustement
        t_data = np.arange(len(normalized))
        y_data = normalized.values
        dates = finland.index

        print(f"✅ Données Finlande chargées: {len(t_data)} points")
        print(f"   Période: {dates[0].strftime('%Y-%m-%d')} → {dates[-1].strftime('%Y-%m-%d')}")
        print(f"   Max décès quotidiens: {int(max_deaths_raw)} (avant normalisation)")
        print(f"   📍 Politique: Confinement STRICT précoce (12 mars 2020)")
        print(f"   🧪 TEST: vs Suède (culture identique, politique opposée)")

        return t_data, y_data, dates, max_deaths_raw

    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)

# ============================================================================
# AJUSTEMENT DES MODÈLES
# ============================================================================

def fit_superradiant(t_data, y_data, n_modes=3):
    """Ajuste le modèle Super-Radiant avec n modes."""
    model = SuperRadiantModel(n_modes=n_modes)

    try:
        model.fit(t_data, y_data)
        y_pred = model.predict(t_data)
        residuals = y_data - y_pred
        rms = np.sqrt(np.mean(residuals**2))
        rms_percent = rms * 100

        print(f"   ✅ {n_modes} modes: RMS = {rms:.6f} ({rms_percent:.2f}%)")
        return model, rms, rms_percent

    except Exception as e:
        print(f"   ❌ Erreur ajustement {n_modes} modes: {e}")
        return None, None, None

def fit_sir(t_data, y_data):
    """Ajuste le modèle SIR standard."""
    model = SIRModel()

    try:
        model.fit(t_data, y_data)
        y_pred = model.predict(t_data, y_max=1.0)  # Données normalisées, max=1.0
        residuals = y_data - y_pred
        rms = np.sqrt(np.mean(residuals**2))
        rms_percent = rms * 100

        print(f"   ✅ SIR: RMS = {rms:.6f} ({rms_percent:.2f}%)")
        return model, rms, rms_percent

    except Exception as e:
        print(f"   ❌ Erreur ajustement SIR: {e}")
        return None, None, None

# ============================================================================
# VISUALISATION
# ============================================================================

def plot_comparison(t_data, y_data, dates, models_dict, output_path):
    """Génère le graphique de comparaison."""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('COVID-19 Finlande Vague 1 - Comparaison Super-Radiant vs SIR\n(Confinement STRICT - Test vs Suède)',
                 fontsize=16, fontweight='bold')

    # Convertir indices en dates pour l'axe x
    date_labels = [dates[i].strftime('%Y-%m-%d') for i in range(0, len(dates), 20)]
    date_positions = list(range(0, len(dates), 20))

    # ---- Subplot 1: Comparaison 3 vs 4 modes ----
    ax1 = axes[0, 0]
    ax1.plot(t_data, y_data, 'o', markersize=3, alpha=0.5, label='Données réelles', color='black')

    if models_dict['sr3'] is not None:
        y_pred_3 = models_dict['sr3'].predict(t_data)
        ax1.plot(t_data, y_pred_3, '--', linewidth=2,
                label=f"Super-Radiant 3 modes (RMS={models_dict['rms3']:.2f}%)", color='blue')

    if models_dict['sr4'] is not None:
        y_pred_4 = models_dict['sr4'].predict(t_data)
        ax1.plot(t_data, y_pred_4, '-', linewidth=2,
                label=f"Super-Radiant 4 modes (RMS={models_dict['rms4']:.2f}%)", color='green')

    ax1.set_xlabel('Jours', fontsize=11)
    ax1.set_ylabel('Décès quotidiens (normalisés)', fontsize=11)
    ax1.set_title('Comparaison Super-Radiant 3 vs 4 modes', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(date_positions)
    ax1.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # ---- Subplot 2: Super-Radiant vs SIR ----
    ax2 = axes[0, 1]
    ax2.plot(t_data, y_data, 'o', markersize=3, alpha=0.5, label='Données réelles', color='black')

    best_sr = models_dict['sr4'] if models_dict['rms4'] and models_dict['rms4'] < models_dict['rms3'] else models_dict['sr3']
    best_rms = models_dict['rms4'] if models_dict['rms4'] and models_dict['rms4'] < models_dict['rms3'] else models_dict['rms3']

    if best_sr is not None:
        y_pred_sr = best_sr.predict(t_data)
        ax2.plot(t_data, y_pred_sr, '--', linewidth=2,
                label=f"Super-Radiant (RMS={best_rms:.2f}%)", color='blue')

    if models_dict['sir'] is not None:
        y_pred_sir = models_dict['sir'].predict(t_data, y_max=1.0)
        ax2.plot(t_data, y_pred_sir, ':', linewidth=2,
                label=f"SIR Standard (RMS={models_dict['rms_sir']:.2f}%)", color='red')

    ax2.set_xlabel('Jours', fontsize=11)
    ax2.set_ylabel('Décès quotidiens (normalisés)', fontsize=11)
    ax2.set_title('Super-Radiant vs SIR', fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(date_positions)
    ax2.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # ---- Subplot 3: Décomposition en modes (4 modes) ----
    ax3 = axes[1, 0]
    ax3.plot(t_data, y_data, 'o', markersize=3, alpha=0.5, label='Données réelles', color='black')

    if models_dict['sr4'] is not None:
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
        mode_names = ['Mode 1 (Helsinki)', 'Mode 2 (Régions)', 'Mode 3 (Régional)', 'Mode 4 (Laponie)']

        for i in range(4):
            y_mode = models_dict['sr4'].get_mode_intensity(t_data, i)
            ax3.plot(t_data, y_mode, '-', linewidth=1.5, label=mode_names[i], color=colors[i], alpha=0.7)

        y_total = models_dict['sr4'].predict(t_data)
        ax3.plot(t_data, y_total, '--', linewidth=2, label='Super-Radiant Total', color='blue')

    ax3.set_xlabel('Jours', fontsize=11)
    ax3.set_ylabel('Intensité (normalisée)', fontsize=11)
    ax3.set_title('Décomposition en 4 modes géographiques', fontsize=12, fontweight='bold')
    ax3.legend(loc='best', fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(date_positions)
    ax3.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    # ---- Subplot 4: Résidus ----
    ax4 = axes[1, 1]

    if best_sr is not None:
        residuals_sr = y_data - best_sr.predict(t_data)
        ax4.plot(t_data, residuals_sr, 'o-', markersize=2, linewidth=1,
                label=f"Résidus SR (RMS={best_rms:.2f}%)", color='blue', alpha=0.7)

    if models_dict['sir'] is not None:
        residuals_sir = y_data - models_dict['sir'].predict(t_data, y_max=1.0)
        ax4.plot(t_data, residuals_sir, 'o-', markersize=2, linewidth=1,
                label=f"Résidus SIR (RMS={models_dict['rms_sir']:.2f}%)", color='red', alpha=0.7)

    ax4.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax4.set_xlabel('Jours', fontsize=11)
    ax4.set_ylabel('Résidus (normalisés)', fontsize=11)
    ax4.set_title('Analyse des résidus', fontsize=12, fontweight='bold')
    ax4.legend(loc='best', fontsize=9)
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(date_positions)
    ax4.set_xticklabels(date_labels, rotation=45, ha='right', fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"   ✓ Graphique: {output_path}")
    plt.close()

# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """Fonction principale d'analyse."""

    print("=" * 70)
    print("  ANALYSE COVID-19 FINLANDE VAGUE 1")
    print("  Super-Radiant (sech²) vs SIR Standard")
    print("  TEST CRITIQUE: Finlande (strict) vs Suède (volontaire)")
    print("=" * 70)
    print()

    # [1] Chargement des données
    print("[1/5] Chargement des données Finlande...")
    t_data, y_data, dates, max_deaths_raw = load_finland_data_github()
    print()

    # [2] Ajustement Super-Radiant (3 modes)
    print("[2/5] Ajustement Super-Radiant (3 modes)...")
    sr_model_3, rms_3, rms_percent_3 = fit_superradiant(t_data, y_data, n_modes=3)
    print()

    # [2b] Ajustement Super-Radiant (4 modes)
    print("[2/5] Ajustement Super-Radiant (4 modes)...")
    sr_model_4, rms_4, rms_percent_4 = fit_superradiant(t_data, y_data, n_modes=4)
    print()

    # [3] Ajustement SIR
    print("[3/5] Ajustement SIR classique...")
    sir_model, rms_sir, rms_percent_sir = fit_sir(t_data, y_data)
    print()

    # [4] Résumé comparatif
    print("[4/5] Résumé des performances...")
    print("=" * 70)
    print()

    best_model = sr_model_4 if (rms_4 and rms_percent_4 < rms_percent_3) else sr_model_3
    best_rms = rms_percent_4 if (rms_4 and rms_percent_4 < rms_percent_3) else rms_percent_3
    best_n_modes = 4 if (rms_4 and rms_percent_4 < rms_percent_3) else 3

    if best_model and sir_model:
        improvement = best_rms / rms_percent_sir  # Ratio inversé pour cohérence
        print(f"📊 RÉSULTATS FINLANDE VAGUE 1:")
        print(f"   • Super-Radiant ({best_n_modes} modes): RMS = {best_rms:.2f}%")
        print(f"   • SIR Standard:          RMS = {rms_percent_sir:.2f}%")
        if improvement > 1.0:
            print(f"   • Résultat:              SIR {improvement:.2f}x meilleur")
        else:
            print(f"   • Amélioration:          SR {1.0/improvement:.2f}x meilleur")
        print()

    # [5] Génération des graphiques
    print("[5/5] Génération des graphiques...")
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    models_dict = {
        'sr3': sr_model_3,
        'sr4': sr_model_4,
        'sir': sir_model,
        'rms3': rms_percent_3,
        'rms4': rms_percent_4,
        'rms_sir': rms_percent_sir
    }

    output_path = reports_dir / "comparison_finland_wave1.png"
    plot_comparison(t_data, y_data, dates, models_dict, output_path)
    print()

    # Résumé final avec paramètres des modes
    print("=" * 70)
    print("📋 RÉSUMÉ FINAL - FINLANDE VAGUE 1")
    print("=" * 70)
    print()

    if best_model:
        print(f"🏆 MEILLEUR MODÈLE ({best_n_modes} modes):")
        mode_names = ['Helsinki        ', 'Régions      ', 'Régional    ', 'Laponie        ']
        for i in range(best_n_modes):
            A = best_model.params[i]
            tau = best_model.params[best_n_modes + i]
            T = best_model.params[2 * best_n_modes + i]
            print(f"   Mode {i+1} ({mode_names[i]}): τ={tau:6.1f}j, T={T:5.1f}j, A={A:.3f}")
        print()

    print(f"✅ Super-Radiant: RMS = {best_rms:.2f}%")
    print(f"{'✅' if rms_percent_sir > best_rms else '❌'} SIR Standard:  RMS = {rms_percent_sir:.2f}%")
    if sir_model:
        if improvement > 1.0:
            print(f"⚠️  Résultat:     SIR est meilleur de {improvement:.2f}x")
        else:
            print(f"🎯 Amélioration:  SR est {1.0/improvement:.1f}x meilleur")
    print()
    print("🧪 COMPARAISON SCANDINAVIE - Culture vs Politique:")
    print("   ┌────────────┬─────────────────┬──────────┬─────────────┐")
    print("   │ Pays       │ Politique       │ Gagnant  │ Performance │")
    print("   ├────────────┼─────────────────┼──────────┼─────────────┤")
    print("   │ Suède      │ Volontaire      │ SR       │ RMS 6.32%   │")
    if improvement < 1.0:
        print("   │ Finlande    │ État urgence (16 mars)│ SR       │ RMS {:.2f}%  │".format(best_rms))
    else:
        print("   │ Finlande    │ État urgence (16 mars)│ SIR      │ RMS {:.2f}%  │".format(rms_percent_sir))
    print("   └────────────┴─────────────────┴──────────┴─────────────┘")
    print()
    if improvement > 1.0:
        print("   ✅ CONFIRMÉ: Politique > Culture")
        print("      Confinement strict → SIR, malgré culture scandinave")
    else:
        print("   ⚠️  SURPRISE: SR gagne malgré confinement strict")
        print("      Géographie norvégienne (fjords) → hétérogénéité naturelle?")
    print()
    print("✅ Analyse Finlande terminée!")
    print("=" * 70)

    return {
        'sr_model': best_model,
        'sir_model': sir_model,
        'rms_sr': best_rms,
        'rms_sir': rms_percent_sir,
        'improvement': improvement if sir_model else None,
        't_data': t_data,
        'y_data': y_data,
        'dates': dates
    }, sir_model

if __name__ == "__main__":
    results, sir = main()
