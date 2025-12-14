"""
Modèle CWT avec Ondelette Personnalisée de Type Soliton.

Cette approche utilise une ondelette dont la forme est spécifiquement adaptée
aux structures recherchées (sech²), contrairement aux ondelettes standards
(Morlet, Mexican Hat) qui sont mal adaptées aux solitons.

L'ondelette utilisée est la DÉRIVÉE de la fonction sech :
    ψ(x) = sech(x) × tanh(x)

Cette fonction a :
- Moyenne nulle (condition nécessaire pour une ondelette)
- Forme adaptée aux fronts de solitons sech²
- Corrélation maximale avec les structures recherchées

AVANTAGE CLEF : La corrélation CWT sera forte car l'ondelette "ressemble"
aux structures du signal, contrairement à Morlet qui est oscillante.
"""

import numpy as np
from scipy.signal import find_peaks, correlate


class SolitonCWTModel:
    """
    Modèle basé sur une Transformée en Ondelettes Continue (CWT) avec une ondelette
    personnalisée de type soliton (dérivée de sech).

    Cette approche utilise une ondelette dont la forme est similaire aux
    structures recherchées (sech²), ce qui devrait améliorer drastiquement
    la détection des modes par rapport à une ondelette standard comme Morlet.
    """

    def __init__(self, n_modes=4, scale_range=(2, 40), n_scales=80, threshold_factor=0.8, min_time_separation=8):
        """
        Initialise le modèle CWT avec une ondelette de type soliton.

        Args:
            n_modes (int): Nombre de modes à extraire du scalogramme.
            scale_range (tuple): Plage des échelles à analyser (en jours, correspond à T).
            n_scales (int): Nombre de points d'échelle à tester.
            threshold_factor (float): Facteur pour le seuil de détection des pics.
            min_time_separation (int): Séparation temporelle minimale entre modes (jours).
        """
        self.n_modes = n_modes
        self.scale_range = scale_range
        self.n_scales = n_scales
        self.threshold_factor = threshold_factor
        self.min_time_separation = min_time_separation
        self.modes = None
        self.rms_error = None
        self.scalogram = None  # Stockera le scalogramme complet
        self.scales = None  # Stockera les échelles utilisées

    def _sech(self, x):
        """
        Fonction sécante hyperbolique.
        sech(x) = 1/cosh(x)
        """
        return 1.0 / np.cosh(np.clip(x, -50, 50))  # Clip pour éviter overflow

    def _soliton_wavelet(self, x):
        """
        Ondelette personnalisée : sech² avec moyenne nulle.

        ψ(x) = sech²(x) - mean(sech²(x))

        Cette ondelette a :
        - Forme identique aux structures sech² recherchées
        - Moyenne nulle (condition pour ondelette, obtenue par soustraction)
        - Corrélation maximale avec les pics sech²

        Note: La dérivée de sech créait des annulations destructives. On utilise
        maintenant sech² directement, centré à moyenne nulle.

        Returns:
            array: Valeurs de l'ondelette
        """
        x_clipped = np.clip(x, -50, 50)
        sech2 = (self._sech(x_clipped))**2
        # Soustraire la moyenne pour obtenir une ondelette de moyenne nulle
        return sech2 - np.mean(sech2)

    def _sech2_function(self, t, A, tau, T):
        """
        Fonction de base sech² pour la reconstruction.

        Args:
            t (array): Temps
            A (float): Amplitude
            tau (float): Temps du pic
            T (float): Largeur temporelle

        Returns:
            array: Valeurs de la fonction sech²
        """
        x = (t - tau) / (2.0 * T)
        return A * (self._sech(x))**2

    def fit(self, t_data, y_data):
        """
        Analyse le signal avec une CWT personnalisée et identifie les modes.

        Méthode :
        1. Calcul du scalogramme en corrélant le signal avec l'ondelette soliton
           à différentes échelles
        2. Détection des pics dans le scalogramme avec séparation temporelle forcée
        3. Extraction des paramètres (A, τ, T) pour chaque mode
        4. Reconstruction du signal et calcul de l'erreur RMS

        Args:
            t_data (array): Données temporelles (en jours)
            y_data (array): Données d'intensité (nouveaux cas/décès quotidiens)

        Returns:
            float: Erreur RMS entre le signal original et la reconstruction.
        """
        # 1. Préparation des données
        y_data = np.asarray(y_data, dtype=float)
        n_points = len(t_data)
        dt = np.mean(np.diff(t_data))  # Période d'échantillonnage moyenne

        # 2. Génération des échelles (correspondent approximativement à T)
        self.scales = np.linspace(self.scale_range[0], self.scale_range[1], self.n_scales)

        # 3. Calcul de la CWT MANUELLEMENT (corrélation)
        # Le scalogramme stockera les résultats de la corrélation
        self.scalogram = np.zeros((len(self.scales), n_points))

        # Créer une fenêtre d'ondelette centrée (longueur adaptative)
        max_wavelet_width = int(self.scale_range[1] * 10)  # 10× l'échelle max

        for i, scale in enumerate(self.scales):
            # Créer l'ondelette à l'échelle actuelle
            # x va de -max_wavelet_width à +max_wavelet_width
            x_wavelet = np.arange(-max_wavelet_width, max_wavelet_width) * dt / scale
            wavelet_values = self._soliton_wavelet(x_wavelet)

            # Normalisation : Énergie unitaire (L2 norm = 1)
            # Cela garantit que la corrélation est proportionnelle à l'amplitude du signal
            wavelet_norm = np.linalg.norm(wavelet_values)
            if wavelet_norm > 0:
                wavelet_values = wavelet_values / wavelet_norm

            # Calculer la corrélation (convolution avec ondelette retournée)
            # mode='same' pour garder la même taille que le signal
            # Utiliser scipy.signal.correlate pour gérer correctement les tailles différentes
            correlation = correlate(y_data, wavelet_values, mode='same')
            self.scalogram[i, :] = np.abs(correlation)

        # 4. NOUVELLE APPROCHE : Détection multi-échelle puis fusion
        # Détecter les maxima dans différentes bandes d'échelle séparément
        # pour éviter que le pic principal masque les modes secondaires

        peak_candidates = []

        # Définir des bandes d'échelle à analyser séparément
        n_scales_total = len(self.scales)
        scale_bands = [
            (0, n_scales_total//3, "petites"),           # Échelles 2-15j
            (n_scales_total//3, 2*n_scales_total//3, "moyennes"),  # Échelles 15-27j
            (2*n_scales_total//3, n_scales_total, "grandes")       # Échelles 27-40j
        ]

        for s_start, s_end, band_name in scale_bands:
            band_scalogram = self.scalogram[s_start:s_end, :]

            # Pour chaque bande, trouver les maxima temporels
            # Prendre le max sur les échelles pour avoir un profil 1D
            band_profile = np.max(band_scalogram, axis=0)

            # Détecter les pics avec séparation minimale
            time_peaks, properties = find_peaks(
                band_profile,
                distance=self.min_time_separation,
                prominence=np.std(band_profile) * 0.5  # Seuil adaptatif par bande
            )

            # Pour chaque pic temporel, trouver l'échelle optimale dans la bande
            for time_idx in time_peaks:
                # Trouver l'échelle qui maximise dans cette bande
                scale_idx_in_band = np.argmax(band_scalogram[:, time_idx])
                scale_idx = s_start + scale_idx_in_band
                amplitude = self.scalogram[scale_idx, time_idx]

                peak_candidates.append({
                    'scale_idx': scale_idx,
                    'time_idx': time_idx,
                    'amplitude': amplitude,
                    'scale': self.scales[scale_idx],
                    'band': band_name
                })

        # Si on n'a pas trouvé assez de pics, ajouter le maximum global
        if len(peak_candidates) < self.n_modes:
            max_idx = np.unravel_index(np.argmax(self.scalogram), self.scalogram.shape)
            max_already_found = any(
                p['scale_idx'] == max_idx[0] and p['time_idx'] == max_idx[1]
                for p in peak_candidates
            )
            if not max_already_found:
                peak_candidates.append({
                    'scale_idx': max_idx[0],
                    'time_idx': max_idx[1],
                    'amplitude': self.scalogram[max_idx],
                    'scale': self.scales[max_idx[0]],
                    'band': 'global_max'
                })

        # Fusionner les pics trop proches temporellement (garder le plus fort)
        def merge_close_peaks(candidates, min_separation):
            if len(candidates) == 0:
                return []

            # Trier par temps
            sorted_cand = sorted(candidates, key=lambda x: x['time_idx'])
            merged = [sorted_cand[0]]

            for cand in sorted_cand[1:]:
                # Vérifier si trop proche du dernier pic accepté
                if cand['time_idx'] - merged[-1]['time_idx'] < min_separation:
                    # Garder le plus fort
                    if cand['amplitude'] > merged[-1]['amplitude']:
                        merged[-1] = cand
                else:
                    merged.append(cand)

            return merged

        peak_candidates = merge_close_peaks(peak_candidates, self.min_time_separation)

        # Trier par amplitude décroissante
        peak_candidates = sorted(peak_candidates, key=lambda x: x['amplitude'], reverse=True)

        # Prendre les n_modes premiers
        selected_peaks = peak_candidates[:self.n_modes]

        # 7. Extraction des paramètres des modes
        self.modes = []
        for peak in selected_peaks:
            scale_idx = peak['scale_idx']
            time_idx = peak['time_idx']

            # Amplitude depuis le scalogramme
            # Avec normalisation L2, la corrélation est proportionnelle à l'amplitude
            A_raw = self.scalogram[scale_idx, time_idx]

            # Calibration empirique : la corrélation avec dérivée de sech
            # donne une amplitude environ 20× trop grande (intégrale sur fenêtre)
            # Facteur ajusté empiriquement pour correspondre aux amplitudes réelles
            A = A_raw / 20.0

            # Temps du pic
            tau = t_data[time_idx]

            # L'échelle CWT correspond directement à T (largeur du soliton)
            T = self.scales[scale_idx]

            self.modes.append({
                'A': A,
                'tau': tau,
                'T': T,
                'scale_idx': scale_idx,
                'time_idx': time_idx,
                'correlation_strength': A_raw
            })

        # Trier les modes par temps de pic (tau) pour cohérence
        self.modes = sorted(self.modes, key=lambda x: x['tau'])

        # 8. Calcul de l'erreur RMS de la reconstruction
        if self.modes:
            y_fit = self.predict(t_data)
            residuals = y_data - y_fit
            self.rms_error = np.sqrt(np.mean(residuals**2))
        else:
            self.rms_error = np.inf

        return self.rms_error

    def predict(self, t):
        """
        Reconstruit le signal en sommant les modes identifiés.

        Args:
            t (array): Temps (en jours)

        Returns:
            array: Signal reconstruit
        """
        if self.modes is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        t = np.asarray(t, dtype=float)
        intensity = np.zeros_like(t, dtype=float)

        for mode in self.modes:
            intensity += self._sech2_function(t, mode['A'], mode['tau'], mode['T'])

        return intensity

    def get_mode_parameters(self):
        """
        Retourne les paramètres des modes sous forme structurée.

        Returns:
            list: Liste de dictionnaires contenant A, tau, T pour chaque mode
        """
        if self.modes is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")
        return self.modes

    def get_mode_intensity(self, t, mode_index):
        """
        Retourne l'intensité d'un mode spécifique.

        Args:
            t (array): Temps (en jours)
            mode_index (int): Index du mode (0 à n_modes-1)

        Returns:
            array: Intensité du mode spécifié
        """
        if self.modes is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")
        if mode_index < 0 or mode_index >= len(self.modes):
            raise ValueError(f"mode_index doit être entre 0 et {len(self.modes)-1}")

        mode = self.modes[mode_index]
        return self._sech2_function(t, mode['A'], mode['tau'], mode['T'])

    def get_scalogram(self):
        """
        Retourne le scalogramme CWT (coefficients temps-échelle).

        Returns:
            tuple: (scalogram, scales, t_data)
                - scalogram: array 2D des corrélations
                - scales: array des échelles utilisées
        """
        if self.scalogram is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        return self.scalogram, self.scales

    def get_fit_quality(self, t_data, y_data):
        """
        Calcule les métriques de qualité du fit.

        Args:
            t_data (array): Données temporelles
            y_data (array): Données observées

        Returns:
            dict: Dictionnaire contenant rms, nrmse, r2
        """
        y_fit = self.predict(t_data)
        residuals = y_data - y_fit

        rms = np.sqrt(np.mean(residuals**2))
        nrmse = (rms / np.mean(y_data)) * 100

        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y_data - np.mean(y_data))**2)
        r2 = 1 - (ss_res / ss_tot)

        return {
            'rms': rms,
            'nrmse': nrmse,
            'r2': r2
        }

    def compare_with_sr_modes(self, sr_model):
        """
        Compare les modes SolitonCWT avec les modes d'un SuperRadiantModel.

        Args:
            sr_model: Instance de SuperRadiantModel déjà ajusté

        Returns:
            dict: Statistiques de comparaison
        """
        if self.modes is None:
            raise ValueError("SolitonCWTModel doit être ajusté avant comparaison")

        sr_params = sr_model.get_mode_parameters()

        # Comparer nombre de modes
        comparison = {
            'n_modes_soliton': len(self.modes),
            'n_modes_sr': len(sr_params),
            'mode_comparison': []
        }

        # Comparer chaque mode (par ordre temporel)
        for i, (soliton_mode, sr_mode) in enumerate(zip(self.modes, sr_params)):
            mode_comp = {
                'mode_index': i,
                'soliton_tau': soliton_mode['tau'],
                'sr_tau': sr_mode['tau'],
                'delta_tau': soliton_mode['tau'] - sr_mode['tau'],
                'soliton_T': soliton_mode['T'],
                'sr_T': sr_mode['T'],
                'delta_T': soliton_mode['T'] - sr_mode['T'],
                'soliton_A': soliton_mode['A'],
                'sr_A': sr_mode['A'],
                'ratio_A': soliton_mode['A'] / sr_mode['A'] if sr_mode['A'] != 0 else np.inf,
                'correlation_strength': soliton_mode['correlation_strength']
            }
            comparison['mode_comparison'].append(mode_comp)

        return comparison
