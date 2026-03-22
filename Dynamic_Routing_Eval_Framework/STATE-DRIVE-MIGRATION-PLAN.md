# Drive State Migration Plan

This document records the **state-storage migration plan** for the GA project so the
reasoning, constraints, and approval steps are preserved before any code changes.

---

## 1) Goal

Move large state/checkpoint storage off the local machine and onto the new shared
Google Drive, while preserving resume behavior and minimizing local disk use.

### Target policy

- **When the shared drive is available**
  - write locally only as a **temporary staging step**
  - persist the completed state to the shared drive
  - verify the shared-drive copy
  - remove the staged local file
- **When resuming/loading**
  - prefer the local file if it exists
  - otherwise load from the shared drive
- **When the shared drive is unavailable**
  - fall back to local behavior safely

---

## 2) Current local state layout

Project root:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework`

Current large state roots:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state` — about `41G`
- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/model_state` — about `25G`

Other current config-state paths:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/tools/state`
- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state_backups`
- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state_quarantine`

---

## 3) New shared-drive target

Shared drive URL provided by user:

- `https://drive.google.com/drive/u/0/folders/0AK0VchnNyM-xUk9PVA`

Mounted shared-drive root discovered locally:

- `/Users/pitergarcia/Library/CloudStorage/GoogleDrive-garciapiterz@gmail.com/Shared drives/equitable_routing_and_diagnostic_ai`

Recommended mirrored workspace root on the shared drive:

- `/Users/pitergarcia/Library/CloudStorage/GoogleDrive-garciapiterz@gmail.com/Shared drives/equitable_routing_and_diagnostic_ai/projects/hybrid_variable_framework/Dynamic_Routing_Eval_Framework`

Expected shared-drive state roots:

- `/Users/pitergarcia/Library/CloudStorage/GoogleDrive-garciapiterz@gmail.com/Shared drives/equitable_routing_and_diagnostic_ai/projects/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state`
- `/Users/pitergarcia/Library/CloudStorage/GoogleDrive-garciapiterz@gmail.com/Shared drives/equitable_routing_and_diagnostic_ai/projects/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/model_state`

---

## 4) Constraints and rules

- **No code changes are applied without explicit review/approval.**
- Every proposed modification should go through:
  - task
  - before
  - after
  - reason
- Prefer changes in the **backup/storage layer** over orchestration code.
- Avoid touching `experiment_config.py` unless the manager layer cannot enforce the
  required policy by itself.
- This document should be updated as the migration proceeds.

---

## 5) Code review findings

### A) Active manager

`ExperimentConfiguration` currently instantiates:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/experiment_config.py`

and uses:

- `LocalBackupManager(date_str=self.day_str, config_dir=self.dir, verbose=self.verbose)`

### B) Current write ownership

The actual pickle write currently happens in:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/experiment_config.py`

inside `save_obj()`.

This matters because a strict “write local temporarily, then offload and delete local”
policy is harder to guarantee if the backup manager does not own the write lifecycle.

### C) Existing Drive-aware layer

The project already has a Drive-aware manager:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/gd_backup_manager.py`

Key findings:

- `DRIVE_FOLDER_ID` is currently hardcoded to an older drive.
- `_find_drive_workspace_root()` already supports `DAQR_DRIVE_WORKSPACE_ROOT`.
- `quantum_data_paths` already tracks both local and drive locations.

### D) Local backup manager findings

Relevant file:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/local_backup_manager.py`

Findings:

- `save_file()` exists, but the static grep pass found no direct call sites outside
  its definition. Runtime use through inheritance or indirect dispatch has not yet
  been ruled out.
- `build_registry()` scans local and drive paths and persists registry state.
- `get_latest_state()` is brittle because it mixes path lookup concerns with parent
  manager behavior that may return loaded data rather than a clean path.
- `_scan_local_files()` scans `"drive"` first and `"local"` second, then applies a
  size/mtime dedupe rule. That means registry entries can still resolve to local
  files even when drive copies exist, depending on which copy appears “better” to
  the dedupe policy.
- `save_registry()` is inherited from the parent manager, so the registry cache
  persistence policy must be reviewed together with `LocalBackupManager`; otherwise
  a drive-first state design may still keep the canonical registry cache local.
- A drive-first/offload design will likely need a clean distinction between:
  - a **local staging path**
  - a **durable drive path**
  - the **registry path** recorded for resume

