"""Chip layout construction utilities.

Step 1: load the sharing template GDS, apply basic modifications, and
export to output/gds.
"""

from __future__ import annotations
from pathlib import Path
import gdsfactory as gf
import sys
import ubcpdk

from star_coupler import star_coupler


# ============================================================================
# Component Generation Functions (Relative positioning within circuit)
# ============================================================================

def add_input_grating_coupler_array(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_couplers: int = 8,
	pitch: float = 127.0,
	orientation: str = "East",
) -> list[tuple[float, float]]:
	"""Add input grating coupler array to circuit.
	
	Args:
		circuit: The circuit component to add couplers to.
		origin: Relative origin position (x, y).
		num_couplers: Number of grating couplers.
		pitch: Spacing between couplers (um).
		orientation: Output direction ("North", "South", "East", "West").
	
	Returns:
		List of output port positions (x, y) for routing.
	"""
	gc = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	
	orientation_map = {
		"East": {"angle": 0, "dx": 0, "dy": -pitch},
		"West": {"angle": 180, "dx": 0, "dy": -pitch},
		"North": {"angle": 90, "dx": pitch, "dy": 0},
		"South": {"angle": 270, "dx": pitch, "dy": 0},
	}
	
	config = orientation_map[orientation]
	output_positions = []
	
	for i in range(num_couplers):
		gc_ref = circuit << gc
		x_pos = origin[0] + i * config["dx"]
		y_pos = origin[1] + i * config["dy"]
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(config["angle"])
		
		# Store output port position for routing (offset from GC position)
		output_positions.append((x_pos + 10, y_pos))  # 10um offset
	
	return output_positions


def add_star_coupler(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
	n_inputs: int = 8,
	n_outputs: int = 8,
	**kwargs,
) -> dict:
	"""Add star coupler to circuit (DUMMY - to be implemented).
	
	Args:
		circuit: The circuit component.
		origin: Relative origin position (x, y).
		n_inputs: Number of input ports.
		n_outputs: Number of output ports.
		**kwargs: Additional parameters for star coupler.
	
	Returns:
		Dict with 'input_ports' and 'output_ports' positions.
	"""
	# TODO: Implement actual star coupler using star_coupler() function
	# For now, return dummy port positions
	print(f"[DUMMY] Star coupler at {origin} with {n_inputs} inputs, {n_outputs} outputs")
	
	input_ports = [(origin[0], origin[1] + i * 10) for i in range(n_inputs)]
	output_ports = [(origin[0] + 100, origin[1] + i * 10) for i in range(n_outputs)]
	
	return {"input_ports": input_ports, "output_ports": output_ports}


def add_power_splitter(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
	split_ratio: float = 0.5,
) -> dict:
	"""Add 1x2 power splitter (3dB, 50/50).
	
	Args:
		circuit: The circuit component.
		origin: Relative origin position (x, y).
		split_ratio: Power split ratio (default 0.5 for 50/50).
	
	Returns:
		Dict with 'input_port' and 'output_ports' positions.
	"""
	# TODO: Implement actual 2x1 MMI or Y-branch
	print(f"[DUMMY] Power splitter (1x2) at {origin}")
	
	return {
		"input_port": (origin[0], origin[1]),
		"output_ports": [
			(origin[0] + 50, origin[1] + 5),
			(origin[0] + 50, origin[1] - 5),
		]
	}


def add_interferometer_merger(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
) -> dict:
	"""Add 2x1 interferometer merger (merge two waveguides).
	
	Args:
		circuit: The circuit component.
		origin: Relative origin position (x, y).
	
	Returns:
		Dict with 'input_ports' and 'output_port' positions.
	"""
	# TODO: Implement actual 2x1 combiner/interferometer
	print(f"[DUMMY] Interferometer merger (2x1) at {origin}")
	
	return {
		"input_ports": [
			(origin[0], origin[1] + 5),
			(origin[0], origin[1] - 5),
		],
		"output_port": (origin[0] + 50, origin[1])
	}


