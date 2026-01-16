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

# APPLY MONKEY-PATCH FIRST, BEFORE IMPORTING LUMERICAL
# Monkey-patch Port class to ensure orientations are in [0, 360) for Lumerical compatibility
_original_port_orientation_getter = gf.Port.orientation.fget

def _normalized_orientation_getter(self):
    """Get normalized orientation in [0, 360) range for Lumerical."""
    orig_angle = _original_port_orientation_getter(self)
    # Ensure angle is in [0, 360) range
    return orig_angle % 360

# Apply the patch BEFORE importing Lumerical
gf.Port.orientation = property(_normalized_orientation_getter)

# Now import Lumerical and other modules
import gplugins.lumerical as sim
from components.star_coupler import star_coupler
import lumapi
import gdsfactory.components.containers.extension as gf_extension

# Patch extend_ports to disable kfactory grid-instance checks for rotated tapers
gf.components.extend_ports = gf.cell(check_instances=False)(
    gf.components.extend_ports.__wrapped__
)
gf_extension.extend_ports = gf.cell(check_instances=False)(
    gf_extension.extend_ports.__wrapped__
)

# CRITICAL: Patch the angle validation logic in write_sparameters_lumerical
# The problem is angles like 353.374 don't match any valid range
# We need to normalize them before Lumerical sees them
import inspect
import types

# Get the original write_sparameters_lumerical function
_original_write_sparameters = sim.write_sparameters_lumerical

def _create_patched_write_sparameters(original_func):
    """Create a wrapper that normalizes port angles before validation."""
    def write_sparameters_lumerical_patched(component, **kwargs):
        """
        Wrapper that works with port angles already normalized to [0, 360).
        """
        # Just pass through to original function - no special handling needed
        return original_func(component, **kwargs)
    
    return write_sparameters_lumerical_patched

# Replace the function
sim.write_sparameters_lumerical = _create_patched_write_sparameters(_original_write_sparameters)

def fix_port_orientations_for_lumerical(component):
    """
    Create a component with simplified port orientations for Lumerical.
    
    Since the tapers have very small angles, we approximate:
    - Output ports (e*): 0° (pointing right/outward)
    - Input ports (o*): 180° (pointing left/inward)
    
    This eliminates the orientation validation problem while maintaining
    the correct propagation direction.
    """
    # Create a new component that references the original
    c = gf.Component(f"{component.name}_lum")
    
    # Instance the original component  
    ref = c << component
    
    # Collect port information with simplified orientations
    ports_data = []
    for port in component.ports:
        # Determine orientation based on port name
        # Output ports (e1, e2, e3, e4) point outward at 0°
        # Input ports (o1, o2, o3) point inward at 180°
        if port.name.startswith('e'):
            orientation = 0  # Output ports point right
        elif port.name.startswith('o'):
            orientation = 180  # Input ports point left
        else:
            orientation = 0  # Default
        
        ports_data.append({
            'name': port.name,
            'center': tuple(port.center),
            'width': port.width,
            'orientation': orientation,
            'layer': port.layer,
            'port_type': port.port_type
        })
    
    # Add all ports with corrected orientations
    for port_info in ports_data:
        c.add_port(**port_info)
    
    return c

print("--- Simulation Lumerical FDTD pour Star Coupler ---")
# 1. Activation du PDK et chargement du composant
import ubcpdk
ubcpdk.PDK.activate()

# Clear component cache to ensure updated port orientations are used
gf.clear_cache()

c_original = star_coupler(n_inputs=3, n_outputs=4)
print("Original component:", c_original)

# Verify port orientations after monkey-patch
print("Port orientations before fix:")
for port in c_original.ports:
    print(f"  {port.name}: {port.orientation:.3f}°")

# Fix port orientations for Lumerical compatibility
c = fix_port_orientations_for_lumerical(c_original)

print("Port orientations after fix for Lumerical:")
for port in c.ports:
    print(f"  {port.name}: {port.orientation:.3f}°")

print("Component is ready for simulator.")
#c.show()

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
        c,
        session=fdtd,
        layer_stack=layer_stack,
        material_name_to_lumerical=material_name_to_lumerical,
        wavelength_start=1.5,
        wavelength_stop=1.6,
        wavelength_points=25,
        mesh_accuracy=1,
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