### D.1) Static review notes on local manager behavior

The current local-manager review suggests four concrete concerns to resolve before
state migration:

1. **Registry preference is not explicitly drive-first**
   - the current scan/merge logic can prefer local files over drive files
   - this conflicts with the desired “durable copy lives on drive” policy

2. **Path contract is not cleanly separated from data loading**
   - `get_latest_state()` in the local manager treats the parent manager as if it
     returns a path-like result
   - but the parent manager also contains actual state-loading behavior
   - this should be normalized before adding more fallback logic

3. **Write lifecycle is not yet explicitly staged**
   - the desired policy is:
     - write local temporarily
     - persist to drive
     - verify
     - delete local staged file
   - this lifecycle is not yet clearly expressed in the manager layer

4. **Registry durability needs an explicit rule**
   - we need to decide whether the source of truth for the registry is:
     - the local cache
     - the drive-backed registry
     - or a synchronized pair with one designated authority

### E) Practical conclusion

The first-pass targets should be:

- `daqr/config/gd_backup_manager.py`
- `daqr/config/local_backup_manager.py`

`experiment_config.py` should remain **review-only** unless a later step proves that
the backup managers alone cannot enforce the policy.

---

## 5.1) Current registry structure (inspected)

This section records the **actual current registry shape** before any schema change.

### Registry files found

Under:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config`

the active registry file currently present is:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/local_backup_registry.json`

No separate `metadata.json` was found in the same config root during this inspection.

### Actual top-level structure

The live registry is a top-level `dict` with these keys:

- `framework_state`
- `model_state`
- `framework_state_backups`
- `framework_state_quarantine`

Current entry counts at inspection time:

- `framework_state` — `3140`
- `model_state` — `12663`
- `framework_state_backups` — `26`
- `framework_state_quarantine` — `1`

### Actual entry shape

The current live entry shape is **flat string paths**, not nested objects.

Examples:

- `backup_registry["framework_state"][filename] = "/absolute/path/to/file.pkl"`
- `backup_registry["model_state"][filename] = "/absolute/path/to/file.pkl"`

Sample inspected values:

- `framework_state` sample value:
  - `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state/day_20260308/QuantumExperimentRunner_1_4000-Default_Adversarial_OnlineAdaptive-4000_1_paper8_m2_balanced.pkl`
- `model_state` sample value:
  - `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/model_state/day_20260308/Oracle(base)_6000-Default_Adversarial_Adaptive-6000_EXP3.pkl`
- `framework_state_backups` sample value:
  - `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state_backups/_state_repair_backup_20260301_004009/day_20260228/QuantumExperimentRunner_2_6000-Default_Adversarial_Adaptive-6000_2_paper2.pkl`
- `framework_state_quarantine` sample value:
  - `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state_quarantine/_quarantine_20260301_004009/day_20260207/QuantumExperimentRunner_1_4000-Default_Stochastic_Random-4000_1_paper2.pkl`

### Code assumptions tied to that shape

The current helper and caller code largely assume **string-valued entries**:

- `daqr/config/state_registry.py`
  - `register_state_path(..., path: str)` writes `config_registry[component][filename] = path`
  - the same helper also writes plain strings into:
    - `backup_mgr.backup_registry`
    - `backup_mgr.new_entries`
- `daqr/config/experiment_config.py`
  - several resume/search paths treat `self.backup_registry[item_k][item_v]` as a direct path string
- `daqr/evaluation/experiment_runner.py`
  - reads registry values as path strings
- `daqr/evaluation/multi_run_evaluator.py`
  - parses registry values as path strings

### Important implication for the next design step

Any move from:

- `entry = "/absolute/path.pkl"`

to something like:

- `entry = {"active_path": "...", "drive_path": "...", ...}`

will require a controlled compatibility plan, because the current runtime does not
consistently treat registry entries as dicts.

That means the next schema discussion should answer two questions explicitly:

1. whether the registry should remain **flat** with more keys per existing entry
2. how to preserve compatibility for existing callers that currently expect a string

---

## 5.2) Preferred registry strategy (current direction)

The current preferred direction is:

- keep a **single flat canonical section**
- avoid adding another traversal object/layer
- use the file name itself to infer state type
- treat `state` as the structure that should eventually replace the legacy registry buckets

### Canonical target shape

Preferred canonical section:

- `registry["state"][file_name] = {...}`

Naming note:

