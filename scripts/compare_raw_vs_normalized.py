#!/usr/bin/env python3
"""
Analyse comparative BRUT vs NORMALISÉ sur 15 pays.
Extrait γ_mean(window) pour chaque pays et compare.
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

# 15 pays avec les 2 versions
countries = [
    'austria', 'belgium', 'denmark', 'finland', 'france',
    'germany', 'ireland', 'italy', 'netherlands', 'norway',
    'portugal', 'spain', 'sweden', 'switzerland', 'united_kingdom'
]

# Données extraites du log (à compléter manuellement ou automatiser)
# Pour simplifier, je vais créer un extracteur depuis les logs

def extract_gamma_stats_from_log(logfile):
    """Parse le log pour extraire γ_mean par fenêtre et par pays."""
    results = {}

    with open(logfile, 'r') as f:
        lines = f.readlines()

    current_country = None
    current_mode = None  # 'raw' ou 'normalized'

    for i, line in enumerate(lines):
        # Détecter pays
        if 'Analyse scalogramme 2D:' in line:
            parts = line.split(':')
            if len(parts) > 1:
                country_mode = parts[1].strip()
                if '[BRUT]' in country_mode:
                    current_country = country_mode.replace('[BRUT]', '').strip().lower().replace(' ', '_')
                    current_mode = 'raw'
                elif '[NORMALISÉ]' in country_mode:
                    current_country = country_mode.replace('[NORMALISÉ]', '').strip().lower().replace(' ', '_')
                    current_mode = 'normalized'

                if current_country not in results:
                    results[current_country] = {'raw': {}, 'normalized': {}}

        # Extraire stats γ par fenêtre
        if current_country and current_mode and 'window=' in line and 'γ =' in line:
            try:
                # Format: "    window= 2j: γ = 2.55 ± 0.46, range=[1.26, 3.00]"
                parts = line.split(':')
                window_part = parts[0].strip().split('=')[1].replace('j', '').strip()
                window = int(window_part)

                gamma_part = parts[1].split('±')[0].split('=')[1].strip()
                gamma_mean = float(gamma_part)

                std_part = parts[1].split('±')[1].split(',')[0].strip()
                gamma_std = float(std_part)

                results[current_country][current_mode][window] = {
                    'mean': gamma_mean,
                    'std': gamma_std
                }
            except:
                pass

    return results

def plot_comparison(results, countries):
    """Génère graphiques de comparaison."""

    # Figure 1: γ_mean(window) pour chaque pays (overlay brut vs normalisé)
    fig, axes = plt.subplots(5, 3, figsize=(18, 20))
    axes = axes.flatten()

    for idx, country in enumerate(countries):
        ax = axes[idx]

        if country in results:
            # Raw
            if 'raw' in results[country] and len(results[country]['raw']) > 0:
                windows_raw = sorted(results[country]['raw'].keys())
                gamma_raw = [results[country]['raw'][w]['mean'] for w in windows_raw]
                std_raw = [results[country]['raw'][w]['std'] for w in windows_raw]

                ax.errorbar(windows_raw, gamma_raw, yerr=std_raw,
                           fmt='o-', label='BRUT', color='blue', alpha=0.7, linewidth=2)

            # Normalized
            if 'normalized' in results[country] and len(results[country]['normalized']) > 0:
                windows_norm = sorted(results[country]['normalized'].keys())
                gamma_norm = [results[country]['normalized'][w]['mean'] for w in windows_norm]
                std_norm = [results[country]['normalized'][w]['std'] for w in windows_norm]

                ax.errorbar(windows_norm, gamma_norm, yerr=std_norm,
                           fmt='s--', label='NORMALISÉ', color='red', alpha=0.7, linewidth=2)

        ax.axhline(y=2.4, color='gray', linestyle=':', linewidth=1, alpha=0.5)
        ax.set_xlabel('Fenêtre χ (jours)')
        ax.set_ylabel('γ_mean')
        ax.set_title(country.replace('_', ' ').title())
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, 3.5])

    plt.suptitle('Comparaison BRUT vs NORMALISÉ - γ_mean(window) pour 15 pays',
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('results/comparison_raw_vs_normalized_15countries.png', dpi=150, bbox_inches='tight')
    print(f"✅ Figure sauvegardée: results/comparison_raw_vs_normalized_15countries.png")

    # Figure 2: Différence γ(raw) - γ(normalized) par fenêtre
    fig2, ax2 = plt.subplots(figsize=(12, 6))

    for country in countries:
        if country in results:
            windows_common = sorted(set(results[country]['raw'].keys()) &
                                   set(results[country]['normalized'].keys()))

            if len(windows_common) > 0:
                diff = [results[country]['raw'][w]['mean'] -
                       results[country]['normalized'][w]['mean']
                       for w in windows_common]

                ax2.plot(windows_common, diff, 'o-', alpha=0.6, label=country, linewidth=1)

    ax2.axhline(y=0, color='black', linestyle='--', linewidth=2)
    ax2.set_xlabel('Fenêtre χ (jours)')
    ax2.set_ylabel('Δγ = γ(raw) - γ(normalized)')
    ax2.set_title('Différence γ BRUT - γ NORMALISÉ par fenêtre (15 pays)')
    ax2.legend(fontsize=7, ncol=3)
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('results/difference_raw_normalized_15countries.png', dpi=150, bbox_inches='tight')
    print(f"✅ Figure sauvegardée: results/difference_raw_normalized_15countries.png")

def main():
    logfile = '/tmp/scalogram_full_analysis.log'

    if not os.path.exists(logfile):
        print(f"❌ Log file not found: {logfile}")
        return

    print("Extraction des données du log...")
    results = extract_gamma_stats_from_log(logfile)

    print(f"\n📊 Pays trouvés dans le log: {len(results)}")
    for country in sorted(results.keys()):
        n_raw = len(results[country]['raw'])
        n_norm = len(results[country]['normalized'])
        print(f"  {country}: {n_raw} fenêtres (raw), {n_norm} fenêtres (normalized)")

    print(f"\n📈 Génération des graphiques comparatifs...")
    plot_comparison(results, countries)

    print(f"\n✅ Analyse comparative terminée!")

if __name__ == "__main__":
    main()
