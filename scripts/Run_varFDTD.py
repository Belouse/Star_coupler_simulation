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
set("index", 1.444);

# Configure GPU acceleration
select("varFDTD");
set("force symmetric x mesh", 0);
set("force symmetric y mesh", 0);
"""
    mode.eval(solver_script)
    
    # Try to enable GPU
    try:
        mode.eval('select("varFDTD"); set("auto shutoff min", 1.00e-5);')
        print("  ✓ Solveur varFDTD configuré (GPU)")
    except:
        print("  ✓ Solveur varFDTD configuré (CPU)")
        
except Exception as e:
    print(f"  ✗ Erreur solveur: {e}")

# --- 6. AJOUT DES SOURCES ET MONITEURS ---
print("\n[ÉTAPE 5] Configuration des sources et moniteurs...")

# Wavelength configuration
wavelength_center = 1.55e-6  # 1550 nm
wavelength_span = 0.1e-6     # 100 nm range

try:
    # Add sources at input ports (o1, o2, o3)
    input_ports = sorted([p for p in ports_info.keys() if p.startswith('o')])
    
    for port_name in input_ports:
        port = ports_info[port_name]
        x, y = port['center']
        x_m = x * 1e-6  # Convert from µm to m
        y_m = y * 1e-6
        port_width = port['width'] * 1e-6
        orientation = port['orientation']
        
        # Determine injection axis and direction based on port orientation
        # orientation: 0=East, 90=North, 180=West, 270=South
        if abs(orientation - 0) < 45 or abs(orientation - 360) < 45:
            # Port facing East (0°) - inject from left (backward)
            injection_axis = "x-axis"
            direction = "Backward"
            y_span = port_width * 3
            x_span = 1e-9  # Very small x span for x-axis source
        elif abs(orientation - 180) < 45:
            # Port facing West (180°) - inject from right (forward)
            injection_axis = "x-axis"
            direction = "Forward"
            y_span = port_width * 3
            x_span = 1e-9  # Very small x span for x-axis source
        elif abs(orientation - 90) < 45:
            # Port facing North (90°) - inject from bottom (backward)
            injection_axis = "y-axis"
            direction = "Backward"
            x_span = port_width * 3
            y_span = 1e-9  # Very small y span for y-axis source
        elif abs(orientation - 270) < 45:
            # Port facing South (270°) - inject from top (forward)
            injection_axis = "y-axis"
            direction = "Forward"
            x_span = port_width * 3
            y_span = 1e-9  # Very small y span for y-axis source
        else:
            # Default to x-axis backward
            injection_axis = "x-axis"
            direction = "Backward"
            y_span = port_width * 3
            x_span = 1e-9
        
        source_script = f"""
addmodesource;
set("name", "source_{port_name}");
set("injection axis", "{injection_axis}");
set("direction", "{direction}");
set("x", {x_m});
set("y", {y_m});
set("y span", {y_span});
set("x span", {x_span});
set("z", {wg_height/2});
set("wavelength start", {wavelength_center - wavelength_span/2});
set("wavelength stop", {wavelength_center + wavelength_span/2});
set("mode selection", "fundamental TE mode");
"""
        try:
            mode.eval(source_script)
        except Exception as e:
            print(f"  ⚠ Erreur source {port_name}: {e}")
    
    print(f"  ✓ {len(input_ports)} sources ajoutées: {input_ports}")
    
    # Add power monitors at output ports (e1, e2, e3, e4)
    output_ports = sorted([p for p in ports_info.keys() if p.startswith('e')])
    
    for port_name in output_ports:
        port = ports_info[port_name]
        x, y = port['center']
        x_m = x * 1e-6  # Convert from µm to m
        y_m = y * 1e-6
        port_width = port['width'] * 1e-6
        orientation = port['orientation']
        
        # Monitors are Linear Y for horizontal waveguides, Linear X for vertical
        if abs(orientation - 0) < 45 or abs(orientation - 180) < 45 or abs(orientation - 360) < 45:
            # Horizontal waveguide - use Linear Y (monitor type 6)
            monitor_script = f"""
adddftmonitor;
set("name", "monitor_{port_name}");
set("monitor type", 6);
set("x", {x_m});
set("y", {y_m});
set("y span", {port_width * 3});
set("z", {wg_height/2});
"""
        else:
            # Vertical waveguide - use Linear X (monitor type 5)
            monitor_script = f"""
adddftmonitor;
set("name", "monitor_{port_name}");
set("monitor type", 5);
set("x", {x_m});
set("y", {y_m});
set("x span", {port_width * 3});
set("z", {wg_height/2});
"""
        
        try:
            mode.eval(monitor_script)
        except Exception as e:
            print(f"  ⚠ Erreur moniteur {port_name}: {e}")
    
    print(f"  ✓ {len(output_ports)} moniteurs ajoutés: {output_ports}")
    
except Exception as e:
    print(f"  ✗ Erreur configuration sources/moniteurs: {e}")
    import traceback
    traceback.print_exc()

# --- 7. SAUVEGARDE ---
print("\n[ÉTAPE 6] Sauvegarde de la configuration...")

# Create output/fsp folder if it doesn't exist
fsp_folder = os.path.join(project_root, "output", "fsp")
os.makedirs(fsp_folder, exist_ok=True)
fsp_path = os.path.join(fsp_folder, "star_coupler_varFDTD.fsp")
try:
    mode.save(fsp_path)
    print(f"  ✓ Fichier sauvegardé: {fsp_path}")
except Exception as e:
    print(f"  ✗ Erreur sauvegarde: {e}")

# --- 8. LANCEMENT DE LA SIMULATION ---
print("\n" + "="*70)
print("LANCEMENT DE LA SIMULATION")
print("="*70)
print("\nConfiguration:")
print(f"  • Sources: {len([p for p in ports_info.keys() if p.startswith('o')])} ports d'entrée")
print(f"  • Moniteurs: {len([p for p in ports_info.keys() if p.startswith('e')])} ports de sortie")
print(f"  • Domaine: {sim_x_span*1e6:.1f} × {sim_y_span*1e6:.1f} µm")
print(f"  • Temps simulation: 5000 fs")
print(f"\n⏳ Démarrage de la simulation (cela peut prendre plusieurs minutes)...")

try:
    # Run the simulation
    mode.run()
    print("\n✓ Simulation terminée avec succès!")
    
    # Save after simulation
    mode.save(fsp_path)
    print(f"✓ Résultats sauvegardés: {fsp_path}")
    
    print("\n" + "="*70)
    print("PROCHAINES ÉTAPES")
    print("="*70)
    print("\n1. ANALYSER LES RÉSULTATS")
    print(f"   python scripts/extract_varFDTD_results.py")
    print("\n2. VISUALISER DANS LUMERICAL")
    print("   - Les moniteurs contiennent maintenant les données de transmission")
    print("   - Vous pouvez visualiser les champs et les puissances")
    
except Exception as e:
    print(f"\n✗ Erreur lors de la simulation: {e}")
    print("\nLe fichier a été sauvegardé. Vous pouvez:")
    print("1. Ouvrir le fichier dans Lumerical MODE")
    print("2. Vérifier la configuration")
    print("3. Lancer manuellement avec le bouton Run")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Lumerical MODE reste ouvert pour analyse")
print("="*70)