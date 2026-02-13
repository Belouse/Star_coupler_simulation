import gdsfactory as gf
import ubcpdk
from gdsfactory.typings import LayerSpec

@gf.cell
def my_mmi_3db(
    gds_path: str = "components/ANT_PDK.gds",
    cell_name: str = "MMI_TE_3dB",
    layer_port: LayerSpec = (4, 0) 
) -> gf.Component:
    """
    Imports the MMI from the GDS and adds ports manually.
    """
    try:
        # 1. Attempt to import the GDS
        c = gf.import_gds(gds_path, cellname=cell_name)
        
        # 2. If successful, add manual ports ON THE GDS COMPONENT
        c.add_port(
            name="o1", 
            center=(-12.88, 0),       
            width=0.75,           
            orientation=180,
            layer=layer_port
        )

        c.add_port(
            name="o2", 
            center=(12.88, 0.975),  
            width=0.75, 
            orientation=0,
            layer=layer_port
        )

        c.add_port(
            name="o3", 
            center=(12.88, -0.975), 
            width=0.75, 
            orientation=0,
            layer=layer_port
        )
        return c

    except Exception as e:
        # 3. Fallback: If error, return the Black Box (BB) directly
        # We do NOT add manual ports because the BB already has them
        print(f" Warning: Unable to load GDS '{gds_path}'.")
        print(f"   Error: {e}")
        print("   -> Using ubcpdk Black Box (BB) component.")
        
        return ubcpdk.cells.ANT_MMI_1x2_te1550_3dB_BB()


@gf.cell
def ANT_GC(
    gds_path: str = "components/ANT_PDK.gds",
    cell_name: str = "GratingCoupler_TE_Oxide_8degrees_Nitride",
    layer_port: LayerSpec = (4, 0)
) -> gf.Component:
    """
    Imports the Grating Coupler from GDS. 
    Falls back to ubcpdk BB if file not found.
    """
    try:
        # 1. Attempt to import GDS
        c = gf.import_gds(gds_path, cellname=cell_name)

        # 2. Add Port o1
        # IMPORTANT: Verify X,Y center in KLayout. 
        # Assuming (0,0) for the taper tip.
        c.add_port(
            name="o1",
            center=(0, 0), 
            width=0.75,
            orientation=180, # Facing West (Left)
            layer=layer_port
        )
        return c

    except Exception as e:
        # 3. Fallback
        print(f" Warning: Unable to load GC from GDS '{gds_path}'.")
        print(f"   Error: {e}")
        print("   -> Using ubcpdk GC Black Box (BB).")
        
        # Note: Ensure this component exists in your version of ubcpdk
        return ubcpdk.components.GC_SiN_TE_1310_8degOxide_BB()


if __name__ == "__main__":
    # Test to visualize and check ports
    
    print("--- Testing MMI and GC ---")
    
    # Create the two components
    mmi = my_mmi_3db()
    gc = ANT_GC()

    # Create a parent component to hold both
    c = gf.Component("MMI_and_GC_Test")
    
    # Add references to the MMI and GC
    mmi_ref = c << mmi
    gc_ref = c << gc
    
    # Move one component to avoid overlap
    gc_ref.movex(mmi.xsize + 20)
    
    c.show()