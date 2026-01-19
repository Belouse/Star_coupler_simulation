"""
Script d'extraction des résultats varFDTD

Ce script extrait les données des moniteurs depuis tous les fichiers .lms
et exporte les résultats en format numpy et texte.

Utilisation:
    1. Lancez Run_varFDTD.py pour configurer les simulations
    2. Lancez les simulations dans Lumerical (bouton Run pour chaque fichier)
    3. Exécutez ce script: python extract_varFDTD_results.py
"""

import sys
import os
import numpy as np
import glob

# Add the project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuration API Lumerical ---
lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python" 
if lumerical_api_path not in sys.path:
    sys.path.append(lumerical_api_path)

import lumapi

print("="*70)
print("EXTRACTION DES RÉSULTATS VARFDTD")
print("="*70)

# Look for all .lms files in output/lms folder
lms_folder = os.path.join(project_root, "output", "lms")
lms_files = glob.glob(os.path.join(lms_folder, "*.lms"))

if not lms_files:
    print(f"✗ Aucun fichier .lms trouvé dans: {lms_folder}")
    sys.exit(1)

print(f"\n[1] Fichiers .lms trouvés: {len(lms_files)}")
for lms_file in lms_files:
    print(f"    • {os.path.basename(lms_file)}")

print(f"\n[1] Fichiers .lms trouvés: {len(lms_files)}")
for lms_file in lms_files:
    print(f"    • {os.path.basename(lms_file)}")

# Prepare results directory
results_dir = os.path.join(project_root, "simulations")
os.makedirs(results_dir, exist_ok=True)

# Process each LMS file
all_results = {}

for lms_path in lms_files:
    lms_filename = os.path.basename(lms_path)
    # Extract source name from filename (e.g., star_coupler_varFDTD_o1.lms -> o1)
    source_name = lms_filename.replace("star_coupler_varFDTD_", "").replace(".lms", "")
    
    print("\n" + "="*70)
    print(f"TRAITEMENT: {lms_filename} (source: {source_name})")
    print("="*70)

    # Ouvrir Lumerical et charger le fichier
    try:
        mode = lumapi.MODE(hide=True)  # Hide GUI for faster processing
        mode.load(lms_path)
        print(f"  ✓ Fichier chargé")
    except Exception as e:
        print(f"  ✗ Erreur chargement: {e}")
        try:
            mode.close()
        except:
            pass
        continue

    # --- Extraction des résultats ---
    print(f"\n  [2] Extraction des données des moniteurs...")
    
    results = {}
    monitor_data = {}
    
    # Get list of monitors
    # For MODE, use known monitor names directly
    monitors = ["monitor_e1", "monitor_e2", "monitor_e3", "monitor_e4", "global_profile", "index_map"]
    print(f"    ✓ Utilisation des moniteurs standards: {monitors}")
    
    # Extract data for each monitor
    print(f"\n  [3] Récupération des données de transmission...")
    for monitor_name in monitors:
        try:
            print(f"    • Extraction {monitor_name}...")
            
            # For varFDTD in MODE, try direct data access
            mode.eval(f'select("{monitor_name}");')
            
            # Get power data (for DFT monitors)
            try:
                power_values = mode.getdata(monitor_name, "power")
                f_values = mode.getdata(monitor_name, "f")
                
                if power_values is not None and len(power_values) > 0:
                    power_mean = float(np.mean(np.abs(power_values)))
                    monitor_data[monitor_name] = power_mean
                    
                    # Convert frequency to wavelength
                    c = 299792458  # m/s
                    wavelengths = c / np.array(f_values) * 1e6  # convert to µm
                    
                    print(f"      ✓ P_mean = {power_mean:.6e} W (sur {len(power_values)} λ)")
                    
                    # Store arrays
                    results[f"{monitor_name}_power"] = np.array(power_values).flatten()
                    results[f"{monitor_name}_lambda"] = wavelengths.flatten()
                    results[f"{monitor_name}_f"] = np.array(f_values).flatten()
                else:
                    print(f"      ⚠ Données vides ou nulles")
            except Exception as e:
                print(f"      ⚠ Erreur getdata: {e}")
            
        except Exception as e:
            print(f"    ⚠ {monitor_name}: {e}")
    
    # Calculate transmissions
    if monitor_data:
        total_power = sum(monitor_data.values())
        transmissions = {}
        
        print(f"\n  [4] Calcul des transmissions relatives...")
        print("    " + "-"*60)
        
        for monitor_name, power in sorted(monitor_data.items()):
            if total_power > 0:
                transmission = power / total_power * 100
            else:
                transmission = 0
            transmissions[monitor_name] = transmission
            print(f"    {monitor_name:15s}: {power:12.6f} ({transmission:6.2f}%)")
        
        print(f"    {'Total':15s}: {total_power:12.6f} (100.00%)")
        print("    " + "-"*60)
        
        results["transmissions"] = transmissions
        results["total_power"] = total_power
        results["source_name"] = source_name
    
    # Save results for this source
    try:
        results_file = os.path.join(results_dir, f"varFDTD_results_{source_name}.npz")
        np.savez(results_file, **results)
        print(f"\n    ✓ Résultats numpy: {results_file}")
    except Exception as e:
        print(f"    ✗ Erreur sauvegarde numpy: {e}")
    
    # Save text file
    try:
        results_txt = os.path.join(results_dir, f"varFDTD_results_{source_name}.txt")
        with open(results_txt, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write(f"RÉSULTATS VARFDTD - SOURCE: {source_name}\n")
            f.write("="*70 + "\n\n")
            
            if monitor_data:
                f.write("TRANSMISSIONS ABSOLUES:\n")
                f.write("-"*70 + "\n")
                for monitor_name, power in sorted(monitor_data.items()):
                    f.write(f"  {monitor_name:15s}: {power:12.6f}\n")
                
                if transmissions:
                    f.write("\nTRANSMISSIONS RELATIVES (%):\n")
                    f.write("-"*70 + "\n")
                    total = sum(transmissions.values()) if transmissions else 0
                    for monitor_name, transmission in sorted(transmissions.items()):
                        f.write(f"  {monitor_name:15s}: {transmission:6.2f}%\n")
                    f.write(f"  {'Total':15s}: {total:6.2f}%\n")
            else:
                f.write("Aucune donnée extraite\n")
        
        print(f"    ✓ Résultats texte: {results_txt}")
    except Exception as e:
        print(f"    ✗ Erreur sauvegarde texte: {e}")
    
    # Store in global results
    all_results[source_name] = results
    
    # Close MODE
    try:
        mode.close()
    except:
        pass

print("\n" + "="*70)
print("✓ EXTRACTION TERMINÉE")
print("="*70)
print(f"\nFichiers générés dans {results_dir}:")
for source_name in all_results.keys():
    print(f"  • varFDTD_results_{source_name}.npz")
    print(f"  • varFDTD_results_{source_name}.txt")
print("="*70)
