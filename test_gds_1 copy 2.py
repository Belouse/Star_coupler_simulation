from __future__ import annotations
from functools import partial
import numpy as np
import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.typings import ComponentSpec, CrossSectionSpec



@gf.cell
def free_propagation_region(
    radius: float = 117,
    theta1: float = 40,
    theta2: float = 20,
    da: float = 2,
    dg: float = 5,
    wg_width: float = 0.5,
    inputs: int = 3,
    outputs: int = 4,
    layer: tuple = (1,0)
) -> gf.Component:
    c = gf.Component()

    num_points1 = int(theta1/ 0.01) + 1
    angles1 = np.linspace(-0.5*theta1, 0.5*theta1, num_points1)
    angles_rad1 = np.deg2rad(angles1)
    x1 = radius*np.cos(angles_rad1)
    y1 = radius*np.sin(angles_rad1)

    num_points2 = int(theta2/ 0.01) + 1
    angles2 = np.linspace(180-0.5*theta2, 180+0.5*theta2, num_points2)
    angles_rad2 = np.deg2rad(angles2)

    x2 = radius*np.cos(angles_rad2)+radius
    y2 = radius*np.sin(angles_rad2)



    xpts = np.concatenate([x1, x2, x2[::-1], x1[::-1]])
    ypts = np.concatenate([y1, y2, -y2[::-1], -y1[::-1]])


    c = gf.Component()
    c.add_polygon(list(zip(xpts, ypts)), layer=(1, 0))


    if inputs == 1:
        c.add_port(
            "o1",
            center=(0, 0),
            width=wg_width,
            orientation=180,
            layer=layer,
        )

    else:
        for i in range(inputs):
            theta = np.pi-0.5*(inputs-1)*da/radius + i*da/radius
            x = (radius - 0.002) * np.cos(theta) + radius
            y = (radius - 0.002) * np.sin(theta)
            x = gf.snap.snap_to_grid(x)
            y = gf.snap.snap_to_grid(y)
            c.add_port(
                f"W{i}",
                center=(x, y),
                width=wg_width,
                orientation=theta/np.pi*180,
                layer=layer,
            )

    for i in range(outputs):
        theta = -0.5*(outputs-1)*dg/radius + i*dg/radius
        x = (radius - 0.002) * np.cos(theta)
        y = (radius - 0.002) * np.sin(theta)
        x = gf.snap.snap_to_grid(x)
        y = gf.snap.snap_to_grid(y)
        c.add_port(
            f"E{i}",
            center=(x, y),
            width=wg_width,
            orientation=theta/np.pi*180,
            layer=layer,
        )
    return c


free_propagation_region_input = partial(free_propagation_region, inputs=1)

free_propagation_region_output = partial(
    free_propagation_region, inputs=10
)


@gf.cell(check_instances=False)
def star_coupler(
    inputs: int = 3,
    outputs: int = 4,
    wg_width: float = 0.5,
    input_wg_length: float = 50.0,
    output_wg_length: float = 50.0,
    layer: tuple = (1,0),
) -> Component:
    """
    Créer un star coupler unique avec des entrées sur la gauche et des sorties sur la droite.
    
    Args:
        inputs: Nombre d'entrées (sur la gauche)
        outputs: Nombre de sorties (sur la droite)
        wg_width: Largeur des guides d'onde
        input_wg_length: Longueur des guides d'onde d'entrée
        output_wg_length: Longueur des guides d'onde de sortie
        layer: Couche GDS
    
    Returns:
        Component: Le composant star coupler
    """
    c = Component()

    # Créer la région de propagation libre unique
    fpr = gf.get_component(
        free_propagation_region,
        inputs=inputs,
        outputs=outputs,
        layer=layer,
        wg_width=wg_width
    )

    fpr_ref = c.add_ref(fpr)

    # Créer la section transversale pour les guides d'onde
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Ajouter les guides d'onde d'entrée (côté gauche)
    for i in range(inputs):
        # Créer un guide d'onde droit
        wg = gf.components.straight(length=input_wg_length, cross_section=xs)
        wg_ref = c.add_ref(wg)
        
        # Connecter le guide d'onde au port d'entrée du FPR
        wg_ref.connect("o2", fpr_ref.ports[f"W{i}"])
        
        # Exposer le port d'entrée du guide d'onde
        c.add_port(f"input_{i}", port=wg_ref.ports["o1"])
    
    # Ajouter les guides d'onde de sortie (côté droit)
    for i in range(outputs):
        # Créer un guide d'onde droit
        wg = gf.components.straight(length=output_wg_length, cross_section=xs)
        wg_ref = c.add_ref(wg)
        
        # Connecter le guide d'onde au port de sortie du FPR
        wg_ref.connect("o1", fpr_ref.ports[f"E{i}"])
        
        # Exposer le port de sortie du guide d'onde
        c.add_port(f"output_{i}", port=wg_ref.ports["o2"])

    return c



