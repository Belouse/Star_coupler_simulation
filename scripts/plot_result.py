import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Configuration: Plot all wavelengths or only closest to 1.55um
PLOT_ALL_WAVELENGTHS = True
PLOT_AMPLITUDE = False
PLOT_PHASE = False
PLOT_PHASE_AMPLITUDE = False
PLOT_PHASE_SHIFT_AMPLITUDE = False
PLOT_PHASE_FOR_ALL_SOURCES = True
PLOT_PHASE_ERROR_FOR_ALL_SOURCES = False


# Path to the simulation results (last block after the final "Source:" marker is used)
DATA_PATH = Path(r"C:\\Users\\Éloi Blouin\\Desktop\\git\\Star_coupler_simulation\\output\\simulations\\star_coupler_S_matrix_V9.txt")


def load_all_sources(path: Path):
    """Load all source blocks from the results file."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find all "Source:" markers
    source_indices = []
    for i, line in enumerate(lines):
        if line.startswith("Source:"):
            source_indices.append(i)
    
    if not source_indices:
        raise ValueError("No 'Source:' marker found in the file.")

    sources_data = {}
    
    # Extract data for each source
    for source_num, start_idx in enumerate(source_indices):
        source_name = lines[start_idx].split(":")[-1].strip()
        
        # Find the end of this source's data (start of next source or end of file)
        end_idx = source_indices[source_num + 1] if source_num + 1 < len(source_indices) else len(lines)
        
        # Extract block
        block = [line.strip() for line in lines[start_idx + 1:end_idx] if line.strip()]
        if len(block) < 2:
            continue
        
        # Parse CSV data
        reader = csv.DictReader(block, skipinitialspace=True)
        data = defaultdict(lambda: {"wavelength": [], "transmission": [], "phase_rad": [], "phase_deg": []})
        
        for row in reader:
            monitor = row["Monitor"].strip()
            data[monitor]["wavelength"].append(float(row["Wavelength(um)"]))
            data[monitor]["transmission"].append(float(row["Transmission(T)"]))
            data[monitor]["phase_rad"].append(float(row["Phase(rad)"]))
            data[monitor]["phase_deg"].append(float(row["Phase(deg)"]))
        
        sources_data[source_name] = data
    
    return sources_data


def filter_to_closest_wavelength(data, target_wavelength=1.55):
    """Filter data to only the wavelength closest to target_wavelength."""
    filtered_data = defaultdict(lambda: {"wavelength": [], "transmission": [], "phase_rad": [], "phase_deg": []})
    
    for monitor, series in data.items():
        if not series["wavelength"]:
            continue
        
        # Find index of closest wavelength to target
        closest_idx = min(range(len(series["wavelength"])), 
                         key=lambda i: abs(series["wavelength"][i] - target_wavelength))
        
        filtered_data[monitor]["wavelength"].append(series["wavelength"][closest_idx])
        filtered_data[monitor]["transmission"].append(series["transmission"][closest_idx])
        filtered_data[monitor]["phase_rad"].append(series["phase_rad"][closest_idx])
        filtered_data[monitor]["phase_deg"].append(series["phase_deg"][closest_idx])
    
    return filtered_data


def plot_amplitude_and_phase_for_source(data, source_name):
    """Plot amplitude and phase for a single source, respecting global flags."""
    if PLOT_AMPLITUDE and PLOT_PHASE:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        # Amplitude plot
        for monitor, series in data.items():
            ax1.plot(series["wavelength"], series["transmission"], marker="o", label=_display_monitor_name(monitor))
        ax1.set_title(f"Output port amplitudes - Source {source_name}")
        ax1.set_xlabel("Wavelength (um)")
        ax1.set_ylabel("Transmission (T)")
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Phase plot
        for monitor, series in data.items():
            ax2.plot(series["wavelength"], series["phase_deg"], marker="o", label=_display_monitor_name(monitor))
        ax2.set_title(f"Output port phases - Source {source_name}")
        ax2.set_xlabel("Wavelength (um)")
        ax2.set_ylabel("Phase (deg)")
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        plt.tight_layout()
    elif PLOT_AMPLITUDE and not PLOT_PHASE:
        plot_amplitude_for_source(data, source_name)
    elif PLOT_PHASE and not PLOT_AMPLITUDE:
        plot_phase_for_source(data, source_name)


def plot_amplitude_and_phase(data):
    plt.figure(figsize=(10, 6))
    for monitor, series in data.items():
        plt.plot(series["wavelength"], series["transmission"], marker="o", label=f"{_display_monitor_name(monitor)} amplitude")
    plt.title("Output port amplitudes")
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Transmission (T)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.figure(figsize=(10, 6))
    for monitor, series in data.items():
        plt.plot(series["wavelength"], series["phase_deg"], marker="o", label=f"{_display_monitor_name(monitor)} phase")
    plt.title("Output port phases")
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Phase (deg)")
    plt.grid(True, alpha=0.3)
    plt.legend()


def plot_amplitude_for_source(data, source_name):
    """Plot amplitude only for a single source."""
    plt.figure(figsize=(10, 6))
    for monitor, series in data.items():
        plt.plot(series["wavelength"], series["transmission"], marker="o", label=_display_monitor_name(monitor))
    plt.title(f"Output port amplitudes - Source {source_name}")
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Transmission (T)")
    plt.grid(True, alpha=0.3)
    plt.legend()


def plot_phase_for_source(data, source_name):
    """Plot phase only for a single source."""
    plt.figure(figsize=(10, 6))
    for monitor, series in data.items():
        plt.plot(series["wavelength"], series["phase_deg"], marker="o", label=_display_monitor_name(monitor))
    plt.title(f"Output port phases - Source {source_name}")
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Phase (deg)")
    plt.grid(True, alpha=0.3)
    plt.legend()


def plot_phase_shift(data, ref="freq_monitor_out1", target="freq_monitor_out2"):
    if ref not in data or target not in data:
        print(f"Skipping phase shift: missing data for {ref} or {target}.")
        return

    ref_map = {wl: ph for wl, ph in zip(data[ref]["wavelength"], data[ref]["phase_deg"])}
    tgt_map = {wl: ph for wl, ph in zip(data[target]["wavelength"], data[target]["phase_deg"])}
    common_wl = sorted(set(ref_map) & set(tgt_map))
    if not common_wl:
        print("No common wavelengths to compute phase shift.")
        return

    shift = [tgt_map[wl] - ref_map[wl] for wl in common_wl]

    plt.figure(figsize=(8, 4))
    plt.plot(common_wl, shift, marker="o")
    plt.title(f"Phase shift: {target} - {ref}")
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Phase shift (deg)")
    plt.grid(True, alpha=0.3)


def _get_reference_monitor_name(data, candidates=("output_i1", "freq_monitor_out1")):
    """Return a suitable reference monitor name from candidates or fallback to the first available monitor."""
    for name in candidates:
        if name in data:
            return name
    return sorted(data.keys())[0] if data else None


def _display_monitor_name(name: str) -> str:
    """Return a cleaned monitor name for plot labels.

    Removes the leading 'freq_monitor_' if present.
    Examples:
    - 'freq_monitor_out1' -> 'out1'
    - 'output_i1' -> 'output_i1' (unchanged)
    """
    prefix = "freq_monitor_"
    if isinstance(name, str) and name.startswith(prefix):
        return name[len(prefix):]
    return name


def plot_polar_phase_for_source(data, source_name):
    """Plot phase of each output port in polar coordinates (phasor diagram) for a single source."""
    monitors = sorted(data.keys())
    
    # Create polar plot
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    # Colors for each monitor
    colors = ['red', 'blue', 'green', 'orange']
    
    # Plot each monitor as a phasor
    for monitor, color in zip(monitors, colors):
        # Get phase in radians (convert from degrees if needed)
        phase_rad = np.radians(data[monitor]["phase_deg"][0])
        # Use transmission as magnitude
        magnitude = data[monitor]["transmission"][0]
        
        # Plot arrow from origin to the point
        ax.arrow(phase_rad, 0, 0, magnitude, head_width=0.1, head_length=0.01, 
            fc=color, ec=color, linewidth=2.5, label=_display_monitor_name(monitor))
        
        # Add label at the end of the arrow
        ax.text(phase_rad, magnitude + 0.01, f"{_display_monitor_name(monitor)}\n{data[monitor]['phase_deg'][0]:.1f}°", 
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_ylim(0, 0.15)
    ax.set_title(f"Phase and amplitude phasor diagram - Source {source_name}", pad=20, fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)


def _get_reference_monitor_name(data, candidates=("output_i1", "freq_monitor_out1")):
    """Return a suitable reference monitor name from candidates or fallback to the first available monitor."""
    for name in candidates:
        if name in data:
            return name
    return sorted(data.keys())[0] if data else None


def plot_polar_phase_referenced_for_source(data, source_name, reference_monitor=None):
    """Plot a polar (phasor) diagram with phases referenced so that the reference monitor is at 0°.

    If `reference_monitor` is None, tries `output_i1` then `freq_monitor_out1`, else falls back to the first monitor.
    """
    monitors = sorted(data.keys())
    if not monitors:
        print("Skipping referenced polar plot: no monitors available.")
        return

    ref_name = reference_monitor or _get_reference_monitor_name(data)
    if ref_name not in data:
        print(f"Reference monitor '{ref_name}' not found; using '{_get_reference_monitor_name(data)}' instead.")
        ref_name = _get_reference_monitor_name(data)

    # Use the first available wavelength entry (assumes filtering to a single wavelength when PLOT_ALL_WAVELENGTHS=False)
    try:
        ref_phase_deg = data[ref_name]["phase_deg"][0]
    except (KeyError, IndexError):
        print("Skipping referenced polar plot: reference phase is unavailable.")
        return

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    colors = ['red', 'blue', 'green', 'orange']

    for (monitor, color) in zip(monitors, colors):
        try:
            magnitude = data[monitor]["transmission"][0]
            phase_rel_deg = data[monitor]["phase_deg"][0] - ref_phase_deg
        except (KeyError, IndexError):
            continue

        phase_rad = np.radians(phase_rel_deg)
        ax.arrow(phase_rad, 0, 0, magnitude, head_width=0.1, head_length=0.01,
                 fc=color, ec=color, linewidth=2.5, label=_display_monitor_name(monitor))
        ax.text(phase_rad, magnitude + 0.01, f"{_display_monitor_name(monitor)}\n{phase_rel_deg:.1f}°",
                ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_ylim(0, 0.15)
    ax.set_title(f"Phasor diagram referenced to {ref_name} = 0° - Source {source_name}",
                 pad=20, fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)


def plot_polar_phase(data):
    """Plot phase of each output port in polar coordinates (phasor diagram)."""
    monitors = sorted(data.keys())
    
    # Create polar plot
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
    
    # Colors for each monitor
    colors = ['red', 'blue', 'green', 'orange']
    
    # Plot each monitor as a phasor
    for monitor, color in zip(monitors, colors):
        # Get phase in radians (convert from degrees if needed)
        phase_rad = np.radians(data[monitor]["phase_deg"][0])
        # Use transmission as magnitude
        magnitude = data[monitor]["transmission"][0]
        
        # Plot arrow from origin to the point
        ax.arrow(phase_rad, 0, 0, magnitude, head_width=0.1, head_length=0.01, 
            fc=color, ec=color, linewidth=2.5, label=_display_monitor_name(monitor))
        
        # Add label at the end of the arrow
        ax.text(phase_rad, magnitude + 0.01, f"{_display_monitor_name(monitor)}\n{data[monitor]['phase_deg'][0]:.1f}°", 
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_ylim(0, 0.15)
    ax.set_title("Phase and amplitude phasor diagram of output ports", pad=20, fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)


def _get_common_wavelengths_all_sources(sources_data, max_sources=5):
    """Return sorted wavelengths common to all monitors and sources (limited to max_sources)."""
    common_wl = None
    for _, data in sorted(sources_data.items())[:max_sources]:
        source_common = None
        for series in data.values():
            wl_set = set(series.get("wavelength", []))
            source_common = wl_set if source_common is None else source_common & wl_set
        if source_common is None:
            continue
        common_wl = source_common if common_wl is None else common_wl & source_common
    return sorted(common_wl) if common_wl else []


def _get_default_wavelengths(sources_data, max_sources=5):
    """Fallback wavelengths list from the first available monitor in the first available source."""
    for _, data in sorted(sources_data.items())[:max_sources]:
        for series in data.values():
            wls = series.get("wavelength", [])
            if wls:
                return sorted(set(wls))
    return []


def plot_phase_shift_all_sources(sources_data, max_sources=5, plot_all_wavelengths=False):
    """Plot phase shift (relative to i1 at 0°) for all sources in subplots.
    
    Creates a figure with subplots for each source (one subplot per input port).
    Each subplot shows the phasor diagram with i1 referenced to 0°.
    If plot_all_wavelengths=True, one figure is created per wavelength.
    """
    num_sources = min(len(sources_data), max_sources)
    if num_sources == 0:
        return

    wavelengths = _get_common_wavelengths_all_sources(sources_data, max_sources=max_sources)
    if not wavelengths:
        wavelengths = _get_default_wavelengths(sources_data, max_sources=max_sources)
        if wavelengths:
            print("No common wavelengths across all sources; using available wavelengths from the first source.")

    if not wavelengths:
        print("No wavelengths available to plot.")
        return

    if not plot_all_wavelengths:
        wavelengths = [wavelengths[0]]

    colors = ['red', 'blue', 'green', 'orange', 'purple']
    desired_source_phases = {
        'i1': 180,
        'i2': 90,
        'i3': 0,
        'i4': 90,
        'i5': 180,
    }

    for wl in wavelengths:
        fig, axes = plt.subplots(1, num_sources, figsize=(5 * num_sources, 5),
                                 subplot_kw=dict(projection='polar'))

        # Handle single subplot case
        if num_sources == 1:
            axes = [axes]

        for idx, (source_name, data) in enumerate(sorted(sources_data.items())[:max_sources]):
            ax = axes[idx]
            monitors = sorted(data.keys())

            # Get reference phase from i1
            ref_monitor = _get_reference_monitor_name(data)
            if ref_monitor not in data:
                print(f"Reference monitor not found in source {source_name}")
                continue

            ref_phase_map = dict(zip(data[ref_monitor]["wavelength"], data[ref_monitor]["phase_deg"]))
            if wl not in ref_phase_map:
                print(f"Reference phase unavailable for source {source_name} at {wl:.5f} μm")
                continue

            ref_phase_deg = ref_phase_map[wl]

            # Plot each monitor as a phasor at this wavelength
            for monitor, color in zip(monitors, colors):
                try:
                    phase_map = dict(zip(data[monitor]["wavelength"], data[monitor]["phase_deg"]))
                    trans_map = dict(zip(data[monitor]["wavelength"], data[monitor]["transmission"]))
                except KeyError:
                    continue

                if wl not in phase_map or wl not in trans_map:
                    continue

                magnitude = trans_map[wl]
                phase_rel_deg = phase_map[wl] - ref_phase_deg

                phase_rad = np.radians(phase_rel_deg)
                ax.arrow(phase_rad, 0, 0, magnitude, head_width=0.1, head_length=0.01,
                         fc=color, ec=color, linewidth=2.5, label=_display_monitor_name(monitor))
                ax.text(phase_rad, magnitude + 0.01, f"{_display_monitor_name(monitor)}\n{phase_rel_deg:.1f}°",
                        ha='center', va='bottom', fontsize=8, fontweight='bold')

            ax.set_ylim(0, 0.15)
            desired_phase = desired_source_phases.get(source_name, 0)
            ax.set_title(f"Source {source_name}\n(Desired: {desired_phase}°)", fontsize=10, fontweight='bold')
            ax.grid(True)

        # Remove legend duplication by using the last subplot
        if num_sources > 0:
            axes[-1].legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=8)

        fig.suptitle(
            f"Phase shift phasor diagrams for all sources (i1 referenced to 0°) - {wl:.5f} μm",
            fontsize=12,
            fontweight='bold',
            y=0.98,
        )
        fig.tight_layout(rect=[0, 0.02, 1, 0.95])


def plot_phase_error_all_sources(sources_data, max_sources=5):
    """Plot phase error (desired vs simulated) for all sources in subplots.
    
    Each input source has a desired phase shift relative to i1:
    - i3: 0° (centre)
    - i2: 90°
    - i4: 90°
    - i1: 180°
    - i5: 180°
    
    Error = simulated phase shift - desired phase shift
    """
    # Desired phase shifts for 5 inputs (centre i3 = 0°, i2/i4 = 90°, i1/i5 = 180°)
    desired_source_phases = {
        'i1': 180,
        'i2': 90,
        'i3': 0,
        'i4': 90,
        'i5': 180,
    }
    
    num_sources = min(len(sources_data), max_sources)
    fig, axes = plt.subplots(1, num_sources, figsize=(5 * num_sources, 5), 
                             subplot_kw=dict(projection='polar'))
    
    # Handle single subplot case
    if num_sources == 1:
        axes = [axes]
    
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    
    for idx, (source_name, data) in enumerate(sorted(sources_data.items())[:max_sources]):
        ax = axes[idx]
        monitors = sorted(data.keys())
        
        # Get reference phase from i1
        ref_monitor = _get_reference_monitor_name(data)
        if ref_monitor not in data:
            print(f"Reference monitor not found in source {source_name}")
            continue
        
        try:
            ref_phase_deg = data[ref_monitor]["phase_deg"][0]
        except (KeyError, IndexError):
            print(f"Reference phase unavailable for source {source_name}")
            continue
        
        # Extract input number from source name (e.g., "i1", "i2")
        desired_phase_shift = desired_source_phases.get(source_name, 0)
        
        # Plot each monitor as a phasor with error calculation
        for monitor, color in zip(monitors, colors):
            try:
                magnitude = data[monitor]["transmission"][0]
                phase_sim_deg = data[monitor]["phase_deg"][0] - ref_phase_deg
            except (KeyError, IndexError):
                continue
            
            # Error = simulated - desired
            phase_error_deg = phase_sim_deg - desired_phase_shift
            
            # Normalize error to [-180, 180]
            while phase_error_deg > 180:
                phase_error_deg -= 360
            while phase_error_deg < -180:
                phase_error_deg += 360
            
            phase_rad = np.radians(phase_error_deg)
            ax.arrow(phase_rad, 0, 0, magnitude, head_width=0.1, head_length=0.01,
                     fc=color, ec=color, linewidth=2.5, label=_display_monitor_name(monitor))
            ax.text(phase_rad, magnitude + 0.01, f"{_display_monitor_name(monitor)}\n{phase_error_deg:.1f}°",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
        
        ax.set_ylim(0, 0.15)
        ax.set_title(f"Source {source_name}\n(Desired: {desired_phase_shift}°)", fontsize=10, fontweight='bold')
        ax.grid(True)
    
    # Remove legend duplication by using the last subplot
    # Remove legend duplication by using the last subplot
    if num_sources > 0:
        axes[-1].legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=8)
    
    fig.suptitle("Phase error phasor diagrams for all sources (Error = Simulated - Desired)", 
                fontsize=12, fontweight='bold', y=0.98)
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])


def main():
    sources_data = load_all_sources(DATA_PATH)
    print(f"Loaded sources: {list(sources_data.keys())}")
    
    # Filter data for all sources to closest wavelength if needed
    filtered_sources_data = {}
    for source_name, data in sources_data.items():
        filtered_sources_data[source_name] = data if PLOT_ALL_WAVELENGTHS else filter_to_closest_wavelength(data, target_wavelength=1.55)
    
    # Plot data for each source
    for source_name in sorted(sources_data.keys()):
        data = sources_data[source_name]
        print(f"\nProcessing Source {source_name}:")
        print(f"  Monitors: {list(data.keys())}")
        
        # Filter to closest wavelength if not plotting all
        plot_data = data if PLOT_ALL_WAVELENGTHS else filter_to_closest_wavelength(data, target_wavelength=1.55)
        
        if not PLOT_ALL_WAVELENGTHS:
            wl = plot_data[list(plot_data.keys())[0]]["wavelength"][0]
            print(f"  Wavelength: {wl:.5f} μm")
        
        # Create plots for this source based on flags
        if PLOT_AMPLITUDE or PLOT_PHASE:
            plot_amplitude_and_phase_for_source(plot_data, source_name)

        if PLOT_PHASE_AMPLITUDE:
            # Absolute phasor diagram
            plot_polar_phase_for_source(plot_data, source_name)
            # Referenced phasor diagram (output_i1 or freq_monitor_out1 at 0°)
            plot_polar_phase_referenced_for_source(plot_data, source_name)
    
    # Plot all sources phase shifts in one figure with subplots
    if PLOT_PHASE_FOR_ALL_SOURCES:
        plot_phase_shift_all_sources(filtered_sources_data, plot_all_wavelengths=PLOT_ALL_WAVELENGTHS)
    
    # Plot all sources phase errors in one figure with subplots
    if PLOT_PHASE_ERROR_FOR_ALL_SOURCES:
        plot_phase_error_all_sources(filtered_sources_data)
    
    plt.show()


if __name__ == "__main__":
    main()
