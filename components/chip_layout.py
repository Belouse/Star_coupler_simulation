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
	chip: gf.Component,
	ref: gf.ComponentReference,
	subdie_name: str = "Sub_Die_2",
	num_couplers: int = 8,
	pitch: float = 20.0,
) -> None:
	"""Add a line of grating couplers inside Sub_Die_2.
	
	The grating couplers are arranged in a line with outputs facing right (0 degrees).
	"""
	# For now, just add grating couplers to the chip at simple positions
	# Create grating coupler component with output facing right (0 degrees)
	gc = gf.components.grating_coupler_elliptical_te()
	
	# Base position for the grating coupler array
	x_start = 3200  # Starting position in um
	y_start = 6200  # Starting position in um
	
	# Add grating couplers in a line
	for i in range(num_couplers):
		gc_ref = chip << gc
		x_pos = x_start + i * pitch
		y_pos = y_start
		gc_ref.move((x_pos, y_pos))
		gc_ref.rotate(0)  # Output facing right
	
	print(f"[OK] {num_couplers} grating couplers added to {subdie_name}")


ROOT_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_GDS = ROOT_DIR / "components" / "sharing_template_etch.gds"
OUTPUT_DIR = ROOT_DIR / "output" / "gds"

# Target lower-left origin for the chip (in um)
CHIP_ORIGIN = (3143.33023, 6156.66426)


def build_from_template(
	template_path: Path = TEMPLATE_GDS,
	chip_origin: tuple[float, float] = CHIP_ORIGIN,
) -> gf.Component:
	"""Load the template GDS and apply a minimal modification.

	Current modification: add grating couplers inside Sub_Die_2 of the template.
	"""

	if not template_path.exists():
		raise FileNotFoundError(f"Template GDS not found: {template_path}")

	template = gf.import_gds(template_path)
	chip = gf.Component("chip_layout")
	ref = chip << template

	# Don't move the reference - keep it in place
	# ref.move((chip_origin[0] - ref.xmin, chip_origin[1] - ref.ymin))

	# Access Sub_Die_2 and add grating couplers to it
	add_grating_coupler_array_to_subdie(chip, ref, subdie_name="Sub_Die_2", num_couplers=8)

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
