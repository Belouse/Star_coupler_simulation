"""
Script d'extraction des résultats varFDTD

Ce script extrait les données des moniteurs depuis un fichier .fsp existant
et exporte les résultats en format numpy.

Utilisation:
    1. Lancez Run_varFDTD.py pour configurer la simulation
    2. Configurez manuellement les sources et moniteurs dans Lumerical
    3. Lancez la simulation (bouton Run)
    4. Une fois terminée, exécutez ce script: python extract_varFDTD_results.py
"""

import sys
import os
import numpy as np

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

# Look for .fsp file in output/fsp folder
fsp_folder = os.path.join(project_root, "output", "fsp")
fsp_file = "star_coupler_varFDTD.fsp"
fsp_path = os.path.join(fsp_folder, fsp_file)

if not os.path.exists(fsp_path):
    print(f"✗ Fichier non trouvé: {fsp_path}")
    sys.exit(1)

print(f"\n[1] Ouverture du fichier: {fsp_file}")

# Ouvrir Lumerical et charger le fichier
try:
    mode = lumapi.MODE(hide=False)
    mode.load(fsp_path)
    print(f"  ✓ Fichier chargé")
except Exception as e:
    print(f"  ✗ Erreur: {e}")
    sys.exit(1)

# --- Extraction des résultats ---
print(f"\n[2] Extraction des données des moniteurs...")

results = {}
monitor_data = {}

# Essayer de récupérer la liste des moniteurs
try:
    monitors_script = """
monitors = find("monitor");
monitor_list = "";
for (i = 1 : length(monitors)) {
    monitor_list = monitor_list + monitors(i) + ",";
}
monitor_list;
"""
    monitors_str = mode.eval(monitors_script)
    monitors = [m.strip() for m in monitors_str.split(",") if m.strip()]
    print(f"  ✓ Moniteurs trouvés: {monitors}")
except Exception as e:
    print(f"  ⚠ Impossible de récupérer la liste automatiquement: {e}")
    # Essayer manuellement avec les noms connus
    monitors = ["monitor_e1", "monitor_e2", "monitor_e3", "monitor_e4"]
    print(f"  ℹ Utilisation des moniteurs par défaut: {monitors}")

# Extraire les données pour chaque moniteur
print(f"\n[3] Récupération des données...")
for monitor_name in monitors:
    try:
        # Extraire la puissance intégrée
        power_script = f"""
data = getresult("{monitor_name}", "P");
if (isempty(data)) {{
    0;
}} else {{
    sum(data);
}};
"""
        power = mode.eval(power_script)
        monitor_data[monitor_name] = float(power) if power is not None else 0
        print(f"  ✓ {monitor_name}: {power}")
        
        # Essayer d'extraire aussi les données complètes
        try:
            data_script = f'getdata("{monitor_name}");'
            full_data = mode.eval(data_script)
            results[f"{monitor_name}_full"] = full_data
        except:
            pass
            
    except Exception as e:
        print(f"  ⚠ {monitor_name}: {e}")

# Calculer les transmissions
print(f"\n[4] Calcul des transmissions...")
if monitor_data:
    total_power = sum(monitor_data.values())
    transmissions = {}
    
    print("\n" + "-"*70)
    print("RÉSULTATS DE TRANSMISSION:")
    print("-"*70)
    
    for monitor_name, power in sorted(monitor_data.items()):
        if total_power > 0:
            transmission = power / total_power * 100
        else:
            transmission = 0
        transmissions[monitor_name] = transmission
        print(f"  {monitor_name:15s}: {power:12.6e} ({transmission:6.2f}%)")
    
    print(f"  {'Total':15s}: {total_power:12.6e} (100.00%)")
    print("-"*70)
    
    results["transmissions"] = transmissions
    results["total_power"] = total_power

# Sauvegarder les résultats
print(f"\n[5] Sauvegarde des résultats...")
results_dir = os.path.join(os.getcwd(), "simulations")
os.makedirs(results_dir, exist_ok=True)

try:
    results_file = os.path.join(results_dir, "varFDTD_results.npz")
    np.savez(results_file, **results)
    print(f"  ✓ Résultats sauvegardés: {results_file}")
except Exception as e:
    print(f"  ✗ Erreur sauvegarde: {e}")

# Sauvegarder aussi en format texte lisible
try:
    results_txt = os.path.join(results_dir, "varFDTD_results.txt")
    with open(results_txt, 'w') as f:
        f.write("="*70 + "\n")
        f.write("RÉSULTATS VARFDTD\n")
        f.write("="*70 + "\n\n")
        
        if monitor_data:
            f.write("PUISSANCES MESURÉES:\n")
            f.write("-"*70 + "\n")
            for monitor_name, power in sorted(monitor_data.items()):
                f.write(f"  {monitor_name:15s}: {power:12.6e}\n")
            
            if transmissions:
                f.write("\nTRANSMISSIONS (%):\n")
                f.write("-"*70 + "\n")
                total = sum(transmissions.values()) if transmissions else 0
                for monitor_name, transmission in sorted(transmissions.items()):
                    f.write(f"  {monitor_name:15s}: {transmission:6.2f}%\n")
                f.write(f"  {'Total':15s}: {total:6.2f}%\n")
        else:
            f.write("Aucune donnée extraite\n")
    
    print(f"  ✓ Résultats texte: {results_txt}")
except Exception as e:
    print(f"  ✗ Erreur écriture texte: {e}")

print("\n" + "="*70)
print("✓ EXTRACTION TERMINÉE")
print("="*70)
print(f"Fichiers générés:")
print(f"  • {os.path.join(results_dir, 'varFDTD_results.npz')}")
print(f"  • {os.path.join(results_dir, 'varFDTD_results.txt')}")
print("="*70)
