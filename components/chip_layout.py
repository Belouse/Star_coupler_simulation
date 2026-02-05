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
	layer: tuple[int, int] = ubcpdk.LAYER.TEXT,
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
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(config["angle"])
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
		sbend_indices = {1, 2, 3}
		bundle_in = [p for i, p in enumerate(input_ports_norm) if i not in sbend_indices]
		bundle_gc = [p for i, p in enumerate(gc_ports_norm) if i not in sbend_indices]
		sbend_in = [p for i, p in enumerate(input_ports_norm) if i in sbend_indices]
		sbend_gc = [p for i, p in enumerate(gc_ports_norm) if i in sbend_indices]

		# Push bends to the right by extending GC-side ports (bundle only)
		bundle_gc = [extend_port(circuit, p, 150.0) for p in bundle_gc]

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

	# Use S-bend for OUT3/OUT4 (indices 1 and 2 in top-to-bottom order)
	sbend_indices = {1, 2}
	bundle_out = [p for i, p in enumerate(output_ports_norm) if i not in sbend_indices]
	bundle_gc = [p for i, p in enumerate(gc_ports_norm) if i not in sbend_indices]
	sbend_out = [p for i, p in enumerate(output_ports_norm) if i in sbend_indices]
	sbend_gc = [p for i, p in enumerate(gc_ports_norm) if i in sbend_indices]

	# Push bundle bends away from GC ports (OUT2/OUT5)
	bundle_gc = [extend_port(circuit, p, 200.0) for p in bundle_gc]

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


def _route_outputs_phase_mode(
	circuit: gf.Component,
	star_ref: gf.ComponentReference,
	MMI_star_coupler_shift_x: float = 0.0,
	MMI_star_coupler_shift_y: float = 0.0,
	delta_L: float = 175.0,
) -> None:
	"""Interfere star coupler outputs pairwise (phase mode).

	Architecture:
	- OUT#2 (2nd from top) -> short arm (MMI_star_coupler_shift_x) -> MMI o2 bottom
	- OUT#1 (top) -> long arm (MMI_star_coupler_shift_x + delta_L) with loop -> MMI o3 top
	- MMI outputs -> to GCs (later)
	"""
	# Get star coupler output ports
	output_ports = [p for p in star_ref.ports if p.name.startswith("out")]
	if len(output_ports) < 2:
		print("[WARN] Phase mode needs at least 2 output ports")
		return

	# Sort top to bottom
	output_ports.sort(key=lambda p: p.center[1], reverse=True)
	out1 = output_ports[0]  # Top
	out2 = output_ports[1]  # Second from top

	# Place MMI aligned to OUT#2 (short arm)
	try:
		mmi_ref, mmi_ports = place_mmi_aligned_to_port(
			circuit=circuit,
			target_port=out2,
			align_port_name="o2",
			shift_x=MMI_star_coupler_shift_x,
			shift_y=MMI_star_coupler_shift_y,
			rotation=180.0,
		)
	except ValueError as exc:
		print(f"[ERROR] {exc}")
		return

	# Identify MMI input ports (o2 and o3 are the two inputs when used in reverse mode)
	port_o2 = mmi_ports.get("o2", None)
	port_o3 = mmi_ports.get("o3", None)
	if port_o2 and port_o3:
		mmi_top_port = max([port_o2, port_o3], key=lambda p: p.center[1])
		mmi_bot_port = min([port_o2, port_o3], key=lambda p: p.center[1])
	else:
		print("[ERROR] MMI ports o2/o3 not found")
		return

	# Create cross-section for phase mode routing
	cs_phase = gf.cross_section.cross_section(
		layer=SIN_LAYER,
		width=0.75,
		radius=25.0,
	)

	# Normalize port widths (SC outputs are 1000 nm, need 750 nm)
	target_width = 0.75
	out1_norm = normalize_port_width(circuit, out1, target_width, length=10.0)
	out2_norm = normalize_port_width(circuit, out2, target_width, length=10.0)

	# Create compatible MMI target ports on SIN layer
	mmi_top_target = _make_port_compatible(mmi_top_port, SIN_LAYER, target_width)
	mmi_bot_target = _make_port_compatible(mmi_bot_port, SIN_LAYER, target_width)

	result = route_arms_to_mmi(
		circuit=circuit,
		short_start=out2_norm,
		long_start=out1_norm,
		mmi_top_port=mmi_top_target,
		mmi_bot_port=mmi_bot_target,
		short_length=MMI_star_coupler_shift_x,
		delta_L=delta_L,
		loop_side="north",
		cross_section=cs_phase,
		bend_radius=25.0,
		h1=50.0,
		h3=20.0,
	)

	print(
		f"[DEBUG] Phase mode lengths: L_SHORT={result['L_SHORT']} um, "
		f"L_LONG={result['L_LONG']} um, delta_L={delta_L} um"
	)



