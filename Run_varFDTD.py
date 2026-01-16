import sys
import os
import gdsfactory as gf
import numpy as np

# --- 1. CONFIGURATION DE L'API LUMERICAL ---
lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python" 
if lumerical_api_path not in sys.path:
    sys.path.append(lumerical_api_path)

import lumapi
import ubcpdk
from components.star_coupler import star_coupler

# --- 2. PRÉPARATION DU GDS ---
print("="*60)
print("WORKFLOW VARFDTD AUTOMATISÉ - STAR COUPLER")
print("="*60)

print("\n[1/5] Génération du composant...")
ubcpdk.PDK.activate()
c = star_coupler(n_inputs=3, n_outputs=4)
gds_path = os.path.join(os.getcwd(), "star_coupler_for_mode.gds")
c.write_gds(gds_path)
print(f"    ✓ GDS sauvegardé: {gds_path}")

# Récupération des positions des ports pour placement automatique des sources
ports_info = {}
for port in c.ports:
    ports_info[port.name] = {
        'center': port.center,
        'width': port.width,
        'orientation': port.orientation
    }
print(f"    ✓ {len(ports_info)} ports détectés: {list(ports_info.keys())}")

# --- 3. LANCEMENT DE LUMERICAL MODE ---
print("\n[2/5] Lancement de Lumerical MODE...")
try:
    mode = lumapi.MODE(hide=False)
    print("    ✓ Connexion établie")
except Exception as e:
    print(f"    ✗ Erreur: {e}")
    sys.exit(1)

# --- 4. CONFIGURATION DE LA SIMULATION ---
print("\n[3/5] Configuration de la structure et du solveur varFDTD...")

# Paramètres de la simulation
wg_height = 0.22e-6  # 220 nm
wg_z_center = wg_height / 2
wavelength = 1.55e-6
mesh_accuracy = 2
sim_time = 5000e-15

# Dimensions de la région de simulation
sim_x_span = 350e-6
sim_y_span = 250e-6

setup_script = f"""
# === CONFIGURATION STRUCTURE ===
deleteall;
switchtolayout;

# Import du GDS (couche Si)
gdsimport("{gds_path.replace(os.sep, '/')}", "{c.name}", "1:0", "Si (Silicon) - Palik", 0, {wg_height});

# Cladding SiO2 (substrat + overcladding)
addrect;
set("name", "SiO2_Substrate");
set("x", 0); set("y", 0);
set("x span", 500e-6); set("y span", 500e-6);
set("z min", -2e-6); set("z max", 0);
set("material", "SiO2 (Glass) - Palik");
set("override mesh order from material database", 1);
set("mesh order", 1);

addrect;
set("name", "SiO2_Overcladding");
set("x", 0); set("y", 0);
set("x span", 500e-6); set("y span", 500e-6);
set("z min", {wg_height}); set("z max", {wg_height + 2e-6});
set("material", "SiO2 (Glass) - Palik");
set("override mesh order from material database", 1);
set("mesh order", 1);

# === CONFIGURATION VARFDTD ===
addvarfdtd;
set("x", 0); 
set("y", 0);
set("x span", {sim_x_span});
set("y span", {sim_y_span});
set("z", {wg_z_center});
set("simulation time", {sim_time});
set("mesh accuracy", {mesh_accuracy});

# Configuration indice effectif
set("effective index method", "calculate from structure");
set("background index", 1.444);  # Index du SiO2
"""

mode.eval(setup_script)
print("    ✓ Structure importée")
print("    ✓ Solveur varFDTD configuré")

# --- 5. AJOUT DES PORTS ET SOURCES ---
print("\n[4/5] Configuration des ports et sources...")

# Ajout des sources sur les ports d'entrée (o1, o2, o3)
for port_name in sorted([p for p in ports_info.keys() if p.startswith('o')]):
    port = ports_info[port_name]
    x, y = port['center']
    width = port['width']
    angle = port['orientation']
    
    # Conversion en microns
    x_um = x * 1e-6
    y_um = y * 1e-6
    width_um = width * 1e-6
    
    # Direction de propagation basée sur l'orientation
    if abs(angle) < 90:  # Vers la droite
        direction = "Forward"
        inject_axis = "x-axis"
    else:  # Vers la gauche ou autre
        direction = "Backward"
        inject_axis = "x-axis"
    
    port_script = f"""
addport;
set("name", "{port_name}");
set("x", {x_um});
set("y", {y_um});
set("y span", {width_um * 3});
set("injection axis", "{inject_axis}");
set("direction", "{direction}");
set("mode selection", "fundamental TE mode");
"""
    mode.eval(port_script)
    print(f"    ✓ Port {port_name} ajouté à ({x:.2f}, {y:.2f}) µm")

# Ajout des moniteurs sur les ports de sortie (e1, e2, e3, e4)
for port_name in sorted([p for p in ports_info.keys() if p.startswith('e')]):
    port = ports_info[port_name]
    x, y = port['center']
    width = port['width']
    
    x_um = x * 1e-6
    y_um = y * 1e-6
    width_um = width * 1e-6
    
    monitor_script = f"""
addpower;
set("name", "monitor_{port_name}");
set("monitor type", "Linear X");
set("x", {x_um});
set("y", {y_um});
set("y span", {width_um * 3});
"""
    mode.eval(monitor_script)
    print(f"    ✓ Moniteur sur {port_name} à ({x:.2f}, {y:.2f}) µm")

# --- 6. CALCUL DE N_EFF ET LANCEMENT DE LA SIMULATION ---
print("\n[5/5] Calcul de l'indice effectif et lancement de la simulation...")

# Sauvegarde du fichier avant de lancer
fsp_path = os.path.join(os.getcwd(), "star_coupler_varFDTD.fsp")
mode.save(fsp_path)
print(f"    ✓ Fichier sauvegardé: {fsp_path}")

# Lancement de la simulation
print("    ⚙ Calcul de n_eff en cours...")
try:
    mode.eval("findmodes;")  # Calcul des modes pour obtenir n_eff
    print("    ✓ Calcul n_eff terminé")
except Exception as e:
    print(f"    ⚠ Avertissement lors du calcul n_eff: {e}")

print("    ⚙ Lancement de la simulation varFDTD 2D...")
try:
    mode.eval("run;")
    print("    ✓ Simulation terminée!")
except Exception as e:
    print(f"    ✗ Erreur lors de la simulation: {e}")
    sys.exit(1)

# --- 7. EXTRACTION DES RÉSULTATS ---
print("\n[6/6] Extraction des résultats...")

# Sauvegarde des résultats
results_dir = os.path.join(os.getcwd(), "simulations")
os.makedirs(results_dir, exist_ok=True)

results = {}
output_ports = [p for p in ports_info.keys() if p.startswith('e')]

for port_name in output_ports:
    try:
        # Récupération de la puissance transmise
        power = mode.eval(f'getresult("monitor_{port_name}", "T");')
        results[port_name] = power
        print(f"    ✓ Données extraites pour {port_name}")
    except Exception as e:
        print(f"    ⚠ Impossible d'extraire {port_name}: {e}")

# Sauvegarde des résultats en fichier numpy
results_file = os.path.join(results_dir, "varFDTD_results.npz")
np.savez(results_file, **results)
print(f"    ✓ Résultats sauvegardés: {results_file}")

print("\n" + "="*60)
print("SIMULATION TERMINÉE AVEC SUCCÈS!")
print("="*60)
print(f"Fichier de simulation: {fsp_path}")
print(f"Résultats: {results_file}")
print("\nLa fenêtre Lumerical MODE reste ouverte pour inspection visuelle.")
print("="*60)