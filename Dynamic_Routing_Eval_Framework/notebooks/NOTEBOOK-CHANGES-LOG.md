# Notebook Changes Log

This log records **surgical notebook changes** (issues encountered, what was changed, and why), to avoid accidental “extra” modifications.

## 2026-03-01

### Paper 7 — Standardized run configuration notebook created
- **New file:** `H-MABs_Eval-Testbed-Paper7-StandardizedRunConfig.ipynb` (copied from `H-MABs_Eval-Testbed-Paper7.ipynb`)
- **Goal:** run Paper 7 testbed under our standard run configuration (base `4000` frames, `2000` step, runs `3` and `5`).
- **Change (run config only):** replaced the dev settings (`50` frames / `50` step / `5` experiments / runs `[5]`) with:
  - `current_frames = FRAMEWORK_CONFIG['base_frames']`
  - `frame_step = FRAMEWORK_CONFIG['frame_step']`
  - `current_experiments = FRAMEWORK_CONFIG['exp_num']`
  - `RUNS = [3, 5]`

### Notebook KeyError fix — `FRAMEWORK_CONFIG['intensity']`
- **Issue:** some cells referenced `FRAMEWORK_CONFIG['intensity']` but intensity is stored in `FRAMEWORK_CONFIG['env_attrs']['intensity']`.
- **Fix:** added a compatibility alias immediately after `FRAMEWORK_CONFIG` is defined:
  - `FRAMEWORK_CONFIG['intensity'] = FRAMEWORK_CONFIG['env_attrs']['intensity']`
- **Applied in:** `H-MABs_Eval-Testbed-Paper2.ipynb`, `H-MABs_Eval-Testbed-Paper2-StandardizedRunConfig.ipynb`, `H-MABs_Eval-Testbed-Paper7.ipynb`, `H-MABs_Eval-Testbed-Paper12.ipynb`.

### Notebook NameError fix — `test_scenarios`
- **Issue:** evaluator/runner cells call `scenarios=test_scenarios` but `test_scenarios` was never defined in Paper 7 / Paper 12 notebooks.
- **Fix:** added a single shared `test_scenarios = {...}` dict right after `FRAMEWORK_CONFIG` is defined (in the same config cell).
- **Applied in:** `H-MABs_Eval-Testbed-Paper7.ipynb`, `H-MABs_Eval-Testbed-Paper7-StandardizedRunConfig.ipynb`, `H-MABs_Eval-Testbed-Paper12.ipynb`.

### Paper 7 — Fix path-count mismatch (prevents GNeuralUCB index error)
- **Issue:** Paper 7 config had `num_paths=4`, but the Paper 7 path generator used `k=5` and `n_qisps=3`, which yields `5 * C(3,2) = 15` paths/contexts/rewards. Models infer `num_groups = len(reward_list)`, so they could select a path index ≥4 while the allocator/attack arrays are sized for 4 paths → runtime errors like `index 4 is out of bounds for axis 0 with size 4`.
- **Fix (settings only, standardized notebook):** set `paper7.k=4` and `paper7.n_qisps=2` so the generator produces exactly 4 paths (matching `num_paths=4`).
- **Applied in:** `H-MABs_Eval-Testbed-Paper7-StandardizedRunConfig.ipynb`.

### Paper 12 — Standardized run configuration notebook created
- **New file:** `H-MABs_Eval-Testbed-Paper12-StandardizedRunConfig.ipynb` (copied from `H-MABs_Eval-Testbed-Paper12.ipynb`)
- **Goal:** run Paper 12 testbed under our standard run configuration (base `4000` frames, `2000` step, runs `3` and `5`).
- **Change (run config only):** replaced the QuARC dev settings (e.g., `1500` frames / `500` step / `1` experiment / runs `[5]`) with:
  - `current_frames = FRAMEWORK_CONFIG['base_frames']`
  - `frame_step = FRAMEWORK_CONFIG['frame_step']`
  - `current_experiments = FRAMEWORK_CONFIG['exp_num']`
  - `RUNS = [3, 5]`

## 2026-03-02

### Paper 8 — Standardized run configuration notebook created
- **New file:** `H-MABs_Eval-Testbed-Paper8-StandardizedRunConfig.ipynb`
- **Goal:** run Paper 8 testbed under our standard run configuration (base `4000` frames, `2000` step, runs `3` and `5`) using the same `AllocatorRunner + get_physics_params(...)` flow as the other testbeds.
- **Design constraint:** Paper 8 components come from core modules (`Paper8RandomConnectedTopologyGenerator`, `Paper8NoiseModel`, `Paper8FidelityCalculator`); notebook wiring only (no framework code changes).
- **Default safety:** `SMOKE_TEST=True` (runs `[3]`, scales `[1]`) to avoid accidental long runs; set `SMOKE_TEST=False` for the full standardized sweep.
