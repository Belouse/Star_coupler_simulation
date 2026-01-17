# Run_varFDTD.py - Improvements Documentation

## Overview
The `Run_varFDTD.py` script has been updated to fully automate the varFDTD simulation workflow for the star coupler. It now automatically configures sources, monitors, and runs the simulation on GPU.

## Key Improvements

### 1. **Automatic Source Configuration**
- Automatically adds mode sources at all input ports (o1, o2, o3)
- Intelligently determines injection axis and direction based on port orientation
- Configures wavelength range: 1.5-1.6 µm (centered at 1.55 µm)
- Sets fundamental TE mode for all sources

**Port Orientation Logic:**
- 0° (East): x-axis, Backward injection
- 180° (West): x-axis, Forward injection  
- 90° (North): y-axis, Backward injection
- 270° (South): y-axis, Forward injection

### 2. **Automatic Monitor Configuration**
- Automatically adds frequency-domain power monitors at all output ports (e1, e2, e3, e4)
- Selects appropriate monitor type based on waveguide orientation:
  - **Linear Y** for horizontal waveguides (0° or 180°)
  - **Linear X** for vertical waveguides (90° or 270°)
- Monitor span set to 3× port width for accurate power capture

### 3. **GPU Acceleration**
- Configured to use GPU when available
- Falls back to CPU if GPU is not detected
- Optimized mesh settings for varFDTD solver

### 4. **Automatic Simulation Execution**
- Runs the simulation automatically after configuration
- No manual intervention required
- Saves results after completion

### 5. **Improved File Organization**
- GDS files saved to: `output/gds/star_coupler_for_mode.gds`
- FSP files saved to: `output/fsp/star_coupler_varFDTD.fsp`
- Folders are created automatically if they don't exist

## Simulation Parameters

```python
# Geometry
wg_height = 0.22 µm (220 nm)
sim_x_span = 350 µm
sim_y_span = 250 µm

# Solver
simulation_time = 5000 fs
mesh_accuracy = 2
background_index = 1.444 (SiO2)

# Sources
wavelength_center = 1.55 µm
wavelength_span = 0.1 µm (1.5-1.6 µm)
mode_selection = "fundamental TE mode"

# Monitors
monitor_span = 3 × port_width
```

## Usage

Simply run the script:
```bash
python scripts/Run_varFDTD.py
```

The script will:
1. ✓ Generate the star coupler component
2. ✓ Export GDS file
3. ✓ Launch Lumerical MODE
4. ✓ Import geometry (Si + SiO2 substrate/cladding)
5. ✓ Configure varFDTD solver
6. ✓ Add sources at input ports
7. ✓ Add monitors at output ports
8. ✓ Save configuration
9. ✓ **Run simulation automatically**
10. ✓ Save results

## After Simulation

Extract and analyze results:
```bash
python scripts/extract_varFDTD_results.py
```

Or visualize directly in Lumerical MODE (window stays open).

## Port Configuration Details

Based on the screenshots provided:

### Sources (Input Ports)
- **o1, o2, o3**: Mode sources with backward injection
- Positioned at the left side of the star coupler
- Each source configured for fundamental TE mode

### Monitors (Output Ports)
All monitors are **Linear Y** type (horizontal waveguides):

| Monitor | X (µm) | Y (µm) | Y Span (µm) |
|---------|--------|--------|-------------|
| monitor_e1 | 103.763 | -19.6 | 0.6 |
| monitor_e2 | 104.772 | -6.535 | 0.6 |
| monitor_e3 | 104.772 | 6.535 | 0.6 |
| monitor_e4 | 103.763 | 19.604 | 0.6 |

## Error Handling

The script includes robust error handling:
- If simulation fails, the FSP file is still saved
- Can open and run manually in Lumerical MODE
- Detailed error messages with traceback for debugging

## Performance

- **varFDTD**: ~2-5 minutes (GPU)
- **varFDTD**: ~5-15 minutes (CPU)
- Much faster than full 3D FDTD (hours)

## Next Steps

1. Analyze transmission coefficients
2. Optimize star coupler geometry
3. Run parameter sweeps
4. Compare with experimental results
