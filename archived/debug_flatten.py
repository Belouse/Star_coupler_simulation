import numpy as np
import gdsfactory as gf
from components.star_coupler import fpr_slab, _taper_with_clad
import ubcpdk

# This script is designed to systematically debug the issue where .flatten() returns None.

print("--- Starting Flatten Debug ---")
ubcpdk.PDK.activate()

# Test Case 1: A bare gf.components.taper
# =================================================
print("\n[1] Testing a bare gf.components.taper...")
try:
    c1 = gf.components.taper(length=40, width1=0.5, width2=3.0)
    c1_flat = c1.flatten()
    print(f"    Result of flatten: {'OK' if c1_flat else 'None'}")
    assert c1_flat is not None, "Bare taper failed to flatten."
    print("    ✅ PASSED")
except Exception as e:
    print(f"    ❌ FAILED: {e}")


# Test Case 2: The custom fpr_slab component
# =================================================
print("\n[2] Testing the custom 'fpr_slab' component...")
try:
    c2 = fpr_slab()
    c2_flat = c2.flatten()
    print(f"    Result of flatten: {'OK' if c2_flat else 'None'}")
    assert c2_flat is not None, "fpr_slab failed to flatten."
    print("    ✅ PASSED")
except Exception as e:
    print(f"    ❌ FAILED: {e}")


# Test Case 3: The custom _taper_with_clad component
# =================================================
print("\n[3] Testing the custom '_taper_with_clad' component...")
try:
    c3 = _taper_with_clad(length=40, width1=0.5, width2=3.0, clad_layer=(111,0), clad_offset=3.0)
    c3_flat = c3.flatten()
    print(f"    Result of flatten: {'OK' if c3_flat else 'None'}")
    assert c3_flat is not None, "_taper_with_clad failed to flatten."
    print("    ✅ PASSED")
except Exception as e:
    print(f"    ❌ FAILED: {e}")


# Test Case 4: A component with a single, transformed taper instance
# =================================================================
print("\n[4] Testing a component with one transformed taper instance...")
try:
    c4 = gf.Component("container_single_taper")
    taper_inst = _taper_with_clad(length=40, width1=0.5, width2=3.0, clad_layer=(111,0), clad_offset=3.0)
    
    tref = c4 << taper_inst
    tref.rotate(10)
    tref.move((50, 25))

    c4_flat = c4.flatten()
    print(f"    Result of flatten: {'OK' if c4_flat else 'None'}")
    assert c4_flat is not None, "Container with transformed taper failed to flatten."
    print("    ✅ PASSED")
except Exception as e:
    print(f"    ❌ FAILED: {e}")


# Test Case 5: The full star_coupler component
# =================================================
print("\n[5] Testing the full 'star_coupler' component...")
try:
    # Need to import the full component for this test
    from components.star_coupler import star_coupler
    c5 = star_coupler(n_inputs=3, n_outputs=4)
    c5_flat = c5.flatten()
    print(f"    Result of flatten: {'OK' if c5_flat else 'None'}")
    assert c5_flat is not None, "Full star_coupler failed to flatten."
    print("    ✅ PASSED")
except Exception as e:
    print(f"    ❌ FAILED: {e}")

print("\n--- Flatten Debug Finished ---")
