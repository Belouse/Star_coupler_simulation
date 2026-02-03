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


def normalize_port_width(
	circuit: gf.Component,
	port: gf.Port,
	target_width: float,
	length: float = 10.0,
) -> gf.Port:
	"""Insert a taper if needed so the returned port has target_width."""
	if abs(port.width - target_width) < 1e-6:
		return port
	taper = gf.components.taper(
		length=length,
		width1=port.width,
		width2=target_width,
		layer=port.layer,
	)
	ref = circuit << taper
	ref.connect("o1", port)
	return ref.ports["o2"]


def flip_port_orientation(
	circuit: gf.Component,
	port: gf.Port,
	target_orientation: int,
	length: float = 20.0,
) -> gf.Port:
	"""Returns a new port with target orientation by inserting a short straight."""
	if port.orientation == target_orientation:
		return port
	cs_port = gf.cross_section.cross_section(layer=port.layer, width=port.width)
	straight = gf.components.straight(length=length, cross_section=cs_port)
	ref = circuit << straight
	if target_orientation == 0:
		ref.connect("o2", port)
		return ref.ports["o1"]
	if target_orientation == 180:
		ref.connect("o1", port)
		return ref.ports["o2"]
	return port


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
	n_inputs: int = 5,
	n_outputs: int = 4,
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
	star = star_coupler(n_inputs=n_inputs, n_outputs=n_outputs, layer=SIN_LAYER, **kwargs)
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
	label_order: str = "top_to_bottom",
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

	# Add engraved labels after placement to enforce ordering
	if label_prefix and gc_refs:
		if label_order not in {"top_to_bottom", "bottom_to_top"}:
			raise ValueError("label_order must be 'top_to_bottom' or 'bottom_to_top'")
		sorted_refs = sorted(gc_refs, key=lambda r: r.center[1], reverse=(label_order == "top_to_bottom"))
		for index, gc_ref in enumerate(sorted_refs, start=1):
			add_port_label(
				circuit,
				text=f"{label_prefix}{index}",
				position=(gc_ref.center[0] + label_offset[0], gc_ref.center[1] + label_offset[1]),
				size=label_size,
			)

	return gc_refs


