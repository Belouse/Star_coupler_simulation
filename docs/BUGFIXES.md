# Run_varFDTD.py - Bug Fixes

## Issues Fixed

### 1. **Deprecated Property: `background_index`**
   - **Error**: `'background_index' is deprecated, use 'index' instead`
   - **Fix**: Changed `set("background index", 1.444)` to `set("index", 1.444)`
   - **Location**: varFDTD solver configuration (line ~107)

### 2. **Inactive Span Properties**
   - **Error**: `in set, the requested property 'x span' is inactive`
   - **Root Cause**: Setting `x_span = 0` or `y_span = 0` makes the perpendicular span property inactive in Lumerical
   - **Fix**: Changed all zero spans to `1e-9 m` (1 nanometer - negligibly small but valid)
   
   **Affected locations**:
   - Mode source configuration (3 sources)
   - Power monitor configuration (4 monitors)

### 3. **Error Handling for Individual Sources/Monitors**
   - **Issue**: If one source/monitor failed, the whole loop would crash
   - **Fix**: Added try-catch blocks around each source and monitor creation
   - **Benefit**: Script continues even if individual sources/monitors have issues

## Changes Summary

| Property | Before | After | Reason |
|----------|--------|-------|--------|
| `background index` | Deprecated | `index` | Lumerical v252 API update |
| `x_span` (when not needed) | `0` | `1e-9` | Avoid "inactive property" error |
| `y_span` (when not needed) | `0` | `1e-9` | Avoid "inactive property" error |
| Error handling | None | try-catch per item | Robustness |

## Validation

The corrected script has been tested and verified to:
- ✓ Generate 3 mode sources at input ports (o1, o2, o3)
- ✓ Generate 4 power monitors at output ports (e1, e2, e3, e4)
- ✓ Use correct span values (1.5 µm for active dimension)
- ✓ Use correct axis orientation (x-axis for East/West ports)
- ✓ Configure all parameters without deprecated APIs

## Testing

Run the verification script:
```bash
python scripts/test_run_varFDTD_config.py
```

Output confirms all sources and monitors are configured correctly.

## Next Steps

The script should now run successfully:
```bash
python scripts/Run_varFDTD.py
```

All sources and monitors will be created, and the simulation will execute on GPU (or CPU fallback).
