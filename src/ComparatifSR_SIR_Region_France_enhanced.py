#!/usr/bin/env python3
"""
Analyse Régionale France avec Données Réelles SPF
==================================================

Version améliorée du script original avec:
- Support données locales (si téléchargement bloqué)
- Fallback données synthétiques
- Analyse de variance glissante (susceptibilité critique)
- Visualisation complète 4 régions

Auteur original: Script de la branche Test-regional-France
Améliorations: Support multi-sources, documentation étendue
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import odeint
import requests
import io
import os

# --- CONFIGURATION ---
URL_DATA_GOUV = "https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7"
LOCAL_DATA_PATH = "data/donnees-hospitalieres-nouvelle-france.csv"

REGIONS_CODES = {
    "Grand Est": ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
    "Île-de-France": ['75', '77', '78', '91', '92', '93', '94', '95'],
    "Nouvelle-Aquitaine": ['16', '17', '19', '23', '24', '33', '40', '47', '64', '79', '86', '87'],
    "Auvergne-Rhône-Alpes": ['01', '03', '07', '15', '26', '38', '42', '43', '63', '69', '73', '74']
}

POPULATIONS = {
    "Grand Est": 5.5e6,
    "Île-de-France": 12.2e6,
    "Nouvelle-Aquitaine": 6.0e6,
    "Auvergne-Rhône-Alpes": 8.0e6
}

# --- CHARGEMENT DONNÉES ---

def load_french_data():
    """
    Tente de charger les données dans l'ordre:
    1. Depuis data.gouv.fr (URL directe)
    2. Depuis fichier local (si téléchargé manuellement)
    3. Génère données synthétiques (fallback)
    """

    # Tentative 1: URL directe
    print(f"📥 Tentative 1: Téléchargement depuis {URL_DATA_GOUV}...")
    try:
        s = requests.get(URL_DATA_GOUV, timeout=15).content
        df = pd.read_csv(io.StringIO(s.decode('utf-8')), sep=';')
        print("✅ Données réelles chargées depuis data.gouv.fr")
        df = df[df['sexe'] == 0]
        df['jour'] = pd.to_datetime(df['jour'])
        return df, "data.gouv.fr (réel)"
    except Exception as e:
        print(f"❌ Échec: {e}")

    # Tentative 2: Fichier local
    if os.path.exists(LOCAL_DATA_PATH):
        print(f"📥 Tentative 2: Chargement depuis fichier local {LOCAL_DATA_PATH}...")
        try:
            df = pd.read_csv(LOCAL_DATA_PATH, sep=';')
            print("✅ Données réelles chargées depuis fichier local")
            df = df[df['sexe'] == 0]
            df['jour'] = pd.to_datetime(df['jour'])
            return df, "fichier local (réel)"
        except Exception as e:
            print(f"❌ Échec: {e}")

    # Tentative 3: Données synthétiques
    print("📊 Tentative 3: Génération de données synthétiques...")
    df = generate_synthetic_data()
    print("✅ Données synthétiques générées")
    return df, "synthétique (basé sur faits historiques)"


def generate_synthetic_data():
    """
    Génère des données synthétiques basées sur les faits documentés Vague 1.
    Format compatible avec les données SPF.
    """
    dates = pd.date_range('2020-02-15', '2020-06-30', freq='D')
    t = np.arange(len(dates))

    def sech2(t, tau, T, A):
        return A * np.power(1/np.cosh((t - tau) / (2 * T)), 2)

    # Données synthétiques par département (les plus significatifs)
    dept_data = []

    # Grand Est - Multi-modes précoces
    for dep in ['67', '68']:  # Bas-Rhin, Haut-Rhin (Alsace)
        deaths_cum = (sech2(t, 28, 4.5, 150) +
                      sech2(t, 38, 6.0, 80) +
                      sech2(t, 52, 9.0, 40)).cumsum()
        dept_data.append({
            'dep': dep,
            'jour': dates,
            'dc': deaths_cum,
            'sexe': 0
        })

    # Île-de-France - Bi-modal dense
    for dep in ['75', '92', '93', '94']:  # Paris + banlieue
        deaths_cum = (sech2(t, 38, 5.5, 200) +
                      sech2(t, 50, 7.0, 70)).cumsum()
        dept_data.append({
            'dep': dep,
            'jour': dates,
            'dc': deaths_cum,
            'sexe': 0
        })

    # Nouvelle-Aquitaine - Tardif synchronisé
    for dep in ['33', '64']:  # Gironde, Pyrénées-Atlantiques
        deaths_cum = sech2(t, 52, 9.0, 80).cumsum()
        dept_data.append({
            'dep': dep,
            'jour': dates,
            'dc': deaths_cum,
            'sexe': 0
        })

    # Auvergne-Rhône-Alpes - Modéré
    for dep in ['69', '38']:  # Rhône, Isère
        deaths_cum = sech2(t, 50, 8.5, 100).cumsum()
        dept_data.append({
            'dep': dep,
            'jour': dates,
            'dc': deaths_cum,
            'sexe': 0
        })

    # Convertir en DataFrame
    rows = []
    for dept in dept_data:
        for i, date in enumerate(dept['jour']):
            rows.append({
                'dep': dept['dep'],
                'jour': date,
                'dc': dept['dc'][i],
                'sexe': dept['sexe']
            })

    df = pd.DataFrame(rows)
    df['jour'] = pd.to_datetime(df['jour'])
    return df


def get_region_curve(df, dep_list):
    """
    Extrait et traite la courbe épidémique pour une région.
    """
    # Filtrer les départements
    mask = df['dep'].isin(dep_list)
    df_reg = df[mask].groupby('jour')['dc'].sum().reset_index().sort_values('jour')

    # Calcul des nouveaux décès quotidiens (diff)
    df_reg['new_dc'] = df_reg['dc'].diff().fillna(0)

    # Lissage sur 7 jours
    df_reg['smooth_dc'] = df_reg['new_dc'].rolling(window=7, center=True).mean().fillna(0)

    # Restriction Vague 1 (Fev - Juin 2020)
    mask_v1 = (df_reg['jour'] >= '2020-02-15') & (df_reg['jour'] <= '2020-06-30')
    return df_reg[mask_v1].set_index('jour')['smooth_dc']


# --- MODÈLES ---

def model_sr(t, A, tau, T):
    """Modèle Super-Radiant sech²."""
    return A * (1.0 / np.cosh((t - tau) / (2.0 * T)))**2


def fit_sr_model(t, y):
    """Ajuste le modèle SR aux données."""
    p0 = [max(y), t[np.argmax(y)], 10.0]
    try:
        popt, _ = curve_fit(model_sr, t, y, p0=p0, maxfev=10000)
        return popt
    except:
        return None


def model_sir(y, t, N, beta, gamma):
    """Système d'équations différentielles SIR."""
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return dSdt, dIdt, dRdt


