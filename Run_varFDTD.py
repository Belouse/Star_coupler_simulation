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

# Étape 1: Nettoyage et import GDS
print("    ⚙ Étape 1: Nettoyage et import du GDS...")
try:
    step1_script = f"""
deleteall;
switchtolayout;
gdsimport("{gds_path.replace(os.sep, '/')}", "{c.name}", "1:0", "Si (Silicon) - Palik", 0, {wg_height});
"""
    mode.eval(step1_script)
    print("    ✓ GDS importé avec succès")
except Exception as e:
    print(f"    ✗ Erreur lors de l'import GDS: {e}")
    # Continuer malgré tout pour déboguer

# Étape 2: Ajout des matériaux cladding
print("    ⚙ Étape 2: Ajout du substrat et overcladding SiO2...")
try:
    step2_script = f"""
# Substrat SiO2
addrect;
set("name", "SiO2_Substrate");
set("x", 0); 
set("y", 0);
set("x span", 500e-6); 
set("y span", 500e-6);
set("z min", -2e-6); 
set("z max", 0);
set("material", "SiO2 (Glass) - Palik");
set("override mesh order from material database", 1);
set("mesh order", 1);

# Overcladding SiO2
addrect;
set("name", "SiO2_Overcladding");
set("x", 0); 
set("y", 0);
set("x span", 500e-6); 
set("y span", 500e-6);
set("z min", {wg_height}); 
set("z max", {wg_height + 2e-6});
set("material", "SiO2 (Glass) - Palik");
set("override mesh order from material database", 1);
set("mesh order", 1);
"""
    mode.eval(step2_script)
    print("    ✓ Matériaux cladding ajoutés")
except Exception as e:
    print(f"    ✗ Erreur lors de l'ajout du cladding: {e}")

# Étape 3: Configuration du varFDTD
print("    ⚙ Étape 3: Configuration du solveur varFDTD...")
try:
    step3_script = f"""
addvarfdtd;
set("x", 0); 
set("y", 0);
set("x span", {sim_x_span});
set("y span", {sim_y_span});
set("z", {wg_z_center});
set("simulation time", {sim_time});
set("mesh accuracy", {mesh_accuracy});
set("background index", 1.444);
"""
    mode.eval(step3_script)
    print("    ✓ Solveur varFDTD configuré")
except Exception as e:
    print(f"    ✗ Erreur lors de la configuration varFDTD: {e}")
    print("    ℹ Cela peut être normal - on continue avec les ports...")

# --- 5. AJOUT DES PORTS ET SOURCES ---
print("\n[4/5] Configuration des ports et sources...")

input_ports = sorted([p for p in ports_info.keys() if p.startswith('o')])
output_ports = sorted([p for p in ports_info.keys() if p.startswith('e')])

# Ajout des sources sur les ports d'entrée (o1, o2, o3)
for i, port_name in enumerate(input_ports):
    port = ports_info[port_name]
    x, y = port['center']
    width = port['width']
    angle = port['orientation']
    
    # Conversion en microns
    x_um = x * 1e-6
    y_um = y * 1e-6
    width_um = width * 1e-6
    
    try:
        port_script = f"""
addport;
set("name", "{port_name}");
set("x", {x_um});
set("y", {y_um});
set("y span", {width_um * 3});
set("injection axis", "x-axis");
set("direction", "Backward");
set("mode selection", "fundamental TE mode");
"""
        mode.eval(port_script)
        print(f"    ✓ Port {port_name} ajouté à ({x:.2f}, {y:.2f}) µm")
    except Exception as e:
        print(f"    ⚠ Erreur port {port_name}: {e}")

# Ajout des moniteurs sur les ports de sortie (e1, e2, e3, e4)
for port_name in output_ports:
    port = ports_info[port_name]
    x, y = port['center']
    width = port['width']
    
    x_um = x * 1e-6
    y_um = y * 1e-6
    width_um = width * 1e-6
    
    try:
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
    except Exception as e:
        print(f"    ⚠ Erreur moniteur {port_name}: {e}")

# --- 6. CALCUL DE N_EFF ET LANCEMENT DE LA SIMULATION ---
print("\n[5/5] Calcul de l'indice effectif et lancement de la simulation...")

# Sauvegarde du fichier avant de lancer
fsp_path = os.path.join(os.getcwd(), "star_coupler_varFDTD.fsp")
try:
    mode.save(fsp_path)
    print(f"    ✓ Fichier sauvegardé: {fsp_path}")
except Exception as e:
    print(f"    ⚠ Erreur sauvegarde: {e}")

# Lancement de la simulation
print("    ⚙ Calcul de n_eff en cours...")
try:
    mode.eval("findmodes;")
    print("    ✓ Calcul n_eff terminé")
except Exception as e:
    print(f"    ⚠ findmodes a rencontré un problème: {e}")
    print("    ℹ La simulation peut continuer sans ce calcul")

print("    ⚙ Lancement de la simulation varFDTD 2D...")
try:
    mode.eval("run;")
    print("    ✓ Simulation terminée!")
except Exception as e:
    print(f"    ⚠ Erreur lors de run: {e}")
    print("    ℹ La fenêtre reste ouverte pour déboguer")

# --- 7. EXTRACTION DES RÉSULTATS ---
print("\n[6/6] Extraction des résultats...")

# Sauvegarde des résultats
results_dir = os.path.join(os.getcwd(), "simulations")
os.makedirs(results_dir, exist_ok=True)

results = {}
transmission_data = {}

for port_name in output_ports:
    try:
        # Récupération de la puissance transmise depuis le moniteur
        result = mode.eval(f'getresult("monitor_{port_name}", "P");')
        if result is not None:
            transmission_data[port_name] = float(result)
            results[port_name] = result
            print(f"    ✓ Puissance mesurée pour {port_name}: {result}")
        else:
            print(f"    ⚠ Pas de données pour {port_name}")
    except Exception as e:
        print(f"    ⚠ Impossible d'extraire {port_name}: {e}")

# Affichage du résumé
print("\n" + "-"*60)
print("RÉSUMÉ DE LA TRANSMISSION:")
print("-"*60)
if transmission_data:
    total_power = sum(transmission_data.values())
    for port, power in sorted(transmission_data.items()):
        pct = (power / total_power * 100) if total_power > 0 else 0
        print(f"  {port}: {power:.6f} ({pct:.1f}%)")
    print(f"  Puissance totale: {total_power:.6f}")
else:
    print("  Aucune donnée extraite")
print("-"*60)

# Sauvegarde des résultats en fichier numpy
try:
    results_file = os.path.join(results_dir, "varFDTD_results.npz")
    np.savez(results_file, **results)
    print(f"    ✓ Résultats sauvegardés: {results_file}")
except Exception as e:
    print(f"    ⚠ Erreur sauvegarde résultats: {e}")

print("\n" + "="*60)
print("WORKFLOW TERMINÉ!")
print("="*60)
print(f"Fichier de simulation: {fsp_path}")
if os.path.exists(results_file):
    print(f"Résultats: {results_file}")
print("\nLa fenêtre Lumerical MODE reste ouverte.")
print("Pour continuer: Vérifiez visuellement les résultats,")
print("puis fermez la fenêtre Lumerical.")
print("="*60)