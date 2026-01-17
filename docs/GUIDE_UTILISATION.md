# Guide d'utilisation - Simulation varFDTD

## Vue d'ensemble

Ce guide détaille l'utilisation du workflow de simulation varFDTD pour le star coupler.

## Pourquoi varFDTD ?

- **Rapidité**: Simulation 2D au lieu de 3D → gain de temps considérable (minutes vs heures)
- **Efficacité mémoire**: Calcul basé sur l'indice effectif → moins de RAM requise
- **Précision acceptable**: Bon compromis pour les premiers tests et optimisations

## Workflow détaillé

### Phase 1: Génération et configuration

```bash
cd "c:\Users\Éloi Blouin\OneDrive - Université Laval\École\Ulaval zMaster\GEL-7070\Star_coupler_simulation"
python scripts/Run_varFDTD.py
```

**Ce qui se passe:**
1. Génération du composant avec gdsfactory
2. Export GDS dans `output/gds/`
3. Lancement de Lumerical MODE
4. Import automatique de la géométrie
5. Configuration du solveur varFDTD
6. Affichage des coordonnées des ports

**Sortie attendue:**
```
[ÉTAPE 1] Génération du composant...
  ✓ GDS sauvegardé: star_coupler_for_mode.gds
  ✓ 7 ports: ['e1', 'e2', 'e3', 'e4', 'o1', 'o2', 'o3']

[ÉTAPE 2] Lancement de Lumerical MODE...
  ✓ Lumerical MODE lancé

[ÉTAPE 3] Importation de la géométrie...
  ✓ Géométrie importée

[ÉTAPE 4] Configuration du solveur varFDTD...
  ✓ Solveur varFDTD configuré

⚠️  CONFIGURATION MANUELLE REQUISE
```

### Phase 2: Configuration manuelle dans Lumerical

#### A. Ajouter les sources (ports d'entrée)

1. Dans l'Object Tree, cliquez sur **Sources** → **Add** → **Mode Source**
2. Configurez pour chaque port d'entrée (`o1`, `o2`, `o3`):
   - **Name**: `source_o1`, `source_o2`, `source_o3`
   - **X, Y**: Utiliser les coordonnées affichées par le script
   - **Y span**: 3x la largeur du guide (~1.5 µm)
   - **Injection axis**: X-axis
   - **Direction**: Backward (vers l'intérieur)
   - **Mode selection**: Fundamental TE mode

#### B. Ajouter les moniteurs (ports de sortie)

1. Dans l'Object Tree, cliquez sur **Monitors** → **Add** → **Frequency-domain field and power**
2. Configurez pour chaque port de sortie (`e1`, `e2`, `e3`, `e4`):
   - **Name**: `monitor_e1`, `monitor_e2`, etc.
   - **Monitor type**: Linear X
   - **X, Y**: Utiliser les coordonnées affichées par le script
   - **Y span**: 3x la largeur du guide (~1.5 µm)

#### C. Vérifier la configuration

- Vue XY: Tous les objets doivent être visibles
- Vue XZ: La couche Si (rouge) doit être centrée sur z = 110 nm
- Vue YZ: Les guides doivent être visibles en coupe

#### D. Lancer la simulation

1. Vérifiez que le solveur varFDTD (boîte orange) couvre tout le composant
2. Cliquez sur le bouton **Run** (ou F5)
3. Attendez la fin de la simulation (quelques minutes)

### Phase 3: Extraction des résultats

```bash
python scripts/extract_varFDTD_results.py
```

**Ce qui se passe:**
1. Chargement du fichier .fsp
2. Récupération des données de chaque moniteur
3. Calcul des transmissions en pourcentage
4. Sauvegarde dans `simulations/`

**Sortie attendue:**
```
[2] Extraction des données des moniteurs...
  ✓ Moniteurs trouvés: ['monitor_e1', 'monitor_e2', 'monitor_e3', 'monitor_e4']

[3] Récupération des données...
  ✓ monitor_e1: 2.456e-13
  ✓ monitor_e2: 2.458e-13
  ✓ monitor_e3: 2.460e-13
  ✓ monitor_e4: 2.462e-13

[4] Calcul des transmissions...
RÉSULTATS DE TRANSMISSION:
  monitor_e1     : 2.456e-13 ( 24.98%)
  monitor_e2     : 2.458e-13 ( 25.00%)
  monitor_e3     : 2.460e-13 ( 25.01%)
  monitor_e4     : 2.462e-13 ( 25.01%)
  Total          : 9.836e-13 (100.00%)
```

## Interprétation des résultats

### Distribution uniforme (idéal)
Si le star coupler est bien conçu, chaque sortie devrait recevoir environ 25% de la puissance d'entrée (pour 4 sorties).

### Pertes
- **Pertes d'insertion**: Différence entre puissance totale entrée et sortie
- **Pertes de désadaptation**: Dues aux réflexions aux interfaces
- **Pertes de diffraction**: Perte d'énergie dans le cladding

### Amélioration du design
Si la distribution n'est pas uniforme:
- Ajuster le rayon de la FPR (`radius`)
- Modifier l'espacement des ports (`pitch_inputs`, `pitch_outputs`)
- Optimiser les tapers (`taper_length`, `taper_wide`)

## Fichiers générés

```
output/
├── gds/
│   └── star_coupler_for_mode.gds     # Géométrie du composant
├── fsp/
│   └── star_coupler_varFDTD.fsp      # Simulation Lumerical (réutilisable)
└── logs/
    ├── star_coupler_varFDTD.lms      # Session Lumerical
    └── star_coupler_varFDTD_p0.log   # Log détaillé

simulations/
├── varFDTD_results.npz               # Données numpy complètes
└── varFDTD_results.txt               # Résumé lisible
```

## Astuces et conseils

### Optimisation de la vitesse
- Réduire `mesh accuracy` (2 → 1) pour des tests rapides
- Augmenter pour précision finale (2 → 3)

### Débogage
- Si les moniteurs ne détectent rien, vérifiez:
  - Position des sources et moniteurs
  - Span suffisant (couvre le guide)
  - Direction d'injection correcte

### Réutilisation
- Gardez le fichier `.fsp` pour relancer des simulations
- Modifiez seulement les sources/moniteurs
- Pas besoin de réimporter le GDS

### Comparaison FDTD 3D
Pour validation finale, utilisez:
```bash
python scripts/Simulation_star_coupler.py
```
(Plus long, mais plus précis)

## Dépannage

### "Failed to evaluate code"
- Normal pour l'API Python varFDTD
- Solution: Configuration manuelle (ce guide)

### Lumerical ne se lance pas
- Vérifier le chemin dans `Run_varFDTD.py`:
  ```python
  lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python"
  ```
- Ajuster selon votre version (v241, v252, etc.)

### Résultats incohérents
- Vérifier le temps de simulation (`simulation time`)
- Augmenter si les champs n'ont pas convergé
- Vérifier que PML est bien configuré

## Contact et support

Pour questions ou bugs, consultez:
- README.md du projet
- Documentation Lumerical
- Documentation gdsfactory

---
*Guide créé: 17 janvier 2026*
