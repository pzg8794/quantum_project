# Tools

This folder contains **framework test + repair utilities**.

## Structure

- `tools/tests/`: fast local sanity checks (naming/resume invariants, etc.).
- `tools/state/`: audit/repair utilities for saved `.pkl` state under `daqr/config/framework_state/`.

## Quick commands

- Naming + Random-resume invariants:
  - `python3 tools/tests/test_state_naming_and_resume.py`

- State metadata audit / repair:
  - `python3 tools/state/audit_and_fix_state_qubit_caps.py --help`
  - `python3 tools/state/repair_state_key_attrs.py --help`
  - `python3 tools/state/fix_key_attrs_qubit_caps.py --help`

## Backward compatibility

Some older docs/scripts referenced tools directly under `tools/*.py`.
Thin wrapper entrypoints are kept at the old paths for convenience.

