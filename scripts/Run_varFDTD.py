import sys
import os
import gdsfactory as gf
import numpy as np

# Add the project root to sys.path to enable imports from components/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 1. CONFIGURATION DE L'API LUMERICAL ---
lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python" 
if lumerical_api_path not in sys.path:
    sys.path.append(lumerical_api_path)

import lumapi
import ubcpdk
from components.star_coupler import star_coupler

# --- 2. PRÉPARATION DU GDS ---
print("="*70)
print("CONFIGURATION VARFDTD - STAR COUPLER")
print("="*70)

print("\n[ÉTAPE 1] Génération du composant...")
ubcpdk.PDK.activate()
c = star_coupler(n_inputs=3, n_outputs=4)

# Create output/gds folder if it doesn't exist
gds_folder = os.path.join(project_root, "output", "gds")
os.makedirs(gds_folder, exist_ok=True)
gds_path = os.path.join(gds_folder, "star_coupler_for_mode.gds")
c.write_gds(gds_path)
print(f"  ✓ GDS sauvegardé: {gds_path}")

# Récupération des positions des ports
ports_info = {}
for port in c.ports:
    ports_info[port.name] = {
        'center': port.center,
        'width': port.width,
        'orientation': port.orientation
    }
print(f"  ✓ {len(ports_info)} ports: {list(ports_info.keys())}")

# --- 3. LANCEMENT DE LUMERICAL MODE ---
print("\n[ÉTAPE 2] Lancement de Lumerical MODE...")
try:
    mode = lumapi.MODE(hide=False)
    print("  ✓ Lumerical MODE lancé")
except Exception as e:
    print(f"  ✗ Erreur: {e}")
    sys.exit(1)

# --- 4. CONFIGURATION DE LA STRUCTURE ---
print("\n[ÉTAPE 3] Importation de la géométrie...")

wg_height = 0.22e-6  # 220 nm
sim_x_span = 350e-6
sim_y_span = 250e-6

try:
    # Nettoyage et import
    setup_script = f"""
deleteall;
switchtolayout;

# Import du GDS (couche Si)
gdsimport("{gds_path.replace(os.sep, '/')}", "{c.name}", "1:0", "Si (Silicon) - Palik", 0, {wg_height});

# Substrat SiO2
addrect;
set("name", "SiO2_Substrate");
set("x", 0); set("y", 0);
set("x span", 500e-6); set("y span", 500e-6);
set("z min", -2e-6); set("z max", 0);
set("material", "SiO2 (Glass) - Palik");

# Overcladding SiO2
addrect;
set("name", "SiO2_Overcladding");
set("x", 0); set("y", 0);
set("x span", 500e-6); set("y span", 500e-6);
set("z min", {wg_height}); set("z max", {wg_height + 2e-6});
set("material", "SiO2 (Glass) - Palik");
"""
    mode.eval(setup_script)
    print("  ✓ Géométrie importée")
except Exception as e:
    print(f"  ✗ Erreur import: {e}")
    sys.exit(1)

# --- 5. CONFIGURATION DU SOLVEUR VARFDTD ---
print("\n[ÉTAPE 4] Configuration du solveur varFDTD...")

try:
    solver_script = f"""
addvarfdtd;
set("x", 0); 
set("y", 0);
set("x span", {sim_x_span});
set("y span", {sim_y_span});
set("z", {wg_height/2});
set("simulation time", 5000e-15);
set("mesh accuracy", 2);
set("background index", 1.444);
"""
    mode.eval(solver_script)
    print("  ✓ Solveur varFDTD configuré")
except Exception as e:
    print(f"  ✗ Erreur solveur: {e}")

# --- 6. SAUVEGARDE ---
print("\n[ÉTAPE 5] Sauvegarde de la configuration...")

# Create output/fsp folder if it doesn't exist
fsp_folder = os.path.join(project_root, "output", "fsp")
os.makedirs(fsp_folder, exist_ok=True)
fsp_path = os.path.join(fsp_folder, "star_coupler_varFDTD.fsp")
try:
    mode.save(fsp_path)
    print(f"  ✓ Fichier sauvegardé: {fsp_path}")
except Exception as e:
    print(f"  ✗ Erreur sauvegarde: {e}")

# --- 7. MESSAGE POUR L'UTILISATEUR ---
print("\n" + "="*70)
print("⚠️  CONFIGURATION MANUELLE REQUISE")
print("="*70)
print("\nPour continuer, effectuez les étapes suivantes dans Lumerical:")
print("\n1. AJOUTER DES SOURCES (ports d'entrée)")
print("   - Allez à l'onglet 'Sources'")
print("   - Créez une source pour chaque port d'entrée:")

input_ports = sorted([p for p in ports_info.keys() if p.startswith('o')])
for port_name in input_ports:
    port = ports_info[port_name]
    x, y = port['center']
    x_um = x * 1e-6
    y_um = y * 1e-6
    print(f"     • {port_name}: x={x_um:.6f} m, y={y_um:.6f} m")

print("\n2. AJOUTER DES MONITEURS (ports de sortie)")
print("   - Allez à l'onglet 'Monitors'")
print("   - Créez un moniteur Power pour chaque port de sortie:")

output_ports = sorted([p for p in ports_info.keys() if p.startswith('e')])
for port_name in output_ports:
    port = ports_info[port_name]
    x, y = port['center']
    x_um = x * 1e-6
    y_um = y * 1e-6
    print(f"     • monitor_{port_name}: x={x_um:.6f} m, y={y_um:.6f} m")

print("\n3. CALCULER ET LANCER LA SIMULATION")
print("   - Appuyez sur le bouton 'Run'")
print("   - Attendez que la simulation se termine")
print("\n4. EXTRAIRE LES RÉSULTATS")
print("   - Une fois terminé, exécutez: python extract_varFDTD_results.py")

print("\n" + "="*70)
print("Lumerical MODE reste ouvert - configurez manuellement et lancez Run")
print("="*70)