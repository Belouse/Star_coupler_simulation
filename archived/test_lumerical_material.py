import sys
sys.path.append(r"C:\Program Files\Lumerical\v252\api\python")
import lumapi

print("Testing Lumerical MODE material import...")
mode = lumapi.MODE(hide=False)  # Show GUI to see what's happening

test_materials = [
    "Si3N4 (Silicon Nitride) - Luke",
    "Si3N4 (Silicon Nitride) - Kischkat",
    "Si3N4 (Silicon Nitride) - Phillip",
]

for mat in test_materials:
    try:
        script = f'''
deleteall;
addrect;
set("material", "{mat}");
'''
        mode.eval(script)
        print(f"✓ SUCCESS: '{mat}' works!")
        break
    except Exception as e:
        print(f"✗ FAILED: '{mat}' - {str(e)[:80]}")

print("\nPress Enter to close MODE...")
input()
mode.close()
