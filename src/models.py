"""
Modèles épidémiologiques pour l'analyse super-radiante et SIR.
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.integrate import odeint


class SuperRadiantModel:
    """
    Modèle super-radiant multi-modes pour la dynamique épidémique.

    Ce modèle représente les épidémies comme des transitions de phase radiatives
    hors-équilibre, inspiré de la super-radiance en optique quantique.
    """

    def __init__(self, n_modes=4):
        """
        Initialise le modèle super-radiant.

        Args:
            n_modes (int): Nombre de modes sociaux à modéliser
        """
        self.n_modes = n_modes
        self.params = None
        self.covariance = None

    def intensity(self, t, *params):
        """
        Calcule l'intensité super-radiante pour des paramètres donnés.

        Utilise la formule sech² canonique de la super-radiance quantique:
        I(t) = Σ A_k * sech²((t - τ_k) / (2T_k))

        où sech(x) = 1/cosh(x) est la sécante hyperbolique.

        Args:
            t (array): Temps
            *params: Paramètres du modèle (A, tau, T pour chaque mode)

        Returns:
            array: Intensité calculée
        """
        intensity = np.zeros_like(t, dtype=float)
        for i in range(self.n_modes):
            A = params[i*3]
            tau = params[i*3 + 1]
            T = params[i*3 + 2]
            # Formule sech²: A * (1/cosh(x))²
            # où x = (t - tau) / (2T)
            x = (t - tau) / (2.0 * T)
            intensity += A * (1.0 / np.cosh(x))**2
        return intensity

    def fit(self, t_data, y_data, maxfev=30000):
        """
        Ajuste le modèle aux données.

        Args:
            t_data (array): Données temporelles
            y_data (array): Données d'intensité/mortalité
            maxfev (int): Nombre maximum d'évaluations de fonction

        Returns:
            tuple: Paramètres optimaux et erreur RMS
        """
        # Génération dynamique des estimations initiales et des bornes
        initial_guess = []
        bounds_lower = []
        bounds_upper = []

        for i in range(self.n_modes):
            initial_guess.extend([1.0, 10 + i*10, 5 + i*5])
            bounds_lower.extend([0, 0, 1])
            bounds_upper.extend([np.inf, 50 + i*20, 80 + i*20])

        # Ajustement
        self.params, self.covariance = curve_fit(
            self.intensity,
            t_data,
            y_data,
            p0=initial_guess,
            bounds=(bounds_lower, bounds_upper),
            maxfev=maxfev
        )

        # Tri des modes par tau croissant
        self._sort_modes()

        # Calcul de l'erreur RMS
        y_fit = self.predict(t_data)
        rms_error = np.sqrt(np.mean((y_data - y_fit)**2))

        return self.params, rms_error

    def _sort_modes(self):
        """Trie les modes par tau (délai) croissant."""
        modes = []
        for i in range(self.n_modes):
            modes.append({
                'A': self.params[i*3],
                'tau': self.params[i*3 + 1],
                'T': self.params[i*3 + 2]
            })

        modes_sorted = sorted(modes, key=lambda x: x['tau'])

        # Réorganise les paramètres dans format bloc:
        # [A1, A2, ..., An, tau1, tau2, ..., taun, T1, T2, ..., Tn]
        self.params = np.array(
            [mode['A'] for mode in modes_sorted] +
            [mode['tau'] for mode in modes_sorted] +
            [mode['T'] for mode in modes_sorted]
        )

    def _intensity_sorted(self, t):
        """
        Calcule l'intensité avec paramètres triés (format bloc).

        Format: [A1...An, tau1...taun, T1...Tn]
        """
        intensity = np.zeros_like(t, dtype=float)
        for i in range(self.n_modes):
            A = self.params[i]
            tau = self.params[self.n_modes + i]
            T = self.params[2 * self.n_modes + i]
            x = (t - tau) / (2.0 * T)
            intensity += A * (1.0 / np.cosh(x))**2
        return intensity

    def predict(self, t):
        """
        Prédit l'intensité pour des temps donnés.

        Args:
            t (array): Temps

        Returns:
            array: Intensité prédite
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")
        # Utiliser _intensity_sorted car params a été réorganisé par _sort_modes
        return self._intensity_sorted(t)

    def get_mode_parameters(self):
        """
        Retourne les paramètres des modes sous forme structurée.

        Returns:
            list: Liste de dictionnaires contenant A, tau, T pour chaque mode
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        modes = []
        for i in range(self.n_modes):
            modes.append({
                'mode': i + 1,
                'A': self.params[i],
                'tau': self.params[self.n_modes + i],
                'T': self.params[2 * self.n_modes + i]
            })
        return modes

    def get_mode_intensity(self, t, mode_index):
        """
        Retourne l'intensité d'un mode spécifique.

        Args:
            t (array): Temps
            mode_index (int): Index du mode (0 à n_modes-1)

        Returns:
            array: Intensité du mode spécifié
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")
        if mode_index < 0 or mode_index >= self.n_modes:
            raise ValueError(f"mode_index doit être entre 0 et {self.n_modes-1}")

        A = self.params[mode_index]
        tau = self.params[self.n_modes + mode_index]
        T = self.params[2 * self.n_modes + mode_index]
        x = (t - tau) / (2.0 * T)
        return A * (1.0 / np.cosh(x))**2