def add_mzi_calibration(
	circuit: gf.Component,
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
) -> None:
	"""Add a standalone MZI calibration using two MMIs."""
	target_width = 0.75
	cs_phase = gf.cross_section.cross_section(
		layer=SIN_LAYER,
		width=target_width,
		radius=bend_radius,
	)

	# Normalize and extend ports from GC
	in_port = normalize_port_width(circuit, input_port, target_width, length=10.0)
	if input_extension > 0:
		in_port = extend_port(circuit, in_port, input_extension)

	out_port = normalize_port_width(circuit, output_port, target_width, length=10.0)
	if output_extension > 0:
		out_port = extend_port(circuit, out_port, output_extension)

	# Splitter MMI (o1 as input)
	splitter = ubcpdk.cells.ANT_MMI_1x2_te1550_3dB_BB()
	splitter_ref = circuit << splitter
	splitter_ref.connect("o1", in_port)
	splitter_ports = {p.name: p for p in splitter_ref.ports}
	sp_o2 = splitter_ports.get("o2")
	sp_o3 = splitter_ports.get("o3")
	if not sp_o2 or not sp_o3:
		print("[ERROR] Splitter MMI ports o2/o3 not found")
		return
	sp_top = max([sp_o2, sp_o3], key=lambda p: p.center[1])
	sp_bot = min([sp_o2, sp_o3], key=lambda p: p.center[1])

	# Combiner MMI aligned to short arm length
	combiner_ref, combiner_ports = place_mmi_aligned_to_port(
		circuit=circuit,
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
		return
	cb_top = max([cb_o2, cb_o3], key=lambda p: p.center[1])
	cb_bot = min([cb_o2, cb_o3], key=lambda p: p.center[1])

	# Route arms between splitter and combiner
	sp_top_norm = _make_port_compatible(sp_top, SIN_LAYER, target_width)
	sp_bot_norm = _make_port_compatible(sp_bot, SIN_LAYER, target_width)
	cb_top_norm = _make_port_compatible(cb_top, SIN_LAYER, target_width)
	cb_bot_norm = _make_port_compatible(cb_bot, SIN_LAYER, target_width)

	route_arms_to_mmi(
		circuit=circuit,
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

	# Connect combiner output to output port
	combiner_out = combiner_ports.get("o1")
	if combiner_out:
		combiner_out_norm = _make_port_compatible(combiner_out, SIN_LAYER, target_width)
		gf.routing.route_single(
			circuit,
			combiner_out_norm,
			out_port,
			cross_section=cs_phase,
			radius=bend_radius,
		)


def generate_SC_circuit(
	parent_cell: gf.Component,
	origin: tuple[float, float] = (0, 0),
	num_inputs: int = 8,
	num_outputs: int = 4,
	gc_pitch: float = 127.0,
	feature_mode: str = "power",
	output_gc_dx: float = 0.0,
	output_gc_dy: float = 0.0,
	sc_align_gc_index: int | None = None,
	phase_mmi_shift_x: float = 200.0,
	phase_delta_L: float = 300.0,
	expose_gc_ports: dict[str, tuple[str, int]] | None = None,
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
		_route_outputs_power_mode(circuit, sc_ports["ref"], output_gc_refs)
	elif mode == "amplitude_same_lenght":
		_route_outputs_amplitude_same_length_mode(circuit, sc_ports["ref"], output_gc_refs)
	elif mode == "phase":
		_route_outputs_phase_mode(
			circuit, sc_ports["ref"],
			MMI_star_coupler_shift_x=phase_mmi_shift_x,
			delta_L=phase_delta_L
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
		sc_main = generate_SC_circuit(
			parent_cell=subdie_2,
			origin=(210, 1150),  # Absolute position within Sub_Die_2
			num_inputs=8,
			num_outputs=8,
			gc_pitch=127.0,
			feature_mode="power",
			output_gc_dx = -1180,
			output_gc_dy= 500,
			sc_align_gc_index=3,  # Align star coupler center with IN4 (index 3)
			expose_gc_ports={
				"cal_in": ("input", 7),
				"cal_out": ("output", 7),
			},
		)

		# Add MZI calibration between IN7 and OUT7 of the first star coupler
		add_mzi_calibration(
			circuit=subdie_2,
			input_port=sc_main["ref"].ports["cal_in"],
			output_port=sc_main["ref"].ports["cal_out"],
			short_length=300.0,
			delta_L=175.0,
			loop_side="north",
		)

		_ = generate_SC_circuit(
			parent_cell=subdie_2,
			origin=(210, 134),  # Absolute position within Sub_Die_2
			num_inputs=7,
			num_outputs=6,
			gc_pitch=127.0,
			feature_mode="phase",
			output_gc_dx = -1180,
			output_gc_dy= 390,
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
