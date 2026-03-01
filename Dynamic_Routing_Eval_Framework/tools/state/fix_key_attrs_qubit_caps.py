#!/usr/bin/env python3
"""
Retrofit saved evaluator states so `key_attrs['qubit_capacities']` matches the
qubit allocations that actually produced the saved outputs.

This is intentionally conservative:
- For non-random allocators:
  - MultiRunEvaluator: uses a stable value inferred from `runner_qubit_caps` if unique.
  - QuantumExperimentRunner: uses `environment.qubit_capacities` if present.
- For random allocators: skips (allocations can vary by design).

It writes in-place, with per-file backups to a timestamped folder under the
framework_state directory.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import pickle
import shutil
from pathlib import Path
from typing import Any, Literal, Optional, Tuple


PaperId = Literal["paper2", "paper7", "paper12", "unknown"]


def _paper_id_from_path(path: Path) -> PaperId:
    name = path.name.lower()
    if name.endswith("_paper2.pkl"):
        return "paper2"
    if name.endswith("_paper7.pkl"):
        return "paper7"
    if name.endswith("_paper12.pkl"):
        return "paper12"
    return "unknown"


def _as_caps_string(caps: Any) -> Optional[str]:
    if caps is None:
        return None
    if isinstance(caps, str):
        # Already stringified (common in key_attrs/runner_qubit_caps)
        return caps
    try:
        return str(tuple(caps))
    except Exception:
        return str(caps)


def _allocator_is_random(state: dict) -> bool:
    key_attrs = state.get("key_attrs") or {}
    alloc = key_attrs.get("allocator")
    if alloc is None:
        alloc = state.get("allocator_id")
    return "random" in str(alloc).lower()


def _infer_stable_caps(state: dict) -> Tuple[Optional[str], str]:
    """
    Returns (caps_string or None, source_tag)
    """
    # MultiRunEvaluator-style
    rqc = state.get("runner_qubit_caps")
    if isinstance(rqc, dict):
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

    # QuantumExperimentRunner-style
    env = state.get("environment")
    if env is not None:
        caps = getattr(env, "qubit_capacities", None)
        cap_s = _as_caps_string(caps)
        if cap_s:
            return cap_s, "environment.qubit_capacities"

    # Fallback: maybe the state stores qubit_capacities directly
    cap_s = _as_caps_string(state.get("qubit_capacities"))
    if cap_s:
        return cap_s, "state.qubit_capacities"

    return None, "missing"


def _tuple_len_if_parseable(caps_s: str) -> Optional[int]:
    try:
        # Expect "(1, 2, 3)" style; eval safely-ish by restricting chars.
        allowed = set("0123456789,() -")
        if any(c not in allowed for c in caps_s):
            return None
        val = eval(caps_s, {"__builtins__": {}}, {})  # noqa: S307
        if isinstance(val, tuple):
            return len(val)
    except Exception:
        return None
    return None


def _update_nested_env_params(state: dict, stable_caps: str) -> bool:
    """
    Best-effort: align configs._env_params['qubit_capacities'] when present.
    """
    cfg = state.get("configs")
    if cfg is None:
        return False
    env_params = getattr(cfg, "_env_params", None)
    if isinstance(env_params, dict):
        env_params["qubit_capacities"] = stable_caps
        return True
    return False


def _backup_file(src: Path, backup_root: Path, state_root: Path) -> Path:
    rel = src.relative_to(state_root)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path("hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state"),
        help="Root framework_state directory.",
    )
    parser.add_argument(
        "--glob",
        default="day_*/**/*_paper*.pkl",
        help="Glob pattern under state-root to consider.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional CSV report path. Defaults to state-root with timestamp.",
    )
    args = parser.parse_args()

    state_root: Path = args.state_root
    paths = sorted(state_root.glob(args.glob))
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = state_root / f"_key_attrs_backup_{ts}"
    report_path = args.report or (state_root / f"key_attrs_qubit_caps_fix_report_{ts}.csv")

    rows = []
    changed = 0
    skipped_random = 0
    skipped_unstable = 0
    errors = 0

    for p in paths:
        if not p.is_file():
            continue
        paper_id = _paper_id_from_path(p)
        size = p.stat().st_size
        try:
            state = pickle.loads(p.read_bytes())
            if not isinstance(state, dict):
                rows.append(
                    {
                        "path": str(p),
                        "paper": paper_id,
                        "size_bytes": size,
                        "status": "skip_non_dict",
                        "old_caps": "",
                        "new_caps": "",
                        "source": "",
                        "notes": "",
                    }
                )
                continue

            key_attrs = state.get("key_attrs")
            if not isinstance(key_attrs, dict):
                key_attrs = {}
                state["key_attrs"] = key_attrs

            alloc_random = _allocator_is_random(state)
            if alloc_random:
                skipped_random += 1
                rows.append(
                    {
                        "path": str(p),
                        "paper": paper_id,
                        "size_bytes": size,
                        "status": "skip_random_allocator",
                        "old_caps": key_attrs.get("qubit_capacities", ""),
                        "new_caps": "",
                        "source": "",
                        "notes": "",
                    }
                )
                continue

            stable_caps, source = _infer_stable_caps(state)
            if stable_caps is None:
                skipped_unstable += 1
                rows.append(
                    {
                        "path": str(p),
                        "paper": paper_id,
                        "size_bytes": size,
                        "status": "skip_no_stable_caps",
                        "old_caps": key_attrs.get("qubit_capacities", ""),
                        "new_caps": "",
                        "source": source,
                        "notes": "",
                    }
                )
                continue

            old_caps = key_attrs.get("qubit_capacities")
            if str(old_caps) == str(stable_caps):
                rows.append(
                    {
                        "path": str(p),
                        "paper": paper_id,
                        "size_bytes": size,
                        "status": "ok_no_change",
                        "old_caps": old_caps,
                        "new_caps": stable_caps,
                        "source": source,
                        "notes": "",
                    }
                )
                continue

            # Backup then patch
            _backup_file(p, backup_root, state_root)
            key_attrs["qubit_capacities"] = str(stable_caps)
            nested_updated = _update_nested_env_params(state, str(stable_caps))

            notes = []
            if nested_updated:
                notes.append("updated_configs._env_params")
            cap_len = _tuple_len_if_parseable(str(stable_caps))
            if cap_len is not None:
                notes.append(f"caps_len={cap_len}")
            if paper_id == "paper2" and cap_len not in (None, 8):
                notes.append("paper2_non8_paths")

            p.write_bytes(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
            changed += 1
            rows.append(
                {
                    "path": str(p),
                    "paper": paper_id,
                    "size_bytes": size,
                    "status": "changed",
                    "old_caps": old_caps,
                    "new_caps": stable_caps,
                    "source": source,
                    "notes": ";".join(notes),
                }
            )
        except Exception as e:
            errors += 1
            rows.append(
                {
                    "path": str(p),
                    "paper": paper_id,
                    "size_bytes": size,
                    "status": "error",
                    "old_caps": "",
                    "new_caps": "",
                    "source": "",
                    "notes": repr(e),
                }
            )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["path", "paper", "size_bytes", "status", "old_caps", "new_caps", "source", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Processed: {len(paths)} files")
    print(f"Changed: {changed}")
    print(f"Skipped random alloc: {skipped_random}")
    print(f"Skipped unstable/missing: {skipped_unstable}")
    print(f"Errors: {errors}")
    print(f"Backups: {backup_root}")
    print(f"Report: {report_path}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