class SIRModel:
    """
    Modèle SIR classique (Susceptible-Infected-Recovered) pour comparaison.
    """

    def __init__(self, population=60e6):
        """
        Initialise le modèle SIR.

        Args:
            population (float): Taille de la population
        """
        self.N = population
        self.params = None

    def _sir_equations(self, y, t, beta, gamma):
        """
        Équations différentielles du modèle SIR.

        Args:
            y (tuple): (S, I, R) - État actuel
            t (float): Temps
            beta (float): Taux de transmission
            gamma (float): Taux de récupération

        Returns:
            tuple: Dérivées (dS/dt, dI/dt, dR/dt)
        """
        S, I, R = y
        dS = -beta * S * I / self.N
        dI = beta * S * I / self.N - gamma * I
        dR = gamma * I
        return dS, dI, dR

    def _sir_fit_curve(self, t, beta, gamma, I0, y_max):
        """
        Fonction de fitting pour le modèle SIR.

        Args:
            t (array): Temps
            beta (float): Taux de transmission
            gamma (float): Taux de récupération
            I0 (float): Nombre initial d'infectés
            y_max (float): Maximum des données pour normalisation

        Returns:
            array: Nombre d'infectés normalisé
        """
        y0 = (self.N - I0, I0, 0)
        sol = odeint(self._sir_equations, y0, t, args=(beta, gamma))
        I = sol[:, 1]
        return I / I.max() * y_max

    def fit(self, t_data, y_data):
        """
        Ajuste le modèle SIR aux données.

        Args:
            t_data (array): Données temporelles
            y_data (array): Données d'intensité/mortalité

        Returns:
            tuple: Paramètres optimaux et erreur RMS
        """
        y_max = y_data.max()

        def fit_wrapper(t, beta, gamma, I0):
            return self._sir_fit_curve(t, beta, gamma, I0, y_max)

        self.params, _ = curve_fit(
            fit_wrapper,
            t_data,
            y_data,
            p0=[0.3, 0.1, 1000],
            bounds=([0, 0, 1], [1, 1, 1e6])
        )

        # Calcul de l'erreur RMS
        y_fit = self.predict(t_data, y_max)
        rms_error = np.sqrt(np.mean((y_data - y_fit)**2))

        return self.params, rms_error

    def predict(self, t, y_max):
        """
        Prédit le nombre d'infectés pour des temps donnés.

        Args:
            t (array): Temps
            y_max (float): Maximum pour normalisation

        Returns:
            array: Nombre d'infectés prédit
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")
        return self._sir_fit_curve(t, *self.params, y_max)

    def get_parameters(self):
        """
        Retourne les paramètres du modèle.

        Returns:
            dict: Dictionnaire contenant beta, gamma, I0
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        return {
            'beta': self.params[0],
            'gamma': self.params[1],
            'I0': self.params[2],
            'R0': self.params[0] / self.params[1]  # Nombre de reproduction de base
        }
