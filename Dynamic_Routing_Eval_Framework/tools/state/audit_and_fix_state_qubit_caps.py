#!/usr/bin/env python3
"""
Audit and (when possible) retrofit saved evaluator/runner states so that
`key_attrs['qubit_capacities']` reflects the qubit-allocation object actually used.

Ground-truth sources (in priority order):
  1) MultiRunEvaluator: stable value in `runner_qubit_caps` (non-random allocators only)
  2) QuantumExperimentRunner: `environment.qubit_capacities` (non-random allocators only)
  3) Random allocator runner states: allocation encoded in filename suffix `_(...)`

If no ground truth is present in the saved state, we DO NOT guess.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import pickle
import re
import shutil
from pathlib import Path
from typing import Any, Optional, Tuple


def _as_caps_string(caps: Any) -> Optional[str]:
    if caps is None:
        return None
    if isinstance(caps, str):
        return caps
    try:
        return str(tuple(caps))
    except Exception:
        return str(caps)


def _allocator_is_random(state: dict, path: Path) -> bool:
    key_attrs = state.get("key_attrs") or {}
    alloc = key_attrs.get("allocator")
    if alloc is None:
        alloc = state.get("allocator_id")
    if alloc is None:
        alloc = path.name
    return "random" in str(alloc).lower()


def _infer_from_runner_qubit_caps(state: dict) -> Tuple[Optional[str], str]:
    rqc = state.get("runner_qubit_caps")
    if not isinstance(rqc, dict):
        return None, "no_runner_qubit_caps"
    unique: set[str] = set()
    for _scenario, exps in rqc.items():
        if not isinstance(exps, dict):
            continue
        for _exp_id, caps in exps.items():
            cap_s = _as_caps_string(caps)
            if cap_s:
                unique.add(cap_s)
    if len(unique) == 1:
        return next(iter(unique)), "runner_qubit_caps"
    if len(unique) > 1:
        return None, "runner_qubit_caps_unstable"
    return None, "runner_qubit_caps_empty"


def _infer_from_environment(state: dict) -> Tuple[Optional[str], str]:
    env = state.get("environment")
    if env is None:
        return None, "no_environment"
    cap_s = _as_caps_string(getattr(env, "qubit_capacities", None))
    if cap_s:
        return cap_s, "environment.qubit_capacities"
    return None, "environment_missing_qubit_capacities"


_FILENAME_CAPS_RE = re.compile(r"_\((?P<caps>[0-9_]+)\)_paper(2|7|12)\\.pkl$", re.IGNORECASE)


def _infer_from_filename(path: Path) -> Tuple[Optional[str], str]:
    m = _FILENAME_CAPS_RE.search(path.name)
    if not m:
        return None, "no_filename_caps"
    raw = m.group("caps")
    try:
        ints = tuple(int(x) for x in raw.split("_") if x != "")
        return str(ints), "filename_caps"
    except Exception:
        return None, "filename_caps_parse_error"


def _backup_file(src: Path, backup_root: Path, state_root: Path) -> Path:
    rel = src.relative_to(state_root)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _update_nested_env_params(state: dict, stable_caps: str) -> bool:
    cfg = state.get("configs")
    if cfg is None:
        return False
    env_params = getattr(cfg, "_env_params", None)
    if isinstance(env_params, dict):
        env_params["qubit_capacities"] = stable_caps
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path("hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state"),
    )
    parser.add_argument(
        "--glob",
        default="day_*/*_paper*.pkl",
        help="Glob under --state-root.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="If set, apply changes in-place (with backups). Otherwise audit only.",
    )
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    state_root: Path = args.state_root
    paths = sorted(state_root.glob(args.glob))
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = state_root / f"_key_attrs_backup_{ts}"
    report_path = args.report or (state_root / f"state_qubit_caps_audit_{ts}.csv")

    rows = []
    changed = 0
    need_change = 0
    unknown = 0
    errors = 0

    for p in paths:
        if not p.is_file():
            continue
        try:
            state = pickle.loads(p.read_bytes())
            if not isinstance(state, dict):
                continue

            key_attrs = state.get("key_attrs")
            if not isinstance(key_attrs, dict):
                key_attrs = {}
                state["key_attrs"] = key_attrs
            old_caps = str(key_attrs.get("qubit_capacities", ""))

            is_random = _allocator_is_random(state, p)

            # Determine ground truth
            new_caps = None
            source = ""
            if p.name.startswith("MultiRunEvaluator_"):
                if is_random:
                    new_caps, source = None, "random_allocator_multirun_unstable"
                else:
                    new_caps, source = _infer_from_runner_qubit_caps(state)
            elif p.name.startswith("QuantumExperimentRunner_"):
                if is_random:
                    new_caps, source = _infer_from_filename(p)
                else:
                    new_caps, source = _infer_from_environment(state)
            else:
                # Unknown object type; best-effort on what we know
                if is_random:
                    new_caps, source = _infer_from_filename(p)
                else:
                    new_caps, source = _infer_from_runner_qubit_caps(state)
                    if new_caps is None:
                        new_caps, source = _infer_from_environment(state)

            if new_caps is None:
                unknown += 1
                rows.append(
                    {
                        "path": str(p),
                        "status": "unknown_no_ground_truth",
                        "old_caps": old_caps,
                        "new_caps": "",
                        "source": source,
                    }
                )
                continue

            if old_caps == str(new_caps):
                rows.append(
                    {
                        "path": str(p),
                        "status": "ok",
                        "old_caps": old_caps,
                        "new_caps": str(new_caps),
                        "source": source,
                    }
                )
                continue

            need_change += 1
            if args.apply:
                _backup_file(p, backup_root, state_root)
                key_attrs["qubit_capacities"] = str(new_caps)
                _update_nested_env_params(state, str(new_caps))
                p.write_bytes(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
                changed += 1
                status = "changed"
            else:
                status = "would_change"

            rows.append(
                {
                    "path": str(p),
                    "status": status,
                    "old_caps": old_caps,
                    "new_caps": str(new_caps),
                    "source": source,
                }
            )
        except Exception as e:
            errors += 1
            rows.append(
                {
                    "path": str(p),
                    "status": "error",
                    "old_caps": "",
                    "new_caps": "",
                    "source": repr(e),
                }
            )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "status", "old_caps", "new_caps", "source"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Files: {len(paths)}")
    print(f"Need change: {need_change}")
    print(f"Changed: {changed}")
    print(f"Unknown (no ground truth): {unknown}")
    print(f"Errors: {errors}")
    if args.apply:
        print(f"Backups: {backup_root}")
    print(f"Report: {report_path}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
