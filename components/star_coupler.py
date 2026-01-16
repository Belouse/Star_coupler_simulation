import numpy as np
import gdsfactory as gf
from klayout.db import LayerInfo
from typing import Tuple, Optional, List
from math import asin, sqrt, cos, sin, radians, degrees
from shapely.geometry import Polygon as ShapelyPolygon
import ubcpdk

# ==============================================================================
# "Manual Flattening" Version of the Star Coupler Components
#
# NOTE: This version is a radical departure from the original. It is designed
# to work around a suspected bug in the user's gdsfactory environment where
# component.flatten() fails.
#
# Instead of creating a hierarchy of Component objects and instancing them,
# these functions calculate raw polygon geometry. The final star_coupler
# then manually transforms and adds these polygons to a single, flat component.
# This avoids the use of instances (`<<`) and the .flatten() method entirely.
# ==============================================================================


def get_fpr_slab_polygons(
    radius: float = 76.5,
    width_rect: float = 80.54,
    height_rect: float = 152.824,
    layer: Tuple[int, int] = (1, 0),
    npoints: int = 361,
    clad_layer: Optional[Tuple[int, int]] = (111, 0),
    clad_offset: float = 3.0,
) -> List[Tuple[np.ndarray, Tuple[int, int]]]:
    """
    Calculates the polygons for the FPR slab, centered at (0,0).
    Returns a list of tuples, where each tuple is (polygon_points, layer).
    """
    polygons = []
    half_h = height_rect / 2
    radius = max(radius, half_h)
    alpha = np.arcsin(min(1.0, half_h / radius))
    theta = np.linspace(alpha, -alpha, npoints)

    cx_right = width_rect / 2 - radius * np.cos(alpha)
    cx_left = -width_rect / 2 + radius * np.cos(alpha)

    x_right = cx_right + radius * np.cos(theta)
    y_right = radius * np.sin(theta)
    x_left = cx_left - radius * np.cos(theta)
    y_left = radius * np.sin(theta)

    poly_x = np.concatenate([x_right, [-width_rect/2, -width_rect/2], x_left[::-1], [width_rect/2, width_rect/2]])
    poly_y = np.concatenate([y_right, [-half_h, half_h], y_left[::-1], [half_h, -half_h]])

    core_points = np.column_stack([poly_x, poly_y])
    
    # Center the polygons before adding cladding
    bbox = ShapelyPolygon(core_points).bounds
    dx = -(bbox[0] + bbox[2]) / 2
    dy = -(bbox[1] + bbox[3]) / 2
    core_points += np.array([dx, dy])

    polygons.append((core_points, layer))

    if clad_layer and clad_offset > 0:
        shapely_poly = ShapelyPolygon(core_points)
        clad_poly = shapely_poly.buffer(clad_offset)
        clad_points = np.array(clad_poly.exterior.coords)
        polygons.append((clad_points, clad_layer))

    return polygons


def get_taper_polygons_and_ports(
    length: float,
    width1: float,
    width2: float,
    clad_layer: Optional[Tuple[int, int]],
    clad_offset: float,
    pdk_taper_layer: Tuple[int, int] = (1, 0),
) -> Tuple[List[Tuple[np.ndarray, Tuple[int, int]]], List[gf.Port]]:
    """
    Calculates the polygons and port objects for a taper centered at (0,0).
    Does not return a component.
    """
    polygons = []
    
    x = [-length / 2, length / 2, length / 2, -length / 2]
    y = [-width1 / 2, -width2 / 2, width2 / 2, width1 / 2]
    core_points = np.column_stack([x, y])
    polygons.append((core_points, pdk_taper_layer))

    if clad_layer and clad_offset > 0:
        shapely_poly = ShapelyPolygon(core_points)
        clad_poly = shapely_poly.buffer(clad_offset)
        clad_points = np.array(clad_poly.exterior.coords)
        polygons.append((clad_points, clad_layer))
        
    # Use simple dictionaries instead of Port objects to avoid kfactory/gdsfactory conflict
    port1 = {'name': 'o1', 'center': (-length / 2, 0), 'width': width1, 'orientation': 180}
    port2 = {'name': 'o2', 'center': (length / 2, 0), 'width': width2, 'orientation': 0}
    ports = [port1, port2]

    return polygons, ports


def _normalize_angle(angle_deg: float) -> float:
    """Normalize angle to range [-180, 180) for gdsfactory/Lumerical compatibility."""
    angle = angle_deg % 360
    if angle >= 180:
        angle -= 360
    return angle


def _transform_points_and_port(
    points_list: List[np.ndarray],
    port: dict,
    rotation_deg: float,
    move_x: float,
    move_y: float,
) -> Tuple[List[np.ndarray], dict]:
    """Helper to transform a list of polygons and a port dictionary."""
    angle_rad = radians(rotation_deg)
    ca = cos(angle_rad)
    sa = sin(angle_rad)
    rot_matrix = np.array([[ca, -sa], [sa, ca]])

    # Transform polygons
    transformed_points_list = []
    for points in points_list:
        rotated_points = points @ rot_matrix.T
        translated_points = rotated_points + np.array([move_x, move_y])
        transformed_points_list.append(translated_points)

    # Transform port
    center = np.array(port['center'])
    new_center = center @ rot_matrix.T + np.array([move_x, move_y])
    # Normalize orientation to [-180, 180) range
    new_orientation = _normalize_angle(port['orientation'] + rotation_deg)
    
    new_port = {
        'name': port['name'],
        'center': tuple(new_center),
        'width': port['width'],
        'orientation': new_orientation
    }

    return transformed_points_list, new_port


