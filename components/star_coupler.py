import numpy as np
import gdsfactory as gf
from typing import Tuple, Optional
from math import asin, sqrt
from ubcpdk import components as pdk_components
from shapely.geometry import Polygon as ShapelyPolygon


@gf.cell
def fpr_slab(
    radius: float = 76.5,
    width_rect: float = 80.54,
    height_rect: float = 152.824,
    layer: Tuple[int, int] = (1, 0),
    npoints: int = 361,
    clad_layer: Optional[Tuple[int, int]] = (111, 0),
    clad_offset: float = 3.0,
) -> gf.Component:
    """FPR en capsule : rectangle central + deux arcs de même rayon.

    - Les arcs ont le même rayon et se raccordent aux côtés verticaux du
      rectangle en (± width_rect/2, ± height_rect/2).
    - Si le rayon est très grand, les coins s'approchent de 90° (arcs presque plats).

    Args:
        radius: Rayon des arcs (µm).
        width_rect: Largeur du rectangle central (µm).
        height_rect: Hauteur du rectangle central (µm).
        layer: Couche GDS (WG Si par défaut: (1, 0)).
        npoints: Discrétisation des arcs.
    """
    c = gf.Component()

    half_h = height_rect / 2
    # Clamp radius to at least half the rectangle height to ensure connection
    radius = max(radius, half_h)

    # Angle couvert par les arcs, limité par la hauteur du rectangle
    alpha = np.arcsin(min(1.0, half_h / radius))
    theta = np.linspace(alpha, -alpha, npoints)

    # Centres des arcs pour qu'ils touchent le rectangle aux coins (±width_rect/2, ±half_h)
    cx_right = width_rect / 2 - radius * np.cos(alpha)
    cx_left = -width_rect / 2 + radius * np.cos(alpha)

    # Arc droit (haut -> bas)
    x_right = cx_right + radius * np.cos(theta)
    y_right = radius * np.sin(theta)

    # Arc gauche (haut -> bas)
    x_left = cx_left - radius * np.cos(theta)
    y_left = radius * np.sin(theta)

    # Polygone fermé : arc droit (haut->bas), base rectangle, arc gauche (bas->haut), top rectangle
    poly_x = np.concatenate([
        x_right,
        [-width_rect / 2, -width_rect / 2],
        x_left[::-1],
        [width_rect / 2, width_rect / 2],
    ])
    poly_y = np.concatenate([
        y_right,
        [-half_h, half_h],
        y_left[::-1],
        [half_h, -half_h],
    ])

    points = np.column_stack([poly_x, poly_y])
    c.add_polygon(points, layer=layer)

    if clad_layer and clad_offset > 0:
        shapely_poly = ShapelyPolygon(points)
        clad_poly = shapely_poly.buffer(clad_offset)
        clad_points = np.array(clad_poly.exterior.coords)
        c.add_polygon(clad_points, layer=clad_layer)

    bbox = c.bbox()
    if bbox is not None:
        c.move(origin=(0, 0), destination=(-bbox.left, -bbox.bottom))

    return c


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
    radius: float = 76.5,
    width_rect: float = 80.54,
    height_rect: float = 152.824,
    layer: Tuple[int, int] = (1, 0),
    npoints: int = 361,
    taper_overlap: float = 0.1,
    clad_layer: Optional[Tuple[int, int]] = (111, 0),
    clad_offset: float = 3.0,
) -> gf.Component:
    """Star Coupler complet : FPR + tapers d'entrée (gauche) + tapers de sortie (droite).

    - Les tapers sont centrés autour de y=0.
    - ``angle_inputs``/``angle_outputs`` contrôlent l'orientation :
        * True  -> perpendiculaire à la surface (normal du cercle)
        * False -> toujours horizontal (orientation 0°)
    - Ports nommés o1..oN (entrées) et e1..eM (sorties).
    """
    c = gf.Component()

    @gf.cell
    def taper_with_clad(
        clad_layer: Optional[Tuple[int, int]], clad_offset: float
    ) -> gf.Component:
        taper_core = (
            pdk_components.ebeam_routing_taper_te1550_w500nm_to_w3000nm_L40um()
        )

        taper_cell = gf.Component()
        core_ref = taper_cell << taper_core

        if clad_layer and clad_offset > 0:
            bbox = taper_core.bbox()
            if bbox is not None:
                clad_rect = gf.components.rectangle(
                    size=(
                        bbox.right - bbox.left + 2 * clad_offset,
                        bbox.top - bbox.bottom + 2 * clad_offset,
                    ),
                    layer=clad_layer,
                )
                clad_ref = taper_cell << clad_rect
                clad_ref.center = (
                    (bbox.left + bbox.right) / 2,
                    (bbox.bottom + bbox.top) / 2,
                )

        bbox = taper_cell.bbox()
        if bbox is not None:
            taper_cell.move(origin=(0, 0), destination=(-bbox.left, -bbox.bottom))

        taper_cell.add_ports(core_ref.ports)
        return taper_cell

    slab = c << fpr_slab(
        radius=radius,
        width_rect=width_rect,
        height_rect=height_rect,
        layer=layer,
        npoints=npoints,
        clad_layer=clad_layer,
        clad_offset=clad_offset,
    )
    # Since fpr_slab is now aligned at its bottom-left, we need to place it relative to that
    # For simplicity, let's keep the star coupler centered around (0,0) for now
    # and adjust placement if boundary errors persist.
    slab.center = (0, 0)

    half_h = height_rect / 2
    radius_eff = max(radius, half_h)
    # Centre du cercle droit et angle utile
    alpha = asin(min(1.0, half_h / radius_eff))
    cx_right = width_rect / 2 - radius_eff * np.cos(alpha)

    # === SORTIES (côté droit) ===
    # Positions en y des centres des tapers, centrés autour de 0
    offsets_out = np.arange(n_outputs) - (n_outputs - 1) / 2
    y_positions_out = offsets_out * pitch_outputs

    if np.max(np.abs(y_positions_out)) > half_h:
        raise ValueError(
            "Outputs exceed FPR height; reduce pitch_outputs or n_outputs."
        )

    taper_to_place = taper_with_clad(clad_layer=clad_layer, clad_offset=clad_offset)

    for i, y in enumerate(y_positions_out):
        # Angle local sur l'arc (si on suit la courbure)
        theta = asin(np.clip(y / radius_eff, -1.0, 1.0))
        x_arc = cx_right + radius_eff * np.cos(theta)

        orient_deg = np.degrees(theta) if angle_outputs else 0.0

        tref = c << taper_to_place
        # Orienter pour que o2 (large) soit perpendiculaire à l'arc (ou horizontal)
        tref.rotate(orient_deg - 180)
        # Placer la partie large sur l'arc : translation de o2 vers (x_arc, y)
        o2_center = tref.ports["o2"].center
        dx = x_arc - o2_center[0]
        dy = y - o2_center[1]

        # Ajout de l'overlap
        if taper_overlap != 0:
            overlap_dx = -taper_overlap * np.cos(theta)
            overlap_dy = -taper_overlap * np.sin(theta)
            dx += overlap_dx
            dy += overlap_dy


        # Ajout de l'overlap
        if taper_overlap != 0:
            overlap_dx = -taper_overlap * np.cos(theta)
            overlap_dy = -taper_overlap * np.sin(theta)
            dx += overlap_dx
            dy += overlap_dy

        tref.move((dx, dy))
        # Exposer le port de sortie (côté étroit, vers la droite)
        c.add_port(name=f"e{i+1}", port=tref.ports["o1"])

    # === ENTRÉES (côté gauche) ===
    # Centre du cercle gauche
    cx_left = -width_rect / 2 + radius_eff * np.cos(alpha)

    # Positions en y des centres des tapers d'entrée, centrés autour de 0
    offsets_in = np.arange(n_inputs) - (n_inputs - 1) / 2
    y_positions_in = offsets_in * pitch_inputs

    if np.max(np.abs(y_positions_in)) > half_h:
        raise ValueError("Inputs exceed FPR height; reduce pitch_inputs or n_inputs.")

    for i, y in enumerate(y_positions_in):
        # Angle local sur l'arc gauche
        theta = asin(np.clip(y / radius_eff, -1.0, 1.0))
        x_arc = cx_left - radius_eff * np.cos(theta)

        # Orientation du taper (180° inversé pour côté gauche)
        orient_deg = (180 - np.degrees(theta)) if angle_inputs else 180.0

        tref = c << taper_to_place
        # Orienter pour que o2 (large) soit perpendiculaire à l'arc (ou horizontal)
        tref.rotate(orient_deg - 180)
        # Placer la partie large sur l'arc : translation de o2 vers (x_arc, y)
        o2_center = tref.ports["o2"].center
        dx = x_arc - o2_center[0]
        dy = y - o2_center[1]

        # Ajout de l'overlap
        if taper_overlap != 0:
            overlap_dx = taper_overlap * np.cos(theta)
            overlap_dy = -taper_overlap * np.sin(theta)
            dx += overlap_dx
            dy += overlap_dy

        tref.move((dx, dy))
        # Exposer le port d'entrée (côté étroit, vers la gauche)
        c.add_port(name=f"o{i+1}", port=tref.ports["o1"])

    return c



if __name__ == "__main__":
    # Test du Star Coupler complet (5 entrées + 4 sorties)

    sc = star_coupler(
        n_inputs=5,
        n_outputs=4,
        pitch_inputs=5.2790946,
        pitch_outputs=5.2742795,
        angle_inputs=True,
        angle_outputs=True,
        taper_length=40.0,
        taper_wide=3.0,
        wg_width=0.5,
        radius=130.0,
        width_rect=80.344,
        height_rect=152.824,
        layer=(1, 0),
        npoints=361,
    )
    sc.show()