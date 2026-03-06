# Resume/State Integrity Log — `key_attrs.qubit_capacities`

This log captures the **issue → diagnosis → fixes** for mismatched / contaminated `key_attrs["qubit_capacities"]` in saved evaluator states (`daqr/config/framework_state/*.pkl`) and the code changes that prevent recurrence.

---

## 1) Problem Statement

During resumed runs, some saved evaluator objects had **inconsistent qubit-allocation metadata**:

- `key_attrs["qubit_capacities"]` did **not** match the qubit allocation actually used by the run (or by the allocator).
- This caused resume/equality checks to fail (or to resume from an incompatible superset) and created confusing “contamination” signals even when the underlying results were still valid.

**Important exception:** when the allocator is **Random**, per-run qubit allocations can vary by design, so we treat `qubit_capacities` differently for resume consistency.

---

## 2) User-Visible Symptoms

- Resume comparison failures showed mismatched attrs like:
  - `key_attrs.qubit_capacities` differed between “Current attrs” and “Loaded attrs”.
  - `entanglement_success_factor` inconsistently stored as `"None"` vs `"100"` (metadata mismatch).
- Some early runtime failures were triggered by resumed states with missing/None physics parameters (separate but related “resume hardening”).

---

## 3) Diagnosis (What Was Actually Wrong)

### A) Metadata drift (state vs actual run)

For **non-random allocators**, the *effective qubit allocation* should be stable (allocator-determined) and should be stored consistently so that:

- resume selection chooses the correct file
- equality checks don’t fail
- resume-from-superset reconstruction doesn’t get blocked by unrelated metadata mismatches

### B) Random allocator must be excluded from “stable qubit caps”

For **Random** allocators, `key_attrs["qubit_capacities"]` can vary, and is already embedded into filenames in several runner states (e.g., suffix `_(...)`).

Attempting to “normalize” random runs by overwriting `key_attrs["qubit_capacities"]` is incorrect and can destroy the record of what was run.

---

## 4) Fixes Implemented (Chronological, by Commit)

### Commit `9cc67c18` — Paper2 noise: default None params
- **Goal:** prevent `None` physics params from breaking calculations (esp. in resumed states).
- **File:** `daqr/core/quantum_physics.py`

### Commit `f4ceff33` — Harden Paper2 noise for resumed states
- **Goal:** additional Paper2 resume robustness around physics/noise parameter defaults.
- **File:** `daqr/core/quantum_physics.py`

### Commit `121f8642` — Fix resume: enforce allocator-derived qubit caps
- **Goal:** ensure runs strongly prefer allocator-derived qubit allocations (avoid legacy fallbacks).
- **File:** `daqr/evaluation/multi_run_evaluator.py`

### Commit `7b97cff6` — Ensure qubit caps stored correctly in saved evaluator state
- **Goal:** before saving `MultiRunEvaluator`, set `key_attrs["qubit_capacities"]` to the **stable** value inferred from `runner_qubit_caps` (non-random allocators only).
- **Files:**
  - `daqr/evaluation/multi_run_evaluator.py`
  - `daqr/config/experiment_config.py` (normalize `entanglement_success_factor` default to `100` when config value is `None`)

### Commit `3a96ca09` — Fix: persist qubit_capacities in runner key_attrs
- **Goal:** before saving `QuantumExperimentRunner`, force `key_attrs["qubit_capacities"]` to match the actual `environment.qubit_capacities` (non-random allocators only).
- **Files:**
  - `daqr/evaluation/experiment_runner.py`
  - `tools/fix_key_attrs_qubit_caps.py` (conservative retrofit script; skips Random allocators)

---

## 5) Retrofit / State Cleanup (What Was Changed On Disk)

### A) MultiRunEvaluator states (non-random allocators)
These were already consistent in practice after the above fixes:
- `key_attrs["qubit_capacities"]` matches the single stable value present in `runner_qubit_caps`.

### B) QuantumExperimentRunner states
Many runner states (esp. for paper7/paper12) do **not** pickle `environment`, so there is no independent “ground truth” to repair against; going forward we enforce correctness at save-time (commit `3a96ca09`).

### C) Random allocator runner states
A previous attempted mass-fix incorrectly overwrote some Random-run `key_attrs["qubit_capacities"]`.
Those files were restored from backups:

- Backup root (example): `daqr/config/framework_state/_key_attrs_backup_20260228_232437/`
- Restored targets: selected `day_20260204/QuantumExperimentRunner_*Random*_paper12.pkl`

---

## 6) Verification / How To Confirm It’s Fixed

### A) Spot-check a MultiRunEvaluator (non-random)
Confirm `key_attrs["qubit_capacities"]` matches the unique value in `runner_qubit_caps`:

- Load the `.pkl`, compute `unique(set(str(caps) for caps in runner_qubit_caps[*][*]))`.
- If `len(unique)==1`, it should equal `key_attrs["qubit_capacities"]`.

### B) Runner save-time enforcement (non-random)
Run a small non-random runner and confirm the saved state has:
- `key_attrs["qubit_capacities"] == str(tuple(environment.qubit_capacities))`

### C) Random allocators
Confirm we do **not** overwrite/normalize random allocations:
- `QuantumExperimentRunner.__eq__` and `MultiRunEvaluator.__eq__` both treat random allocators as a special case.

---

## 7) Operational Notes

- Unpickling `framework_state/*.pkl` can import heavy deps; use the existing audit venv:
  - `.venv-audit` (created previously for audits / state inspection)
