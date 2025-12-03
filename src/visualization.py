"""
Utilitaires de visualisation pour les modèles épidémiologiques.
"""

import matplotlib.pyplot as plt
import numpy as np


def plot_model_comparison(t_data, y_data, y_fit_sr, y_fit_sir,
                          rms_sr, rms_sir, n_modes=4,
                          title="Validation COVID-19",
                          save_path=None):
    """
    Crée une visualisation comparative des modèles.

    Args:
        t_data (array): Données temporelles
        y_data (array): Données réelles
        y_fit_sr (array): Prédictions du modèle super-radiant
        y_fit_sir (array): Prédictions du modèle SIR
        rms_sr (float): Erreur RMS du modèle super-radiant
        rms_sir (float): Erreur RMS du modèle SIR
        n_modes (int): Nombre de modes super-radiants
        title (str): Titre du graphique
        save_path (str): Chemin pour sauvegarder la figure (optionnel)

    Returns:
        tuple: (fig, ax) - Figure et axes matplotlib
    """
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 8))

    # Tracé des données et modèles
    ax.plot(t_data, y_data, 'k-',
            label='Données réelles (Italie)',
            linewidth=2.5)
    ax.plot(t_data, y_fit_sr, 'b--',
            label=f'Modèle Super-Radiant ({n_modes} modes, RMS: {rms_sr:.3f})',
            linewidth=2.5)
    ax.plot(t_data, y_fit_sir, 'r:',
            label=f'Modèle SIR (RMS: {rms_sir:.3f})',
            linewidth=2.5)

    # Labels et légende
    ax.set_title(f'{title} - {n_modes} Modes',
                 fontsize=16, fontweight='bold')
    ax.set_xlabel('Jours depuis le début de la vague', fontsize=12)
    ax.set_ylabel('Nombre de décès (normalisé)', fontsize=12)
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Figure sauvegardée : {save_path}")

    return fig, ax


def plot_residuals(t_data, y_data, y_fit_sr, y_fit_sir, save_path=None):
    """
    Visualise les résidus des deux modèles.

    Args:
        t_data (array): Données temporelles
        y_data (array): Données réelles
        y_fit_sr (array): Prédictions super-radiant
        y_fit_sir (array): Prédictions SIR
        save_path (str): Chemin pour sauvegarder (optionnel)

    Returns:
        tuple: (fig, axes) - Figure et axes
    """
    residuals_sr = y_data - y_fit_sr
    residuals_sir = y_data - y_fit_sir

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Résidus Super-Radiant
    axes[0].plot(t_data, residuals_sr, 'b-', label='Résidus Super-Radiant')
    axes[0].axhline(y=0, color='k', linestyle='--', alpha=0.3)
    axes[0].fill_between(t_data, residuals_sr, alpha=0.3)
    axes[0].set_ylabel('Résidus', fontsize=12)
    axes[0].set_title('Résidus du Modèle Super-Radiant', fontsize=14)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Résidus SIR
    axes[1].plot(t_data, residuals_sir, 'r-', label='Résidus SIR')
    axes[1].axhline(y=0, color='k', linestyle='--', alpha=0.3)
    axes[1].fill_between(t_data, residuals_sir, alpha=0.3)
    axes[1].set_xlabel('Jours', fontsize=12)
    axes[1].set_ylabel('Résidus', fontsize=12)
    axes[1].set_title('Résidus du Modèle SIR', fontsize=14)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Figure des résidus sauvegardée : {save_path}")

    return fig, axes