def add_output_grating_coupler_array(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_couplers: int = 8,
	pitch: float = 127.0,
	orientation: str = "West",
) -> list[tuple[float, float]]:
	"""Add output grating coupler array to circuit.
	
	Args:
		circuit: The circuit component to add couplers to.
		origin: Relative origin position (x, y).
		num_couplers: Number of grating couplers.
		pitch: Spacing between couplers (um).
		orientation: Input direction ("North", "South", "East", "West").
	
	Returns:
		List of input port positions (x, y) for routing.
	"""
	gc = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	
	orientation_map = {
		"East": {"angle": 0, "dx": 0, "dy": -pitch},
		"West": {"angle": 180, "dx": 0, "dy": -pitch},
		"North": {"angle": 90, "dx": pitch, "dy": 0},
		"South": {"angle": 270, "dx": pitch, "dy": 0},
	}
	
	config = orientation_map[orientation]
	input_positions = []
	
	for i in range(num_couplers):
		gc_ref = circuit << gc
		x_pos = origin[0] + i * config["dx"]
		y_pos = origin[1] + i * config["dy"]
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(config["angle"])
		
		# Store input port position for routing
		input_positions.append((x_pos - 10, y_pos))  # 10um offset
	
	return input_positions


def generate_SC_circuit(
	parent_cell: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_inputs: int = 8,
	num_outputs: int = 8,
	gc_pitch: float = 127.0,
) -> gf.Component:
	"""Generate complete Star Coupler circuit with all components.
	
	This function creates a modular circuit that can be instantiated multiple times.
	All positions are relative to the origin parameter.
	
	Circuit flow:
	1. Input GC array (East orientation)
	2. Star coupler
	3. Power splitters (1x2, 50/50)
	4. Interferometer mergers (2x1)
	5. Output GC array (West orientation)
	
	Args:
		parent_cell: Parent component to add circuit to.
		origin: Absolute origin position for this circuit instance.
		num_inputs: Number of input channels.
		num_outputs: Number of output channels.
		gc_pitch: Grating coupler pitch (um).
	
	Returns:
		The circuit component.
	"""
	print(f"\n=== Generating SC Circuit at origin {origin} ===")
	
	# Create circuit sub-component with relative coordinates
	circuit = gf.Component(f"SC_circuit_{int(origin[0])}_{int(origin[1])}")
	
	# Define relative positions within the circuit
	input_gc_pos = (0, 0)
	star_coupler_pos = (200, 0)
	splitter_start_pos = (400, 0)
	merger_start_pos = (600, 0)
	output_gc_pos = (800, 0)
	
	# 1. Add input grating couplers
	input_ports = add_input_grating_coupler_array(
		circuit,
		origin=input_gc_pos,
		num_couplers=num_inputs,
		pitch=gc_pitch,
		orientation="East",
	)
	
	# 2. Add star coupler
	sc_ports = add_star_coupler(
		circuit,
		origin=star_coupler_pos,
		n_inputs=num_inputs,
		n_outputs=num_outputs,
	)
	
	# 3. Add power splitters (one per output channel)
	splitter_outputs = []
	for i in range(num_outputs):
		splitter_pos = (splitter_start_pos[0], splitter_start_pos[1] + i * 50)
		splitter = add_power_splitter(circuit, origin=splitter_pos)
		splitter_outputs.extend(splitter["output_ports"])
	
	# 4. Add interferometer mergers
	merger_outputs = []
	for i in range(num_outputs):
		merger_pos = (merger_start_pos[0], merger_start_pos[1] + i * 50)
		merger = add_interferometer_merger(circuit, origin=merger_pos)
		merger_outputs.append(merger["output_port"])
	
	# 5. Add output grating couplers
	output_ports = add_output_grating_coupler_array(
		circuit,
		origin=output_gc_pos,
		num_couplers=num_outputs,
		pitch=gc_pitch,
		orientation="West",
	)
	
	print(f"[OK] SC Circuit generated with {num_inputs} inputs, {num_outputs} outputs")
	
	# Add circuit to parent cell at absolute origin position
	circuit_ref = parent_cell << circuit
	circuit_ref.move(origin)
	
	return circuit


