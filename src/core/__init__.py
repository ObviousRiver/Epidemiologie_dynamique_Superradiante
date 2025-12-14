"""
Épidémiologie Radiative - Modèles super-radiants pour la dynamique épidémique.
"""

from .models import SuperRadiantModel, SIRModel
from .data_loader import CovidDataLoader, load_italy_wave1, load_country_wave
from .visualization import (
    plot_model_comparison,
    plot_residuals,
    plot_mode_decomposition,
    print_analysis_summary,
    create_report_figure
)

__version__ = "0.1.0"
__all__ = [
    'SuperRadiantModel',
    'SIRModel',
    'CovidDataLoader',
    'load_italy_wave1',
    'load_country_wave',
    'plot_model_comparison',
    'plot_residuals',
    'plot_mode_decomposition',
    'print_analysis_summary',
    'create_report_figure'
]
