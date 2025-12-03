"""
Utilitaires pour le téléchargement et le prétraitement des données COVID-19.
"""

import os
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi


class CovidDataLoader:
    """
    Classe pour télécharger et prétraiter les données COVID-19 depuis Kaggle.
    """

    def __init__(self, data_path='covid_data'):
        """
        Initialise le loader.

        Args:
            data_path (str): Chemin où stocker les données téléchargées
        """
        self.data_path = data_path
        self.api = None

    def authenticate(self):
        """Authentifie l'API Kaggle."""
        print("Authentification à l'API Kaggle...")
        self.api = KaggleApi()
        self.api.authenticate()
        print("✅ Authentification réussie.")

    def download_dataset(self, dataset='sudalairajkumar/covid19-daily-reports'):
        """
        Télécharge le dataset COVID-19 depuis Kaggle.

        Args:
            dataset (str): Identifiant du dataset Kaggle

        Returns:
            str: Chemin vers les données téléchargées
        """
        if self.api is None:
            self.authenticate()

        print(f"Téléchargement du dataset '{dataset}'...")
        self.api.dataset_download_files(dataset, path=self.data_path, unzip=True)
        print("✅ Dataset téléchargé et décompressé avec succès.")

        return os.path.join(self.data_path, 'csse_covid_19_daily_reports')

    def load_country_data(self, country='Italy', covid_data_path=None):
        """
        Charge les données pour un pays spécifique.

        Args:
            country (str): Nom du pays
            covid_data_path (str): Chemin vers les données (optionnel)

        Returns:
            pd.Series: Série temporelle des décès
        """
        if covid_data_path is None:
            covid_data_path = self.download_dataset()

        all_files = [
            os.path.join(covid_data_path, f)
            for f in os.listdir(covid_data_path)
            if f.endswith('.csv')
        ]

        country_dfs = []
        for filename in sorted(all_files):
            df = pd.read_csv(filename)

            # Standardiser les noms de colonnes
            df = df.rename(columns={
                'Country_Region': 'Country/Region',
                'Province_State': 'Province/State'
            })

            if 'Country/Region' in df.columns:
                df_country = df[df['Country/Region'] == country]
                if not df_country.empty:
                    date_str = os.path.basename(filename).split('.')[0]
                    df_country['Date'] = pd.to_datetime(date_str, errors='coerce')
                    country_dfs.append(df_country[['Date', 'Deaths', 'Province/State']])

        if not country_dfs:
            raise ValueError(f"Aucune donnée pour '{country}' trouvée.")

        country_all = pd.concat(country_dfs, ignore_index=True)
        deaths_series = country_all.groupby('Date')['Deaths'].sum().sort_index()

        print(f"✅ Données pour '{country}' extraites et agrégées avec succès.")
        return deaths_series

    @staticmethod
    def preprocess_wave(deaths_series, start_date, end_date, window=7, normalize=True):
        """
        Prétraite les données pour une vague spécifique.

        Args:
            deaths_series (pd.Series): Série temporelle des décès
            start_date (str): Date de début (format YYYY-MM-DD)
            end_date (str): Date de fin (format YYYY-MM-DD)
            window (int): Taille de la fenêtre de lissage
            normalize (bool): Normaliser par la première valeur

        Returns:
            tuple: (t_data, y_data, dates) - Temps, données, et dates
        """
        # Extraction de la période
        wave_data = deaths_series[start_date:end_date]

        # Lissage (moyenne mobile)
        wave_smooth = wave_data.rolling(window=window, center=True).mean().dropna()

        # Normalisation
        if normalize:
            wave_norm = wave_smooth / wave_smooth.iloc[0]
        else:
            wave_norm = wave_smooth

        # Création des arrays pour l'analyse
        t_data = range(len(wave_norm))
        y_data = wave_norm.values

        print(f"\nPériode analysée : {wave_norm.index.min().date()} au {wave_norm.index.max().date()}")
        print(f"Nombre de jours : {len(wave_norm)}")

        return t_data, y_data, wave_norm.index


def load_italy_wave1(data_path='covid_data'):
    """
    Fonction de convénience pour charger la première vague italienne.

    Args:
        data_path (str): Chemin des données

    Returns:
        tuple: (t_data, y_data, dates) - Données prétraitées
    """
    loader = CovidDataLoader(data_path=data_path)

    try:
        # Charger les données
        italy_deaths = loader.load_country_data(country='Italy')

        # Prétraiter pour la première vague
        t_data, y_data, dates = loader.preprocess_wave(
            italy_deaths,
            start_date='2020-02-20',
            end_date='2020-06-30',
            window=7,
            normalize=True
        )

        return t_data, y_data, dates

    except Exception as e:
        print(f"❌ Erreur lors du traitement des données: {e}")
        raise


def load_country_wave(country, start_date, end_date, data_path='covid_data', window=7):
    """
    Fonction générique pour charger une vague pour n'importe quel pays.

    Args:
        country (str): Nom du pays
        start_date (str): Date de début
        end_date (str): Date de fin
        data_path (str): Chemin des données
        window (int): Fenêtre de lissage

    Returns:
        tuple: (t_data, y_data, dates) - Données prétraitées
    """
    loader = CovidDataLoader(data_path=data_path)

    try:
        # Charger les données
        deaths = loader.load_country_data(country=country)

        # Prétraiter
        t_data, y_data, dates = loader.preprocess_wave(
            deaths,
            start_date=start_date,
            end_date=end_date,
            window=window,
            normalize=True
        )

        return t_data, y_data, dates

    except Exception as e:
        print(f"❌ Erreur lors du traitement des données pour {country}: {e}")
        raise
