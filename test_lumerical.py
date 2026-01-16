import sys
lumerical_api_path = r"C:\Program Files\Lumerical\v252\api\python"
lumerical_python_path = r"C:\Program Files\Lumerical\v252\python"
lumerical_site_packages_path = r"C:\Program Files\Lumerical\v252\python\Lib\site-packages"

if lumerical_api_path not in sys.path:
    sys.path.append(lumerical_api_path)
if lumerical_python_path not in sys.path:
    sys.path.append(lumerical_python_path)
if lumerical_site_packages_path not in sys.path:
    sys.path.append(lumerical_site_packages_path)

import lumapi

print("Testing Lumerical connection...")
try:
    fdtd = lumapi.FDTD(hide=True)
    print("SUCCESS: Lumerical connected")
    fdtd.close()
except Exception as e:
    print(f"FAILED: {e}")