- the enclosing object may still be called `backup_registry` for compatibility
- but `state` is the canonical internal structure and should eventually replace:
  - `framework_state`
  - `model_state`
  - other legacy bucket-style registry sections used for active lookups

Preferred entry shape:

```python
registry["state"][file_name] = {
    "component": "framework_state" | "model_state",
    "active_path": "...",
    "drive_path": "...",
    "offload_status": "active",
    "ready_for_offload": False,
}
```

### Component classification rule

Component should be stored explicitly in the canonical state entry, but derived
from a configurable classification map so the rule can grow over time.

Preferred strategy:

- keep a key-based component registry/config structure
- use regex patterns to classify filenames into components
- default unmatched files to `model_state`

Current matching rule:

- filenames matching `Evaluator|Runner` → `framework_state`
- everything else → `model_state`

Example shape:

```python
STATE_COMPONENT_PATTERNS = {
    "framework_state": [r"Evaluator", r"Runner"],
}
```

Classification behavior:

1. iterate component keys
2. evaluate that component's regex patterns against `file_name`
3. first match wins
4. if nothing matches, use `model_state`

This keeps the registry lookup simple:

- lookup key = `file_name`
- read path = `entry["active_path"]`

and still preserves an explicit `component` field for routing, validation, and
future component growth.

### Immediate implication

The migration strategy should now focus on:

1. defining `registry["state"][file_name]` as the canonical target
2. preserving compatibility for legacy readers that still expect:
   - `registry["framework_state"][file_name] = "/path"`
   - `registry["model_state"][file_name] = "/path"`
3. using `state` as the long-term replacement for those legacy lookup buckets
4. deferring any code patch until that compatibility path is reviewed

---

## 5.3) Legacy reader compatibility map

The current runtime still has several direct string-path readers. These are the
main compatibility points that must be handled before the canonical `registry["state"]`
schema can replace the old structure.

### A) `state_registry.py`

File:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/state_registry.py`

Current assumption:

- `register_state_path(..., path: str)` writes a plain string path into:
  - `config_registry[component][filename]`
  - `backup_mgr.backup_registry[component][filename]`
  - `backup_mgr.new_entries[component][filename]`

Compatibility requirement:

- either keep this helper writing the legacy structure during transition
- or introduce a schema-aware adapter that can write both legacy and canonical forms

### B) `experiment_config.py`

File:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/experiment_config.py`

Current assumption:

- `self.backup_registry[item_k][item_v]` is treated as a direct path string
- the method then converts it to `Path(...)`, reconstructs local/drive variants,
  and may overwrite the registry entry with a new string path

Compatibility requirement:

- `get_latest_state()` / resume lookup needs a schema-aware read path before the
  registry value can stop being a plain string

### C) `experiment_runner.py`

File:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/evaluation/experiment_runner.py`

Current assumption:

- reads `self.configs.backup_mgr.backup_registry.get(self.component, {}).get(file_name)`
- treats the returned value as a plain path string
- wraps it directly in `Path(...)`

Compatibility requirement:

- resume logic needs a read adapter that returns the active usable path from the
  canonical registry entry

### D) `multi_run_evaluator.py`

File:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/evaluation/multi_run_evaluator.py`

Current assumption:

- reads `self.configs.backup_mgr.backup_registry[self.component][file_name]`
- treats the returned value as a plain path string
- uses it for `Path(...)`, `exists()`, and size-based candidate ordering

Compatibility requirement:

- candidate enumeration can keep using file names, but path resolution must be
  routed through a canonical accessor instead of assuming the registry value is a string

### Migration conclusion

The safest transition order is:

1. **dual-read**
   - add schema-aware accessors that can read either:
     - legacy string entries, or
     - canonical `registry["state"][file_name]` entries
2. **dual-write**
   - once reads are safe, write both:
     - legacy component buckets
     - canonical `registry["state"]`
3. **cleanup**
   - after validation, remove legacy direct-string assumptions

This minimizes breakage and avoids a flag-day schema cutover.

---

## 6) Target behavior contract

### Save path behavior

This section now reflects the **deferred offload** strategy, not the earlier
immediate-offload idea.

If the shared drive is available:

1. write the state to a local staging location
2. keep that local file available while the run is still active
3. once the run is complete, mark the state as ready for offload
4. a separate offload pass persists the state to the shared-drive target path
5. verify the shared-drive copy exists and is usable
6. update registry metadata
7. only then remove durable local copies