def connect_gc_top_bottom_drawn(
	circuit: gf.Component,
	gc_refs: list,
	front_dx: float = 0.0,
	first_drop: float = 20.0,
	back_offset: float = 5.0,
	bottom_rise: float = 0.0,
	bottom_dx1: float = 30.0,
	bottom_dx2: float = 30.0,
	end_dx: float = 0.0,
) -> None:
	"""Connect top GC to bottom GC

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
	bend_r = gf.components.bend_euler(angle=-90, cross_section=cs, radius=30.0)
	bend_l = gf.components.bend_euler(angle=90, cross_section=cs, radius=30.0)

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
	backbone_len = abs(cur.y - y_mid - 135)
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



def place_star_coupler_gcs(
	star_ref: gf.ComponentReference,
	gc_refs: list,
	gap: float = 0.0,
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
	bend_radius: float = 60.0,
) -> None:
	"""Route star coupler input ports to the GC array starting at IN2.

	Mapping: top star port -> IN2, bottom star port -> IN6 (top-to-bottom order).
	"""
	input_ports = [port for port in star_ref.ports if port.name.startswith("i")]
	input_ports.sort(key=lambda p: p.center[1], reverse=True)

	gc_ports = []
	for i in range(len(input_ports)):
		gc_index = start_gc_index + i
		if gc_index >= len(gc_refs):
			break
		gc_port = list(gc_refs[gc_index].ports)[0]
		gc_ports.append(
			gf.Port(
				name=f"gc_{gc_index}",
				center=gc_port.center,
				width=gc_port.width,
				orientation=gc_port.orientation,
				layer=gf.get_layer(SIN_LAYER),
			)
		)

	def _extend_port(port: gf.Port, length: float = 25.0) -> gf.Port:
		"""Extend a port in its facing direction by a straight of given length."""
		cs_port = gf.cross_section.cross_section(layer=port.layer, width=port.width)
		straight = gf.components.straight(length=length, cross_section=cs_port)
		ref = circuit << straight
		ref.connect("o1", port)
		return ref.ports["o2"]

	if input_ports and gc_ports:
		count = min(len(input_ports), len(gc_ports))
		input_ports = input_ports[:count]
		gc_ports = gc_ports[:count]

		# Normalize widths and orientations for S-bend routing (expects same orientation)
		target_orientation = int(gc_ports[0].orientation)
		target_width = min([p.width for p in (input_ports + gc_ports)])
		cs = gf.cross_section.cross_section(
			layer=input_ports[0].layer,
			width=target_width,
			radius=bend_radius,
		)
		input_ports_norm = [
			flip_port_orientation(
				circuit,
				normalize_port_width(circuit, port, target_width),
				target_orientation,
			)
			for port in input_ports
		]
		gc_ports_norm = [
			flip_port_orientation(
				circuit,
				normalize_port_width(circuit, port, target_width),
				target_orientation,
			)
			for port in gc_ports
		]

		# Keep a deterministic top-to-bottom pairing
		input_ports_norm.sort(key=lambda p: p.center[1], reverse=True)
		gc_ports_norm.sort(key=lambda p: p.center[1], reverse=True)

		# Use S-bend only for i3/i4 (indices 2 and 3 in top-to-bottom order) for SC input ports
		sbend_indices = {	2, 3}
		bundle_in = [p for i, p in enumerate(input_ports_norm) if i not in sbend_indices]
		bundle_gc = [p for i, p in enumerate(gc_ports_norm) if i not in sbend_indices]
		sbend_in = [p for i, p in enumerate(input_ports_norm) if i in sbend_indices]
		sbend_gc = [p for i, p in enumerate(gc_ports_norm) if i in sbend_indices]

		# Push bends 25um to the right by extending GC-side ports (bundle only)
		bundle_gc = [_extend_port(p, 35.0) for p in bundle_gc]

		if bundle_in and bundle_gc:
			gf.routing.route_bundle(
				circuit,
				bundle_gc,
				bundle_in,
				cross_section=cs,
				radius=bend_radius,
				sort_ports=False,
				separation=10.0
			)

		if sbend_in and sbend_gc:
			gf.routing.route_bundle_sbend(
				circuit,
				sbend_gc,
				sbend_in,
				enforce_port_ordering=True,
				cross_section=cs,
			)

def _route_outputs_power_mode(
	circuit: gf.Component,
	star_ref: gf.ComponentReference,
	output_gc_refs: list,
) -> None:
	"""Route star coupler outputs directly to GC array (power mode).

	TODO: Implement direct routing from star outputs to GC ports.
	"""
	# TODO: Replace with production routing constraints if needed
	output_ports = [p for p in star_ref.ports if p.name.startswith("out")]
	if not output_ports or not output_gc_refs:
		return

	# Ensure OUT1 (top) connects to OUT6 (bottom)
	gc_refs_sorted = sorted(output_gc_refs, key=lambda r: r.center[1], reverse=True)
	if len(gc_refs_sorted) >= 2:
		connect_gc_top_bottom_drawn(circuit, gc_refs_sorted)

	# Route star outputs to OUT2..OUT5 (skip top/bottom GC)
	gc_refs_for_outputs = gc_refs_sorted
	if len(gc_refs_sorted) >= len(output_ports) + 2:
		gc_refs_for_outputs = gc_refs_sorted[1:-1]

	output_ports = [
		gf.Port(
			name=port.name,
			center=port.center,
			width=port.width,
			orientation=port.orientation,
			layer=gf.get_layer(SIN_LAYER),
		)
		for port in output_ports
	]
	output_ports.sort(key=lambda p: p.center[1], reverse=True)

	gc_ports = []
	for ref in gc_refs_for_outputs:
		gc_port = list(ref.ports)[0]
		gc_ports.append(
			gf.Port(
				name=gc_port.name,
				center=gc_port.center,
				width=gc_port.width,
				orientation=gc_port.orientation,
				layer=gf.get_layer(SIN_LAYER),
			)
		)
	gc_ports.sort(key=lambda p: p.center[1], reverse=True)

	count = min(len(output_ports), len(gc_ports))
	output_ports = output_ports[:count]
	gc_ports = gc_ports[:count]

	# Normalize widths and orientations for routing
	target_orientation = int(gc_ports[0].orientation)
	target_width = min([p.width for p in (output_ports + gc_ports)])
	cs = gf.cross_section.cross_section(
		layer=output_ports[0].layer,
		width=target_width,
		radius=50.0,
	)
	output_ports_norm = [
		flip_port_orientation(
			circuit,
			normalize_port_width(circuit, port, target_width),
			target_orientation,
		)
		for port in output_ports
	]
	gc_ports_norm = [
		flip_port_orientation(
			circuit,
			normalize_port_width(circuit, port, target_width),
			target_orientation,
		)
		for port in gc_ports
	]

	output_ports_norm.sort(key=lambda p: p.center[1], reverse=True)
	gc_ports_norm.sort(key=lambda p: p.center[1], reverse=True)

	# Use S-bend for OUT3/OUT4 (indices 1 and 2 in top-to-bottom order)
	sbend_indices = {1, 2}
	bundle_out = [p for i, p in enumerate(output_ports_norm) if i not in sbend_indices]
	bundle_gc = [p for i, p in enumerate(gc_ports_norm) if i not in sbend_indices]
	sbend_out = [p for i, p in enumerate(output_ports_norm) if i in sbend_indices]
	sbend_gc = [p for i, p in enumerate(gc_ports_norm) if i in sbend_indices]

	if bundle_out and bundle_gc:
		gf.routing.route_bundle(
			circuit,
			bundle_gc,
			bundle_out,
			cross_section=cs,
			radius=50.0,
			sort_ports=False,
			separation=10.0,
			auto_taper=False,
		)

	if sbend_out and sbend_gc:
		gf.routing.route_bundle_sbend(
			circuit,
			sbend_gc,
			sbend_out,
			enforce_port_ordering=True,
			cross_section=cs,
		)


def _route_outputs_amplitude_same_length_mode(
	circuit: gf.Component,
	star_ref: gf.ComponentReference,
	output_gc_refs: list,
) -> None:
	"""Route star coupler outputs to GC array with equal path length.

	TODO: Implement equal-length routing from star outputs to GC ports.
	"""
	# TODO: Add length-matching serpentine or path-equalization routing
	_ = (circuit, star_ref, output_gc_refs)


def _route_outputs_phase_mode(
	circuit: gf.Component,
	star_ref: gf.ComponentReference,
) -> None:
	"""Interfere star coupler outputs pairwise (phase mode).

	Pairs: 1vs2, 2vs3, 3vs4.
	TODO: Implement interferometer/combiner routing for these pairs.
	"""
	# TODO: Insert interferometers (1vs2, 2vs3, 3vs4)
	_ = (circuit, star_ref)


def generate_SC_circuit(
	parent_cell: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_inputs: int = 8,
	num_outputs: int = 4,
	gc_pitch: float = 127.0,
	feature_mode: str = "power",
	output_gc_dx: float = 0.0,
	output_gc_dy: float = 0.0,
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
		n_inputs=5,
		n_outputs=4,
	)
	place_star_coupler_gcs(sc_ports["ref"], input_gc_refs, gap=-470.0)
	connect_star_coupler_inputs_to_gcs(
		circuit,
		star_ref=sc_ports["ref"],
		gc_refs=input_gc_refs,
		start_gc_index=1,
		bend_radius=50.0,
	)
	
	# 3. Add output grating couplers (returns instance refs)
	output_gc_count = num_outputs + 2
	output_ports = sc_ports.get("output_ports", [])
	if output_ports:
		max_x = max(p.center[0] for p in output_ports)
		min_y = min(p.center[1] for p in output_ports)
		max_y = max(p.center[1] for p in output_ports)
		star_outputs_center_y = (min_y + max_y) / 2.0
	else:
		star_bbox = sc_ports["ref"].dbbox()
		max_x = star_bbox.right
		star_outputs_center_y = (star_bbox.top + star_bbox.bottom) / 2.0
	array_height = (output_gc_count - 1) * gc_pitch
	output_gc_pos = (
		max_x + output_gc_dx,
		star_outputs_center_y + (array_height / 2.0) + output_gc_dy,
	)
	output_gc_refs = add_output_grating_coupler_array(
		circuit,
		origin=output_gc_pos,
		num_couplers=output_gc_count,
		pitch=gc_pitch,
		orientation="West",
	)

	# 4. Feature-specific output routing
	mode = feature_mode.lower()
	if mode == "power":
		_route_outputs_power_mode(circuit, sc_ports["ref"], output_gc_refs)
	elif mode == "amplitude_same_lenght":
		_route_outputs_amplitude_same_length_mode(circuit, sc_ports["ref"], output_gc_refs)
	elif mode == "phase":
		_route_outputs_phase_mode(circuit, sc_ports["ref"])
	else:
		raise ValueError(
			"feature_mode must be one of: power, amplitude_same_lenght, phase"
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
			num_outputs=4,
			gc_pitch=127.0,
			feature_mode="power",
			output_gc_dx = -800,
			output_gc_dy= 450,
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
