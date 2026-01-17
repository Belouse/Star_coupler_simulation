# Star Coupler Simulation - GEL-7070

Projet de simulation d'un coupleur étoile (star coupler) utilisant gdsfactory et Lumerical MODE (varFDTD).

## 📁 Structure du projet

```
Star_coupler_simulation/
├── components/           # Définitions des composants photoniques
│   └── star_coupler.py  # Composant star coupler principal
│
├── scripts/             # Scripts de simulation et d'analyse
│   ├── Run_varFDTD.py              # Configuration automatique varFDTD
│   ├── extract_varFDTD_results.py  # Extraction des résultats
│   └── Simulation_star_coupler.py  # Simulation FDTD 3D complète
│
├── output/              # Fichiers générés par les simulations
│   ├── gds/            # Fichiers GDS exportés
│   ├── fsp/            # Fichiers de simulation Lumerical (.fsp)
│   └── logs/           # Logs de simulation (.lms, .log)
│
├── simulations/         # Résultats de simulation (npz, données)
│
├── build/               # Fichiers de build temporaires
│
├── archived/            # Anciens fichiers et tests
│
├── tests/               # Scripts de test
│
├── requirements.txt     # Dépendances Python
└── README.md           # Ce fichier
```

## 🚀 Workflow de simulation varFDTD

### Prérequis
- Python 3.8+
- gdsfactory
- ubcpdk
- Lumerical MODE v252

### Installation
```bash
pip install -r requirements.txt
```

### Étape 1: Configuration automatique
```bash
python scripts/Run_varFDTD.py
```
Ce script:
- Génère le composant star coupler avec gdsfactory
- Exporte le fichier GDS
- Lance Lumerical MODE
- Configure automatiquement la structure (Si, SiO2)
- Configure le solveur varFDTD
- Affiche les positions des ports pour configuration manuelle

### Étape 2: Configuration manuelle dans Lumerical
Une fois le script terminé, dans Lumerical MODE:
1. **Ajoutez des sources** aux ports d'entrée (o1, o2, o3)
   - Type: Mode source
   - Position: Utiliser les coordonnées affichées par le script
   
2. **Ajoutez des moniteurs Power** aux ports de sortie (e1, e2, e3, e4)
   - Type: Frequency-domain field and power
   - Position: Utiliser les coordonnées affichées par le script

3. **Lancez la simulation** (bouton Run)

### Étape 3: Extraction des résultats
```bash
python scripts/extract_varFDTD_results.py
```
Ce script:
- Charge le fichier .fsp généré
- Extrait les données des moniteurs
- Calcule les transmissions
- Sauvegarde les résultats dans `simulations/`

## 📊 Résultats

Les résultats sont sauvegardés dans le dossier `simulations/`:
- `varFDTD_results.npz`: Données numpy complètes
- `varFDTD_results.txt`: Résumé lisible des transmissions

## 🔧 Configuration du composant

Le star coupler peut être configuré dans [components/star_coupler.py](components/star_coupler.py):

```python
star_coupler(
    n_inputs=3,           # Nombre d'entrées
    n_outputs=4,          # Nombre de sorties
    pitch_inputs=10.0,    # Espacement des entrées (µm)
    pitch_outputs=10.0,   # Espacement des sorties (µm)
    taper_length=40.0,    # Longueur des tapers (µm)
    taper_wide=3.0,       # Largeur max des tapers (µm)
    wg_width=0.5,         # Largeur des guides d'onde (µm)
    radius=130.0,         # Rayon de la FPR (µm)
)
```

## 📝 Notes importantes

### varFDTD vs FDTD 3D
- **varFDTD**: Simulation 2D rapide (minutes), utilise un indice effectif
- **FDTD 3D**: Simulation 3D complète (heures), plus précise mais gourmande en ressources

### Fichiers générés
- `.gds`: Géométrie du composant
- `.fsp`: Fichier de simulation Lumerical
- `.lms`: Session Lumerical
- `.log`: Logs de simulation

## 🐛 Dépannage

### Erreur "Failed to evaluate code" dans Lumerical
- Les commandes d'API Python pour varFDTD sont limitées
- Configuration manuelle des ports requise
- Solution: Utilisez le workflow en 3 étapes décrit ci-dessus

### Ports mal alignés
- Vérifiez les coordonnées affichées par `Run_varFDTD.py`
- Assurez-vous que le span des sources/moniteurs couvre la largeur du guide

## 📚 Références

- [gdsfactory Documentation](https://gdsfactory.github.io/gdsfactory/)
- [ubcpdk Documentation](https://gdsfactory.github.io/ubc/)
- [Lumerical MODE Documentation](https://optics.ansys.com/hc/en-us/articles/360034914793)

## 👤 Auteur

Projet réalisé dans le cadre du cours GEL-7070 à l'Université Laval.

---
*Dernière mise à jour: 17 janvier 2026*
