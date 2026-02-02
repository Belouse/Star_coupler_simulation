"""Chip layout construction utilities.

Step 1: load the sharing template GDS, apply basic modifications, and
export to output/gds.
"""

from __future__ import annotations
from pathlib import Path
import warnings
import gdsfactory as gf
import ubcpdk

from star_coupler import star_coupler


# Suppress gdsfactory warnings about width being ignored when a cross_section is provided
warnings.filterwarnings("ignore", message=".*ignored for cross_section.*")


# ============================================================================
# Component Generation Functions (Relative positioning within circuit)
# ============================================================================

def add_port_label(
	circuit: gf.Component,
	text: str,
	position: tuple[float, float],
	size: float = 8.0,
	layer: tuple[int, int] = ubcpdk.LAYER.TEXT,
) -> None:
	"""Add engraved text label on the chip."""
	label = gf.components.text(text=text, size=size, layer=layer)
	label_ref = circuit << label
	label_ref.move(position)

def add_input_grating_coupler_array(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_couplers: int = 8,
	pitch: float = 127.0,
	orientation: str = "East",
	label_prefix: str | None = "IN",
	label_offset: tuple[float, float] = (25.0, 5.0),
	label_size: float = 8.0,
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

		# Add engraved label near port
		if label_prefix:
			add_port_label(
				circuit,
				text=f"{label_prefix}{i + 1}",
				position=(gc_ref.center[0] + label_offset[0], gc_ref.center[1] + label_offset[1]),
				size=label_size,
			)

	return gc_refs


def add_star_coupler(
	circuit: gf.Component,
	origin: tuple[float, float] = (0, 0),
	n_inputs: int = 8,
	n_outputs: int = 8,
	**kwargs,
) -> dict:
	"""Add star coupler to circuit.
	
	Args:
		circuit: The circuit component.
		origin: Relative origin position (x, y).
		n_inputs: Number of input ports.
		n_outputs: Number of output ports.
		**kwargs: Additional parameters for star coupler.
	
	Returns:
		Dict with 'ref', 'input_ports', and 'output_ports'.
	"""
	star = star_coupler(n_inputs=n_inputs, n_outputs=n_outputs, **kwargs)
	star_ref = circuit << star
	star_ref.move(origin)

	input_ports = []
	for i in range(n_inputs):
		name = f"i{i + 1}"
		if name in star_ref.ports:
			input_ports.append(star_ref.ports[name])

	output_ports = []
	for i in range(n_outputs):
		name = f"out{i + 1}"
		if name in star_ref.ports:
			output_ports.append(star_ref.ports[name])

	return {"ref": star_ref, "input_ports": input_ports, "output_ports": output_ports}


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
	label_prefix: str | None = "OUT",
	label_offset: tuple[float, float] = (-35.0, 0.0),
	label_size: float = 8.0,
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

		# Add engraved label near port
		if label_prefix:
			add_port_label(
				circuit,
				text=f"{label_prefix}{i + 1}",
				position=(gc_ref.center[0] + label_offset[0], gc_ref.center[1] + label_offset[1]),
				size=label_size,
			)

	return gc_refs


def connect_gc_top_bottom_drawn(
	circuit: gf.Component,
	gc_refs: list,
	front_dx: float = 0.0,
	first_drop: float = 20.0,
	back_offset: float = 25.0,
	bottom_rise: float = 0.0,
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

	# Build explicit SiN waveguide segments with Euler bends
	cs = gf.cross_section.cross_section(layer=SIN_LAYER, width=0.75)
	bend_r = gf.components.bend_euler(angle=-90, cross_section=cs)
	bend_l = gf.components.bend_euler(angle=90, cross_section=cs)

	def place_chain(start_port, elements):
		current_port = start_port
		for comp in elements:
			ref = circuit << comp
			ref.connect("o1", current_port)
			current_port = ref.ports["o2"]
		return current_port

	def place_start_straight_at(port, length: float = 5.0):
		"""Place a short SiN straight with its o1 aligned to a given port position."""
		straight = gf.components.straight(length=length, cross_section=cs)
		ref = circuit << straight
		# rotate to match port orientation, then move so o1 aligns to port center
		try:
			ref.rotate(port.orientation, center=(0, 0))
		except Exception:
			pass
		dx = port.center[0] - ref.ports["o1"].center[0]
		dy = port.center[1] - ref.ports["o1"].center[1]
		ref.move((dx, dy))
		return ref.ports["o2"]

	def place_start_taper_at(port, length: float = 20.0):
		"""Place a short SiN taper with its o1 aligned to a given port position."""
		taper = gf.components.taper(length=length, width1=0.75, width2=0.75, layer=SIN_LAYER)
		ref = circuit << taper
		try:
			ref.rotate(port.orientation, center=(0, 0))
		except Exception:
			pass
		dx = port.center[0] - ref.ports["o1"].center[0]
		dy = port.center[1] - ref.ports["o1"].center[1]
		ref.move((dx, dy))
		return ref.ports["o2"]

	# Top segment: taper -> right bend -> right bend -> straight -> right bend (down) to backbone
	cur = place_start_taper_at(p_top, length=20)
	cur = place_chain(cur, [gf.components.straight(length=front_dx, cross_section=cs)])
	cur = place_chain(cur, [bend_r])
	cur = place_chain(cur, [gf.components.straight(length=first_drop, cross_section=cs)])
	cur = place_chain(cur, [bend_r])
	straight_len = max(10, cur.x - x_back)
	cur = place_chain(cur, [gf.components.straight(length=straight_len, cross_section=cs)])
	cur = place_chain(cur, [bend_l])

	# Backbone vertical straight from top to bottom anchor
	backbone_len = abs(cur.y - y_mid - 45)
	backbone = circuit << gf.components.straight(length=max(1, backbone_len), cross_section=cs)
	backbone.rotate(90)
	backbone.connect("o1", cur)
	backbone_bottom = backbone.ports["o2"]

	# Bottom segment: taper -> left bend -> left bend -> straight -> right bend into backbone
	cur_b = place_start_taper_at(p_bottom, length=20)
	cur_b = place_chain(cur_b, [bend_l])
	cur_b = place_chain(cur_b, [gf.components.straight(length=bottom_rise, cross_section=cs)])
	cur_b = place_chain(cur_b, [bend_l])
	straight_len_b = max(10, cur_b.x - x_back)
	cur_b = place_chain(cur_b, [gf.components.straight(length=straight_len_b, cross_section=cs)])
	cur_b = place_chain(cur_b, [bend_r])
	# Connect to backbone bottom by a short straight if needed
	join_len = abs(backbone_bottom.y - cur_b.y)
	if join_len > 0:
		cur_b = place_chain(cur_b, [gf.components.straight(length=max(1, join_len), cross_section=cs)])



def place_star_coupler_left_of_gcs(
	star_ref: gf.ComponentReference,
	gc_refs: list,
	gap: float = 50.0,
) -> None:
	"""Place star coupler to the left of the GC array with a fixed gap."""
	if not gc_refs:
		return
	gc_min_x = min(ref.dbbox().left for ref in gc_refs)
	gc_center_y = sum(ref.center[1] for ref in gc_refs) / len(gc_refs)

	star_bbox = star_ref.dbbox()
	star_center_y = (star_bbox.top + star_bbox.bottom) / 2
	dx = gc_min_x - gap - star_bbox.right
	dy = gc_center_y - star_center_y
	star_ref.move((dx, dy))


def connect_star_coupler_inputs_to_gcs(
	circuit: gf.Component,
	star_ref: gf.ComponentReference,
	gc_refs: list,
	start_gc_index: int = 1,
	bend_radius: float = 40.0,
) -> None:
	"""Route star coupler input ports to the GC array starting at IN2.

	Mapping: i1 -> IN2, i2 -> IN3, i3 -> IN4, ...
	"""
	cs = gf.cross_section.cross_section(layer=SIN_LAYER, width=0.75)

	input_port_names = [port.name for port in star_ref.ports if port.name.startswith("i")]
	input_port_names.sort(key=lambda n: int(n[1:]))

	for i, port_name in enumerate(input_port_names):
		gc_index = i + start_gc_index
		if gc_index >= len(gc_refs):
			break
		gc_port = list(gc_refs[gc_index].ports)[0]
		sc_port = star_ref.ports[port_name]
		gf.routing.route_single(
			circuit,
			sc_port,
			gc_port,
			cross_section=cs,
			radius=bend_radius,
			auto_taper=False,
			allow_width_mismatch=True,
		)

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
	
	# Create circuit sub-component with relative coordinates
	circuit = gf.Component(f"SC_circuit_{int(origin[0])}_{int(origin[1])}")
	
	# Define relative positions within the circuit
	input_gc_pos = (0, 0)
	star_coupler_pos = (0, 0)
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
	
	# 2. Add star coupler (placed left of input GC array)
	sc_ports = add_star_coupler(
		circuit,
		origin=star_coupler_pos,
		n_inputs=num_inputs,
		n_outputs=num_outputs,
	)
	place_star_coupler_left_of_gcs(sc_ports["ref"], input_gc_refs, gap=50.0)
	connect_star_coupler_inputs_to_gcs(
		circuit,
		star_ref=sc_ports["ref"],
		gc_refs=input_gc_refs,
		start_gc_index=1,
		bend_radius=40.0,
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
	
	
	# Add circuit to parent cell at absolute origin position
	circuit_ref = parent_cell << circuit
	circuit_ref.move(origin)
	
	return circuit



ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_GDS = ROOT_DIR / "components" / "sharing_template_etch.gds"
OUTPUT_DIR = ROOT_DIR / "output" / "gds"

# Target lower-left origin for the chip (in um)
CHIP_ORIGIN = (3143.33023, 6156.66426)

# SiN waveguide layer (SiePIC 4/0)
SIN_LAYER = (4, 0)


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
