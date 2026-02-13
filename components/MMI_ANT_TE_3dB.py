import gdsfactory as gf
import ubcpdk
from gdsfactory.typings import LayerSpec

@gf.cell
def my_mmi_3db(
    gds_path: str = "components/ANT_MMI_TE_3dB.gds",
    cell_name: str = "MMI_TE_3dB",
    layer_port: LayerSpec = (1, 0) # Vérifiez la couche de vos guides (souvent 1,0 ou 68,0)
) -> gf.Component:
    """
    Importe le MMI depuis le GDS et ajoute les ports manuellement.
    """
    try:
        # 1. Tentative d'importation du GDS
        c = gf.import_gds(gds_path, cellname=cell_name)
        
        # 2. Si ça marche, on ajoute les ports manuels SUR LE GDS
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
        # 3. Fallback : Si erreur, on retourne la BB directement
        # On n'ajoute PAS de ports manuels car la BB en a déjà
        print(f"⚠️ Attention : Impossible de charger le GDS '{gds_path}'.")
        print(f"   Erreur : {e}")
        print("   -> Utilisation du composant Black Box (BB) de ubcpdk.")
        
        return ubcpdk.cells.ANT_MMI_1x2_te1550_3dB_BB()

if __name__ == "__main__":
    # Test pour visualiser et vérifier les ports
    c = my_mmi_3db()
    c.show()