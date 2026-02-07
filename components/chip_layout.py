"""Chip layout construction utilities.

Step 1: load the sharing template GDS, apply basic modifications, and
export to output/gds.
"""

from __future__ import annotations
from pathlib import Path
import warnings
import uuid
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


def extend_port(
	circuit: gf.Component,
	port: gf.Port,
	length: float = 25.0,
) -> gf.Port:
	"""Extend a port in its facing direction by a straight of given length."""
	cs_port = gf.cross_section.cross_section(layer=port.layer, width=port.width)
	straight = gf.components.straight(length=length, cross_section=cs_port)
	ref = circuit << straight
	ref.connect("o1", port)
	return ref.ports["o2"]


# ============================================================================
# Component Generation Functions (Relative positioning within circuit)
# ============================================================================

def add_port_label(
	circuit: gf.Component,
	text: str,
	position: tuple[float, float],
	size: float = 8.0,
	layer: tuple[int, int] = (4, 0),
) -> None:
	"""Add engraved text label on the chip."""
	label = gf.components.text(text=text, size=size, layer=layer)
	label_ref = circuit << label
	label_ref.move(position)


def _add_grating_coupler_array(
	circuit: gf.Component,
	origin: tuple[float, float],
	num_couplers: int,
	pitch: float,
	orientation: str,
	label_prefix: str | None,
	label_offset: tuple[float, float],
	label_size: float,
	label_order: str = "placement",
) -> list:
	"""Add a grating coupler array to circuit."""
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
		# Rotate first so the placement order stays consistent for all orientations
		gc_ref.rotate(config["angle"])
		gc_ref.move((x_pos, y_pos))
		gc_refs.append(gc_ref)

	if label_prefix and gc_refs:
		if label_order == "placement":
			label_refs = gc_refs
		elif label_order in {"top_to_bottom", "bottom_to_top"}:
			label_refs = sorted(
				gc_refs,
				key=lambda r: r.center[1],
				reverse=(label_order == "top_to_bottom"),
			)
		else:
			raise ValueError(
				"label_order must be 'placement', 'top_to_bottom', or 'bottom_to_top'"
			)
		for index, gc_ref in enumerate(label_refs, start=1):
			add_port_label(
				circuit,
				text=f"{label_prefix}{index}",
				position=(gc_ref.center[0] + label_offset[0], gc_ref.center[1] + label_offset[1]),
				size=label_size,
			)

	return gc_refs

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
	return _add_grating_coupler_array(
		circuit=circuit,
		origin=origin,
		num_couplers=num_couplers,
		pitch=pitch,
		orientation=orientation,
		label_prefix=label_prefix,
		label_offset=label_offset,
		label_size=label_size,
		label_order="placement",
	)


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
	label_offset: tuple[float, float] = (-52.0, 5.0),
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
	return _add_grating_coupler_array(
		circuit=circuit,
		origin=origin,
		num_couplers=num_couplers,
		pitch=pitch,
		orientation=orientation,
		label_prefix=label_prefix,
		label_offset=label_offset,
		label_size=label_size,
		label_order=label_order,
	)