@gf.cell(check_instances=False)
def star_coupler_with_gc(
    num_gc: int = 5,
    gc_spacing: float = 127.0,
    inputs: int = 3,
    outputs: int = 4,
    wg_width: float = 0.5,
    input_wg_length: float = 50.0,
    output_wg_length: float = 50.0,
    layer: tuple = (1,0),
) -> Component:
    """
    Créer un star coupler avec des grating couplers en entrée.
    
    Args:
        num_gc: Nombre de grating couplers
        gc_spacing: Espacement entre les grating couplers (en μm)
        inputs: Nombre d'entrées du star coupler
        outputs: Nombre de sorties du star coupler
        wg_width: Largeur des guides d'onde
        input_wg_length: Longueur des guides d'onde d'entrée
        output_wg_length: Longueur des guides d'onde de sortie
        layer: Couche GDS
    
    Returns:
        Component: Le composant complet
    """
    c = Component()

    # Créer le star coupler
    sc = star_coupler(
        inputs=inputs,
        outputs=outputs,
        wg_width=wg_width,
        input_wg_length=input_wg_length,
        output_wg_length=output_wg_length,
        layer=layer
    )
    sc_ref = c.add_ref(sc)

    # Créer les grating couplers alignés en rangée verticale
    gc_component = gf.components.grating_coupler_elliptical_te()
    
    # Positionner les grating couplers en rangée verticale
    gc_refs = []
    for i in range(num_gc):
        gc_ref = c.add_ref(gc_component)
        # Positionner les GC en rangée verticale, espacés de gc_spacing
        gc_ref.x = 0
        gc_ref.y = i * gc_spacing
        # Orienter les GC horizontalement (pas de rotation)
        # gc_ref.rotate(0)  # Pas besoin de rotation, ils sont déjà horizontaux
        gc_refs.append(gc_ref)

    # Router chaque connexion individuellement
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer, radius=10)
    
    # Connecter seulement les GC #2, #3, #4 (indices 1, 2, 3) aux entrées du star coupler
    # GC #1 (indice 0) et GC #5 (indice 4) ne sont pas connectés
    gc_to_connect = [1, 2, 3]  # Indices des GC à connecter
    for idx, gc_idx in enumerate(gc_to_connect):
        if gc_idx < num_gc and idx < inputs:
            gc_port = gc_refs[gc_idx].ports["o1"]
            sc_port = sc_ref.ports[f"input_{idx}"]
            
            # Utiliser route_single pour router chaque connexion individuellement
            route = gf.routing.route_single(
                c,
                gc_port,
                sc_port,
                cross_section=xs,
            )

    # Exposer les ports de sortie du star coupler
    for i in range(outputs):
        c.add_port(f"output_{i}", port=sc_ref.ports[f"output_{i}"])

    return c


@gf.cell
def GC_array()->gf.Component:
    c = gf.Component()
    return c


if __name__ == "__main__":
    # Créer un star coupler avec 5 grating couplers espacés de 127 μm
    c = star_coupler_with_gc(num_gc=5, gc_spacing=127.0, inputs=3, outputs=4)
    c.show()

  