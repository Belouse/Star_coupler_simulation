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

# Create the star coupler (now includes input/output waveguides)
c = star_coupler(n_inputs=5, n_outputs=4)

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
print("\n[ÉTAPE 2] Préparation des simulations Lumerical...")

# --- 4. CONFIGURATION DE LA STRUCTURE ---
wg_height = 0.4e-6  # 400 nm SiN core (per NanoSOI specs)

# Wavelength configuration (global)
# TODO: Modify for final simulation

wavelength_start = 1.55e-6
wavelength_stop = 1.55e-6

# Monitor coverage of the full component (used for index monitors)
component_bbox = c.bbox()
print(component_bbox)
print(type(component_bbox))
bbox_center_x = (component_bbox.left + component_bbox.right) / 2
bbox_center_y = (component_bbox.bottom + component_bbox.top) / 2
bbox_span_x = component_bbox.right - component_bbox.left
bbox_span_y = component_bbox.top - component_bbox.bottom

# Create output folders
fsp_folder = os.path.join(project_root, "output", "fsp")
os.makedirs(fsp_folder, exist_ok=True)
lms_folder = os.path.join(project_root, "output", "lms")
os.makedirs(lms_folder, exist_ok=True)

# Save a single FSP snapshot for reference (optional, no run)
fsp_path = os.path.join(fsp_folder, "star_coupler_varFDTD.fsp")

# Prepare list of input ports for per-source LMS generation
input_ports = sorted([p for p in ports_info.keys() if p.startswith('i')])
output_ports = sorted([p for p in ports_info.keys() if p.startswith('out')])

print(f"\n[ÉTAPE 2] Génération de {len(input_ports)} fichiers LMS (un par entrée)...")