def plot_mode_decomposition(t_data, sr_model, save_path=None):
    """
    Visualise la décomposition en modes du modèle super-radiant.

    Args:
        t_data (array): Données temporelles
        sr_model (SuperRadiantModel): Modèle ajusté
        save_path (str): Chemin pour sauvegarder (optionnel)

    Returns:
        tuple: (fig, ax) - Figure et axes
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    modes = sr_model.get_mode_parameters()
    colors = plt.cm.viridis(np.linspace(0, 0.9, len(modes)))

    # Tracer chaque mode individuellement
    for i, mode in enumerate(modes):
        A = mode['A']
        tau = mode['tau']
        T = mode['T']

        effective_t = np.maximum(t_data - tau, 0)
        mode_intensity = A * (effective_t**2) * np.exp(-effective_t / T)

        ax.plot(t_data, mode_intensity,
                label=f"Mode {mode['mode']}: τ={tau:.1f}j, T={T:.1f}j",
                color=colors[i], linewidth=2)

    # Tracer la somme totale
    total = sr_model.predict(t_data)
    ax.plot(t_data, total, 'k--',
            label='Somme totale', linewidth=3, alpha=0.7)

    ax.set_xlabel('Jours', fontsize=12)
    ax.set_ylabel('Intensité (normalisée)', fontsize=12)
    ax.set_title('Décomposition en Modes Super-Radiants',
                 fontsize=16, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Figure de décomposition sauvegardée : {save_path}")

    return fig, ax


def print_analysis_summary(sr_model, sir_model, rms_sr, rms_sir):
    """
    Affiche un résumé textuel de l'analyse.

    Args:
        sr_model (SuperRadiantModel): Modèle super-radiant ajusté
        sir_model (SIRModel): Modèle SIR ajusté
        rms_sr (float): Erreur RMS super-radiant
        rms_sir (float): Erreur RMS SIR
    """
    print("\n" + "="*70)
    print("ANALYSE FINALE - RÉSULTATS")
    print("="*70)

    # Performance comparative
    improvement_factor = rms_sir / rms_sr
    print(f"\n📊 PERFORMANCE COMPARATIVE:")
    print(f"   • Erreur RMS Super-Radiant: {rms_sr:.4f}")
    print(f"   • Erreur RMS SIR: {rms_sir:.4f}")
    print(f"   • Amélioration: {improvement_factor:.1f}x plus précis")

    # Paramètres Super-Radiant
    print(f"\n🌟 PARAMÈTRES SUPER-RADIANT ({sr_model.n_modes} modes):")
    modes = sr_model.get_mode_parameters()
    for mode in modes:
        print(f"   Mode {mode['mode']}:")
        print(f"      - Amplitude (A): {mode['A']:.3f}")
        print(f"      - Délai (τ): {mode['tau']:.2f} jours")
        print(f"      - Temps caractéristique (T): {mode['T']:.2f} jours")

    # Interprétation sociologique
    print(f"\n🏙️  INTERPRÉTATION SOCIOLOGIQUE:")
    tau_values = [mode['tau'] for mode in modes]
    mode_names = ["Urbain", "Péri-urbain", "Rural", "Isolé"]
    for i, (tau, name) in enumerate(zip(tau_values[:len(mode_names)], mode_names)):
        print(f"   • Mode {i+1} ({name}): τ = {tau:.1f} jours")

    # Paramètres SIR
    print(f"\n🦠 PARAMÈTRES SIR:")
    sir_params = sir_model.get_parameters()
    print(f"   • β (transmission): {sir_params['beta']:.4f}")
    print(f"   • γ (récupération): {sir_params['gamma']:.4f}")
    print(f"   • R₀ (reproduction de base): {sir_params['R0']:.2f}")
    print(f"   • I₀ (infectés initiaux): {sir_params['I0']:.0f}")

    print("\n" + "="*70 + "\n")


def create_report_figure(t_data, y_data, sr_model, sir_model,
                         rms_sr, rms_sir, save_path=None):
    """
    Crée une figure complète pour un rapport avec plusieurs sous-graphiques.

    Args:
        t_data (array): Données temporelles
        y_data (array): Données réelles
        sr_model (SuperRadiantModel): Modèle super-radiant
        sir_model (SIRModel): Modèle SIR
        rms_sr (float): Erreur RMS super-radiant
        rms_sir (float): Erreur RMS SIR
        save_path (str): Chemin pour sauvegarder

    Returns:
        tuple: (fig, axes) - Figure et axes
    """
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # 1. Comparaison principale
    ax1 = fig.add_subplot(gs[0, :])
    y_fit_sr = sr_model.predict(t_data)
    y_fit_sir = sir_model.predict(t_data, y_data.max())

    ax1.plot(t_data, y_data, 'k-', label='Données réelles', linewidth=2.5)
    ax1.plot(t_data, y_fit_sr, 'b--',
             label=f'Super-Radiant (RMS: {rms_sr:.3f})', linewidth=2.5)
    ax1.plot(t_data, y_fit_sir, 'r:',
             label=f'SIR (RMS: {rms_sir:.3f})', linewidth=2.5)
    ax1.set_title('Comparaison des Modèles', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Décès normalisés', fontsize=11)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # 2. Décomposition en modes
    ax2 = fig.add_subplot(gs[1, :])
    modes = sr_model.get_mode_parameters()
    colors = plt.cm.viridis(np.linspace(0, 0.9, len(modes)))

    for i, mode in enumerate(modes):
        A, tau, T = mode['A'], mode['tau'], mode['T']
        effective_t = np.maximum(t_data - tau, 0)
        mode_intensity = A * (effective_t**2) * np.exp(-effective_t / T)
        ax2.plot(t_data, mode_intensity,
                 label=f"Mode {mode['mode']}", color=colors[i], linewidth=2)

    ax2.plot(t_data, y_fit_sr, 'k--', label='Total', linewidth=2.5, alpha=0.7)
    ax2.set_title('Décomposition en Modes', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Intensité', fontsize=11)
    ax2.legend(fontsize=9, ncol=2)
    ax2.grid(True, alpha=0.3)

    # 3. Résidus SR
    ax3 = fig.add_subplot(gs[2, 0])
    residuals_sr = y_data - y_fit_sr
    ax3.plot(t_data, residuals_sr, 'b-')
    ax3.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax3.fill_between(t_data, residuals_sr, alpha=0.3)
    ax3.set_title('Résidus Super-Radiant', fontsize=12)
    ax3.set_xlabel('Jours', fontsize=11)
    ax3.set_ylabel('Résidus', fontsize=11)
    ax3.grid(True, alpha=0.3)

    # 4. Résidus SIR
    ax4 = fig.add_subplot(gs[2, 1])
    residuals_sir = y_data - y_fit_sir
    ax4.plot(t_data, residuals_sir, 'r-')
    ax4.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax4.fill_between(t_data, residuals_sir, alpha=0.3)
    ax4.set_title('Résidus SIR', fontsize=12)
    ax4.set_xlabel('Jours', fontsize=11)
    ax4.set_ylabel('Résidus', fontsize=11)
    ax4.grid(True, alpha=0.3)

    plt.suptitle('Rapport Complet - Analyse Super-Radiante',
                 fontsize=16, fontweight='bold', y=0.995)

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ Rapport complet sauvegardé : {save_path}")

    return fig, (ax1, ax2, ax3, ax4)
