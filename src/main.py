import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import odeint
import os
from kaggle.api.kaggle_api_extended import KaggleApi

# --- PARAMÈTRES GLOBAUX ---
N_MODES = 4 # <--- CHANGEZ CETTE VALEUR POUR TESTER DIFFÉRENTS NOMBRES DE MODES

# --- Étape 1 : Téléchargement et Préparation des Données via API Kaggle (MÉTHODE ROBUSTE) ---
try:
    print("Authentification à l'API Kaggle...")
    api = KaggleApi()
    api.authenticate()

    print("Téléchargement du dataset 'covid19-daily-reports'...")
    # Télécharge et décompresse directement dans le dossier 'covid_data'
    api.dataset_download_files('sudalairajkumar/covid19-daily-reports', path='covid_data', unzip=True)
    print("✅ Dataset téléchargé et décompressé avec succès.")

    # Maintenant, traitons les fichiers
    covid_data_path = 'covid_data/csse_covid_19_daily_reports'
    all_files = [os.path.join(covid_data_path, f) for f in os.listdir(covid_data_path) if f.endswith('.csv')]

    italy_dfs = []
    for filename in sorted(all_files):
        df = pd.read_csv(filename)
        # Standardiser les noms de colonnes qui peuvent varier selon les dates
        df = df.rename(columns={
            'Country_Region': 'Country/Region',
            'Province_State': 'Province/State'
        })
        if 'Country/Region' in df.columns:
            df_italy = df[df['Country/Region'] == 'Italy']
            if not df_italy.empty:
                date_str = os.path.basename(filename).split('.')[0]
                df_italy['Date'] = pd.to_datetime(date_str, errors='coerce')
                italy_dfs.append(df_italy[['Date', 'Deaths', 'Province/State']])

    if not italy_dfs:
        raise ValueError("Aucune donnée pour l'Italie trouvée.")

    italy_all = pd.concat(italy_dfs, ignore_index=True)
    italy_deaths_series = italy_all.groupby('Date')['Deaths'].sum().sort_index()
    print("✅ Données italiennes extraites et agrégées avec succès.")

except Exception as e:
    print(f"❌ Erreur lors du traitement des données Kaggle: {e}")
    exit()

# --- Prétraitement des données ---
start_date = '2020-02-20'
end_date = '2020-06-30'
italy_deaths_wave1 = italy_deaths_series[start_date:end_date]
italy_deaths_smooth = italy_deaths_wave1.rolling(window=7, center=True).mean().dropna()
italy_deaths_norm = italy_deaths_smooth / italy_deaths_smooth.iloc[0]

t_data = np.arange(len(italy_deaths_norm))
y_data = italy_deaths_norm.values
print(f"\nPériode analysée : {italy_deaths_norm.index.min().date()} au {italy_deaths_norm.index.max().date()}")
print(f"Nombre de jours : {len(italy_deaths_norm)}")


# --- Étape 2 : Définition et Ajustement des Modèles ---
def super_radiant_fit_wrapper(t, *params):
    intensity = np.zeros_like(t, dtype=float)
    for i in range(N_MODES):
        A, tau, T = params[i*3], params[i*3 + 1], params[i*3 + 2]
        effective_t = np.maximum(t - tau, 0)
        intensity += A * (effective_t**2) * np.exp(-effective_t / T)
    return intensity

# Génération dynamique des estimations initiales et des bornes
initial_guess_sr = []
param_bounds_sr_lower = []
param_bounds_sr_upper = []
for i in range(N_MODES):
    initial_guess_sr.extend([1.0, 10 + i*10, 5 + i*5])
    param_bounds_sr_lower.extend([0, 0, 1])
    param_bounds_sr_upper.extend([np.inf, 50 + i*20, 80 + i*20]) # Bornes T plus larges

print(f"\n--- Ajustement du modèle Super-Radiant ({N_MODES} modes) ---")
popt_sr, pcov_sr = curve_fit(super_radiant_fit_wrapper, t_data, y_data, p0=initial_guess_sr, bounds=(param_bounds_sr_lower, param_bounds_sr_upper), maxfev=30000)

# --- TRI DES MODES ET AFFICHAGE CORRECT ---
modes_unsorted = []
for i in range(N_MODES):
    modes_unsorted.append({'tau': popt_sr[i*3 + 1], 'A': popt_sr[i*3], 'T': popt_sr[i*3 + 2]})

modes_sorted = sorted(modes_unsorted, key=lambda x: x['tau'])
popt_sr_sorted = np.array([mode['A'] for mode in modes_sorted] + [mode['tau'] for mode in modes_sorted] + [mode['T'] for mode in modes_sorted])

y_fit_sr = super_radiant_fit_wrapper(t_data, *popt_sr_sorted)
rms_error_sr = np.sqrt(np.mean((y_data - y_fit_sr)**2))

print("Ajustement terminé et paramètres triés par τ croissant :")
for i in range(N_MODES):
    print(f"  Mode {i+1}: A={popt_sr_sorted[i]:.3f}, τ={popt_sr_sorted[N_MODES+i]:.2f} jours, T={popt_sr_sorted[2*N_MODES+i]:.2f} jours")
print(f"Erreur RMS : {rms_error_sr:.4f}")

# --- Modèle SIR (pour comparaison) ---
def sir_fit_curve(t, beta, gamma, I0):
    N = 60e6
    y0 = N - I0, I0, 0
    sol = odeint(lambda y, t: (-beta*y[0]*y[1]/N, beta*y[0]*y[1]/N - gamma*y[1], gamma*y[1]), y0, t)
    I = sol[:, 1]
    return I / I.max() * y_data.max()

print("\n--- Ajustement du modèle SIR ---")
popt_sir, _ = curve_fit(sir_fit_curve, t_data, y_data, p0=[0.3, 0.1, 1000], bounds=([0, 0, 1], [1, 1, 1e6]))
rms_error_sir = np.sqrt(np.mean((y_data - sir_fit_curve(t_data, *popt_sir))**2))
print(f"Erreur RMS SIR : {rms_error_sir:.4f}")


# --- Étape 3 : Visualisation et Analyse ---
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(14, 8))
ax.plot(t_data, y_data, 'k-', label='Données réelles (Italie)', linewidth=2.5)
ax.plot(t_data, y_fit_sr, 'b--', label=f'Modèle Super-Radiant ({N_MODES} modes, RMS: {rms_error_sr:.3f})', linewidth=2.5)
ax.plot(t_data, sir_fit_curve(t_data, *popt_sir), 'r:', label=f'Modèle SIR (RMS: {rms_error_sir:.3f})', linewidth=2.5)
ax.set_title(f'Validation de la Théorie : COVID-19 Vague 1 (Italie) - {N_MODES} Modes', fontsize=16, fontweight='bold')
ax.set_xlabel('Jours depuis le début de la vague', fontsize=12)
ax.set_ylabel('Nombre de décès (normalisé)', fontsize=12)
ax.legend(fontsize=12)
plt.tight_layout()
plt.show()

print("\n--- Analyse Finale ---")
print(f"Performance : Le modèle super-radiant est {rms_error_sir / rms_error_sr:.1f} fois plus précis que le SIR.")
tau_values = [popt_sr_sorted[N_MODES+i] for i in range(N_MODES)]
print(f"Délais (τ) ordonnés : {', '.join([f'{tau:.1f}j' for tau in tau_values])}")
