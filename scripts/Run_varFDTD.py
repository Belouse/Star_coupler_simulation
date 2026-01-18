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

# Create the star coupler
c_star = star_coupler(n_inputs=3, n_outputs=4)

# Create a new top-level component with straight waveguides
c = gf.Component("simulation_assembly")
ref_star = c << c_star

# Add straight waveguides (10µm) to the INPUT ports (o1, o2, o3)
# These waveguides are connected to the taper's small side
waveguide_length = 10.0  # 10 µm
for port_name in ['o1', 'o2', 'o3']:
    # Get the port from the star coupler reference
    p = ref_star.ports[port_name]
    
    # Add a straight waveguide extending from this port
    extension = c << gf.components.straight(length=waveguide_length, width=p.width)
    extension.connect("o2", p)  # Connect output of straight to input port of star coupler
    
    # Add the waveguide's input port to the top-level component
    c.add_port(name=port_name, port=extension.ports["o1"])

# Copy output ports from star coupler to top-level component
for port_name in ['e1', 'e2', 'e3', 'e4']:
    c.add_port(name=port_name, port=ref_star.ports[port_name])

# Create output/gds folder if it doesn't exist
gds_folder = os.path.join(project_root, "output", "gds")
os.makedirs(gds_folder, exist_ok=True)
gds_path = os.path.join(gds_folder, "star_coupler_for_mode.gds")
c.write_gds(gds_path)
print(f"  ✓ GDS sauvegardé avec waveguides de {waveguide_length} µm: {gds_path}")

# Récupération des positions des ports (now from the assembly component)
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
set("mesh accuracy", 1);
set("index", 1.444);
set("auto shutoff min", 1.00e-5);
"""
    mode.eval(solver_script)
    print("  ✓ Solveur varFDTD configuré")
        
except Exception as e:
    print(f"  ✗ Erreur solveur: {e}")

# --- 6. AJOUT DES SOURCES ET MONITEURS ---
print("\n[ÉTAPE 5] Configuration des sources et moniteurs...")

# Wavelength configuration
wavelength_center = 1.55e-6  # 1550 nm
wavelength_span = 0.1e-6     # 100 nm range

try:
    # Add source only at o2 input port for current simulation
    # (will test o1 and o3 in separate simulations)
    input_ports = sorted([p for p in ports_info.keys() if p.startswith('o')])
    # Filter to only o2
    input_ports = [p for p in input_ports if p == 'o2']
    
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
        elif abs(orientation - 180) < 45:
            # Port facing West (180°) - inject from right (forward)
            injection_axis = "x-axis"
            direction = "Forward"
            y_span = port_width * 3
        elif abs(orientation - 90) < 45:
            # Port facing North (90°) - inject from bottom (backward)
            injection_axis = "y-axis"
            direction = "Backward"
            x_span = port_width * 3
        elif abs(orientation - 270) < 45:
            # Port facing South (270°) - inject from top (forward)
            injection_axis = "y-axis"
            direction = "Forward"
            x_span = port_width * 3
        else:
            # Default to x-axis backward
            injection_axis = "x-axis"
            direction = "Backward"
            y_span = port_width * 3
        
        source_script = f"""
addmodesource;
set("name", "source_{port_name}");
set("injection axis", "{injection_axis}");
set("direction", "{direction}");
set("x", {x_m});
set("y", {y_m});
"""

        # Set only the transverse span (do not set the inactive axis)
        if injection_axis == "x-axis":
            source_script += f"set(\"y span\", {y_span});\n"
        else:
            source_script += f"set(\"x span\", {x_span});\n"

        source_script += f"""
set("wavelength start", {wavelength_center - wavelength_span/2});
set("wavelength stop", {wavelength_center + wavelength_span/2});
set("mode selection", "fundamental mode");
"""
        try:
            mode.eval(source_script)
        except Exception as e:
            print(f"  ⚠ Erreur source {port_name}: {e}")
    
    print(f"  ✓ {len(input_ports)} sources ajoutées: {input_ports}")
    
    # Add power monitors at output ports (e1, e2, e3, e4)
    # All output ports face East (0°) so use 2D X-normal monitors (type 5)
    # These are YZ planes perpendicular to the X propagation direction
    output_ports = sorted([p for p in ports_info.keys() if p.startswith('e')])
    
    # Monitor dimensions (matching manual configuration)
    monitor_y_span = 0.6e-6  # 0.6 µm in y (covers waveguide width)
    monitor_z_span = 0.5e-6  # 0.5 µm in z (covers waveguide height)
    monitor_z_center = wg_height / 2  # Center at waveguide midpoint (0.11 µm)
    
    # Add global 2D Z-normal monitor covering the entire simulation domain
    print(f"\n  • Ajout du moniteur global de profil...")
    try:
        global_monitor_script = f"""
addpower;
set("name", "global_profile");
set("monitor type", "2D Z-normal");
set("x", 0); 
set("y", 0);
set("x span", {sim_x_span});
set("y span", {sim_y_span});
set("z", {monitor_z_center});
set("down sample X", 4);
set("down sample Y", 4);
"""
        mode.eval(global_monitor_script)
        print(f"  ✓ Moniteur global ajouté: global_profile")
    except Exception as e:
        print(f"  ⚠ Erreur moniteur global: {e}")
    
    # Add port-specific monitors
    for port_name in output_ports:
        port = ports_info[port_name]
        x, y = port['center']
        x_m = x * 1e-6  # Convert from µm to m
        y_m = y * 1e-6
        
        # Create 2D X-normal monitor (type 5)
        # This creates a rectangular YZ plane at position x
        monitor_script = f"""
adddftmonitor;
set("name", "monitor_{port_name}");
set("monitor type", 5);
set("x", {x_m});
set("y", {y_m});
set("y span", {monitor_y_span});
set("z", {monitor_z_center});
set("z span", {monitor_z_span});
"""
        
        try:
            mode.eval(monitor_script)
        except Exception as e:
            print(f"  ⚠ Erreur moniteur {port_name}: {e}")
    
    print(f"  ✓ {len(output_ports)} moniteurs de port ajoutés: {output_ports}")
    
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