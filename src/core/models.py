"""
Modèles épidémiologiques pour l'analyse super-radiante et SIR.

VERSION CONSOLIDÉE - Corrections méthodologiques :
- SIR : IFR explicite pour modéliser les décès
- Échelle temporelle rigoureuse (jours réels, pas indices)
- Documentation des hypothèses et limites
"""

import numpy as np
from scipy.optimize import curve_fit
from scipy.integrate import odeint


class SuperRadiantModel:
    """
    Modèle super-radiant multi-modes pour la dynamique épidémique.

    Ce modèle représente les épidémies comme des transitions de phase radiatives
    hors-équilibre, inspiré de la super-radiance en optique quantique.

    Formulation théorique :
    I(t) = Σ_k A_k * sech²((t - τ_k) / (2T_k))

    où :
    - A_k : Amplitude du mode k (nombre d'individus dans le mode cohérent)
    - τ_k : Temps d'allumage du mode k (pic de super-radiance)
    - T_k : Temps de cohérence (durée de synchronisation)

    Référence : Dicke superradiance et modèle d'Ising social
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
            t (array): Temps (en unités réelles, ex: jours)
            *params: Paramètres du modèle (A, tau, T pour chaque mode)

        Returns:
            array: Intensité calculée (nouveaux cas ou décès quotidiens)
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
            t_data (array): Données temporelles (en jours)
            y_data (array): Données d'intensité (nouveaux cas ou décès quotidiens)
            maxfev (int): Nombre maximum d'évaluations de fonction

        Returns:
            tuple: Paramètres optimaux et erreur RMS
        """
        # Génération dynamique des estimations initiales et des bornes
        initial_guess = []
        bounds_lower = []
        bounds_upper = []

        t_max = t_data.max()
        y_max = y_data.max()

        for i in range(self.n_modes):
            # Estimation initiale intelligente
            initial_guess.extend([y_max / self.n_modes, t_max * (i+1) / (self.n_modes+1), 5 + i*5])
            bounds_lower.extend([0, 0, 1])
            bounds_upper.extend([y_max * 2, t_max, t_max / 2])

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
            t (array): Temps (en jours)

        Returns:
            array: Intensité prédite (nouveaux cas ou décès quotidiens)
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
            t (array): Temps (en jours)
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

    VERSION CONSOLIDÉE avec IFR explicite.

    Hypothèses :
    1. Population fermée (pas de naissance/mort hors COVID)
    2. Mélange homogène (pas de structure spatiale)
    3. Taux de transmission β et récupération γ constants
    4. Les décès sont proportionnels à I(t) via IFR × γ_death

    Limitations connues :
    - β et γ sont corrélés : sans données de prévalence, ils sont non-identifiables
    - Le fit sur décès seuls ne valide pas le modèle SIR
    - Pas de mémoire (confinements, vaccinations ignorés)

    Référence : Kermack-McKendrick (1927)
    """

    def __init__(self, population=60e6, IFR=0.01):
        """
        Initialise le modèle SIR.

        Args:
            population (float): Taille de la population
            IFR (float): Infection Fatality Rate (proportion d'infectés qui décèdent)
                        Valeurs typiques : 0.005 - 0.02 (0.5% - 2%)
        """
        self.N = population
        self.IFR = IFR
        self.params = None

    def _sir_equations(self, y, t, beta, gamma):
        """
        Équations différentielles du modèle SIR.

        dS/dt = -β * S * I / N
        dI/dt = β * S * I / N - γ * I
        dR/dt = γ * I

        Args:
            y (tuple): (S, I, R) - État actuel
            t (float): Temps (en jours)
            beta (float): Taux de transmission (contacts infectieux par jour)
            gamma (float): Taux de récupération (1/γ = durée moyenne infection)

        Returns:
            array: Dérivées [dS/dt, dI/dt, dR/dt]
        """
        S, I, R = y
        dS = -beta * S * I / self.N
        dI = beta * S * I / self.N - gamma * I
        dR = gamma * I
        return np.array([dS, dI, dR])

    def _deaths_from_I(self, I_t, gamma):
        """
        Modélise les décès quotidiens à partir de I(t).

        Hypothèse simplifiée : D(t) = IFR * γ * I(t)
        (Les infectés qui "sortent" de I via récupération, une fraction IFR meurt)

        LIMITATION : Ignore le délai entre infection et décès (typiquement 2-3 semaines)

        Args:
            I_t (array): Nombre d'infectés au temps t
            gamma (float): Taux de récupération

        Returns:
            array: Décès quotidiens prédits
        """
        return self.IFR * gamma * I_t

    def _sir_fit_deaths(self, t, beta, gamma, I0, scale):
        """
        Fonction de fitting pour le modèle SIR ajusté sur les décès.

        Args:
            t (array): Temps (en jours)
            beta (float): Taux de transmission
            gamma (float): Taux de récupération
            I0 (float): Nombre initial d'infectés
            scale (float): Facteur d'échelle pour calibrer les décès
                          (compense les incertitudes sur IFR, sous-déclaration, etc.)

        Returns:
            array: Décès quotidiens prédits
        """
        # Conditions initiales
        S0 = self.N - I0
        R0_count = 0
        y0 = (S0, I0, R0_count)

        # Intégration ODE
        sol = odeint(self._sir_equations, y0, t, args=(beta, gamma))
        I_t = sol[:, 1]

        # Modélisation des décès
        deaths = self._deaths_from_I(I_t, gamma)

        # Application du facteur d'échelle
        return deaths * scale

    def fit(self, t_data, y_data):
        """
        Ajuste le modèle SIR aux données de décès quotidiens.

        AVERTISSEMENT : Ce fit a des limitations intrinsèques :
        - β et γ sont corrélés (non-identifiables sans données de prévalence)
        - scale absorbe les incertitudes (IFR, sous-déclaration, délais)
        - Un bon fit ne valide PAS le modèle SIR

        Args:
            t_data (array): Temps (en jours, échelle réelle)
            y_data (array): Décès quotidiens observés

        Returns:
            tuple: Paramètres optimaux [beta, gamma, I0, scale] et erreur RMS
        """
        y_max = y_data.max()
        t_max = t_data.max()

        # Estimation initiale raisonnable
        p0 = [
            0.3,           # beta : taux de transmission (R0 ≈ beta/gamma ≈ 3)
            0.1,           # gamma : 1/gamma ≈ 10 jours (durée infection)
            1000,          # I0 : quelques milliers d'infectés initiaux
            1.0            # scale : facteur de calibration
        ]

        # Bornes réalistes
        bounds_lower = [0, 0, 1, 0]
        bounds_upper = [
            5.0,           # beta max : R0 max ≈ 50 (peu réaliste au-delà)
            1.0,           # gamma max : durée infection min ≈ 1 jour
            self.N / 100,  # I0 max : 1% de la population
            100.0          # scale max : facteur 100 (large marge)
        ]

        try:
            self.params, self.covariance = curve_fit(
                self._sir_fit_deaths,
                t_data,
                y_data,
                p0=p0,
                bounds=(bounds_lower, bounds_upper),
                maxfev=10000
            )

            # Calcul de l'erreur RMS
            y_fit = self.predict(t_data)
            rms_error = np.sqrt(np.mean((y_data - y_fit)**2))

            return self.params, rms_error

        except RuntimeError as e:
            print(f"⚠ Avertissement : Fit SIR échoué ({e})")
            self.params = None
            return None, np.inf

    def predict(self, t):
        """
        Prédit les décès quotidiens pour des temps donnés.

        Args:
            t (array): Temps (en jours)

        Returns:
            array: Décès quotidiens prédits
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")
        return self._sir_fit_deaths(t, *self.params)

    def get_parameters(self):
        """
        Retourne les paramètres du modèle.

        Returns:
            dict: Dictionnaire contenant beta, gamma, I0, scale, R0
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        beta, gamma, I0, scale = self.params

        return {
            'beta': beta,
            'gamma': gamma,
            'I0': I0,
            'scale': scale,
            'R0': beta / gamma,  # Nombre de reproduction de base
            'infection_duration_days': 1 / gamma,
            'IFR_effective': self.IFR * scale  # IFR calibré
        }

    def get_sir_curve(self, t):
        """
        Retourne les courbes S(t), I(t), R(t) complètes.

        Args:
            t (array): Temps (en jours)

        Returns:
            dict: {'S': S(t), 'I': I(t), 'R': R(t), 'deaths': D(t)}
        """
        if self.params is None:
            raise ValueError("Le modèle doit d'abord être ajusté avec fit()")

        beta, gamma, I0, scale = self.params

        S0 = self.N - I0
        R0_count = 0
        y0 = (S0, I0, R0_count)

        sol = odeint(self._sir_equations, y0, t, args=(beta, gamma))

        return {
            'S': sol[:, 0],
            'I': sol[:, 1],
            'R': sol[:, 2],
            'deaths': self._deaths_from_I(sol[:, 1], gamma) * scale
        }