If the shared drive is unavailable:

1. write locally
2. keep the local file available
3. preserve resumability
4. make the fallback explicit in logs

### Resume/load behavior

For a registry entry:

1. if a local file exists, use it
2. otherwise try the shared-drive path
3. if neither exists, fail clearly and do not silently continue with a bad path

### Offload control behavior

The offload decision should not be made inside the low-level `save_file()` call.

Instead:

1. the framework writes locally during active execution
2. a higher-level completion trigger marks a state as ready for offload
3. the registry carries that offload state explicitly
4. a separate offload pass uploads/verifies/cleans up

### Space policy

The design goal is to use **near-zero local space** for durable state when the drive is
mounted and writable, while still preserving active-run local availability.

---

## 7) Approval-gated implementation plan

### Phase 1 — configuration and path resolution

- [x] review and update `gd_backup_manager.py`
- [x] make the new Drive folder ID configurable
- [ ] use the new shared-drive root via `DAQR_DRIVE_WORKSPACE_ROOT`
- [ ] confirm `quantum_data_paths["obj"]` resolves to the mirrored drive paths

### Phase 2 — save/offload policy

- [x] review and update `local_backup_manager.py`
- [x] inspect and document current registry behavior
- [ ] define the canonical `registry["state"][file_name]` schema in code
- [ ] design compatibility for legacy string-path registry readers
- [ ] replace immediate-offload behavior with deferred offload behavior
- [x] harden `get_latest_state()` to return resolved paths deterministically
- [x] add pre-implementation offload contract tests

### Proposed `save_file()` contract change (reviewed before implementation)

The next planned implementation change is **not** a rename or signature change.
It is a behavioral extension of the existing method:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/local_backup_manager.py`
- method: `save_file(self, component, filename, file_data)`

Current behavior:

- writes the pickle locally
- verifies the local file is non-empty
- updates the registry to the local path
- returns the local path

Planned behavior:

1. write the file locally as a **staged** file
2. verify the staged local file is non-empty
3. if Drive is unavailable:
   - keep the local file
   - update registry to the local path
   - return the local path
4. if Drive is available:
   - attempt to persist the staged file to the mirrored Drive path
5. if Drive upload fails:
   - keep the local file
   - update registry to the local path
   - return the local path
6. if Drive verification fails:
   - keep the local file
   - update registry to the local path
   - return the local path
7. if Drive persistence and verification both succeed:
   - update registry to the Drive-backed path
   - delete the local staged file
   - return the Drive-backed path

Non-negotiable rule:

- **The local staged file must only be deleted after the Drive-backed copy has been verified.**

No planned changes in this step:

- no rename of `save_file()`
- no method signature change
- no direct changes to `experiment_config.py`

### Phase 3 — migration

- [ ] create mirrored destination folders on the new drive
- [ ] copy registry files first
- [ ] copy a small sample of state files
- [ ] verify drive-backed resume/load works
- [ ] bulk-copy `framework_state`
- [ ] bulk-copy `model_state`

### Phase 4 — validation

- [ ] test with drive available and local staged files removed
- [ ] test with drive unavailable and local fallback
- [ ] confirm registry entries remain valid across both modes

### Test-first contract coverage

Added test file:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/tests/test_drive_state_offload.py`

Contract tests included:

- `test_drive_available_moves_staged_file_and_updates_registry`
- `test_drive_unavailable_keeps_local_file_and_local_registry_path`
- `test_failed_drive_persist_does_not_delete_local_staged_file`
- `test_failed_drive_verification_does_not_delete_local_staged_file`
- `test_registry_records_drive_path_after_successful_offload`

Additional schema-transition tests have now been added in:

- `/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/tests/test_registry_update_on_save.py`

These new tests define the first dual-read contract for a future registry accessor:

- read legacy `registry[component][file_name] = "/path"`
- read canonical `registry["state"][file_name] = {...}`
- prefer `active_path`, then fall back to `drive_path`

Current status of those new tests:

- the test file syntax is valid
- the test run currently fails at import time because
  `get_registered_state_path` has not been implemented yet
- this is expected and desirable at this stage because the tests now define the
  next patch boundary

Current status:

- The test file is in place before lifecycle implementation.
- The tests currently **skip** in the default `python3` environment because
  `googleapiclient` is not installed there.
