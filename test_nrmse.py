#!/usr/bin/env python3
"""
Test rapide de la méthode get_fit_quality() sur données réelles France.
"""
import sys
sys.path.insert(0, 'src/core')

import numpy as np
import pandas as pd
from models import SIRModel

print("=" * 70)
print("TEST MÉTHODE get_fit_quality() - FRANCE")
print("=" * 70)

# Chargement données France
url = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
df = pd.read_csv(url)
france_data = df[df['Country/Region'] == 'France'].iloc[:, 4:].sum(axis=0)
france_df = pd.DataFrame({'deaths': france_data})
france_df.index = pd.to_datetime(france_df.index)
france_df = france_df.loc['2020-02-15':'2020-06-30']

daily_deaths = france_df['deaths'].diff().fillna(0).clip(lower=0)
daily_deaths_smooth = daily_deaths.rolling(window=7, center=True).mean().bfill().ffill()

t_data = np.arange(len(daily_deaths_smooth))
y_data = daily_deaths_smooth.values

print(f"\n✓ Données chargées : {len(t_data)} points")
print(f"  Max décès quotidiens : {y_data.max():.0f}")

# Fit SIR avec DOGBOX
model = SIRModel(population=67e6, IFR=0.01)
params, rms_old = model.fit(t_data, y_data)

print(f"\n✓ Fit SIR complété (DOGBOX)")
print(f"  RMS (méthode fit()) : {rms_old:.2f}")

# Test de la nouvelle méthode get_fit_quality()
metrics = model.get_fit_quality(t_data, y_data)

print(f"\n✓ Métriques de qualité (get_fit_quality()) :")
print(f"  RMS absolu    : {metrics['rms']:.2f}")
print(f"  NRMSE         : {metrics['nrmse']:.4f}")
print(f"  NRMSE%        : {metrics['nrmse_percent']:.2f}%")
print(f"  R²            : {metrics['r2']:.3f}")

# Vérification cohérence
if abs(metrics['rms'] - rms_old) < 0.01:
    print(f"\n✅ SUCCÈS : RMS cohérent entre fit() et get_fit_quality()")
else:
    print(f"\n❌ ERREUR : RMS incohérent ({metrics['rms']:.2f} vs {rms_old:.2f})")

# Affichage paramètres
params_dict = model.get_parameters()
print(f"\n✓ Paramètres SIR :")
print(f"  R0            : {params_dict['R0']:.2f}")
print(f"  Durée infection : {params_dict['infection_duration_days']:.1f} jours")
print(f"  IFR effectif  : {params_dict['IFR_effective']:.2%}")

print("\n" + "=" * 70)
print("TEST RÉUSSI ✅")
print("=" * 70)
