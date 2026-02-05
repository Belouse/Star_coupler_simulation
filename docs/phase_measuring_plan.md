# Plan de Mesure de Phase - Mode Phase du Star Coupler

## 🎯 Objectif Global
Créer une structure interférométrique pour mesurer la différence de phase entre deux sorties du star coupler en variant la longueur d'onde. Dupliquer cette structure pour calibration.

---

## 📋 Architecture Générale

```
Star Coupler (4 sorties)
    ├── OUT#1 (top)      ──→ [Branche courte L_1]      ──→ MMI_1 (entrée bas)
    ├── OUT#2           ──→ [Branche longue L_1+175]  ──→ MMI_1 (entrée haut)
    ├── OUT#3 (bottom)  ──→ [Branche courte L_1]      ──→ MMI_2 (entrée bas)
    └── OUT#4           ──→ [Branche longue L_1+175]  ──→ MMI_2 (entrée haut)
    
Sorties MMI_1 & MMI_2 → Vers grating couplers de sortie
```

---

## 🔧 Étapes d'Implémentation

### Phase 1 : Fondations & Configuration
- [ ] **1.1** Définir les positions exactes du premier MZI (MZI_1) par rapport aux sorties du star coupler
- [ ] **1.2** Identifier les 2 sorties du SC à utiliser (OUT#1 et OUT#2 ou autres?)
- [ ] **1.3** Charger/définir le composant MMI coupler `ANT_MMI_1x2_te1550_3dB_BB`
- [ ] **1.4** Déterminer les ports d'entrée/sortie du MMI et leurs orientations
- [ ] **1.5** Créer variables globales:
  - `L_BRAS_COURT` (L_1)
  - `L_BRAS_LONG = L_BRAS_COURT + 175` (avec tolérance ±25 μm)
  - `BEND_RADIUS_PHASE = 25.0` (μm)

### Phase 2 : Fonction de création du premier MZI
- [ ] **2.1** Fonction `create_mzi_arm()`: créer un bras avec guide d'onde + bends
  - Input: longueur souhaitée, port de départ
  - Output: port final
  - Design: utiliser `gf.components.straight()` + `gf.components.bend_euler()`
  
- [ ] **2.2** Fonction `create_single_mzi()`: combiner les deux bras + MMI
  - Input: positions des 2 ports d'entrée (sorties SC), position du MMI
  - Output: position des sorties du MMI
  - Étapes internes:
    - Connecter OUT#1 → Branche courte → Entrée bas MMI
    - Connecter OUT#2 → Branche longue → Entrée haut MMI
    - Récupérer sorties du MMI

### Phase 3 : Positionnement & Routage
- [ ] **3.1** Fonction `place_first_mzi()`: positionner MZI_1
  - Input: position du star coupler, ses sorties
  - Décision: à quelle distance verticale/horizontale?
  
- [ ] **3.2** Connecter sorties du MMI_1 aux grating couplers de sortie
  - Routing standard (s-bends ou route_bundle)

### Phase 4 : Duplication pour Calibration
- [ ] **4.1** Fonction `place_second_mzi()`: dupliquer MZI_1 + MMI_2
  - Input: position du premier MZI
  - **Exigence critique**: symétrie EXACTE (même topologie, juste décalée verticalement)
  - Offset vertical: à déterminer

- [ ] **4.2** Intégration dans `_route_outputs_phase_mode()`:
  - Remplacer code TODO par appels aux nouvelles fonctions

### Phase 5 : Intégration au Circuit
- [ ] **5.1** Modifier `_route_outputs_phase_mode()` pour appeler les fonctions MZI
- [ ] **5.2** Tester génération GDS (validation géométrique)
- [ ] **5.3** Vérifier longueurs des bras (mesure dans gdsfactory)

### Phase 6 : Validation & Optimisation
- [ ] **6.1** Vérifier absence d'intersections (chevauchements)
- [ ] **6.2** Tester avec différentes valeurs de `L_1`
- [ ] **6.3** Exporter et visualiser en GDS viewer

---

## 🔌 Points Techniques Clés

### Composants Utilisés
```python
# MMI coupler (pris de ubcpdk)
MMI = ubcpdk.cells.ANT_MMI_1x2_te1550_3dB_BB()

# Cross-section SiN
cs_phase = gf.cross_section.cross_section(
    layer=SIN_LAYER,
    width=0.75,
    radius=25.0  # Bend radius
)
```

### Design des Bras
```
Bras court (L_1):
    Port sortie SC → [Straight L_1] → Port entrée MMI

Bras long (L_1 + 175):
    Port sortie SC → [Bends + Straights pour totaliser L_1 + 175] → Port entrée MMI
```

### Approche pour Atteindre L_1 + 175 μm
Option 1: Un long straight direct
Option 2: Serpentine avec bends pour compenser (plus compact)
Option 3: Hybrid (straight + petits bends)

**À clarifier**: quelle approche préférez-vous?

---

## ✅ Paramètres Validés

### 🎯 Configuration DUT (Device Under Test)
- **Sorties du SC utilisées**: OUT#1 (top) et OUT#2 (second from top)
- **Longueur bras court**: L_1 = **300 μm**
- **Longueur bras long**: L_2 = L_1 + 175 = **475 μm** (tolérance: 450-500 μm si erreurs)
- **Bend radius**: 25 μm partout
- **Branche longue**: monte vers le **haut** (OUT#2 → entrée haute du MMI)
- **Branche courte**: connexion directe (OUT#1 → entrée basse du MMI)

### 🔧 Architecture MZI
```
OUT#1 (SC haut)     ──→ [Branche courte 300 μm]  ──→ MMI entrée bas
OUT#2 (SC 2ème)     ──→ [Branche longue 475 μm]  ──→ MMI entrée haut
                                                       ↓
                                                   MMI sorties → vers GCs
```

### 🔄 Duplication pour Calibration
- **Copier-coller EXACT** du circuit DUT (pas de symétrie, pas de modifications)
- Géométrie identique entre DUT et calibration
- Plus tard: utiliser OUT#3 et OUT#4 pour la calibration (mêmes longueurs)

### 📦 Composant MMI
- **Type**: `ANT_MMI_1x2_te1550_3dB_BB` (ubcpdk)
- **Bounding box**: forme allongée horizontale
- **Ports d'entrée**: 2 (haut et bas)
- **Ports de sortie**: vers GCs (routage ultérieur)

---

## 📐 Structure de Code Attendue

```python
# Nouvelles fonctions à créer:

def create_mzi_arm(
    circuit: gf.Component,
    start_port: gf.Port,
    arm_length: float,
    cs: gf.CrossSection,
) -> gf.Port:
    """Créer un bras du MZI de longueur donnée."""
    # À implémenter

def create_single_mzi(
    circuit: gf.Component,
    port_short_input: gf.Port,
    port_long_input: gf.Port,
    mmi_position: tuple[float, float],
    L_1: float,
) -> dict:
    """Créer un MZI complet (2 bras + MMI)."""
    # À implémenter
    # Retourne: {"mmi_ref": ref, "output_ports": [...]}

def _route_outputs_phase_mode(
    circuit: gf.Component,
    star_ref: gf.ComponentReference,
) -> None:
    """Interfère star coupler outputs avec MZI x2."""
    # Appeler create_single_mzi() deux fois avec décalage
```

---

## 🎨 Checklist de Validation

- [ ] Longueurs des bras mesurées correctement
- [ ] Pas d'intersections entre éléments
- [ ] Symétrie du second MZI exacte
- [ ] Ports bien connectés (pas de gaps)
- [ ] Bend radius = 25 μm respecté partout
- [ ] GDS exporte sans erreurs
- [ ] Visualisation cohérente

---

## 📝 Notes Supplémentaires

- Considérer l'ordre de création: bras court PUIS bras long (pour éviter croisements)
- Vérifier que `ANT_MMI_1x2_te1550_3dB_BB` existe dans ubcpdk
- Tester incrémentalement (d'abord 1 MZI, puis duplication)
- Documenter les positions exactes pour reproducibilité
