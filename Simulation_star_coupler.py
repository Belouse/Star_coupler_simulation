import sys
# Define the paths to the Lumerical installation
lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python"
lumerical_python_path = r"C:\Program Files\Lumerical\v252\python"
lumerical_site_packages_path = r"C:\Program Files\Lumerical\v252\python\Lib\site-packages"

# Add the paths to sys.path if they are not already there
if lumerical_api_path not in sys.path:
    sys.path.append(lumerical_api_path)
if lumerical_python_path not in sys.path:
    sys.path.append(lumerical_python_path)
if lumerical_site_packages_path not in sys.path:
    sys.path.append(lumerical_site_packages_path)

import numpy as np
import gdsfactory as gf
import gplugins.lumerical as sim
from components.star_coupler import star_coupler
import lumapi

print("--- Simulation Lumerical FDTD pour Star Coupler ---")
# 1. Activation du PDK et chargement du composant
import ubcpdk
ubcpdk.PDK.activate()

c_original = star_coupler(n_inputs=3, n_outputs=4)
print("Original component:", c_original)
c_copy = c_original.copy()
print("Copied component:", c_copy)
c_flat = c_copy.flatten()
print("Flattened component:", c_flat)
c = c_flat
c.show()

# 2. Récupération du LayerStack corrigé
layer_stack = gf.get_active_pdk().layer_stack

# 3. Configuration des matériaux pour Lumerical
# On mappe les noms de matériaux du PDK aux noms dans la base de données Lumerical
material_name_to_lumerical = {
    "si": "Si (Silicon) - Palik",
    "sio2": "SiO2 (Glass) - Palik",
}

# 4. Lancement de la simulation
# Cette fonction génère le .fsp, place les ports et lance le solveur
# Note : mesh_accuracy=2 est bien pour tester, passez à 3 ou 4 pour la précision finale

# Création d'une session Lumerical
# Le mode "hide" permet de ne pas afficher l'interface graphique de Lumerical
with lumapi.FDTD(hide=False) as fdtd:
    results = sim.write_sparameters_lumerical(
        session=fdtd,
        component=c,
        layer_stack=layer_stack,
        material_name_to_lumerical=material_name_to_lumerical,
        wavelength_start=1.5,
        wavelength_stop=1.6,
        wavelength_points=50,
        mesh_accuracy=2,
        run=True, # Mettre à False pour inspecter le fichier dans Lumerical avant de calculer
    )

# 5. Analyse de la Phase
# On récupère les paramètres S (coefficients de transmission complexes)
# Les entrées sont nommées o1, o2, o3 et les sorties e1, e2, e3, e4 (selon votre code)
s_params = results

# Longueur d'onde centrale (indice 25 pour 50 points)
idx = 25 

print("--- Résultats de Phase (Port d'entrée #1) ---")
# On calcule la phase relative entre les sorties successives
for i in range(1, 4):
    trans_current = s_params[f"o1@0,e{i}@0"][idx]
    trans_next = s_params[f"o1@0,e{i+1}@0"][idx]
    
    phase_diff = np.angle(trans_next) - np.angle(trans_current)
    # Normalisation entre -pi et pi
    phase_diff = (phase_diff + np.pi) % (2 * np.pi) - np.pi
    
    print(f"Déphasage entre e{i} et e{i+1}: {phase_diff/np.pi:.3f} * π")