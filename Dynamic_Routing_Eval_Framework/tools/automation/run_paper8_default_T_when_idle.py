#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def _latest_mtime_seconds(root: Path, glob_pattern: str) -> float | None:
    latest = None
    for path in root.glob(glob_pattern):
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            continue
        if latest is None or mtime > latest:
            latest = mtime
    return latest


def _has_default_t_states(framework_state_root: Path) -> bool:
    # Expected filename suffix from MultiRunEvaluator.save_obj when suffix="paper8":
    #   ..._S{scale}T_paper8.pkl   (NOT Tb)
    pattern = re.compile(r"^MultiRunEvaluator_.*-Default_.*_S[0-9_]+T_paper8\.pkl$")
    for day_dir in sorted(framework_state_root.glob("day_*")):
        if not day_dir.is_dir():
            continue
        for pkl in day_dir.glob("MultiRunEvaluator_*Default*paper8.pkl"):
            name = pkl.name
            if "Tb_paper8.pkl" in name:
                continue
            if pattern.match(name):
                return True
    return False


def _run_notebook(notebook_path: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"{notebook_path.stem}__out__{ts}.ipynb"

    cmd = [
        sys.executable,
        "-m",
        "jupyter",
        "nbconvert",
        "--execute",
        "--to",
        "notebook",
        "--output",
        str(out_path),
        str(notebook_path),
    ]
    print(f"[automation] executing: {' '.join(cmd)}")
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Runs Paper8 Default-only T notebook once the framework is idle."
    )
    parser.add_argument(
        "--idle-minutes",
        type=int,
        default=20,
        help="Consider the framework busy if any framework_state .pkl changed in the last N minutes.",
    )
    parser.add_argument(
        "--notebook",
        type=str,
        default="Dynamic_Routing_Eval_Framework/notebooks/H-MABs_Eval-Testbed-Paper8-DefaultOnly_T.ipynb",
        help="Notebook to execute when idle.",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="Dynamic_Routing_Eval_Framework/notebooks/_autogen_outputs",
        help="Directory for executed notebook outputs.",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    framework_state_root = (
        repo_root
        / "Dynamic_Routing_Eval_Framework"
        / "daqr"
        / "config"
        / "framework_state"
    )

    latest_mtime = _latest_mtime_seconds(framework_state_root, "day_*/*.pkl")
    if latest_mtime is not None:
        age_seconds = time.time() - latest_mtime
        if age_seconds < (args.idle_minutes * 60):
            age_min = age_seconds / 60.0
            print(
                f"[automation] busy: latest framework_state write {age_min:.1f} min ago (<{args.idle_minutes}m); skipping"
            )
            return 0

    if _has_default_t_states(framework_state_root):
        print("[automation] Default T paper8 state already exists; nothing to do")
        return 0

    notebook_path = (repo_root / args.notebook).resolve()
    if not notebook_path.exists():
        print(f"[automation] notebook missing: {notebook_path}")
        return 2

    out_dir = (repo_root / args.out_dir).resolve()
    rc = _run_notebook(notebook_path, out_dir)
    if rc == 0:
        print("[automation] notebook executed successfully")
    else:
        print(f"[automation] notebook execution failed (rc={rc})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