- The test file has now been aligned to target `save_file()` directly, matching the
  approved implementation direction.
- This keeps the suite stable while preserving the contract we want to enforce
  once the implementation is approved.

### Implemented `save_file()` lifecycle

`save_file()` now follows the approved drive-first contract:

1. write the pickle locally as a staged file
2. verify the staged local file is non-empty
3. if Drive is unavailable:
   - keep the local file
   - update registry to the local path
   - return the local path
4. if Drive is available:
   - attempt to upload the staged file to the mirrored Drive path
5. if upload fails:
   - keep the local file
   - update registry to the local path
   - return the local path
6. if Drive verification fails:
   - keep the local file
   - update registry to the local path
   - return the local path
7. if upload and verification succeed:
   - update registry to the Drive-backed path
   - delete the local staged file
   - return the Drive-backed path

Validation after implementation:

- Syntax validation passed with:
  - `python3 -m py_compile daqr/config/local_backup_manager.py`
- Contract test run completed as:
  - `OK (skipped=5)`
- The tests remain skipped in the default environment because `googleapiclient`
  is still unavailable there.
- Real-environment validation was then run in:
  - `/Users/pitergarcia/DataScience/Semester4/GA-Work/.quantum/bin/activate`
- Result in `.quantum`:
  - `Ran 5 tests`
  - `FAILED (failures=1)`
- Failing test:
  - `test_failed_drive_verification_does_not_delete_local_staged_file`
- Current diagnosis:
  - `save_file()` verifies Drive success with an inline filesystem check
    (`drive_path.exists() and drive_path.stat().st_size > 0`)
  - the test harness overrides `_verify_drive_state_path(...)`, but the current
    implementation does not call that hook
  - therefore the code cannot simulate or honor a verification failure branch yet
  - this means the implementation is **close**, but not fully aligned with the
    documented contract under the “verification fails” case

### Strategy revision note

After reviewing how the framework uses state files during active execution, the
immediate-offload `save_file()` design is now considered **transitional** rather
than the final approach.

Preferred direction:

1. `save_file()` should preserve active local state during the run
2. a later completion trigger should mark state as offload-ready
3. the registry should evolve toward the canonical:
   - `registry["state"][file_name]`
4. a separate offload pass should upload / verify / clean up

No code rollback has been applied yet in this document; this note records the
current design direction before the next patch.

### Phase 5 — local cleanup

- [ ] only after validation, decide whether to remove old local state trees

---

## 8) Risks and watch items

- Google Drive sync latency can make “file exists” checks look inconsistent if validation
  is too aggressive or too early.
- Registry entries may currently mix:
  - absolute local paths
  - drive-derived paths
  - older `{local_path, date}` structures
- A partial migration without registry normalization can break resume selection.
- Because the current write happens in `experiment_config.py`, the manager-layer-only
  design must be verified before assuming that file can remain untouched.

---

## 9) Decision log

### 2026-03-08

- User created a new shared drive because the old one has size limitations.
- User wants the system to use **local disk only temporarily** during writes.
- User wants durable state moved to the shared drive as soon as it is created and verified.
- User requested that **all modifications go through approval first**.
- First approved code change was applied in `daqr/config/gd_backup_manager.py`.
- The Google Drive folder ID is now configurable via `DAQR_DRIVE_FOLDER_ID`.
- The new default Drive folder ID is set to `0AK0VchnNyM-xUk9PVA`.
- Active uses of the previous hardcoded Drive folder constant were replaced with `self.drive_folder_id`.
- Verbose logging now records the resolved Drive folder ID, Drive workspace root, and Drive config directory at manager initialization.
- Syntax validation passed with `python3 -m py_compile daqr/config/gd_backup_manager.py`.
- Second approved code change was applied in `daqr/config/local_backup_manager.py`.
- `get_latest_state()` now acts as a path resolver instead of mixing path lookup with parent-manager state-loading behavior.
- The resolver now follows this order:
  - exact registry path
  - mirrored drive path if the registry points to local
  - mirrored local path if the registry points to drive
  - last-resort Drive recovery
- This establishes a clearer contract for future drive-first/offload work.
- Syntax validation passed with `python3 -m py_compile daqr/config/local_backup_manager.py`.
- Added pre-implementation contract tests in `tests/test_drive_state_offload.py`.
- The drive-offload contract tests were then aligned to call `save_file()` directly
  rather than a hypothetical helper method.
