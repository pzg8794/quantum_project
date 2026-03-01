#!/usr/bin/env python3
"""
Repair saved runner/evaluator state metadata under `daqr/config/framework_state`.

Primary goals:
1) Ensure `key_attrs['qubit_capacities']` matches the *actual* qubit capacities used.
   - MultiRunEvaluator: must be stable/unique from `runner_qubit_caps` (non-random allocators)
   - QuantumExperimentRunner: must match `environment.qubit_capacities` when environment is present
2) Normalize legacy default values that commonly break resume comparisons:
   - `entanglement_success_factor`: None/"None" -> "100"
3) Quarantine obviously-invalid states (do NOT delete):
   - Paper2 states where the used qubit capacities are not length 8
   - States where `len(qubit_capacities) != environment.num_paths` (when environment is present)

This script is conservative: if no ground truth exists, it will not guess.
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


def _as_caps_tuple(caps: Any) -> Optional[tuple]:
    if caps is None:
        return None
    if isinstance(caps, tuple):
        return caps
    if isinstance(caps, str):
        txt = caps.strip()
        allowed = set("0123456789,() -")
        if any(c not in allowed for c in txt):
            return None
        try:
            val = eval(txt, {"__builtins__": {}}, {})  # noqa: S307
            return val if isinstance(val, tuple) else None
        except Exception:
            return None
    try:
        return tuple(caps)
    except Exception:
        return None


def _as_caps_string(caps: Any) -> Optional[str]:
    t = _as_caps_tuple(caps)
    if t is None:
        return None
    return str(t)


def _allocator_is_random(key_attrs: dict, fallback: str) -> bool:
    alloc = key_attrs.get("allocator", None) or fallback
    return "random" in str(alloc).lower()


def _infer_mre_caps(state: dict) -> Tuple[Optional[str], str]:
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
        return next(iter(unique)), "runner_qubit_caps_unique"
    if len(unique) > 1:
        return None, "runner_qubit_caps_unstable"
    return None, "runner_qubit_caps_empty"


def _infer_qer_caps_from_env(state: dict) -> Tuple[Optional[str], str]:
    env = state.get("environment")
    if env is None:
        return None, "no_environment"
    cap_s = _as_caps_string(getattr(env, "qubit_capacities", None))
    if cap_s:
        return cap_s, "environment.qubit_capacities"
    return None, "environment_missing_qubit_capacities"


_FILENAME_CAPS_RE = re.compile(r"_\((?P<caps>[0-9_]+)\)_paper(2|7|12)\\.pkl$", re.IGNORECASE)


def _infer_qer_caps_from_filename(path: Path) -> Tuple[Optional[str], str]:
    m = _FILENAME_CAPS_RE.search(path.name)
    if not m:
        return None, "no_filename_caps"
    raw = m.group("caps")
    try:
        ints = tuple(int(x) for x in raw.split("_") if x != "")
        return str(ints), "filename_caps"
    except Exception:
        return None, "filename_caps_parse_error"


def _normalize_esf(key_attrs: dict, configs: Any) -> bool:
    """
    Normalize entanglement_success_factor to the default 100 when legacy values are None/"None".
    """
    esf = key_attrs.get("entanglement_success_factor", None)
    if esf is not None and str(esf).strip().lower() != "none":
        return False

    default_val = 100
    env_params = getattr(configs, "_env_params", None) if configs is not None else None
    if isinstance(env_params, dict):
        default_val = env_params.get("entanglement_success_factor") or 100
        env_params["entanglement_success_factor"] = default_val

    key_attrs["entanglement_success_factor"] = str(default_val)
    return True


def _backup_file(src: Path, backup_root: Path, state_root: Path) -> Path:
    rel = src.relative_to(state_root)
    dst = backup_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def _move_to_quarantine(src: Path, quarantine_root: Path, state_root: Path) -> Path:
    rel = src.relative_to(state_root)
    dst = quarantine_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return dst


def _paper_id(path: Path) -> str:
    n = path.name.lower()
    if n.endswith("_paper2.pkl"):
        return "paper2"
    if n.endswith("_paper7.pkl"):
        return "paper7"
    if n.endswith("_paper12.pkl"):
        return "paper12"
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path("hybrid_variable_framework/Dynamic_Routing_Eval_Framework/daqr/config/framework_state"),
    )
    parser.add_argument("--glob", default="day_*/*_paper*.pkl")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    state_root: Path = args.state_root
    paths = sorted(state_root.glob(args.glob))

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = state_root.parent / f"framework_state_backups/_state_repair_backup_{ts}"
    quarantine_root = state_root.parent / f"framework_state_quarantine/_quarantine_{ts}"
    report_path = state_root / f"state_repair_report_{ts}.csv"

    rows = []
    changed = 0
    quarantined = 0
    unknown = 0
    errors = 0

    for p in paths:
        if not p.is_file():
            continue
        try:
            state = pickle.loads(p.read_bytes())
            if not isinstance(state, dict):
                continue

            paper = _paper_id(p)
            key_attrs = state.get("key_attrs")
            if not isinstance(key_attrs, dict):
                key_attrs = {}
                state["key_attrs"] = key_attrs

            fallback_alloc = state.get("allocator_id", "") or p.name
            is_random = _allocator_is_random(key_attrs, str(fallback_alloc))

            # Per project convention: random allocator runs are inherently variable.
            # Do not mutate their stored key_attrs (qubit_capacities / esf), except
            # for quarantining obviously-invalid Paper2 states where the saved env
            # indicates a non-8-path configuration.
            if is_random:
                env = state.get("environment")
                env_caps = _as_caps_tuple(getattr(env, "qubit_capacities", None)) if env is not None else None
                if paper == "paper2" and env_caps is not None and len(env_caps) != 8:
                    if args.apply:
                        _backup_file(p, backup_root, state_root)
                        dst = _move_to_quarantine(p, quarantine_root, state_root)
                        quarantined += 1
                        rows.append(
                            {
                                "path": str(p),
                                "paper": paper,
                                "status": "quarantined_paper2_non8_caps",
                                "used_caps_source": "environment.qubit_capacities",
                                "old_caps": str(key_attrs.get("qubit_capacities", "")),
                                "new_caps": str(env_caps),
                                "notes": f"random_allocator_paper2_invalid -> {dst}",
                            }
                        )
                    else:
                        rows.append(
                            {
                                "path": str(p),
                                "paper": paper,
                                "status": "would_quarantine_paper2_non8_caps",
                                "used_caps_source": "environment.qubit_capacities",
                                "old_caps": str(key_attrs.get("qubit_capacities", "")),
                                "new_caps": str(env_caps),
                                "notes": "random_allocator_paper2_invalid",
                            }
                        )
                else:
                    rows.append(
                        {
                            "path": str(p),
                            "paper": paper,
                            "status": "skipped_random_allocator",
                            "used_caps_source": "",
                            "old_caps": str(key_attrs.get("qubit_capacities", "")),
                            "new_caps": "",
                            "notes": "",
                        }
                    )
                continue

            used_caps = None
            used_caps_source = ""
            if p.name.startswith("MultiRunEvaluator_"):
                used_caps, used_caps_source = _infer_mre_caps(state)
            elif p.name.startswith("QuantumExperimentRunner_"):
                used_caps, used_caps_source = _infer_qer_caps_from_env(state)
            else:
                # unknown object type: best-effort
                used_caps, used_caps_source = _infer_mre_caps(state)
                if used_caps is None:
                    used_caps, used_caps_source = _infer_qer_caps_from_env(state)

            if used_caps is None:
                unknown += 1
                rows.append(
                    {
                        "path": str(p),
                        "paper": paper,
                        "status": "unknown_no_ground_truth",
                        "used_caps_source": used_caps_source,
                        "old_caps": str(key_attrs.get("qubit_capacities", "")),
                        "new_caps": "",
                        "notes": "",
                    }
                )
                continue

            used_tuple = _as_caps_tuple(used_caps)
            env = state.get("environment")
            env_paths = getattr(env, "num_paths", None) if env is not None else None
            if env_paths is not None and used_tuple is not None and len(used_tuple) != int(env_paths):
                # Inconsistent state: quarantine.
                notes = f"len(caps)={len(used_tuple)} != env.num_paths={env_paths}"
                if args.apply:
                    _backup_file(p, backup_root, state_root)
                    dst = _move_to_quarantine(p, quarantine_root, state_root)
                    quarantined += 1
                    rows.append(
                        {
                            "path": str(p),
                            "paper": paper,
                            "status": "quarantined_env_len_mismatch",
                            "used_caps_source": used_caps_source,
                            "old_caps": str(key_attrs.get("qubit_capacities", "")),
                            "new_caps": str(used_caps),
                            "notes": f"{notes} -> {dst}",
                        }
                    )
                else:
                    rows.append(
                        {
                            "path": str(p),
                            "paper": paper,
                            "status": "would_quarantine_env_len_mismatch",
                            "used_caps_source": used_caps_source,
                            "old_caps": str(key_attrs.get("qubit_capacities", "")),
                            "new_caps": str(used_caps),
                            "notes": notes,
                        }
                    )
                continue

            if paper == "paper2" and used_tuple is not None and len(used_tuple) != 8:
                # Paper2 must be 8 paths; quarantine the state to avoid reuse.
                notes = f"paper2_invalid_caps_len={len(used_tuple)}"
                if args.apply:
                    _backup_file(p, backup_root, state_root)
                    dst = _move_to_quarantine(p, quarantine_root, state_root)
                    quarantined += 1
                    rows.append(
                        {
                            "path": str(p),
                            "paper": paper,
                            "status": "quarantined_paper2_non8_caps",
                            "used_caps_source": used_caps_source,
                            "old_caps": str(key_attrs.get("qubit_capacities", "")),
                            "new_caps": str(used_caps),
                            "notes": f"{notes} -> {dst}",
                        }
                    )
                else:
                    rows.append(
                        {
                            "path": str(p),
                            "paper": paper,
                            "status": "would_quarantine_paper2_non8_caps",
                            "used_caps_source": used_caps_source,
                            "old_caps": str(key_attrs.get("qubit_capacities", "")),
                            "new_caps": str(used_caps),
                            "notes": notes,
                        }
                    )
                continue

            old_caps = str(key_attrs.get("qubit_capacities", ""))
            new_caps = str(used_caps)

            configs = state.get("configs", None)
            esf_changed = _normalize_esf(key_attrs, configs)

            needs_caps_update = old_caps != new_caps
            if not needs_caps_update and not esf_changed:
                rows.append(
                    {
                        "path": str(p),
                        "paper": paper,
                        "status": "ok",
                        "used_caps_source": used_caps_source,
                        "old_caps": old_caps,
                        "new_caps": new_caps,
                        "notes": "",
                    }
                )
                continue

            if args.apply:
                _backup_file(p, backup_root, state_root)
                key_attrs["qubit_capacities"] = new_caps
                if isinstance(getattr(configs, "_env_params", None), dict):
                    configs._env_params["qubit_capacities"] = new_caps
                state["key_attrs"] = key_attrs
                p.write_bytes(pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL))
                changed += 1
                status = "changed"
            else:
                status = "would_change"

            notes = []
            if needs_caps_update:
                notes.append("updated_qubit_capacities")
            if esf_changed:
                notes.append("normalized_entanglement_success_factor")

            rows.append(
                {
                    "path": str(p),
                    "paper": paper,
                    "status": status,
                    "used_caps_source": used_caps_source,
                    "old_caps": old_caps,
                    "new_caps": new_caps,
                    "notes": ";".join(notes),
                }
            )
        except Exception as e:
            errors += 1
            rows.append(
                {
                    "path": str(p),
                    "paper": _paper_id(p),
                    "status": "error",
                    "used_caps_source": "",
                    "old_caps": "",
                    "new_caps": "",
                    "notes": repr(e),
                }
            )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "paper",
                "status",
                "used_caps_source",
                "old_caps",
                "new_caps",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Files: {len(paths)}")
    print(f"Changed: {changed}")
    print(f"Quarantined: {quarantined}")
    print(f"Unknown: {unknown}")
    print(f"Errors: {errors}")
    print(f"Report: {report_path}")
    if args.apply:
        print(f"Backups: {backup_root}")
        print(f"Quarantine: {quarantine_root}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