for port_name in input_ports:
    print("\n" + "-"*70)
    print(f"Configuration pour la source: {port_name}")
    
    mode = None
    try:
        mode = lumapi.MODE(hide=True)
    except KeyboardInterrupt:
        print(f"  ⚠ Interruption utilisateur")
        if mode:
            try:
                mode.close()
            except:
                pass
        break
    except Exception as e:
        print(f"  ✗ Erreur ouverture MODE: {e}")
        continue

    try:
        setup_script = f"""
deleteall;
switchtolayout;

# Import du GDS (couche SiN, SiePIC 4/0)
gdsimport("{gds_path.replace(os.sep, '/')}", "{c.name}", "4:0", "Si3N4 (Silicon Nitride) - Luke", 0, {wg_height});

# Substrat SiO2 (BOX ~4.5 µm)
addrect;
set("name", "SiO2_Substrate");
set("x", 0); set("y", 0);
set("x span", 500e-6); set("y span", 500e-6);
set("z min", -4.5e-6); set("z max", 0);
set("material", "SiO2 (Glass) - Palik");

# Overcladding SiO2 (PECVD 3 µm standard)
addrect;
set("name", "SiO2_Overcladding");
set("x", 0); set("y", 0);
set("x span", 500e-6); set("y span", 500e-6);
set("z min", {wg_height}); set("z max", {wg_height + 3e-6});
set("material", "SiO2 (Glass) - Palik");
"""
        mode.eval(setup_script)
        print("  ✓ Géométrie importée")
    except Exception as e:
        print(f"  ✗ Erreur import: {e}")
        mode.close()
        continue

    try:
        solver_script = f"""
addvarfdtd;
set("x", {0});
set("y", {0});
set("x span", {235.6e-6});
set("y span", {175e-6});
set("z", {-0.55e-6});  # Centered through BOX (4.5 µm) + core (0.4 µm) + 3 µm top cladding
set("z span", {8.5e-6});
set("simulation time", 5000e-15); 
set("mesh accuracy", 5);
set("index", 1.444);
set("auto shutoff min", 1.00e-5);
"""
        # 5000e-15
        mode.eval(solver_script)
        print("  ✓ Solveur varFDTD configuré")
    except Exception as e:
        print(f"  ✗ Erreur solveur: {e}")
        mode.close()
        continue

    # Sources (single active input per file)
    try:
        port = ports_info[port_name]
        x, y = port['center']
        # Place source directly at the port center (no axial offset)
        x_m = x * 1e-6
        y_m = y * 1e-6
        # Keep default source vertical extent (do not set z / z span explicitly)
        lateral_span = 2e-6
        orientation = port['orientation']

        if abs(orientation - 0) < 45 or abs(orientation - 360) < 45:
            injection_axis = "x-axis"
            direction = "Backward"
        elif abs(orientation - 180) < 45:
            injection_axis = "x-axis"
            direction = "Forward"
        elif abs(orientation - 90) < 45:
            injection_axis = "y-axis"
            direction = "Backward"
        elif abs(orientation - 270) < 45:
            injection_axis = "y-axis"
            direction = "Forward"
        else:
            injection_axis = "x-axis"
            direction = "Backward"

        source_script = f"""
addmodesource;
set("name", "source_{port_name}");
set("injection axis", "{injection_axis}");
set("direction", "{direction}");
set("x", {x_m});
set("y", {y_m});
set("y span", {lateral_span});
set("wavelength start", {wavelength_start});
set("wavelength stop", {wavelength_stop});
set("mode selection", "fundamental mode");
"""

        if injection_axis == "y-axis":
            # When injecting along y, set x span instead
            source_script = source_script.replace(f"set(\"y span\", {lateral_span});", f"set(\"x span\", {lateral_span});")

        mode.eval(source_script)
        print(f"  ✓ Source ajoutée: {port_name}")
    except Exception as e:
        print(f"  ✗ Erreur source {port_name}: {e}")
        mode.close()
        continue

    # Monitors
    monitor_y_span = 0.6e-6
    monitor_z_span = 0.5e-6
    monitor_z_center = wg_height / 2

    try:
        global_monitor_script = f"""
adddftmonitor;
set("name", "global_profile");
set("monitor type", "2D Z-normal");
set("x", 0);
set("y", 0);
set("x span", {235.6e-6});
set("y span", {175e-6});
set("z", {monitor_z_center});
set("down sample X", 4);
set("down sample Y", 4);
"""
        mode.eval(global_monitor_script)
        print("  ✓ Moniteur global ajouté")
    except Exception as e:
        print(f"  ⚠ Erreur moniteur global: {e}")

    for out_name in output_ports:
        try:
            port = ports_info[out_name]
            x, y = port['center']
            x_m = x * 1e-6
            y_m = y * 1e-6

            monitor_script = f"""
adddftmonitor;
set("name", "monitor_{out_name}");
set("monitor type", 5);
set("x", {x_m});
set("y", {y_m});
set("y span", {monitor_y_span});
set("z", {monitor_z_center});
set("z span", {monitor_z_span});
"""
            mode.eval(monitor_script)
        except Exception as e:
            print(f"  ⚠ Erreur moniteur {out_name}: {e}")
    
    # Add 2D frequency monitors (Z-normal) at each output port
    # Monitor is 2 μm larger than the 0.5 μm waveguide width in Y and Z directions
    output_monitor_y_span = 0.5e-6 + 2e-6  # waveguide width + 2 μm
    output_monitor_z_span = wg_height + 2e-6  # waveguide height + 2 μm
    
    for out_name in output_ports:
        try:
            port = ports_info[out_name]
            x, y = port['center']
            x_m = x * 1e-6
            y_m = y * 1e-6

            output_monitor_script = f"""
adddftmonitor;
set("name", "freq_monitor_{out_name}");
set("monitor type", "2D X-normal");
set("x", {x_m});
set("y", {y_m});
set("y span", {output_monitor_y_span});
set("z", {monitor_z_center});
"""
            mode.eval(output_monitor_script)
            print(f"  ✓ Moniteur de fréquence 2D Z-normal ajouté: {out_name}")
        except Exception as e:
            print(f"  ⚠ Erreur moniteur de fréquence {out_name}: {e}")
    print(f"  ✓ {len(output_ports)} moniteurs de port ajoutés")

    # Field monitors covering the whole star coupler (for index/field analysis)
    try:
        index_monitors_script = f"""
adddftmonitor;
set("name", "index_map");
set("monitor type", "2D Z-normal");
set("x", {bbox_center_x * 1e-6});
set("y", {bbox_center_y * 1e-6});
set("x span", {bbox_span_x * 1e-6});
set("y span", {bbox_span_y * 1e-6});
set("z", {wg_height/2});
"""
        mode.eval(index_monitors_script)
        print("  ✓ Moniteur de champ (index_map) ajouté")
    except Exception as e:
        print(f"  ⚠ Erreur moniteur de champ: {e}")

    # Sauvegarde LMS spécifique à l'entrée
    lms_path = os.path.join(lms_folder, f"star_coupler_varFDTD_{port_name}.lms")
    try:
        mode.save(lms_path)
        print(f"  ✓ Fichier sauvegardé: {lms_path}")
    except Exception as e:
        print(f"  ✗ Erreur sauvegarde LMS: {e}")

    # Sauvegarde FSP de référence (écrasée à chaque fois, sans run)
    try:
        mode.save(fsp_path)
    except Exception:
        pass

    try:
        mode.close()
    except Exception:
        pass

print("\n" + "="*70)
print("Configuration terminée pour toutes les entrées. Aucun run lancé.")
print("="*70)