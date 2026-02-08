# Star Coupler Simulation

Silicon photonics design and simulation tools for star coupler circuits using gdsfactory and Lumerical MODE. This project includes automated chip layout generation and varFDTD simulation workflows.

## Project Structure

```
Star_coupler_simulation/
├── components/              # Photonic component definitions
│   ├── star_coupler.py     # Star coupler component
│   ├── chip_layout.py      # Full chip layout generator
│   └── sharing_template_etch.gds
│
├── scripts/                 # Simulation and analysis scripts
│   ├── Run_varFDTD.py      # Automated varFDTD setup
│   ├── extract_varFDTD_results.py
│   └── plot_result.py
│
├── output/                  # Generated files
│   ├── gds/                # GDS layout exports
│   ├── lms/                # Lumerical simulation files
│   └── fsp/
│
├── docs/                    # Documentation
│   ├── GUIDE_UTILISATION.md
│   ├── CONFIGURATION.md
│   └── BUGFIXES.md
│
└── archived/                # Legacy code and tests
```

## Installation

Requirements: Python 3.8+ and Lumerical MODE v252

```bash
pip install -r requirements.txt
```

## Quick Start

### Generate Chip Layout

Run the main chip layout generator to produce a complete GDS file:

```bash
python components/chip_layout.py
```

This generates a multi-circuit layout including:
- Power mode star couplers with direct routing
- Phase mode MZI characterization circuits
- Material loss calibration structures
- Waveguide loop references

### Run varFDTD Simulation

For individual component characterization:

```bash
python scripts/Run_varFDTD.py
```

The script will:
1. Generate the star coupler geometry
2. Export GDS and launch Lumerical MODE
3. Configure the simulation structure and solver
4. Display port coordinates for manual setup

After the script completes, manually add sources and monitors in Lumerical MODE at the displayed coordinates, then run the simulation.

### Extract Results

```bash
python scripts/extract_varFDTD_results.py
```

Results are saved to the output directory as NumPy arrays and text summaries.

## Component Configuration

The star coupler parameters can be adjusted in `components/star_coupler.py`:

```python
star_coupler(
    n_inputs=5,
    n_outputs=4,
    pitch_inputs=10.0,
    pitch_outputs=10.0,
    taper_length=40.0,
    wg_width=0.75,
    radius=130.0,
    layer=(4, 0)  # SiN layer
)
```

The chip layout circuits support phase measurement with configurable MZI parameters:
- `delta_L`: Path length difference for phase delay
- `h1_MZI`, `h3_MZI`: MZI arm routing parameters
- Direct SC-to-GC routing with obstacle avoidance

## Simulation Notes

**varFDTD**: Fast 2D effective index simulation (minutes). Best for initial design iterations.

**FDTD 3D**: Full 3D simulation (hours). Use for final validation after varFDTD optimization.

Due to Lumerical API limitations, varFDTD port configuration requires manual setup through the GUI. The automation scripts handle geometry and solver setup only.

## Troubleshooting

**Port alignment issues**: Check coordinates printed by `Run_varFDTD.py`. Ensure source/monitor spans cover the waveguide width.

**Routing conflicts**: The direct routing feature automatically detects and routes around MZI structures for lower star coupler outputs.

**Path length errors**: The `route_with_loop` function now includes vertical return segments in length calculations. Adjust `loop_height_max` if targeting long delays.

## Documentation

See the `docs/` folder for detailed guides:
- `GUIDE_UTILISATION.md`: Complete user guide
- `CONFIGURATION.md`: Configuration reference
- `RUN_VARFDTD_IMPROVEMENTS.md`: varFDTD workflow details

## References

- gdsfactory: https://gdsfactory.github.io/gdsfactory/
- ubcpdk: https://gdsfactory.github.io/ubc/
- Lumerical MODE: https://optics.ansys.com/hc/en-us/
