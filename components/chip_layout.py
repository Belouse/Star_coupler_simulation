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
) -> list:
	"""Add input grating coupler array to circuit.
	
	Args:
		circuit: The circuit component to add couplers to.
		origin: Relative origin position (x, y).
		num_couplers: Number of grating couplers.
		pitch: Spacing between couplers (um).
		orientation: Output direction ("North", "South", "East", "West").
	
	Returns:
		List of grating coupler instance references.
	"""
	gc = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	
	orientation_map = {
		"East": {"angle": 0, "dx": 0, "dy": -pitch},
		"West": {"angle": 180, "dx": 0, "dy": -pitch},
		"North": {"angle": 90, "dx": pitch, "dy": 0},
		"South": {"angle": 270, "dx": pitch, "dy": 0},
	}
	
	config = orientation_map[orientation]
	gc_refs = []

	for i in range(num_couplers):
		gc_ref = circuit << gc
		x_pos = origin[0] + i * config["dx"]
		y_pos = origin[1] + i * config["dy"]
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(config["angle"])
        
		# Store instance reference for later routing
		gc_refs.append(gc_ref)

	return gc_refs


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
) -> list:
	"""Add output grating coupler array to circuit.
	
	Args:
		circuit: The circuit component to add couplers to.
		origin: Relative origin position (x, y).
		num_couplers: Number of grating couplers.
		pitch: Spacing between couplers (um).
		orientation: Input direction ("North", "South", "East", "West").
	
	Returns:
		List of grating coupler instance references.
	"""
	gc = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	
	orientation_map = {
		"East": {"angle": 0, "dx": 0, "dy": -pitch},
		"West": {"angle": 180, "dx": 0, "dy": -pitch},
		"North": {"angle": 90, "dx": pitch, "dy": 0},
		"South": {"angle": 270, "dx": pitch, "dy": 0},
	}
	
	config = orientation_map[orientation]
	gc_refs = []

	for i in range(num_couplers):
		gc_ref = circuit << gc
		x_pos = origin[0] + i * config["dx"]
		y_pos = origin[1] + i * config["dy"]
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(config["angle"])

		gc_refs.append(gc_ref)

	return gc_refs


def connect_gc_top_bottom_drawn(
	circuit: gf.Component,
	gc_refs: list,
	front_dx: float = 20.0,
	first_drop: float = 20.0,
	back_offset: float = 40.0,
	bottom_rise: float = 20.0,
	bottom_dx1: float = 30.0,
	bottom_dx2: float = 30.0,
	end_dx: float = 0.0,
) -> None:
	"""Connect top GC to bottom GC following the drawn path (image #3).

	Path intent (from top):
	- short straight from top GC (east)
	- right bend (south)
	- right bend (west) to the left backbone
	- long vertical backbone behind the GC array
	- bottom segment: taper, left bend, left bend, straight, right turn into backbone
	"""
	if len(gc_refs) < 2:
		raise ValueError("Need at least 2 grating couplers")

	top = gc_refs[0]
	bottom = gc_refs[-1]
	p_top = list(top.ports)[0]
	p_bottom = list(bottom.ports)[0]

	xs = [ref.center[0] for ref in gc_refs]
	x_back = min(xs) - back_offset

	x_top = p_top.x
	y_top = p_top.y
	y_bottom = p_bottom.y

	# Waypoints (absolute coordinates) defining the drawn path
	# Bottom logic (reverse of user description):
	# backbone -> right -> down -> right -> down -> into GC
	y_mid = y_bottom + bottom_rise
	x_b1 = p_bottom.x - end_dx - bottom_dx1 - bottom_dx2
	x_b2 = p_bottom.x - end_dx - bottom_dx1

	# Build explicit SiN waveguide segments with Euler bends and taper
	cs = ubcpdk.PDK.cross_sections["strip"]
	bend_r = gf.components.bend_euler(angle=-90, cross_section=cs)
	bend_l = gf.components.bend_euler(angle=90, cross_section=cs)

	def add_straight(length: float) -> gf.ComponentReference:
		return circuit << gf.components.straight(length=length, cross_section=cs)

	def place_chain(start_port, elements):
		current_port = start_port
		for comp in elements:
			ref = circuit << comp
			ref.connect("o1", current_port)
			current_port = ref.ports["o2"]
		return current_port

	# Top segment: taper -> right bend -> right bend -> straight to backbone top
	# Taper from GC width to waveguide width
	taper_top = gf.components.taper(length=20, width1=0.75, width2=0.5, cross_section=cs)
	cur = place_chain(p_top, [taper_top])
	cur = place_chain(cur, [gf.components.straight(length=front_dx, cross_section=cs)])
	cur = place_chain(cur, [bend_r])
	cur = place_chain(cur, [gf.components.straight(length=first_drop, cross_section=cs)])
	cur = place_chain(cur, [bend_r])
	straight_len = max(10, cur.x - x_back)
	cur = place_chain(cur, [gf.components.straight(length=straight_len, cross_section=cs)])

	# Backbone vertical straight from top to bottom anchor
	backbone_len = max(10, cur.y - y_mid)
	backbone = circuit << gf.components.straight(length=backbone_len, cross_section=cs)
	backbone.rotate(90)
	backbone.connect("o1", cur)
	backbone_bottom = backbone.ports["o2"]

	# Bottom segment: taper -> left bend -> left bend -> straight -> right bend into backbone
	taper_bot = gf.components.taper(length=20, width1=0.75, width2=0.5, cross_section=cs)
	cur_b = place_chain(p_bottom, [taper_bot])
	cur_b = place_chain(cur_b, [bend_l])
	cur_b = place_chain(cur_b, [gf.components.straight(length=bottom_rise, cross_section=cs)])
	cur_b = place_chain(cur_b, [bend_l])
	straight_len_b = max(10, cur_b.x - x_back)
	cur_b = place_chain(cur_b, [gf.components.straight(length=straight_len_b, cross_section=cs)])
	cur_b = place_chain(cur_b, [bend_r])
	# Connect to backbone bottom by a short straight if needed
	join_len = max(10, cur_b.y - backbone_bottom.y)
	cur_b = place_chain(cur_b, [gf.components.straight(length=join_len, cross_section=cs)])

	print(f"[OK] Drew top->bottom GC with Euler bends + taper, back x={x_back}")


def generate_SC_circuit(
	parent_cell: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_inputs: int = 8,
	num_outputs: int = 0,
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
	
	# 1. Add input grating couplers (returns instance refs)
	input_gc_refs = add_input_grating_coupler_array(
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
	
	# 5. Add output grating couplers (returns instance refs)
	output_gc_refs = add_output_grating_coupler_array(
		circuit,
		origin=output_gc_pos,
		num_couplers=num_outputs,
		pitch=gc_pitch,
		orientation="West",
	)

	# Routing: connect top GC to bottom GC following drawn path
	try:
		connect_gc_top_bottom_drawn(circuit, input_gc_refs)
	except Exception as e:
		print(f"[WARN] connect_gc_top_bottom_drawn failed: {e}")
	
	print(f"[OK] SC Circuit generated with {num_inputs} inputs, {num_outputs} outputs")
	
	# Add circuit to parent cell at absolute origin position
	circuit_ref = parent_cell << circuit
	circuit_ref.move(origin)
	
	return circuit



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
			origin=(200, 1170),  # Absolute position within Sub_Die_2
			num_inputs=8,
			num_outputs=0,
			gc_pitch=127.0,
		)
		# Add another SC circuit instance at different position if needed


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
