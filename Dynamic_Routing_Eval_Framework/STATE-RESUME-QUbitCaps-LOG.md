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
  - `Dynamic_Routing_Eval_Framework/tools/fix_key_attrs_qubit_caps.py`

