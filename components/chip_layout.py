"""Chip layout construction utilities.

Step 1: load the sharing template GDS, apply basic modifications, and
export to output/gds.
"""

from __future__ import annotations
from pathlib import Path
import gdsfactory as gf
import sys

from star_coupler import star_coupler


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
	# Create grating coupler component
	gc = gf.components.grating_coupler_elliptical_te()
	
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
	- Add input grating coupler array (East) to Sub_Die_2
	"""

	if not template_path.exists():
		raise FileNotFoundError(f"Template GDS not found: {template_path}")

	template = gf.import_gds(template_path)
	chip = gf.Component("chip_layout")
	ref = chip << template

	# Find and populate Sub_Die_2 with input grating couplers
	subdie_2 = find_subdie_cell(ref.cell, "Sub_Die_2")
	if subdie_2:
		add_grating_coupler_array_to_subdie(
			subdie_2,
			num_couplers=8,
			pitch=127.0,
			orientation="East",
			start_position=(167.84264, 1148.75036),
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
