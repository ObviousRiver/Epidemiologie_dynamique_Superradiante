"""
Modèle CWT (Continuous Wavelet Transform) pour l'analyse épidémiologique.

Ce modèle utilise la Transformée en Ondelettes Continue pour identifier les modes
significatifs dans un signal épidémiologique de manière non-paramétrique, puis
reconstruit le signal en sommant des fonctions sech² correspondant à ces modes.

Contrairement au SuperRadiantModel qui impose a priori un nombre de modes et
ajuste tous les paramètres simultanément via curve_fit, le CWTModel "découvre"
les modes directement depuis les données via l'analyse temps-échelle.
"""

import numpy as np
import pywt  # Bibliothèque pour les transformations en ondelettes
from scipy.signal import find_peaks  # Pour trouver les pics dans le scalogramme


class CWTModel:
    """
    Modèle basé sur la Transformée en Ondelettes Continue (CWT).

    Ce modèle analyse le signal via une CWT pour identifier les modes les plus
    significatifs, puis reconstruit le signal en sommant des fonctions sech²
    correspondant à ces modes. C'est une approche non-paramétrique pour
    décomposer le signal.

    L'idée est de laisser la CWT "découvrir" les modes, plutôt que de les
    imposer via un fit global comme dans SuperRadiantModel.
    """

    def __init__(self, n_modes=4, wavelet='morl', scales=None, threshold_factor=1.2, min_time_separation=8):
        """
        Initialise le modèle CWT (VERSION AMÉLIORÉE).
    def __init__(self, n_modes=4, wavelet='morl', scales=None, threshold_factor=2.0):
        """
        Initialise le modèle CWT.

        Args:
            n_modes (int): Nombre de modes à extraire du scalogramme.
            wavelet (str): Nom de l'ondelette à utiliser ('morl' est une bonne
                           alternative à sech, 'mexh' est une autre option).
            scales (array, optional): Les échelles à analyser. Si None, des
                                      échelles sont générées automatiquement.
            threshold_factor (float): Facteur pour le seuil de détection des pics.
                                     Réduit à 1.2 pour détecter plus de modes.
            min_time_separation (int): Séparation temporelle minimale entre modes (jours).
                                      Force les modes à être distincts temporellement.
                                     Un facteur plus élevé signifie moins de modes.
        """
        self.n_modes = n_modes
        self.wavelet = wavelet
        self.scales = scales
        self.threshold_factor = threshold_factor
        self.min_time_separation = min_time_separation
        self.modes = None  # Stockera les paramètres des modes identifiés
        self.rms_error = None
        self.coefficients = None  # Scalogramme CWT
        self.frequencies = None  # Fréquences correspondantes

    def _sech2_function(self, t, A, tau, T):
        """
        Fonction de base sech² utilisée pour la reconstruction.

        Args:
            t (array): Temps
            A (float): Amplitude
            tau (float): Temps du pic
            T (float): Largeur temporelle

        Returns:
            array: Valeurs de la fonction sech²
        """
        x = (t - tau) / (2.0 * T)
        # Éviter overflow avec np.clip
        x_clipped = np.clip(x, -50, 50)
        return A * (1.0 / np.cosh(x_clipped))**2

    def fit(self, t_data, y_data):
        """
        Analyse le signal avec la CWT et identifie les modes les plus significatifs.

        Args:
            t_data (array): Données temporelles (en jours)
            y_data (array): Données d'intensité (décès quotidiens)

        Returns:
            float: Erreur RMS entre le signal original et la reconstruction.
        """
        # 1. Préparation des données
        dt = np.mean(np.diff(t_data))  # Période d'échantillonnage moyenne
        y_data = np.asarray(y_data, dtype=float)

        # 2. Génération des échelles si non fournies
        if self.scales is None:
            # AMÉLIORATION: Échelles calibrées pour T typiques de 2-30 jours
            # Résolution plus fine dans la zone critique
            frequencies = np.linspace(1/60, 1/2, 120)  # Fréquences en 1/jour (périodes 2-60j)
            # Génération d'échelles pour couvrir des périodes de 3 à 80 jours
            # C'est un choix heuristique, adaptable.
            # On utilise plus de points pour une meilleure résolution
            frequencies = np.linspace(1/80, 1/3, 100)  # Fréquences en 1/jour
            self.scales = pywt.scale2frequency(self.wavelet, 1.0) / (frequencies * dt)

        # 3. Calcul de la CWT
        self.coefficients, self.frequencies = pywt.cwt(
            y_data,
            self.scales,
            self.wavelet,
            sampling_period=dt
        )

        # 4. AMÉLIORATION: Identification des modes avec séparation temporelle forcée
        abs_coeffs = np.abs(self.coefficients)

        # Calculer le seuil dynamiquement (réduit pour détecter plus de modes)
        threshold = np.mean(abs_coeffs) + self.threshold_factor * np.std(abs_coeffs)

        # Méthode améliorée: Sommer l'énergie sur toutes les échelles pour chaque temps
        # Cela donne un profil temporel robuste indépendant de l'échelle
        energy_profile = np.sum(abs_coeffs, axis=0)  # Somme sur les échelles

        # Trouver les pics temporels dans le profil d'énergie
        # distance=min_time_separation force les pics à être séparés
        time_peaks, properties = find_peaks(
            energy_profile,
            distance=self.min_time_separation,
            prominence=np.std(energy_profile) * 0.3
        )

        # Pour chaque pic temporel, trouver la meilleure échelle
        peak_candidates = []
        for time_idx in time_peaks:
            # Trouver l'échelle qui maximise l'amplitude à ce temps
            scale_idx = np.argmax(abs_coeffs[:, time_idx])
            amplitude = abs_coeffs[scale_idx, time_idx]

            # Filtrer par seuil
            if amplitude > threshold:
                peak_candidates.append({
                    'scale_idx': scale_idx,
                    'time_idx': time_idx,
                    'amplitude': amplitude,
                    'energy': energy_profile[time_idx]
                })

        # Trier par énergie totale (plus robuste que l'amplitude seule)
        peak_candidates = sorted(peak_candidates, key=lambda x: x['energy'], reverse=True)

        # Prendre les n_modes premiers
        # 4. Identification des modes significatifs
        # On cherche les n_modes pics les plus élevés dans le scalogramme
        # Stratégie améliorée: chercher les pics dans chaque échelle temporelle
        abs_coeffs = np.abs(self.coefficients)

        # Calculer le seuil dynamiquement
        threshold = np.mean(abs_coeffs) + self.threshold_factor * np.std(abs_coeffs)

        # Trouver tous les pics qui dépassent le seuil
        peak_candidates = []
        for scale_idx in range(abs_coeffs.shape[0]):
            # Trouver les pics dans cette échelle
            peaks, properties = find_peaks(
                abs_coeffs[scale_idx, :],
                height=threshold,
                prominence=np.std(abs_coeffs[scale_idx, :]) * 0.5
            )

            for peak_time_idx in peaks:
                peak_candidates.append({
                    'scale_idx': scale_idx,
                    'time_idx': peak_time_idx,
                    'amplitude': abs_coeffs[scale_idx, peak_time_idx]
                })

        # Trier par amplitude décroissante et prendre les n_modes premiers
        peak_candidates = sorted(peak_candidates, key=lambda x: x['amplitude'], reverse=True)
        selected_peaks = peak_candidates[:self.n_modes]

        # 5. Stockage des paramètres des modes
        self.modes = []
        for peak in selected_peaks:
            scale_idx = peak['scale_idx']
            time_idx = peak['time_idx']

            # AMÉLIORATION: Amplitude calibrée (moyenne locale)
            # Prendre la moyenne sur une fenêtre pour être plus robuste
            window = 2
            t_start = max(0, time_idx - window)
            t_end = min(len(t_data), time_idx + window + 1)
            A = np.mean(abs_coeffs[scale_idx, t_start:t_end])
            # Amplitude du mode
            A = abs_coeffs[scale_idx, time_idx]

            # Temps du pic
            tau = t_data[time_idx]

            # AMÉLIORATION: Largeur temporelle calibrée
            # Correspondance scale CWT ↔ T sech²
            # Pour Morlet: scale ≈ période ≈ 4*T (empirique)
            scale = self.scales[scale_idx]
            period = 1 / (self.frequencies[scale_idx] + 1e-10)  # Période en jours
            T = period / 4.0  # Calibration empirique Morlet → sech²
            # Largeur temporelle: liée à l'échelle
            # L'échelle CWT correspond approximativement à la largeur temporelle
            # On utilise un facteur de correction pour correspondre à la définition de T dans sech²
            scale = self.scales[scale_idx]
            T = scale * dt / 2.0  # Facteur 2 pour correspondre à la définition de sech²

            self.modes.append({
                'A': A,
                'tau': tau,
                'T': T,
                'scale_idx': scale_idx,
                'time_idx': time_idx
            })

        # Trier les modes par temps de pic (tau) pour cohérence
        self.modes = sorted(self.modes, key=lambda x: x['tau'])

        # 6. Calcul de l'erreur RMS de la reconstruction
        if self.modes:
            y_fit = self.predict(t_data)
            residuals = y_data - y_fit
            self.rms_error = np.sqrt(np.mean(residuals**2))
        else:
            self.rms_error = np.inf

        return self.rms_error

    def predict(self, t):
        """
        Reconstruit le signal en sommant les modes identifiés par la CWT.

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
            tuple: (coefficients, scales, frequencies)
                - coefficients: array 2D des coefficients CWT
                - scales: array des échelles utilisées
                - frequencies: array des fréquences correspondantes
        """
        if self.coefficients is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        return self.coefficients, self.scales, self.frequencies

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
        Compare les modes CWT avec les modes d'un SuperRadiantModel.

        Args:
            sr_model: Instance de SuperRadiantModel déjà ajusté

        Returns:
            dict: Statistiques de comparaison
        """
        if self.modes is None:
            raise ValueError("CWTModel doit être ajusté avant comparaison")

        sr_params = sr_model.get_mode_parameters()

        # Comparer nombre de modes
        comparison = {
            'n_modes_cwt': len(self.modes),
            'n_modes_sr': len(sr_params),
            'mode_comparison': []
        }

        # Comparer chaque mode (par ordre temporel)
        for i, (cwt_mode, sr_mode) in enumerate(zip(self.modes, sr_params)):
            mode_comp = {
                'mode_index': i,
                'cwt_tau': cwt_mode['tau'],
                'sr_tau': sr_mode['tau'],
                'delta_tau': cwt_mode['tau'] - sr_mode['tau'],
                'cwt_T': cwt_mode['T'],
                'sr_T': sr_mode['T'],
                'delta_T': cwt_mode['T'] - sr_mode['T'],
                'cwt_A': cwt_mode['A'],
                'sr_A': sr_mode['A'],
                'ratio_A': cwt_mode['A'] / sr_mode['A'] if sr_mode['A'] != 0 else np.inf
            }
            comparison['mode_comparison'].append(mode_comp)

        return comparison
