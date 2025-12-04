#!/usr/bin/env python3
"""
Analyse complète COVID-19 avec formule sech² correcte
Utilise les données directement depuis GitHub (JHU CSSE)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import odeint

# Configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)


# ============================================================================
# CHARGEMENT DES DONNÉES (méthode GitHub directe)
# ============================================================================

def load_italy_data_github():
    """Télécharge les données COVID-19 Italie depuis GitHub JHU CSSE."""
    url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"

    print("📥 Téléchargement des données depuis GitHub JHU CSSE...")
    try:
        df = pd.read_csv(url)
        italy = df[df['Country/Region'] == 'Italy'].iloc[:, 4:].T
        italy.columns = ['deaths']
        italy.index = pd.to_datetime(italy.index)

        # Filtrer Vague 1
        start_date = '2020-02-20'
        end_date = '2020-06-30'
        mask = (italy.index >= start_date) & (italy.index <= end_date)
        wave1 = italy.loc[mask]

        # Décès quotidiens (différence) + lissage
        daily_deaths = wave1['deaths'].diff().fillna(0)
        y_data = daily_deaths.rolling(window=7, center=True).mean().fillna(0).values

        # Normalisation (max = 1)
        y_data = y_data / y_data.max()

        t_data = np.arange(len(y_data))
        dates = wave1.index

        print(f"✅ Données chargées: {len(t_data)} points")
        print(f"   Période: {dates.min().date()} → {dates.max().date()}")

        return t_data, y_data, dates

    except Exception as e:
        print(f"❌ Erreur: {e}")
        raise


# ============================================================================
# MODÈLES
# ============================================================================

class SuperRadiantModel:
    """Modèle super-radiant avec formule sech² correcte."""

    def __init__(self, n_modes=3):
        self.n_modes = n_modes
        self.params = None

    def intensity(self, t, *params):
        """I(t) = Σ A_k * sech²((t - τ_k) / (2T_k))"""
        intensity = np.zeros_like(t, dtype=float)
        for i in range(self.n_modes):
            A = params[i*3]
            tau = params[i*3 + 1]
            T = params[i*3 + 2]
            x = (t - tau) / (2.0 * T)
            intensity += A * (1.0 / np.cosh(x))**2
        return intensity

    def fit(self, t_data, y_data, maxfev=50000):
        """Ajuste le modèle aux données."""
        # Estimations initiales
        p0 = []
        bounds_min = []
        bounds_max = []

        max_y = np.max(y_data)
        total_time = t_data[-1] - t_data[0]

        for i in range(self.n_modes):
            p0.extend([max_y / self.n_modes, t_data[0] + (i+1)*total_time/(self.n_modes+1), 5.0])
            bounds_min.extend([0, t_data[0], 0.1])
            bounds_max.extend([max_y*2, t_data[-1]*1.5, total_time])

        try:
            self.params, _ = curve_fit(
                self.intensity, t_data, y_data,
                p0=p0, bounds=(bounds_min, bounds_max),
                maxfev=maxfev
            )
        except RuntimeError:
            print("⚠️  Optimisation difficile, utilisation des paramètres initiaux")
            self.params = np.array(p0)

        # Trier par tau
        self._sort_modes()

        # Calcul RMS
        y_pred = self.predict(t_data)
        rms = np.sqrt(np.mean((y_data - y_pred)**2))
        return self.params, rms

    def _sort_modes(self):
        """Trie les modes par délai croissant."""
        modes = []
        for i in range(self.n_modes):
            modes.append({
                'A': self.params[i*3],
                'tau': self.params[i*3 + 1],
                'T': self.params[i*3 + 2]
            })

        modes_sorted = sorted(modes, key=lambda x: x['tau'])

        # Réorganise en format bloc
        self.params = np.array(
            [m['A'] for m in modes_sorted] +
            [m['tau'] for m in modes_sorted] +
            [m['T'] for m in modes_sorted]
        )

    def predict(self, t):
        """Prédiction avec paramètres triés."""
        intensity = np.zeros_like(t, dtype=float)
        for i in range(self.n_modes):
            A = self.params[i]
            tau = self.params[self.n_modes + i]
            T = self.params[2 * self.n_modes + i]
            x = (t - tau) / (2.0 * T)
            intensity += A * (1.0 / np.cosh(x))**2
        return intensity

    def get_mode_parameters(self):
        """Retourne les paramètres structurés."""
        modes = []
        for i in range(self.n_modes):
            modes.append({
                'mode': i + 1,
                'A': self.params[i],
                'tau': self.params[self.n_modes + i],
                'T': self.params[2 * self.n_modes + i]
            })
        return modes


class SIRModel:
    """Modèle SIR classique pour comparaison."""

    def __init__(self, population=60e6):
        self.N = population
        self.params = None

    def _deriv(self, y, t, N, beta, gamma):
        S, I, R = y
        dSdt = -beta * S * I / N
        dIdt = beta * S * I / N - gamma * I
        dRdt = gamma * I
        return dSdt, dIdt, dRdt

    def fit(self, t_data, y_data):
        """Ajuste le modèle SIR."""
        from scipy.optimize import minimize

        def objective(params):
            beta, gamma, k = params
            I0 = 100
            S0 = self.N - I0
            ret = odeint(self._deriv, [S0, I0, 0], t_data, args=(self.N, beta, gamma))
            I_pred = ret[:, 1]
            y_pred = k * I_pred
            return np.sum((y_data - y_pred)**2)

        res = minimize(objective, [0.3, 0.1, 0.001],
                      bounds=[(0, 1), (0, 1), (0, 1)],
                      method='L-BFGS-B')
        self.params = res.x

        # Calcul RMS
        y_pred = self.predict(t_data)
        rms = np.sqrt(np.mean((y_data - y_pred)**2))
        return self.params, rms

    def predict(self, t):
        """Prédiction SIR."""
        beta, gamma, k = self.params
        I0 = 100
        S0 = self.N - I0
        ret = odeint(self._deriv, [S0, I0, 0], t, args=(self.N, beta, gamma))
        return k * ret[:, 1]

    def get_parameters(self):
        return {
            'beta': self.params[0],
            'gamma': self.params[1],
            'R0': self.params[0] / self.params[1] if self.params[1] > 0 else 0
        }


# ============================================================================
# ANALYSE PRINCIPALE
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  ANALYSE COVID-19 ITALIE - MODÈLE SUPER-RADIANT SECH²")
    print("="*70)

    # 1. CHARGEMENT
    print("\n[1/5] Chargement des données...")
    t_data, y_data, dates = load_italy_data_github()

    # 2. SUPER-RADIANT
    print("\n[2/5] Ajustement modèle Super-Radiant (3 modes, formule sech²)...")
    sr_model = SuperRadiantModel(n_modes=3)
    params_sr, rms_sr = sr_model.fit(t_data, y_data)

    print(f"\n✅ Super-Radiant ajusté!")
    print(f"   RMS: {rms_sr:.6f}")

    modes = sr_model.get_mode_parameters()
    print("\n   Paramètres des modes:")
    print("   " + "-"*60)
    for mode in modes:
        print(f"   Mode {mode['mode']}: A={mode['A']:.4f}, τ={mode['tau']:.2f}j, T={mode['T']:.2f}j")

    # 3. SIR
    print("\n[3/5] Ajustement modèle SIR classique...")
    sir_model = SIRModel()
    params_sir, rms_sir = sir_model.fit(t_data, y_data)

    print(f"\n✅ SIR ajusté!")
    print(f"   RMS: {rms_sir:.6f}")

    sir_params = sir_model.get_parameters()
    print(f"\n   Paramètres SIR:")
    print(f"   β={sir_params['beta']:.4f}, γ={sir_params['gamma']:.4f}, R₀={sir_params['R0']:.2f}")

    # 4. COMPARAISON
    print("\n[4/5] Génération des graphiques...")

    y_fit_sr = sr_model.predict(t_data)
    y_fit_sir = sir_model.predict(t_data)

    # Graphique de comparaison
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(t_data, y_data, 'k-', linewidth=2.5, label='Données réelles (Italie)', alpha=0.7)
    ax.plot(t_data, y_fit_sr, 'b--', linewidth=2.5,
            label=f'Super-Radiant sech² (3 modes, RMS={rms_sr:.4f})')
    ax.plot(t_data, y_fit_sir, 'r:', linewidth=2.5,
            label=f'SIR Classique (RMS={rms_sir:.4f})')

    ax.set_title('Validation COVID-19 Vague 1 (Italie) - Formule sech² Correcte',
                fontsize=16, fontweight='bold')
    ax.set_xlabel('Jours depuis le début de la vague', fontsize=12)
    ax.set_ylabel('Décès quotidiens (normalisés)', fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('reports/comparison_sech2_italy.png', dpi=150, bbox_inches='tight')
    print("   ✓ Graphique sauvegardé: reports/comparison_sech2_italy.png")

    # 5. RÉSULTATS FINAUX
    print("\n[5/5] Résumé final")
    print("="*70)
    improvement = rms_sir / rms_sr
    print(f"\n🏆 RÉSULTATS:")
    print(f"   • Erreur RMS Super-Radiant (sech²): {rms_sr:.6f}")
    print(f"   • Erreur RMS SIR:                   {rms_sir:.6f}")
    print(f"   • Amélioration:                     {improvement:.2f}x plus précis")

    print(f"\n📊 INTERPRÉTATION SOCIOLOGIQUE:")
    mode_names = ["Urbain", "Péri-urbain", "Rural"]
    for i, (mode, name) in enumerate(zip(modes, mode_names)):
        print(f"   Mode {i+1} ({name:12s}): τ={mode['tau']:>6.1f}j, T={mode['T']:>5.1f}j, A={mode['A']:.3f}")

    print(f"\n✅ Analyse complète terminée!")
    print("="*70 + "\n")

    return {
        'rms_sr': rms_sr,
        'rms_sir': rms_sir,
        'improvement': improvement,
        'modes': modes
    }


if __name__ == "__main__":
    results = main()