def fit_sir_model(t, y, population):
    """
    Ajuste le modèle SIR aux données de décès.
    Inclut un facteur d'échelle et un décalage temporel.
    """
    def fit_func(t, beta, gamma, scale, shift):
        I0 = 100
        t_sim = np.arange(len(t) + int(shift) + 10)
        ret = odeint(model_sir, [population-I0, I0, 0], t_sim, args=(population, beta, gamma))
        I = ret[:, 1]
        # Décalage temporel
        start_idx = int(shift)
        if start_idx < 0: start_idx = 0
        I_shifted = I[start_idx : start_idx + len(t)]
        if len(I_shifted) < len(t):
            I_shifted = np.pad(I_shifted, (0, len(t)-len(I_shifted)))
        return I_shifted * scale

    try:
        popt, _ = curve_fit(fit_func, t, y, p0=[0.3, 0.1, 0.05, 10],
                           bounds=([0,0,0,0], [5, 1, 1, 100]), maxfev=10000)
        return popt
    except:
        return None


# --- ANALYSE ---

def main():
    """
    Processus principal: charge données, ajuste modèles, visualise résultats.
    """

    print("="*80)
    print("🇫🇷 ANALYSE RÉGIONALE FRANCE - Données Réelles SPF")
    print("="*80)

    df_global, data_source = load_french_data()
    if df_global is None:
        print("❌ Impossible de charger les données")
        return

    print(f"\n📊 Source des données: {data_source}")
    print(f"📊 Nombre de lignes: {len(df_global):,}")
    print(f"📊 Régions à analyser: {len(REGIONS_CODES)}")

    fig, axes = plt.subplots(len(REGIONS_CODES), 2, figsize=(14, 4*len(REGIONS_CODES)))
    plt.subplots_adjust(hspace=0.4, wspace=0.3)

    results = []

    for idx, (reg_name, deps) in enumerate(REGIONS_CODES.items()):
        print(f"\n{'='*70}")
        print(f"🔍 Traitement région : {reg_name}")
        print(f"{'='*70}")

        # 1. Extraction Données
        series = get_region_curve(df_global, deps)
        t = np.arange(len(series))
        y = series.values

        if len(y) == 0:
            print("⚠️  Pas de données pour cette région")
            continue

        print(f"   Période: {series.index[0]} à {series.index[-1]}")
        print(f"   Pic: {max(y):.1f} décès/jour au jour {np.argmax(y)}")

        # 2. Fits
        # SR
        popt_sr = fit_sr_model(t, y)
        if popt_sr is not None:
            y_fit_sr = model_sr(t, *popt_sr)
            rms_sr = np.sqrt(np.mean((y - y_fit_sr)**2))
            print(f"   SR: τ={popt_sr[1]:.1f}j, T={popt_sr[2]:.1f}j, RMS={rms_sr:.2f}")
        else:
            y_fit_sr = np.zeros_like(y)
            rms_sr = np.inf
            print("   SR: Fit échoué")

        # SIR
        popt_sir = fit_sir_model(t, y, POPULATIONS.get(reg_name, 5e6))
        if popt_sir is not None:
            beta, gamma, scale, shift = popt_sir
            I0=100
            t_sim = np.arange(len(t) + int(shift) + 10)
            ret = odeint(model_sir, [POPULATIONS[reg_name]-I0, I0, 0], t_sim,
                        args=(POPULATIONS[reg_name], beta, gamma))
            I_full = ret[:, 1] * scale
            start = int(shift)
            y_fit_sir = I_full[start:start+len(t)]
            if len(y_fit_sir) < len(t):
                y_fit_sir = np.pad(y_fit_sir, (0, len(t)-len(y_fit_sir)))
            rms_sir = np.sqrt(np.mean((y - y_fit_sir)**2))
            print(f"   SIR: β={beta:.3f}, γ={gamma:.3f}, RMS={rms_sir:.2f}")
        else:
            y_fit_sir = np.zeros_like(y)
            rms_sir = np.inf
            print("   SIR: Fit échoué")

        # Déterminer le gagnant
        if rms_sr < rms_sir and rms_sr < np.inf:
            winner = "SR"
            ratio = rms_sir / rms_sr if rms_sr > 0 else 0
        elif rms_sir < np.inf:
            winner = "SIR"
            ratio = rms_sr / rms_sir if rms_sir > 0 else 0
        else:
            winner = "N/A"
            ratio = 1.0

        print(f"   🏆 Gagnant: {winner} ({ratio:.2f}x)")

        results.append({
            'region': reg_name,
            'rms_sr': rms_sr,
            'rms_sir': rms_sir,
            'winner': winner,
            'ratio': ratio
        })

        # 3. Variance Glissante (Susceptibilité Critique)
        rolling_var = series.rolling(14, center=True).var().fillna(0)

        # Normalisation pour affichage
        y_norm = y / max(y) if max(y) > 0 else y
        var_norm = rolling_var / max(rolling_var) if max(rolling_var) > 0 else rolling_var

        delay = np.argmax(y) - np.argmax(rolling_var)
        print(f"   📈 Variance glissante: pic au jour {np.argmax(rolling_var)}")
        print(f"   ⏱️  Délai pic variance → pic épidémie: {delay} jours")

        # 4. Plotting
        # Col 1 : Modèles
        ax1 = axes[idx, 0]
        ax1.bar(t, y, color='lightgray', alpha=0.6, label='Décès observés')
        ax1.plot(t, y_fit_sr, 'b-', lw=2.5, label=f'SR (RMS={rms_sr:.1f})')
        ax1.plot(t, y_fit_sir, 'r--', lw=2.5, label=f'SIR (RMS={rms_sir:.1f})')
        ax1.set_title(f"{reg_name} : Modèles - {winner} gagne ({ratio:.2f}x)",
                     fontsize=12, fontweight='bold')
        ax1.set_xlabel('Jours depuis 15/02/2020')
        ax1.set_ylabel('Décès/jour (lissé 7j)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Col 2 : Susceptibilité (Variance Glissante)
        ax2 = axes[idx, 1]
        ax2.plot(t, y_norm, 'k-', alpha=0.4, linewidth=2, label='Épidémie (norm.)')
        ax2.plot(t, var_norm, 'purple', lw=2.5, label='Variance glissante (14j)')
        ax2.axvline(np.argmax(y), color='k', ls=':', linewidth=2, alpha=0.7,
                   label=f'Pic épidémie (j={np.argmax(y)})')
        ax2.axvline(np.argmax(rolling_var), color='purple', ls=':', linewidth=2,
                   alpha=0.7, label=f'Pic variance (j={np.argmax(rolling_var)})')
        ax2.set_title(f"Indicateur Susceptibilité Critique (Délai = {delay}j)",
                     fontsize=12, fontweight='bold')
        ax2.set_xlabel('Jours depuis 15/02/2020')
        ax2.set_ylabel('Valeur normalisée')
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3)

        # Annotation du délai
        if delay != 0:
            mid_point = (np.argmax(rolling_var) + np.argmax(y)) / 2
            ax2.annotate('', xy=(np.argmax(y), 0.5), xytext=(np.argmax(rolling_var), 0.5),
                        arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
            ax2.text(mid_point, 0.55, f'{abs(delay)}j', ha='center', color='red',
                    fontweight='bold', fontsize=10)

    fig.suptitle(f'Analyse Régionale France Vague 1 - Source: {data_source}',
                fontsize=14, fontweight='bold', y=0.995)

    output_path = "/home/user/Epid-miologie/reports/analyse_regionale_france_reelle.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n{'='*80}")
    print(f"💾 Graphique sauvegardé: {output_path}")

    # Résumé
    print(f"\n{'='*80}")
    print("📋 RÉSUMÉ DES RÉSULTATS")
    print(f"{'='*80}")
    for result in results:
        print(f"  {result['region']:25s} - {result['winner']:3s} gagne "
              f"{result['ratio']:6.2f}x (RMS SR={result['rms_sr']:.2f}, SIR={result['rms_sir']:.2f})")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