- The retrofit script is intentionally conservative and primarily useful for reporting / confirming stability:
  - `Dynamic_Routing_Eval_Framework/tools/state/fix_key_attrs_qubit_caps.py` (wrapper also exists at `tools/fix_key_attrs_qubit_caps.py`)
- Registry persistence (`local_backup_registry.json/.pkl`) is **debounced** and quiet by default:
  - `GoogleDriveBackupManager.save_registry()` writes at most once per `registry_save_min_interval_s` (default `5s`) unless `force=True`
  - `register_state_path()` only triggers persistence when the registry mapping actually changes
  - Optional toggle: set `backup_mgr.registry_autosave = False` to defer writes (manual flush via `backup_mgr.save_registry(force=True)`)

---

## 8) Resume Behavior Contract (Evaluator Priority)

This section captures the **expected evaluator resume behavior** (the “contract” we must not break).

### MultiRunEvaluator (`runs = 5` example)

**Target:** resume must minimize redundant compute while keeping the *current run’s settings* authoritative.

1) **Exact match first:** attempt to resume the evaluator’s own state (e.g., `5` runs).
2) **If exact not found:** attempt to resume from other evaluator states that match all key attrs (allocator/env/attack/capacity/frames/scale/testbed/etc.).
3) **If multiple candidates exist:** try horizons from **highest runs → lowest runs** (e.g., try `8` before `3`).
4) **If highest works:** load it, then *reconstruct* a subset for the target horizon by:
   - keeping only experiments `1..5`,
   - discarding extra experiments beyond target (`6..8`),
   - and allowing the run loop to skip already-computed experiments.
5) **If highest fails but a lower horizon works:** load it and keep `1..3`, then ensure the evaluator remembers it must still run missing experiments (`4..5`) during execution.

**Non-negotiable invariant:** resume must never override the caller-intended settings (target runs/models/scale/allocator/testbed).

### Design guardrails (do not violate)

- **State discovery happens at object creation/resume.** `MultiRunEvaluator`, `QuantumExperimentRunner`, and model objects are responsible for discovering/loading their own state via `ExperimentConfiguration.resume_obj()` and their internal `__eq__` contracts.
- **Do not duplicate state-probing logic in other modules.** Avoid re-deriving filenames, scanning registries, or adding parallel “skip” heuristics outside the object that owns the state.
- **Source of truth for “experiment already completed” is `env_experiments`.** We intentionally do not treat `evaluation_results` as authoritative for skip decisions; it is analysis/aggregation output and may include non-experiment keys.
- **Mental model:** see `docs/guides/STATE_LAYERS_AND_RESUME.md` (sun/world/continent/country/worker narrative) to keep responsibilities clear and code minimal.

### QuantumExperimentRunner (note; defer deeper auditing)

Runner states represent one concrete experiment instance (frames/seed/env/attack/allocator/capacity), so resume must be conservative about **core attrs**.

However, **model-level completeness must not block resume**. Runner resume must support:

- **Subset model-set resume:** if a saved runner state contains results for a *subset* of the current model list, resume is allowed and the run should execute **only the missing models**.
- **Superset model-set resume:** if a saved runner state contains results for *extra* models, resume is allowed and results should be filtered down to the current model list.

**This fixes the “false missing model” symptom** where runner resume would incorrectly skip a valid saved state and force a full rerun. Worst case, a truly missing model should resume from `model_state/` (if present) or rerun only that model—not rerun the entire experiment.

**Before (bad):**
```
❌ MODEL SET MISMATCH in Runner — saved state missing required models (skipping resume)
Missing models: ['iCPursuitNeuralUCB']
```

**After (correct):**
```
ℹ️  Partial runner resume: will run missing models: ['iCPursuitNeuralUCB']
```

---

## 9) Plan + TODO (Resume Hardening)

**Priority now:** evaluator resume behavior (MultiRunEvaluator).

### TODO (Evaluator)
- ✅ Add unit test: when both `3` and `8` run states exist, evaluator tries `8` first even if the `3`-run pickle is larger on disk.
- ✅ Add unit test: if the highest horizon candidate is incompatible (equality fails), evaluator falls back to the next candidate (e.g., use `3`).
- ✅ Confirm run loop skips completed experiments (`1..k`) and runs only missing experiments (`k+1..target`) (validated via stubbed `run_experiment` in tests).

### TODO (Deferred)
- Runner cross-horizon resume semantics (only resume from “higher”, never from “lower”).
- Model cross-horizon resume semantics (e.g., 4k → 2k subset) and fairness rules.
- Runner/model-set compare: treat missing models as partial resume (do not skip resume).

### Logging / Notes
- Every change to resume selection/order must be recorded here (this file) and mirrored in the relevant tracker/notes docs.

---

## 10) Resume Contract Unit Tests (Evaluator)

Implemented in `Dynamic_Routing_Eval_Framework/tests/test_resume_behavior.py`:

- `test_resume_prefers_highest_horizon_even_if_smaller_pickle`
  - Verifies `runs=5` will try `8` before `3` even if the `3`-run pickle is larger on disk.
- `test_resume_falls_back_when_highest_incompatible`
  - Verifies if `8` is incompatible, resume falls back to `3`.
- `test_resume_from_subset_and_extend_runs`
  - Verifies resuming from `3` and then executing `runs=5` only runs missing experiments (`4,5`).
