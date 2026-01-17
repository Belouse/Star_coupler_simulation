# Configuration et chemins - Star Coupler Simulation

## Chemins Lumerical

Mettre à jour selon votre installation:

```python
# Dans scripts/Run_varFDTD.py et scripts/extract_varFDTD_results.py
lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python"
```

Versions supportées:
- v241
- v252
- v231 (avec adaptations possibles)

## Paramètres de simulation varFDTD

### Géométrie
```python
wg_height = 0.22e-6        # Épaisseur guide Si (220 nm)
sim_x_span = 350e-6        # Largeur région simulation (350 µm)
sim_y_span = 250e-6        # Hauteur région simulation (250 µm)
```

### Solveur
```python
mesh_accuracy = 2          # Précision du maillage (1-4)
sim_time = 5000e-15       # Temps de simulation (5 ps)
background_index = 1.444   # Indice de réfraction SiO2
```

### Matériaux
```python
Si: "Si (Silicon) - Palik"
SiO2: "SiO2 (Glass) - Palik"
```

## Paramètres du composant

Fichier: `components/star_coupler.py`

```python
star_coupler(
    n_inputs=3,              # Nombre d'entrées [1-10]
    n_outputs=4,             # Nombre de sorties [1-10]
    pitch_inputs=10.0,       # Espacement entrées (µm) [5-20]
    pitch_outputs=10.0,      # Espacement sorties (µm) [5-20]
    angle_inputs=True,       # Tapers inclinés aux entrées
    angle_outputs=True,      # Tapers inclinés aux sorties
    taper_length=40.0,       # Longueur tapers (µm) [20-100]
    taper_wide=3.0,          # Largeur max tapers (µm) [1-5]
    wg_width=0.5,           # Largeur guides (µm) [0.4-0.6]
    radius=130.0,           # Rayon FPR (µm) [50-200]
    width_rect=80.54,       # Largeur rectangle central (µm)
    height_rect=152.824,    # Hauteur rectangle central (µm)
    taper_overlap=0.1,      # Chevauchement tapers (µm)
    clad_offset=3.0,        # Offset cladding (µm)
)
```

## Structure des dossiers

```
Star_coupler_simulation/
├── components/          # Code des composants
├── scripts/            # Scripts de simulation
├── output/             # Fichiers générés
│   ├── gds/           # Fichiers GDS
│   ├── fsp/           # Fichiers Lumerical
│   └── logs/          # Logs de simulation
├── simulations/        # Résultats numpy
├── archived/           # Anciens fichiers
├── tests/             # Scripts de test
└── docs/              # Documentation
```

## Variables d'environnement (optionnel)

Pour éviter de modifier les scripts:

```bash
# Windows PowerShell
$env:LUMERICAL_PATH = "C:\Program Files\Lumerical\v252"
$env:LUMERICAL_VERSION = "v252"

# Linux/Mac
export LUMERICAL_PATH="/opt/lumerical/v252"
export LUMERICAL_VERSION="v252"
```

## Dépendances Python

Fichier: `requirements.txt`

```
gdsfactory>=7.0.0
ubcpdk
numpy
shapely
klayout
```

Installation:
```bash
pip install -r requirements.txt
```

## Configurations recommandées

### Test rapide (quelques secondes)
```python
mesh_accuracy = 1
sim_time = 1000e-15
sim_x_span = 250e-6
sim_y_span = 150e-6
```

### Production (précision optimale)
```python
mesh_accuracy = 3
sim_time = 10000e-15
sim_x_span = 400e-6
sim_y_span = 300e-6
```

### Par défaut (compromis)
```python
mesh_accuracy = 2
sim_time = 5000e-15
sim_x_span = 350e-6
sim_y_span = 250e-6
```

## Notes sur les versions

### gdsfactory
- v7.x: Version actuelle, recommandée
- v6.x: Compatible avec adaptations mineures

### Lumerical
- MODE Solutions requis (pas FDTD seul)
- Licence valide nécessaire
- Python API doit être installée

### Python
- 3.8 minimum
- 3.10-3.11 recommandé
- 3.12+ non testé

---
*Configuration à jour: 17 janvier 2026*