def connect_gc_top_bottom_drawn(
	circuit: gf.Component,
	gc_refs: list,
	front_dx: float = 0.0,
	first_drop: float = 20.0,
	back_offset: float = 10.0,
	bottom_rise: float = 0.0,
	bottom_dx1: float = 30.0,
	bottom_dx2: float = 30.0,
	end_dx: float = 0.0,
) -> None:
	"""Connect top GC to bottom GC.

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

	# Top segment into the backbone
	cur = place_start_taper_at(p_top, length=20)
	cur = place_chain(cur, [gf.components.straight(length=front_dx, cross_section=cs)])
	cur = place_chain(cur, [bend_r])
	cur = place_chain(cur, [gf.components.straight(length=first_drop, cross_section=cs)])
	cur = place_chain(cur, [bend_r])
	straight_len = abs(cur.x - x_back)
	cur = place_chain(cur, [gf.components.straight(length=straight_len, cross_section=cs)])
	cur = place_chain(cur, [bend_l])

	# Backbone vertical straight from top to bottom anchor
	backbone_len = abs(cur.y - y_mid)/4
	backbone = circuit << gf.components.straight(length=max(1, backbone_len), cross_section=cs)
	backbone.rotate(90)
	backbone.connect("o1", cur)
	backbone_bottom = backbone.ports["o2"]

	# Bottom segment into the backbone
	cur_b = place_start_taper_at(p_bottom, length=20)
	cur_b = place_chain(cur_b, [bend_l])
	cur_b = place_chain(cur_b, [gf.components.straight(length=bottom_rise, cross_section=cs)])
	cur_b = place_chain(cur_b, [bend_l])
	straight_len_b = abs(cur_b.x - x_back)
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
	align_gc_index: int | None = None,
) -> None:
	"""Place star coupler to the left of the GC array with a fixed gap.
	
	Args:
		star_ref: Star coupler reference to position.
		gc_refs: List of grating coupler references.
		gap: Horizontal gap between star coupler and GC array.
		align_gc_index: If provided, align star coupler center with this GC index.
			If None, align with the center of all GCs.
	"""
	if not gc_refs:
		return
	gc_min_x = min(ref.dbbox().left for ref in gc_refs)
	
	# Determine Y position: either center of all GCs or specific GC
	if align_gc_index is not None and 0 <= align_gc_index < len(gc_refs):
		gc_center_y = gc_refs[align_gc_index].center[1]
	else:
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
	s_bend_indices = None,
	distance_GC_first_bend: float = 00.0
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

		# Use S-bend for selected input ports (top-to-bottom indices)
		
		bundle_in = [p for i, p in enumerate(input_ports_norm) if i not in s_bend_indices]
		bundle_gc = [p for i, p in enumerate(gc_ports_norm) if i not in s_bend_indices]
		sbend_in = [p for i, p in enumerate(input_ports_norm) if i in s_bend_indices]
		sbend_gc = [p for i, p in enumerate(gc_ports_norm) if i in s_bend_indices]

		# Push bends to the right by extending GC-side ports (bundle only)
		bundle_gc = [extend_port(circuit, p, distance_GC_first_bend) for p in bundle_gc]

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
	s_bend_indices: set = {None},
	bundle_routing_gap: float = 150.0,
) -> None:
	"""Route star coupler outputs directly to GC array (power mode)."""
	output_ports = [p for p in star_ref.ports if p.name.startswith("out")]
	if not output_ports or not output_gc_refs:
		return

	# Ensure OUT1 (top) connects to OUT6 (bottom)
	gc_refs_sorted = sorted(output_gc_refs, key=lambda r: r.center[1], reverse=True)
	if len(gc_refs_sorted) >= 2:
		# Swap to flip the routing (top goes down, bottom goes up)
		connect_gc_top_bottom_drawn(circuit,
							  list(reversed(gc_refs_sorted)),
							  back_offset=-20
)

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
	
	bundle_out = [p for i, p in enumerate(output_ports_norm) if i not in s_bend_indices]
	bundle_gc = [p for i, p in enumerate(gc_ports_norm) if i not in s_bend_indices]
	sbend_out = [p for i, p in enumerate(output_ports_norm) if i in s_bend_indices]
	sbend_gc = [p for i, p in enumerate(gc_ports_norm) if i in s_bend_indices]

	# Push bundle bends away from GC ports (OUT2/OUT5)
	bundle_gc = [extend_port(circuit, p, bundle_routing_gap) for p in bundle_gc]

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


def add_mmi_coupler(
	circuit: gf.Component,
	position: tuple[float, float] = (0, 0),
	rotation: float = 0.0,
) -> dict:
	"""Add MMI 1x2 coupler to circuit.
	
	Args:
		circuit: The circuit component.
		position: Position (x, y) for the MMI center.
		rotation: Rotation angle in degrees.
	
	Returns:
		Dict with 'ref' and 'ports' (input and output ports).
	"""
	mmi = ubcpdk.cells.ANT_MMI_1x2_te1550_3dB_BB()
	mmi_ref = circuit << mmi
	
	# Position and rotate
	if rotation != 0:
		mmi_ref.rotate(rotation)
	mmi_ref.move(position)
	
	# Extract ports (convert to list)
	all_ports = [port for port in mmi_ref.ports]
	
	ports_dict = {
		"ref": mmi_ref,
		"ports": all_ports,
	}
	
	return ports_dict


def route_with_loop(
	circuit: gf.Component,
	port_start: gf.Port,
	port_end: gf.Port,
	target_length: float,
	loop_side: str = "north",
	cross_section = None,
	bend_radius: float = 25.0,
	h1: float = 40.0,
	h3: float = 40.0,
	max_iterations: int = 20,
	tolerance: float = 0.1,
) -> gf.Port:
	"""Route between two ports with a loop to achieve target path length.
	
	Args:
		circuit: The circuit component to add routing to.
		port_start: Starting port.
		port_end: Ending port.
		target_length: Target total path length (um).
		loop_side: Direction of loop - "north" (up) or "south" (down).
		cross_section: Cross-section for waveguides.
		bend_radius: Bend radius (um).
		h1: Initial straight segment before loop (um).
		h3: Horizontal straight segment across loop (um).
		max_iterations: Maximum iterations for loop height optimization.
		tolerance: Acceptable length error (um).
	
	Returns:
		Final port after routing.
	"""
	if cross_section is None:
		cross_section = gf.cross_section.cross_section(
			layer=port_start.layer,
			width=port_start.width,
			radius=bend_radius,
		)
	
	# Calculate bend arc length (90° bend = pi * r / 2)
	bend_arc_length = 3.14159 * bend_radius / 2
	total_bend_length = 3 * bend_arc_length  # 3 bends: up/down, right, down/up
	
	# Direct distance
	dx_direct = port_end.center[0] - port_start.center[0]
	dy_direct = port_end.center[1] - port_start.center[1]
	
	# Binary search for optimal loop height
	loop_height_min = 10.0
	loop_height_max = 200.0
	loop_height = 100.0
	
	for iteration in range(max_iterations):
		# Calculate path length with current loop height
		h2 = loop_height
		# h4 depends on how much X distance is consumed by h1, h3, and bends
		current_x_after_loop = port_start.center[0] + h1 + h3 + 2 * bend_radius
		h4 = port_end.center[0] - current_x_after_loop
		
		# Total length
		total_length = h1 + h2 + h3 + h4 + total_bend_length
		
		error = total_length - target_length
		
		if abs(error) < tolerance:
			print(f"[DEBUG] route_with_loop converged: loop_height={loop_height:.2f} um, total={total_length:.2f} um (error={error:.3f} um)")
			break
		
		# Adjust loop height (binary search)
		if error > 0:  # Too long, reduce loop height
			loop_height_max = loop_height
			loop_height = (loop_height_min + loop_height) / 2
		else:  # Too short, increase loop height
			loop_height_min = loop_height
			loop_height = (loop_height + loop_height_max) / 2
	else:
		print(f"[WARNING] route_with_loop did not converge after {max_iterations} iterations. Final error: {error:.3f} um")
	
	# Build the route with optimized loop height
	h2 = loop_height
	current_x_after_loop = port_start.center[0] + h1 + h3 + 2 * bend_radius
	h4 = port_end.center[0] - current_x_after_loop
	
	print(f"[DEBUG] route_with_loop: h1={h1}, h2={h2:.2f}, h3={h3}, h4={h4:.2f}, bends={total_bend_length:.2f}")
	
	current_port = port_start
	
	# Segment 1: Initial straight (RIGHT)
	if h1 > 0.1:
		s1 = circuit << gf.components.straight(length=h1, cross_section=cross_section)
		s1.connect("o1", current_port)
		current_port = s1.ports["o2"]
	
	# Determine loop direction
	loop_angle = 90 if loop_side == "north" else -90
	
	# Segment 2: Bend into loop (UP or DOWN)
	b1 = circuit << gf.components.bend_euler(angle=loop_angle, cross_section=cross_section, radius=bend_radius)
	b1.connect("o1", current_port)
	current_port = b1.ports["o2"]
	
	# Segment 3: Vertical segment (UP or DOWN)
	if h2 > 0.1:
		s2 = circuit << gf.components.straight(length=h2, cross_section=cross_section)
		s2.connect("o1", current_port)
		current_port = s2.ports["o2"]
	
	# Segment 4: Bend toward destination (RIGHT)
	b2 = circuit << gf.components.bend_euler(angle=-loop_angle, cross_section=cross_section, radius=bend_radius)
	b2.connect("o1", current_port)
	current_port = b2.ports["o2"]
	
	# Segment 5: Horizontal across loop (RIGHT)
	if h3 > 0.1:
		s3 = circuit << gf.components.straight(length=h3, cross_section=cross_section)
		s3.connect("o1", current_port)
		current_port = s3.ports["o2"]
	
	# Segment 6: Bend back to destination level (DOWN or UP)
	b3 = circuit << gf.components.bend_euler(angle=-loop_angle, cross_section=cross_section, radius=bend_radius)
	b3.connect("o1", current_port)
	current_port = b3.ports["o2"]
	
	# Segment 7: Descend/ascend to destination Y (accounting for next bend offset)
	current_y = current_port.center[1]
	target_y_before_final_bend = port_end.center[1] + (bend_radius if loop_side == "north" else -bend_radius)
	dy_return = abs(current_y - target_y_before_final_bend)
	
	if dy_return > 0.1:
		s4 = circuit << gf.components.straight(length=dy_return, cross_section=cross_section)
		s4.connect("o1", current_port)
		current_port = s4.ports["o2"]
	
	# Segment 8: Final bend toward destination (RIGHT)
	b4 = circuit << gf.components.bend_euler(angle=loop_angle, cross_section=cross_section, radius=bend_radius)
	b4.connect("o1", current_port)
	current_port = b4.ports["o2"]
	
	# Segment 9: Final straight to destination
	dx_final = port_end.center[0] - current_port.center[0]
	if dx_final > 0.1:
		s5 = circuit << gf.components.straight(length=dx_final, cross_section=cross_section)
		s5.connect("o1", current_port)
		current_port = s5.ports["o2"]
	
	print(f"[DEBUG] route_with_loop final position: {current_port.center}")
	return current_port



def _make_port_compatible(
	port: gf.Port,
	layer: tuple[int, int],
	width: float,
) -> gf.Port:
	"""Return a new port with specified layer/width, preserving center/orientation."""
	return gf.Port(
		name=port.name,
		center=port.center,
		width=width,
		orientation=port.orientation,
		layer=gf.get_layer(layer),
	)


def place_mmi_aligned_to_port(
	circuit: gf.Component,
	target_port: gf.Port,
	align_port_name: str = "o2",
	shift_x: float = 0.0,
	shift_y: float = 0.0,
	rotation: float = 180.0,
) -> tuple[gf.ComponentReference, dict[str, gf.Port]]:
	"""Place an MMI so that align_port_name is at target_port + (shift_x, shift_y)."""
	temp_x = target_port.center[0] + shift_x
	temp_y = target_port.center[1] + shift_y

	mmi_data = add_mmi_coupler(
		circuit,
		position=(temp_x, temp_y),
		rotation=rotation,
	)
	mmi_ref = mmi_data["ref"]
	mmi_ports = {p.name: p for p in mmi_ref.ports}
	if align_port_name not in mmi_ports:
		raise ValueError(f"MMI port '{align_port_name}' not found")

	align_port = mmi_ports[align_port_name]
	offset_x = align_port.center[0] - temp_x
	offset_y = align_port.center[1] - temp_y

	# Move MMI so align_port is exactly at target + shift
	mmi_ref.move((-offset_x, -offset_y))

	# Refresh ports after move
	mmi_ports = {p.name: p for p in mmi_ref.ports}
	return mmi_ref, mmi_ports


def route_arms_to_mmi(
	circuit: gf.Component,
	short_start: gf.Port,
	long_start: gf.Port,
	mmi_top_port: gf.Port,
	mmi_bot_port: gf.Port,
	short_length: float,
	delta_L: float,
	loop_side: str = "north",
	cross_section=None,
	bend_radius: float = 25.0,
	h1: float = 50.0,
	h3: float = 20.0,
) -> dict:
	"""Route short/long arms from start ports to MMI top/bottom ports."""
	if cross_section is None:
		cross_section = gf.cross_section.cross_section(
			layer=short_start.layer,
			width=short_start.width,
			radius=bend_radius,
		)

	L_SHORT = short_length
	L_LONG = short_length + delta_L

	# Short arm
	short_arm = gf.components.straight(length=L_SHORT, cross_section=cross_section)
	short_ref = circuit << short_arm
	short_ref.connect("o1", short_start)
	short_end = short_ref.ports["o2"]

	# Close short gap if needed
	dx_short_gap = mmi_bot_port.center[0] - short_end.center[0]
	if abs(dx_short_gap) > 0.1:
		short_connector = circuit << gf.components.straight(
			length=abs(dx_short_gap),
			cross_section=cross_section,
		)
		short_connector.connect("o1", short_end)
		short_end = short_connector.ports["o2"]

	# Long arm with loop
	current_port = route_with_loop(
		circuit=circuit,
		port_start=long_start,
		port_end=mmi_top_port,
		target_length=L_LONG,
		loop_side=loop_side,
		cross_section=cross_section,
		bend_radius=bend_radius,
		h1=h1,
		h3=h3,
	)

	# Close long gap if needed
	dx_long_gap = abs(mmi_top_port.center[0] - current_port.center[0])
	if dx_long_gap > 0.1:
		long_connector = circuit << gf.components.straight(
			length=dx_long_gap,
			cross_section=cross_section,
		)
		long_connector.connect("o1", current_port)
		current_port = long_connector.ports["o2"]

	return {
		"short_end": short_end,
		"long_end": current_port,
		"L_SHORT": L_SHORT,
		"L_LONG": L_LONG,
	}


def _route_single_phase_mzi(
	circuit: gf.Component,
	out_long_port: gf.Port,
	out_short_port: gf.Port,
	MMI_shift_x: float = 0.0,
	MMI_shift_y: float = 0.0,
	delta_L: float = 175.0,
	loop_side: str = "north",
	bend_radius: float = 25.0,
	h1: float = 50.0,
	h3: float = 20.0,
) -> gf.Port | None:
	"""Route a single MZI pair (long/short arms) and return MMI output port.
	
	Args:
		out_long_port: Long arm output from star coupler.
		out_short_port: Short arm output from star coupler.
		loop_side: Direction of loop ("north" or "south").
	"""
	target_width = 0.75
	cs_phase = gf.cross_section.cross_section(
		layer=SIN_LAYER,
		width=target_width,
		radius=bend_radius,
	)

	# Normalize port widths (SC outputs are 1000 nm, need 750 nm)
	out_long_norm = normalize_port_width(circuit, out_long_port, target_width, length=10.0)
	out_short_norm = normalize_port_width(circuit, out_short_port, target_width, length=10.0)

	# Assign short/long based on loop direction to keep routing clear
	ports_sorted = sorted([out_long_norm, out_short_norm], key=lambda p: p.center[1], reverse=True)
	port_top, port_bottom = ports_sorted[0], ports_sorted[1]
	if loop_side == "south":
		short_start = port_top
		long_start = port_bottom
	else:
		short_start = port_bottom
		long_start = port_top

	# Place MMI aligned to the correct input port for the short arm
	align_port_name = "o2" if short_start is port_bottom else "o3"
	try:
		mmi_ref, mmi_ports = place_mmi_aligned_to_port(
			circuit=circuit,
			target_port=short_start,
			align_port_name=align_port_name,
			shift_x=MMI_shift_x,
			shift_y=MMI_shift_y,
			rotation=180.0,
		)
	except ValueError as exc:
		print(f"[ERROR] Failed to place MMI: {exc}")
		return

	# Identify MMI input ports
	port_o2 = mmi_ports.get("o2", None)
	port_o3 = mmi_ports.get("o3", None)
	if not (port_o2 and port_o3):
		print("[ERROR] MMI ports o2/o3 not found")
		return
	
	mmi_top_port = max([port_o2, port_o3], key=lambda p: p.center[1])
	mmi_bot_port = min([port_o2, port_o3], key=lambda p: p.center[1])

	# Swap MMI ports based on loop direction
	if loop_side == "south":
		mmi_top_port, mmi_bot_port = mmi_bot_port, mmi_top_port

	# Create compatible MMI target ports
	mmi_top_target = _make_port_compatible(mmi_top_port, SIN_LAYER, target_width)
	mmi_bot_target = _make_port_compatible(mmi_bot_port, SIN_LAYER, target_width)

	# Route arms
	result = route_arms_to_mmi(
		circuit=circuit,
		short_start=short_start,
		long_start=long_start,
		mmi_top_port=mmi_top_target,
		mmi_bot_port=mmi_bot_target,
		short_length=MMI_shift_x,
		delta_L=delta_L,
		loop_side=loop_side,
		cross_section=cs_phase,
		bend_radius=bend_radius,
		h1=h1,
		h3=h3,
	)

	# Provide MMI output port to caller for bundle routing
	mmi_single_out_port = mmi_ports.get("o1", None)
	if not mmi_single_out_port:
		print("[ERROR] MMI output port o1 not found")
		return None

	mmi_out_compatible = _make_port_compatible(mmi_single_out_port, SIN_LAYER, target_width)

	print(
		f"[DEBUG] Phase MZI: L_SHORT={result['L_SHORT']} um, "
		f"L_LONG={result['L_LONG']} um, delta_L={delta_L} um, loop={loop_side}"
	)

	return mmi_out_compatible


def _route_outputs_phase_mode(
	circuit: gf.Component,
	star_ref: gf.ComponentReference,
	MMI_star_coupler_shift_x: float = 0.0,
	MMI_star_coupler_shift_y: float = 0.0,
	delta_L: float = 175.0,
	output_pairs: list[tuple[int, int]] | None = None,
	gc_output_indices: list[int] | None = None,
	gc_output_refs: list | None = None,
	gc_output_port_index_phase: int | None = None,
) -> None:
	"""Interfere star coupler outputs pairwise (phase mode).

	Supports multiple MZI pairs with configurable loop direction.
	
	Args:
		output_pairs: List of (long_idx, short_idx) tuples for SC output pairs.
			Default is [(0, 1)] for top 2 outputs.
		gc_output_indices: List of GC output indices (one per pair).
			If None, uses [gc_output_port_index_phase] for compatibility.
		gc_output_refs: List of GC references to access output ports.
	"""
	# Get star coupler output ports
	output_ports = [p for p in star_ref.ports if p.name.startswith("out")]
	if len(output_ports) < 2:
		print("[WARN] Phase mode needs at least 2 output ports")
		return

	# Sort top to bottom
	output_ports.sort(key=lambda p: p.center[1], reverse=True)

		# Ensure OUT1 (top) connects to OUT6 (bottom)
	gc_refs_sorted = sorted(gc_output_refs, key=lambda r: r.center[1], reverse=True)
	if len(gc_refs_sorted) >= 2:
		# Swap to flip the routing (top goes down, bottom goes up)
		connect_gc_top_bottom_drawn(circuit,
							  list(reversed(gc_refs_sorted)),
							  back_offset=-20
)
	# Default to first pair if not specified
	if output_pairs is None:
		output_pairs = [(0, 1)]
	
	# Default GC indices for backward compatibility
	if gc_output_indices is None:
		if gc_output_port_index_phase is not None:
			gc_output_indices = [gc_output_port_index_phase]
		else:
			gc_output_indices = [1]  # Default to index 1
	
	# Ensure gc_output_refs is provided
	if gc_output_refs is None:
		print("[ERROR] gc_output_refs must be provided")
		return

	# Collect MMI output ports for bundle routing
	mmi_out_ports: list[gf.Port] = []

	# Process each pair
	for pair_idx, (out_idx_long, out_idx_short) in enumerate(output_pairs):
		# Validate indices
		if out_idx_long >= len(output_ports) or out_idx_short >= len(output_ports):
			print(f"[WARN] Output pair indices {(out_idx_long, out_idx_short)} out of range")
			continue

		# Get ports
		out_long = output_ports[out_idx_long]
		out_short = output_ports[out_idx_short]
		
		# Alternate loop direction: north for even pairs, south for odd
		loop_side = "north" if pair_idx % 2 == 0 else "south"
		
		print(f"[DEBUG] Phase MZI pair {pair_idx}: SC[{out_idx_long},{out_idx_short}] (loop={loop_side})")
		
		# Route this MZI
		mmi_out = _route_single_phase_mzi(
			circuit=circuit,
			out_long_port=out_long,
			out_short_port=out_short,
			MMI_shift_x=MMI_star_coupler_shift_x,
			MMI_shift_y=MMI_star_coupler_shift_y,
			delta_L=delta_L,
			loop_side=loop_side,
			bend_radius=25.0,
			h1=50.0,
			h3=20.0,
		)
		if mmi_out is not None:
			mmi_out_ports.append(mmi_out)

	# Route MMI outputs to GC outputs as a bundle (avoid overlaps)
	if not mmi_out_ports:
		print("[WARN] No MMI outputs to route")
		return

	# Build GC output port list
	if gc_output_indices is None:
		# Auto: top-to-bottom order
		gc_ports_sorted = sorted(
			[list(ref.ports)[0] for ref in gc_output_refs],
			key=lambda p: p.center[1],
			reverse=True,
		)
		gc_ports = gc_ports_sorted[:len(mmi_out_ports)]
		mmi_ports_ordered = sorted(mmi_out_ports, key=lambda p: p.center[1], reverse=True)
		sort_ports = False
	else:
		gc_ports = []
		for idx in gc_output_indices[:len(mmi_out_ports)]:
			if idx >= len(gc_output_refs):
				print(f"[WARN] GC output index {idx} out of range")
				continue
			gc_ports.append(list(gc_output_refs[idx].ports)[0])
		mmi_ports_ordered = mmi_out_ports
		sort_ports = False

	if len(gc_ports) != len(mmi_ports_ordered):
		print("[WARN] Mismatch between MMI outputs and GC outputs for bundle routing")
		return

	# Normalize GC ports to SIN layer
	gc_ports_compatible = [
		_make_port_compatible(p, SIN_LAYER, 0.75) for p in gc_ports
	]

	cs_phase = gf.cross_section.cross_section(
		layer=SIN_LAYER,
		width=0.75,
		radius=25.0,
	)

	gf.routing.route_bundle(
		circuit,
		mmi_ports_ordered,
		gc_ports_compatible,
		cross_section=cs_phase,
		radius=25.0,
		separation=10.0,
		sort_ports=sort_ports,
		auto_taper=False,
	)



def add_mzi_calibration(
	parent_cell: gf.Component,
	input_port: gf.Port,
	output_port: gf.Port,
	short_length: float = 300.0,
	delta_L: float = 175.0,
	loop_side: str = "north",
	bend_radius: float = 25.0,
	h1: float = 50.0,
	h3: float = 20.0,
	input_extension: float = 20.0,
	output_extension: float = 20.0,
	input_mmi_shift_x: float = 0.0,
	input_mmi_shift_y: float = 0.0,
) -> gf.ComponentReference:
	"""Add a standalone MZI calibration using two MMIs as an independent component."""
	# Create independent MZI circuit
	unique_id = str(uuid.uuid4())[:8]
	mzi_circuit = gf.Component(f"mzi_calibration_{unique_id}")
	
	target_width = 0.75
	cs_phase = gf.cross_section.cross_section(
		layer=SIN_LAYER,
		width=target_width,
		radius=bend_radius,
	)

	# Normalize and extend ports from GC (force SiN layer)
	in_port_base = _make_port_compatible(input_port, SIN_LAYER, input_port.width)
	in_port = normalize_port_width(mzi_circuit, in_port_base, target_width, length=10.0)
	if input_extension > 0:
		in_port = extend_port(mzi_circuit, in_port, input_extension)
	in_port_sin = _make_port_compatible(in_port, SIN_LAYER, target_width)

	out_port_base = _make_port_compatible(output_port, SIN_LAYER, output_port.width)
	out_port = normalize_port_width(mzi_circuit, out_port_base, target_width, length=10.0)
	if output_extension > 0:
		out_port = extend_port(mzi_circuit, out_port, output_extension)
	out_port_sin = _make_port_compatible(out_port, SIN_LAYER, target_width)

	# Splitter MMI (o1 as input), positioned relative to IN7 GC
	splitter_ref, splitter_ports = place_mmi_aligned_to_port(
		circuit=mzi_circuit,
		target_port=in_port_sin,
		align_port_name="o1",
		shift_x=input_mmi_shift_x,
		shift_y=input_mmi_shift_y,
		rotation=0.0,
	)
	splitter_in = splitter_ports.get("o1")
	if splitter_in:
		splitter_in_norm = _make_port_compatible(splitter_in, SIN_LAYER, target_width)
		gf.routing.route_single(
			mzi_circuit,
			splitter_in_norm,
			in_port_sin,
			cross_section=cs_phase,
			radius=bend_radius,
			auto_taper=False,
		)
	else:
		print("[ERROR] Splitter MMI port o1 not found")
		return None
	sp_o2 = splitter_ports.get("o2")
	sp_o3 = splitter_ports.get("o3")
	if not sp_o2 or not sp_o3:
		print("[ERROR] Splitter MMI ports o2/o3 not found")
		return None
	sp_top = max([sp_o2, sp_o3], key=lambda p: p.center[1])
	sp_bot = min([sp_o2, sp_o3], key=lambda p: p.center[1])

	# Combiner MMI aligned to short arm length
	combiner_ref, combiner_ports = place_mmi_aligned_to_port(
		circuit=mzi_circuit,
		target_port=sp_bot,
		align_port_name="o2",
		shift_x=short_length,
		shift_y=0.0,
		rotation=180.0,
	)
	cb_o2 = combiner_ports.get("o2")
	cb_o3 = combiner_ports.get("o3")
	if not cb_o2 or not cb_o3:
		print("[ERROR] Combiner MMI ports o2/o3 not found")
		return None
	cb_top = max([cb_o2, cb_o3], key=lambda p: p.center[1])
	cb_bot = min([cb_o2, cb_o3], key=lambda p: p.center[1])

	# Route arms between splitter and combiner
	sp_top_norm = _make_port_compatible(sp_top, SIN_LAYER, target_width)
	sp_bot_norm = _make_port_compatible(sp_bot, SIN_LAYER, target_width)
	cb_top_norm = _make_port_compatible(cb_top, SIN_LAYER, target_width)
	cb_bot_norm = _make_port_compatible(cb_bot, SIN_LAYER, target_width)

	route_arms_to_mmi(
		circuit=mzi_circuit,
		short_start=sp_bot_norm,
		long_start=sp_top_norm,
		mmi_top_port=cb_top_norm,
		mmi_bot_port=cb_bot_norm,
		short_length=short_length,
		delta_L=delta_L,
		loop_side=loop_side,
		cross_section=cs_phase,
		bend_radius=bend_radius,
		h1=h1,
		h3=h3,
	)

	# Connect combiner output to output GC port
	combiner_out = combiner_ports.get("o1")
	if combiner_out:
		combiner_out_norm = _make_port_compatible(combiner_out, SIN_LAYER, target_width)
		gf.routing.route_single(
			mzi_circuit,
			combiner_out_norm,
			out_port_sin,
			cross_section=cs_phase,
			radius=bend_radius,
			auto_taper=False,
		)
	
	# Add the MZI circuit to the parent cell
	mzi_ref = parent_cell << mzi_circuit
	return mzi_ref


def add_material_loss_calibration(
	circuit: gf.Component,
	input_gc_origin: tuple[float, float],
	waveguide_length: float = 1000.0,
	waveguide_width: float = 0.75,
	waveguide_layer: tuple[int, int] = (4, 0),
	bend_radius: float = 25.0,
	gc_in_out_dy: float = 0.0,
	input_extension: float = 0.0,
	output_extension: float = 0.0,
	circuit_name: str = "calibration_material_loss",
) -> None:
	"""Add a material loss calibration circuit: single input GC -> straight waveguide -> single output GC.
	
	This independent circuit is used to measure material loss in the waveguide.
	
	Args:
		circuit: The circuit component to add to.
		input_gc_origin: Position (x, y) of the input grating coupler.
		waveguide_length: Length of the straight SiN waveguide (um).
		waveguide_width: Width of the waveguide (um).
		waveguide_layer: Layer tuple for the waveguide (default: SiN layer (4, 0)).
		bend_radius: Bend radius for routing (um).
		gc_in_out_dy: Vertical spacing between input and output GCs (um).
		input_extension: Extension length after input GC (um).
		output_extension: Extension length before output GC (um).
	"""
	# Create cross-section for the waveguide
	cs_wg = gf.cross_section.cross_section(
		layer=waveguide_layer,
		width=waveguide_width,
		radius=bend_radius,
	)
	
	# Add input grating coupler
	gc_input = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	gc_in_ref = circuit << gc_input
	gc_in_ref.move(input_gc_origin)
	input_port = list(gc_in_ref.ports)[0]
	
	# Add label for input
	add_port_label(
		circuit,
		text=circuit_name + "_IN",
		position=(gc_in_ref.center[0] + 25.0, gc_in_ref.center[1] + 5.0),
		size=8.0,
	)
	
	# Normalize input port and add extension
	in_port_base = _make_port_compatible(input_port, waveguide_layer, input_port.width)
	in_port = normalize_port_width(circuit, in_port_base, waveguide_width, length=10.0)
	if input_extension > 0:
		in_port = extend_port(circuit, in_port, input_extension)
	in_port_wg = _make_port_compatible(in_port, waveguide_layer, waveguide_width)
	
	# Add straight waveguide section
	straight_wg = gf.components.straight(length=waveguide_length, cross_section=cs_wg)
	wg_ref = circuit << straight_wg
	wg_ref.connect("o1", in_port_wg)
	out_port_wg = wg_ref.ports["o2"]
	
	# Add output extension
	if output_extension > 0:
		out_port_wg = extend_port(circuit, out_port_wg, output_extension)
	
	# Add output grating coupler positioned below the input GC
	gc_output = ubcpdk.cells.GC_SiN_TE_1550_8degOxide_BB()
	gc_out_ref = circuit << gc_output
	gc_out_ref.rotate(180)
	# Position output GC at the end of the waveguide path, with vertical offset
	gc_out_ref.move((out_port_wg.x, input_gc_origin[1] - gc_in_out_dy))
	output_port = list(gc_out_ref.ports)[0]
	
	# Add label for output
	add_port_label(
		circuit,
		text=circuit_name + "_OUT",
		position=(gc_out_ref.center[0] - 52.0, gc_out_ref.center[1] + 5.0),
		size=8.0,
	)
	
	# Normalize output port
	out_port_base = _make_port_compatible(output_port, waveguide_layer, output_port.width)
	out_port_norm = normalize_port_width(circuit, out_port_base, waveguide_width, length=10.0)
	out_port_gc = _make_port_compatible(out_port_norm, waveguide_layer, waveguide_width)
	
	# Route from waveguide to output GC
	gf.routing.route_single(
		circuit,
		out_port_wg,
		out_port_gc,
		cross_section=cs_wg,
		radius=bend_radius,
		auto_taper=False,
	)

def add_material_loss_calibration_array(
	number_of_samples: int,
	circuit: gf.Component,
	input_gc_origin: tuple[float, float],
	first_waveguide_length: float = 5000.0,
	waveguide_length_increment: float = 100.0,
	waveguide_width: float = 0.75,
	waveguide_layer: tuple[int, int] = (4, 0),
	bend_radius: float = 25.0,
	gc_spacing: float = 0.0,
	input_extension: float = 0.0,
	output_extension: float = 0.0,
	circuit_name: str = "mat_loss",
	) -> None:


	for i in range(number_of_samples):
		add_material_loss_calibration(
			circuit=circuit,
			waveguide_layer = waveguide_layer,
			waveguide_width=waveguide_width,
			bend_radius=bend_radius,
			circuit_name = str(int(first_waveguide_length + i * waveguide_length_increment)) + "um",
			input_gc_origin=(input_gc_origin[0], input_gc_origin[1] - i * gc_spacing),
			waveguide_length=first_waveguide_length + i * waveguide_length_increment,
		)



	return None


def add_waveguide_loop_reference(
	parent_cell: gf.Component,
	input_port: gf.Port,
	output_port: gf.Port,
	total_length: float = 2000.0,
	waveguide_width: float = 0.75,
	waveguide_layer: tuple[int, int] = (4, 0),
	bend_radius: float = 25.0,
	orientation: str = "west",
) -> None:
	"""Add a horizontal U-shaped waveguide loop reference connecting two ports.
	
	This creates an independent circuit that loops between input_port and output_port
	with a U-shape consisting of:
	- First horizontal segment (calculated)
	- First bend: 90° euler bend
	- Vertical segment: |dy| between ports
	- Second bend: 90° euler bend
	- Second horizontal segment (calculated)
	
	The horizontal segments are calculated so that the total path length equals total_length:
	  horizontal_segment = (total_length - vertical_distance - 2*bend_arc_length) / 2
	
	Example: If total_length=2000 μm, ports 127 μm apart, bend_radius=25 μm:
	  - Bend arc length = π * 25 / 2 ≈ 39.27 μm each
	  - Total bends = 2 * 39.27 ≈ 78.54 μm
	  - Vertical = 127 μm
	  - Each horizontal = (2000 - 127 - 78.54) / 2 ≈ 897.23 μm
	
	Args:
		parent_cell: Parent component to add the loop to.
		input_port: Starting port (e.g., input_1).
		output_port: Ending port (e.g., output_1).
		total_length: Total waveguide path length including all segments and bends (um).
		waveguide_width: Width of the SiN waveguide (um).
		waveguide_layer: Layer tuple for the waveguide (default: SiN layer (4, 0)).
		bend_radius: Bend radius for corners (um).
		orientation: Loop direction "west" or "east" (default: "west").
	"""
	# Create cross-section for the waveguide
	cs_loop = gf.cross_section.cross_section(
		layer=waveguide_layer,
		width=waveguide_width,
		radius=bend_radius,
	)
	
	# Create separate circuit for the loop with unique name
	unique_id = str(uuid.uuid4())[:8]
	loop_circuit = gf.Component(f"waveguide_loop_ref_{unique_id}")
	
	# Normalize and prepare input port
	in_port_base = _make_port_compatible(input_port, waveguide_layer, input_port.width)
	in_port = normalize_port_width(loop_circuit, in_port_base, waveguide_width, length=10.0)
	in_port_wg = _make_port_compatible(in_port, waveguide_layer, waveguide_width)
	
	# Normalize and prepare output port
	out_port_base = _make_port_compatible(output_port, waveguide_layer, output_port.width)
	out_port = normalize_port_width(loop_circuit, out_port_base, waveguide_width, length=10.0)
	out_port_wg = _make_port_compatible(out_port, waveguide_layer, waveguide_width)
	
	# Calculate vertical distance and direction
	dy = out_port_wg.center[1] - in_port_wg.center[1]
	# Invert angle: if output is below (dy < 0), we want positive angle to go down
	vertical_angle = -90 if dy > 0 else 90
	
	# Calculate arc length for 90° bends: arc = pi * r / 2
	bend_arc_length = 3.14159 * bend_radius / 2
	total_bend_length = 2 * bend_arc_length  # Only 2 bends in U-shape
	
	# Vertical straight segment: total vertical distance minus space taken by bends
	# Each 90° bend contributes bend_radius in the vertical direction
	vertical_segment_length = abs(dy) - 2 * bend_radius
	vertical_segment_length = max(0, vertical_segment_length)
	
	# Total horizontal length available after accounting for vertical segment and bend arcs
	# total_length = 2*horizontal + vertical_straight + 2*bend_arcs
	# horizontal_segment_length = (total_length - vertical_straight - 2*bend_arcs) / 2
	available_for_horizontal = total_length - vertical_segment_length - total_bend_length
	horizontal_segment_length = available_for_horizontal / 2.0
	horizontal_segment_length = max(0, horizontal_segment_length)
	
	if orientation.lower() == "west":
		# Loop goes to the left: horizontal_left - bend - vertical - bend - horizontal_right
		current_port = in_port_wg
		
		# Segment 1: Horizontal to the left
		if horizontal_segment_length > 0.1:
			s1 = loop_circuit << gf.components.straight(length=horizontal_segment_length, cross_section=cs_loop)
			s1.connect("o1", current_port)
			current_port = s1.ports["o2"]
		
		# Bend 1: Turn vertical (up or down based on output port height)
		b1 = loop_circuit << gf.components.bend_euler(angle=vertical_angle, cross_section=cs_loop, radius=bend_radius)
		b1.connect("o1", current_port)
		current_port = b1.ports["o2"]
		
		# Segment 2: Vertical segment
		if vertical_segment_length > 0.1:
			s2 = loop_circuit << gf.components.straight(length=vertical_segment_length, cross_section=cs_loop)
			s2.connect("o1", current_port)
			current_port = s2.ports["o2"]
		
		# Bend 2: Turn back horizontal (to the right)
		b2 = loop_circuit << gf.components.bend_euler(angle=vertical_angle, cross_section=cs_loop, radius=bend_radius)
		b2.connect("o1", current_port)
		current_port = b2.ports["o2"]
		
		# Segment 3: Horizontal to the right (back toward output)
		if horizontal_segment_length > 0.1:
			s3 = loop_circuit << gf.components.straight(length=horizontal_segment_length, cross_section=cs_loop)
			s3.connect("o1", current_port)
			current_port = s3.ports["o2"]
	
	elif orientation.lower() == "east":
		# Loop goes to the right: horizontal_right - bend - vertical - bend - horizontal_left
		current_port = in_port_wg
		
		# Segment 1: Horizontal to the right
		if horizontal_segment_length > 0.1:
			s1 = loop_circuit << gf.components.straight(length=horizontal_segment_length, cross_section=cs_loop)
			s1.connect("o1", current_port)
			current_port = s1.ports["o2"]
		
		# Bend 1: Turn vertical (up or down based on output port height)
		b1 = loop_circuit << gf.components.bend_euler(angle=vertical_angle, cross_section=cs_loop, radius=bend_radius)
		b1.connect("o1", current_port)
		current_port = b1.ports["o2"]
		
		# Segment 2: Vertical segment
		if vertical_segment_length > 0.1:
			s2 = loop_circuit << gf.components.straight(length=vertical_segment_length, cross_section=cs_loop)
			s2.connect("o1", current_port)
			current_port = s2.ports["o2"]
		
		# Bend 2: Turn back horizontal (to the left, using -vertical_angle for correct direction)
		b2 = loop_circuit << gf.components.bend_euler(angle=-vertical_angle, cross_section=cs_loop, radius=bend_radius)
		b2.connect("o1", current_port)
		current_port = b2.ports["o2"]
		
		# Segment 3: Horizontal to the left (back toward output)
		if horizontal_segment_length > 0.1:
			s3 = loop_circuit << gf.components.straight(length=horizontal_segment_length, cross_section=cs_loop)
			s3.connect("o1", current_port)
			current_port = s3.ports["o2"]
	
	else:
		raise ValueError(f"Orientation '{orientation}' not supported. Use 'west' or 'east'.")
	
	# Add the loop circuit to the parent cell
	loop_ref = parent_cell << loop_circuit
	

def generate_SC_circuit(
	parent_cell: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_inputs: int = 8,
	num_outputs: int = 4,
	gc_pitch: float = 127.0,
	feature_mode: str = "power",
	output_gc_dx: float = 0.0,
	output_gc_dy: float = 0.0,
	output_gc_align_mode: int | str = 4,
	sc_align_gc_index: int | None = None,
	phase_mmi_shift_x: float = 200.0,
	phase_delta_L: float = 300.0,
	phase_output_pairs: list[tuple[int, int]] | None = None,
	phase_gc_indices: list[int] | None = None,
	expose_gc_ports: dict[str, tuple[str, int]] | None = None,
	gc_output_port_index_phase: int = 1,
	s_bend_input_indices: dict[int, list[int]] | None ={},
	s_bend_output_indices: dict[int, list[int]] | None ={}
) -> dict:
	"""Generate complete Star Coupler circuit with all components.
	
	This function creates a modular circuit that can be instantiated multiple times.
	All positions are relative to the origin parameter.
	
	Circuit flow:
	1. Input GC array (East orientation)
	2. Star coupler
	3. Output GC array (West orientation)
	4. Feature-specific routing
	
	Args:
		parent_cell: Parent component to add circuit to.
		origin: Absolute origin position for this circuit instance.
		num_inputs: Number of input channels.
		num_outputs: Number of output channels.
		gc_pitch: Grating coupler pitch (um).
		output_gc_align_mode: Output GC alignment mode.
			1: align output top GC with input top GC.
			2: center output GC array on input GC array center.
			4: center output GC array on star coupler output center.
	
	Returns:
		Dict with 'component' and 'ref'.
	"""
	
	# Create circuit sub-component with relative coordinates
	circuit = gf.Component(f"SC_circuit_{int(origin[0])}_{int(origin[1])}")
	
	# Define relative positions within the circuit
	input_gc_pos = (0, 0)
	star_coupler_pos = (0, 0)
	
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

	place_star_coupler_gcs(sc_ports["ref"], input_gc_refs, gap=-600.0, align_gc_index=sc_align_gc_index)

	connect_star_coupler_inputs_to_gcs(
		circuit,
		star_ref=sc_ports["ref"],
		gc_refs=input_gc_refs,
		start_gc_index=1,
		bend_radius=50.0,
		s_bend_indices=s_bend_input_indices,
	)
	
	# 3. Add output grating couplers (returns instance refs)
	output_gc_count = num_outputs
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

	input_gc_centers_y = [ref.center[1] for ref in input_gc_refs]
	input_gc_top_y = max(input_gc_centers_y) if input_gc_centers_y else 0.0
	input_gc_center_y = (
		(sum(input_gc_centers_y) / len(input_gc_centers_y)) if input_gc_centers_y else 0.0
	)

	align_mode = output_gc_align_mode
	if isinstance(align_mode, str):
		align_mode = align_mode.strip().lower()
		align_mode = {
			"top": 1,
			"input_top": 1,
			"match_input_top": 1,
			"center_input": 2,
			"input_center": 2,
			"center_star": 4,
			"star_center": 4,
		}.get(align_mode, 4)

	array_height = (output_gc_count - 1) * gc_pitch

	if align_mode == 1:
		output_top_y = input_gc_top_y
	elif align_mode == 2:
		output_top_y = input_gc_center_y + (array_height / 2.0)
	else:
		output_top_y = star_outputs_center_y + (array_height / 2.0)
	
	output_gc_pos = (
		max_x + output_gc_dx,
		output_top_y + output_gc_dy,
	)
	output_gc_refs = add_output_grating_coupler_array(
		circuit,
		origin=output_gc_pos,
		num_couplers=output_gc_count,
		pitch=gc_pitch,
		orientation="West",
	)

	# Expose selected GC ports (1-based indices)
	if expose_gc_ports:
		for port_name, (kind, gc_index) in expose_gc_ports.items():
			refs = input_gc_refs if kind == "input" else output_gc_refs
			idx = gc_index - 1
			if idx < 0 or idx >= len(refs):
				raise ValueError(f"GC index {gc_index} out of range for {kind} array")
			gc_port = list(refs[idx].ports)[0]
			circuit.add_port(name=port_name, port=gc_port)


	# 4. Feature-specific output routing
	mode = feature_mode.lower()
	if mode == "power":
		_route_outputs_power_mode(circuit, sc_ports["ref"], output_gc_refs, s_bend_indices=s_bend_output_indices)
	elif mode == "amplitude_same_lenght":
		_route_outputs_amplitude_same_length_mode(circuit, sc_ports["ref"], output_gc_refs)
	elif mode == "phase":
		_route_outputs_phase_mode(
			circuit, 
			sc_ports["ref"],
			MMI_star_coupler_shift_x=phase_mmi_shift_x,
			delta_L=phase_delta_L,
			output_pairs=phase_output_pairs,
			gc_output_indices=phase_gc_indices,
			gc_output_refs=output_gc_refs,
			gc_output_port_index_phase=gc_output_port_index_phase,
		)
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
	
	return {"component": circuit, "ref": circuit_ref}



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
		sc_power = generate_SC_circuit(
			parent_cell=subdie_2,
			origin=(210, 1150),  # Absolute position within Sub_Die_2
			num_inputs=8,
			num_outputs=7,
			gc_pitch=127.0,
			feature_mode="power",
			output_gc_align_mode=1,
			output_gc_dx = 950,
			output_gc_dy= 0,
			sc_align_gc_index=3,  # Align star coupler center with IN4 (index 3)
			expose_gc_ports={
				"cal_in": ("input", 7),
				"cal_out": ("output", 6),
			},
			s_bend_output_indices={2}
		)


		# Add MZI calibration between IN7 and OUT7 of the first star coupler 
		add_mzi_calibration(
			parent_cell=subdie_2,
			input_port=sc_power["ref"].ports["cal_in"],
			output_port=sc_power["ref"].ports["cal_out"],
			short_length=300.0,
			delta_L=300,
			loop_side="north",
			input_extension=200,
			# For output and output GC port check sc_power expose ports
		)

		SC_phase_1 = generate_SC_circuit(
			parent_cell=subdie_2,
			origin=(350, 330),  # Absolute position within Sub_Die_2
			num_inputs=7,
			num_outputs=6,
			gc_pitch=127.0,
			feature_mode="phase",
			output_gc_align_mode=1,
			output_gc_dx = 810,
			output_gc_dy= 0,
			phase_delta_L=300.0,
			phase_output_pairs=[(0, 1), (2, 3)],  # Two MZI pairs: top two and center two
			phase_gc_indices=[1, 2],
						expose_gc_ports={
				"input_1": ("output", 4),
				"output_1": ("output", 5),
			}
		)
		
		SC_phase_2 = generate_SC_circuit(
			parent_cell=subdie_2,
			origin=(210, -380),  # Absolute position within Sub_Die_2
			num_inputs=7,
			num_outputs=7,
			gc_pitch=127.0,
			feature_mode="phase",
			output_gc_align_mode=1,
			output_gc_dx = 950,
			output_gc_dy= 0,
			phase_delta_L=300.0,
			phase_output_pairs=[(1, 2)],  
			phase_gc_indices=[1],
			expose_gc_ports={
				"input_2": ("output", 3),
				"output_2": ("output", 4),
				"input_3": ("output", 5),
				"output_3": ("output", 6),
			},
		)
		calib_1 = add_waveguide_loop_reference(
			parent_cell=subdie_2,
			input_port=SC_phase_1["ref"].ports["input_1"],
			output_port=SC_phase_1["ref"].ports["output_1"],
			total_length=300.0,
			waveguide_width=0.75,
			waveguide_layer=SIN_LAYER,
			bend_radius=25.0,
			orientation="west",
		)
		
		# Add waveguide loop reference connecting input_1 and output_1
		calib_2 = add_waveguide_loop_reference(
			parent_cell=subdie_2,
			input_port=SC_phase_2["ref"].ports["input_2"],
			output_port=SC_phase_2["ref"].ports["output_2"],
			total_length=500.0,
			waveguide_width=0.75,
			waveguide_layer=SIN_LAYER,
			bend_radius=25.0,
			orientation="west",
		)

		calib_3 = add_waveguide_loop_reference(
			parent_cell=subdie_2,
			input_port=SC_phase_2["ref"].ports["input_3"],
			output_port=SC_phase_2["ref"].ports["output_3"],
			total_length=700.0,
			waveguide_width=0.75,
			waveguide_layer=SIN_LAYER,
			bend_radius=25.0,
			orientation="west",
		)

		add_material_loss_calibration_array(
			number_of_samples=8,
			circuit=subdie_2,
			input_gc_origin=(350, -875),
			first_waveguide_length=100.0,
			waveguide_length_increment=100.0,
			gc_spacing=35.0,
			circuit_name="",
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
