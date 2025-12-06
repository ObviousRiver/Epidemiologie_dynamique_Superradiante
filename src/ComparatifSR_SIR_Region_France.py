import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.integrate import odeint
import requests
import io

# --- CONFIGURATION ---
URL_DATA_GOUV = "https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7"
REGIONS_CODES = {
    "Grand Est": ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
    "Île-de-France": ['75', '77', '78', '91', '92', '93', '94', '95'],
    "Nouvelle-Aquitaine": ['16', '17', '19', '23', '24', '33', '40', '47', '64', '79', '86', '87'],
    "Auvergne-Rhône-Alpes": ['01', '03', '07', '15', '26', '38', '42', '43', '63', '69', '73', '74']
}
POPULATIONS = {
    "Grand Est": 5.5e6, "Île-de-France": 12.2e6, 
    "Nouvelle-Aquitaine": 6.0e6, "Auvergne-Rhône-Alpes": 8.0e6
}

def load_french_data():
    print(f"Téléchargement des données officielles depuis {URL_DATA_GOUV}...")
    try:
        s = requests.get(URL_DATA_GOUV).content
        df = pd.read_csv(io.StringIO(s.decode('utf-8')), sep=';')
    except Exception as e:
        print("ERREUR CRITIQUE : Impossible de télécharger les données.")
        print(f"Détail : {e}")
        return None

    # Nettoyage : On garde sexe=0 (tous), et on groupe par jour/dep
    df = df[df['sexe'] == 0]
    df['jour'] = pd.to_datetime(df['jour'])
    return df

def get_region_curve(df, dep_list):
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
    return A * (1.0 / np.cosh((t - tau) / (2.0 * T)))**2

def fit_sr_model(t, y):
    # Guess initial intelligent
    p0 = [max(y), t[np.argmax(y)], 10.0]
    try:
        popt, _ = curve_fit(model_sr, t, y, p0=p0, maxfev=10000)
        return popt
    except:
        return None

def model_sir(y, t, N, beta, gamma):
    S, I, R = y
    dSdt = -beta * S * I / N
    dIdt = beta * S * I / N - gamma * I
    dRdt = gamma * I
    return dSdt, dIdt, dRdt

def fit_sir_model(t, y, population):
    # On approxime que les décès suivent la courbe I(t) avec un facteur d'échelle et un délai
    # Pour simplifier, on fit directement la forme de I(t) sur les décès
    def fit_func(t, beta, gamma, scale, shift):
        I0 = 100
        t_sim = np.arange(len(t) + int(shift) + 10)
        ret = odeint(model_sir, [population-I0, I0, 0], t_sim, args=(population, beta, gamma))
        I = ret[:, 1]
        # Gestion du décalage temporel (shift)
        start_idx = int(shift)
        if start_idx < 0: start_idx = 0
        I_shifted = I[start_idx : start_idx + len(t)]
        if len(I_shifted) < len(t):
            I_shifted = np.pad(I_shifted, (0, len(t)-len(I_shifted)))
        return I_shifted * scale

    try:
        # Bounds: beta [0,2], gamma [0,1], scale [0, inf], shift [0, 100]
        popt, _ = curve_fit(fit_func, t, y, p0=[0.3, 0.1, 0.05, 10], 
                           bounds=([0,0,0,0], [5, 1, 1, 100]))
        return popt
    except:
        return None

# --- MAIN PROCESS ---
def main():
    df_global = load_french_data()
    if df_global is None: return

    fig, axes = plt.subplots(len(REGIONS_CODES), 2, figsize=(14, 4*len(REGIONS_CODES)))
    plt.subplots_adjust(hspace=0.4)
    
    for idx, (reg_name, deps) in enumerate(REGIONS_CODES.items()):
        print(f"Traitement région : {reg_name}...")
        
        # 1. Extraction Données
        series = get_region_curve(df_global, deps)
        t = np.arange(len(series))
        y = series.values
        
        if len(y) == 0: continue
        
        # 2. Fits
        # SR
        popt_sr = fit_sr_model(t, y)
        y_fit_sr = model_sr(t, *popt_sr) if popt_sr is not None else np.zeros_like(y)
        
        # SIR
        popt_sir = fit_sir_model(t, y, POPULATIONS.get(reg_name, 5e6))
        # Recalcul de la courbe SIR ajustée (c'est un peu tricky car la func est locale)
        # On simplifie pour l'affichage : si fit échoue, ligne plate
        if popt_sir is not None:
            # On réutilise la logique interne de fit_func pour générer la courbe
            beta, gamma, scale, shift = popt_sir
            I0=100
            t_sim = np.arange(len(t) + int(shift) + 10)
            ret = odeint(model_sir, [POPULATIONS[reg_name]-I0, I0, 0], t_sim, args=(POPULATIONS[reg_name], beta, gamma))
            I_full = ret[:, 1] * scale
            start = int(shift)
            y_fit_sir = I_full[start:start+len(t)]
            if len(y_fit_sir) < len(t): y_fit_sir = np.pad(y_fit_sir, (0, len(t)-len(y_fit_sir)))
        else:
            y_fit_sir = np.zeros_like(y)

        # RMS
        rms_sr = np.sqrt(np.mean((y - y_fit_sr)**2))
        rms_sir = np.sqrt(np.mean((y - y_fit_sir)**2))
        
        # 3. Variance Glissante
        rolling_var = series.rolling(14, center=True).var().fillna(0)
        # Normalisation pour affichage
        y_norm = y / max(y)
        var_norm = rolling_var / max(rolling_var)
        
        delay = np.argmax(y) - np.argmax(rolling_var)

        # 4. Plotting
        # Col 1 : Modèles
        ax1 = axes[idx, 0]
        ax1.bar(t, y, color='lightgray', label='Décès Obs.')
        ax1.plot(t, y_fit_sr, 'b-', lw=2, label=f'SR (RMS={rms_sr:.1f})')
        ax1.plot(t, y_fit_sir, 'r--', lw=2, label=f'SIR (RMS={rms_sir:.1f})')
        ax1.set_title(f"{reg_name} : Modèles")
        ax1.legend()
        
        # Col 2 : Susceptibilité
        ax2 = axes[idx, 1]
        ax2.plot(t, y_norm, 'k-', alpha=0.3, label='Épidémie')
        ax2.plot(t, var_norm, 'purple', lw=2, label='Variance (Susceptibilité)')
        ax2.axvline(np.argmax(y), color='k', ls=':')
        ax2.axvline(np.argmax(rolling_var), color='purple', ls=':')
        ax2.set_title(f"Précurseur Variance (Délai = {delay}j)")
        ax2.legend()

    plt.savefig("analyse_regionale_france_reelle.png")
    print("Terminé. Graphique sauvegardé : analyse_regionale_france_reelle.png")

if __name__ == "__main__":
    main()