@gf.cell(check_instances=False)
def star_coupler(
    n_inputs: int = 3,
    n_outputs: int = 4,
    pitch_inputs: float = 10.0,
    pitch_outputs: float = 10.0,
    angle_inputs: bool = True,
    angle_outputs: bool = True,
    taper_length: float = 40.0,
    taper_wide: float = 3.0,
    wg_width: float = 0.5,
    radius: float = 130.0,
    width_rect: float = 80.54,
    height_rect: float = 152.824,
    layer: Tuple[int, int] = (1, 0),
    npoints: int = 361,
    taper_overlap: float = 0.1,
    clad_layer: Optional[Tuple[int, int]] = (111, 0),
    clad_offset: float = 3.0,
) -> gf.Component:
    """
    Star Coupler (Manual Flattening Version).
    This component is built by manually adding and transforming polygons
    to avoid using instances and the flatten() method.
    """
    grid = getattr(gf.get_active_pdk(), "grid", 1e-3)

    def _snap_center(center):
        """Snap a 2D point to the PDK grid to avoid off-grid port placement."""
        return tuple(np.round(np.asarray(center) / grid) * grid)

    c = gf.Component()

    # 1. Add FPR Slab Polygons (already centered at 0,0)
    slab_polygons = get_fpr_slab_polygons(
        radius=radius, width_rect=width_rect, height_rect=height_rect, layer=layer,
        npoints=npoints, clad_layer=clad_layer, clad_offset=clad_offset
    )
    for points, poly_layer in slab_polygons:
        c.add_polygon(points, layer=poly_layer)

    half_h = height_rect / 2
    radius_eff = max(radius, half_h)
    alpha = asin(min(1.0, half_h / radius_eff))

    # 2. Get Taper Geometry (once)
    taper_polygons, taper_ports = get_taper_polygons_and_ports(
        length=taper_length, width1=wg_width, width2=taper_wide,
        clad_layer=clad_layer, clad_offset=clad_offset, pdk_taper_layer=layer
    )
    taper_port_o1 = next(p for p in taper_ports if p['name'] == 'o1')
    taper_port_o2 = next(p for p in taper_ports if p['name'] == 'o2')
    
    taper_poly_points = [p for p, l in taper_polygons]


    # 3. Add Output Tapers (right side)
    cx_right = width_rect / 2 - radius_eff * cos(alpha)
    offsets_out = np.arange(n_outputs) - (n_outputs - 1) / 2
    y_positions_out = offsets_out * pitch_outputs

    for i, y in enumerate(y_positions_out):
        theta_rad = asin(np.clip(y / radius_eff, -1.0, 1.0))
        x_arc = cx_right + radius_eff * cos(theta_rad)
        orient_deg = degrees(theta_rad) if angle_outputs else 0.0
        
        rotation_deg = orient_deg - 180

        # Position the taper by aligning its 'o2' port
        # The base taper has o2 at (L/2, 0). We rotate it, then move it.
        move_x = x_arc - (taper_port_o2['center'][0] * cos(radians(rotation_deg)))
        move_y = y - (taper_port_o2['center'][0] * sin(radians(rotation_deg)))
        
        if taper_overlap != 0:
            move_x -= taper_overlap * cos(theta_rad)
            move_y -= taper_overlap * sin(theta_rad)

        # Transform and add polygons
        final_polys, final_port = _transform_points_and_port(taper_poly_points, taper_port_o1, rotation_deg, move_x, move_y)
        for points, (original_points, layer_tuple) in zip(final_polys, taper_polygons):
            c.add_polygon(points, layer=layer_tuple)

        # Add port directly
        c.add_port(
            name=f"e{i+1}",
            center=_snap_center(final_port['center']),
            width=final_port['width'],
            orientation=final_port['orientation'],
            layer=layer
        )


    # 4. Add Input Tapers (left side)
    cx_left = -width_rect / 2 + radius_eff * cos(alpha)
    offsets_in = np.arange(n_inputs) - (n_inputs - 1) / 2
    y_positions_in = offsets_in * pitch_inputs

    for i, y in enumerate(y_positions_in):
        theta_rad = asin(np.clip(y / radius_eff, -1.0, 1.0))
        x_arc = cx_left - radius_eff * cos(theta_rad)
        orient_deg = 180 - degrees(theta_rad) if angle_inputs else 180.0
        
        rotation_deg = orient_deg - 180

        # Position the taper by aligning its 'o2' port
        move_x = x_arc - (taper_port_o2['center'][0] * cos(radians(rotation_deg)))
        move_y = y - (taper_port_o2['center'][0] * sin(radians(rotation_deg)))
        
        if taper_overlap != 0:
            move_x += taper_overlap * cos(theta_rad)
            move_y += taper_overlap * sin(theta_rad)

        # Transform and add polygons
        final_polys, final_port = _transform_points_and_port(taper_poly_points, taper_port_o1, rotation_deg, move_x, move_y)
        for points, (original_points, layer_tuple) in zip(final_polys, taper_polygons):
            c.add_polygon(points, layer=layer_tuple)
        
        # Add port directly
        c.add_port(
            name=f"o{i+1}",
            center=_snap_center(final_port['center']),
            width=final_port['width'],
            orientation=final_port['orientation'],
            layer=layer
        )

    return c

import ubcpdk

if __name__ == "__main__":
    ubcpdk.PDK.activate()
    sc = star_coupler()
    sc.show()