# ============================================================================
# Legacy Functions (for backward compatibility)
# ============================================================================

def add_grating_coupler_array_to_subdie(
	subdie_cell: gf.Component,
	num_couplers: int = 8,
	pitch: float = 127.0,
	orientation: str = "East",
	start_position: tuple[float, float] = (167.84264, 1148.75036),
) -> None:
	"""Add grating couplers to a Sub_Die cell.
	
	Args:
		subdie_cell: The sub-die cell to add couplers to.
		num_couplers: Number of grating couplers to add.
		pitch: Spacing between couplers (in um).
		orientation: Direction of coupler outputs ("North", "South", "East", "West").
		start_position: Position of the first (top/northmost) coupler (x, y).
	"""
	# Create grating coupler component for SiN TE at 1550 nm from UBCPDK
	gc = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	
	# Map orientation to rotation and spacing direction
	orientation_map = {
		"East": {"angle": 0, "dx": 0, "dy": -pitch},      # Vertical spacing, output right
		"West": {"angle": 180, "dx": 0, "dy": -pitch},    # Vertical spacing, output left
		"North": {"angle": 90, "dx": pitch, "dy": 0},     # Horizontal spacing, output up
		"South": {"angle": 270, "dx": pitch, "dy": 0},    # Horizontal spacing, output down
	}
	
	if orientation not in orientation_map:
		raise ValueError(f"Invalid orientation '{orientation}'. Choose from {list(orientation_map.keys())}")
	
	config = orientation_map[orientation]
	x_start, y_start = start_position
	
	# Add grating couplers
	for i in range(num_couplers):
		gc_ref = subdie_cell << gc
		x_pos = x_start + i * config["dx"]
		y_pos = y_start + i * config["dy"]
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(config["angle"])
	
	print(f"[OK] {num_couplers} grating couplers added to sub-die ({orientation}) with pitch {pitch} um")


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_GDS = ROOT_DIR / "components" / "sharing_template_etch.gds"
OUTPUT_DIR = ROOT_DIR / "output" / "gds"

# Target lower-left origin for the chip (in um)
CHIP_ORIGIN = (3143.33023, 6156.66426)


def find_subdie_cell(cell: gf.Component, target_name: str) -> gf.Component | None:
	"""Recursively search for a Sub_Die cell by name."""
	for inst in cell.insts:
		if target_name in inst.cell.name:
			return inst.cell
		result = find_subdie_cell(inst.cell, target_name)
		if result:
			return result
	return None


def build_from_template(
	template_path: Path = TEMPLATE_GDS,
	chip_origin: tuple[float, float] = CHIP_ORIGIN,
) -> gf.Component:
	"""Load the template GDS and add components.

	Current modifications:
	- Add SC circuit to Sub_Die_2 using new modular functions
	"""

	if not template_path.exists():
		raise FileNotFoundError(f"Template GDS not found: {template_path}")

	template = gf.import_gds(template_path)
	chip = gf.Component("chip_layout")
	ref = chip << template

	# Find Sub_Die_2 and add complete SC circuit
	subdie_2 = find_subdie_cell(ref.cell, "Sub_Die_2")
	if subdie_2:
		# Generate complete SC circuit with relative positioning
		generate_SC_circuit(
			parent_cell=subdie_2,
			origin=(50, 100),  # Absolute position within Sub_Die_2
			num_inputs=8,
			num_outputs=8,
			gc_pitch=127.0,
		)
	else:
		print("[WARNING] Sub_Die_2 not found")

	return chip


def export_gds(component: gf.Component, output_dir: Path = OUTPUT_DIR) -> Path:
	"""Export the component to output/gds."""

	output_dir.mkdir(parents=True, exist_ok=True)
	out_path = output_dir / "SC_circuit_layout.gds"
	component.write_gds(out_path)
	return out_path


def main() -> None:
	"""Entry point for step 1."""

	chip = build_from_template()
	out_path = export_gds(chip)
	print(f"GDS exported to: {out_path}")
	chip.show()




if __name__ == "__main__":
	main()
