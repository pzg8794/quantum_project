# Tools

This folder contains **framework test + repair utilities**.

## Structure

- `tools/tests/`: fast local sanity checks (naming/resume invariants, etc.).
- `tools/state/`: audit/repair utilities for saved `.pkl` state under `daqr/config/framework_state/`.

## Quick commands

- Run the small, fast test battery (no full runs):
  - `bash tools/tests/run_small_tests.sh`

- Naming + Random-resume invariants:
  - `python3 tools/tests/test_state_naming_and_resume.py`

- State metadata audit / repair:
  - `python3 tools/state/audit_and_fix_state_qubit_caps.py --help`
  - `python3 tools/state/repair_state_key_attrs.py --help`
  - `python3 tools/state/fix_key_attrs_qubit_caps.py --help`

- Aggregate state day directories (local) and optionally clean up Drive day folders:
  - Help:
    - `python3 tools/state/aggregate_state_dirs.py --help`
  - Local-only aggregation into today's folder:
    - `python3 tools/state/aggregate_state_dirs.py --components framework_state --target today`
  - Drive scan (no changes):
    - `python3 tools/state/aggregate_state_dirs.py --components framework_state --target today --remote --dry-run`
  - Drive execute (moves winners into target day folder; trashes smaller duplicates + empty old day folders; updates `state_index.json`):
    - `python3 tools/state/aggregate_state_dirs.py --components framework_state --target today --remote --remote-execute`
  - Note: remote cleanup uses Drive Trash (not permanent delete). If quota is tight, you may need to empty Drive Trash to reclaim space.

## Backward compatibility

Some older docs/scripts referenced tools directly under `tools/*.py`.
Thin wrapper entrypoints are kept at the old paths for convenience.