- Syntax validation passed with `python3 -m py_compile tests/test_drive_state_offload.py`.
- Initial test run in the default environment completed as `OK (skipped=5)` because
  the environment lacks `googleapiclient`.
- Approved `save_file()` lifecycle extension was applied without renaming the method
  or changing its signature.
- `save_file()` now updates registry to Drive only after verified Drive persistence,
  and only then deletes the local staged file.
- Validation after the change:
  - `python3 -m py_compile daqr/config/local_backup_manager.py`
  - `python3 -m unittest tests/test_drive_state_offload.py`
  - result: `OK (skipped=5)`
- After further design review, that immediate-offload approach is no longer the
  preferred long-term strategy because active runs may still depend on local state.
- Preferred direction is now:
  - keep active writes local during execution
  - use a deferred completion-triggered offload flow
  - evolve toward a flat canonical registry section:
    - `registry["state"][file_name]`
  - infer state type from file names:
    - `Evaluator` / `Runner` → `framework_state`
    - everything else → `model_state`

### 2026-03-21

- Handoff docs were refreshed for future agents at:
  - `../AGENTS.md`
  - `AGENTS.md`
- The Drive upload guard is already present in `daqr/config/gd_backup_manager.py`:
  - upload when the remote file is missing
  - overwrite only when the remote file exists but is smaller than the local file
  - skip overwrite when the remote file is the same size or larger
- Regression coverage for that behavior lives in:
  - `tools/tests/test_task2d_drive_upload_size_guard_behavior.py`
  - `tools/tests/test_task2d_drive_upload_size_guard_static.py`
- Future agents should verify the current code and these tests before changing Drive migration behavior.
- Cleanup logic clarification:
  - `delete_from_drive(...)` is emergency-only and should not be part of the
    normal successful allocator/testbed completion flow.
  - `ExperimentConfiguration.delete_file(...)` now preserves remote datalake
    backups and deletes only the local corrupted state plus its local registry
    entry.
  - Successful allocator cleanup should verify remote existence first and then
    delete matching local files only.
- Remote confirmation check on 2026-03-21:
  - `quantum_data_lake/framework_state/day_20260321/` does not exist in Drive
  - `quantum_data_lake/model_state/day_20260321/` does not exist in Drive
  - therefore the current `paper12` local files from `day_20260321` are not
    present in the Drive datalake yet
- Shared-drive root fix on 2026-03-21:
  - `_ensure_drive_folder(...)` now resolves root-level datalake folders under
    the shared drive id itself instead of falling back to service-account-owned
    storage
  - regression coverage added in:
    - `tests/test_gd_backup_manager_ensure_drive_folder.py`
- Pattern-based Drive operations were added to the existing backup manager:
  - `LocalBackupManager.upload_files_by_pattern(...)`
  - `LocalBackupManager.check_drive_files_by_pattern(...)`
  - both operate on the existing datalake contract and support regex/testbed or
    filename-style matching without ad hoc scripts
  - upload verifies in batch against remote folder metadata after the upload pass
    instead of per-file Drive verification
  - regression coverage added in:
    - `tests/test_local_backup_manager_pattern_drive_ops.py`
- Standalone batch entrypoint added for data-management work:
  - `create_pattern_drive_manager(date_str, config_dir, verbose=False)`
  - `migrate_files_by_pattern(date_str, config_dir, pattern, components=None, delete_local=False, parallel=False, verbose=False)`
  - intended use:
    - instantiate a Drive-aware manager without forcing the full pipeline save path
    - upload/check/delete by regex or testbed/tag
    - optionally run `framework_state` and `model_state` in parallel
  - important default behavior:
    - `date_str=None` means scan **all** `day_*` folders for matches
    - `date_str='day_YYYYMMDD'` narrows the operation to one day folder
  - status reporting:
    - both `upload_files_by_pattern(...)` and `migrate_files_by_pattern(...)`
      now support built-in progress/status output via `status_callback`
    - default behavior prints status directly to the terminal
- File-based entrypoint added for normal use:
  - `tools/state/manage_drive_pattern.py`
  - use this instead of inline terminal Python for pattern-based check/migrate work

---

## 10) Next approved step

Next proposed code review/change should be:

- registry compatibility and transition strategy for `registry["state"][file_name]`

Reason:

- the canonical schema direction is now clear
- the next step is to map current string-path readers to the new structure before
  any registry helper or reader code is changed
