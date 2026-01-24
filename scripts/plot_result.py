import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Configuration: Plot all wavelengths or only closest to 1.55um
PLOT_ALL_WAVELENGTHS = False

# Path to the simulation results (last block after the final "Source:" marker is used)
DATA_PATH = Path(r"C:\\Users\\Éloi Blouin\\Desktop\\git\\Star_coupler_simulation\\output\\simulations\\star_coupler_S_matrix_unknown.txt")


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
    """Plot amplitude and phase for a single source."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Amplitude plot
    for monitor, series in data.items():
        ax1.plot(series["wavelength"], series["transmission"], marker="o", label=monitor)
    ax1.set_title(f"Output port amplitudes - Source {source_name}")
    ax1.set_xlabel("Wavelength (um)")
    ax1.set_ylabel("Transmission (T)")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Phase plot
    for monitor, series in data.items():
        ax2.plot(series["wavelength"], series["phase_deg"], marker="o", label=monitor)
    ax2.set_title(f"Output port phases - Source {source_name}")
    ax2.set_xlabel("Wavelength (um)")
    ax2.set_ylabel("Phase (deg)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()


def plot_amplitude_and_phase(data):
    plt.figure(figsize=(10, 6))
    for monitor, series in data.items():
        plt.plot(series["wavelength"], series["transmission"], marker="o", label=f"{monitor} amplitude")
    plt.title("Output port amplitudes")
    plt.xlabel("Wavelength (um)")
    plt.ylabel("Transmission (T)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.figure(figsize=(10, 6))
    for monitor, series in data.items():
        plt.plot(series["wavelength"], series["phase_deg"], marker="o", label=f"{monitor} phase")
    plt.title("Output port phases")
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
                fc=color, ec=color, linewidth=2.5, label=monitor)
        
        # Add label at the end of the arrow
        ax.text(phase_rad, magnitude + 0.01, f"{monitor}\n{data[monitor]['phase_deg'][0]:.1f}°", 
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_ylim(0, 0.15)
    ax.set_title(f"Phase and amplitude phasor diagram - Source {source_name}", pad=20, fontsize=12, fontweight='bold')
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
                fc=color, ec=color, linewidth=2.5, label=monitor)
        
        # Add label at the end of the arrow
        ax.text(phase_rad, magnitude + 0.01, f"{monitor}\n{data[monitor]['phase_deg'][0]:.1f}°", 
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_ylim(0, 0.15)
    ax.set_title("Phase and amplitude phasor diagram of output ports", pad=20, fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)


def main():
    sources_data = load_all_sources(DATA_PATH)
    print(f"Loaded sources: {list(sources_data.keys())}")
    
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
        
        # Create plots for this source
        plot_amplitude_and_phase_for_source(plot_data, source_name)
        plot_polar_phase_for_source(plot_data, source_name)
    
    plt.show()


if __name__ == "__main__":
    main()
