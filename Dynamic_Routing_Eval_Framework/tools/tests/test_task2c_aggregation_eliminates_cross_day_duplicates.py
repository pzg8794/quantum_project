#!/usr/bin/env python3
"""
Task 2C (sanity): when aggregation runs, cross-day duplicate filenames should
disappear, reducing the need for LocalBackupManager's scan-time dedupe.

This is a small, dependency-free filesystem test (no experiments).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path


def _write_bytes(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * n)


def _all_day_files(root: Path) -> list[Path]:
    out: list[Path] = []
    if not root.exists():
        return out
    for day_dir in root.iterdir():
        if not day_dir.is_dir() or not day_dir.name.startswith("day_"):
            continue
        out.extend([p for p in day_dir.iterdir() if p.is_file()])
    return out


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = root / "daqr" / "config"
        fw = cfg / "framework_state"
        ms = cfg / "model_state"

        # Create duplicates across day dirs.
        _write_bytes(fw / "day_20260101" / "dup.pkl", 10)
        _write_bytes(fw / "day_20260102" / "dup.pkl", 100)  # winner
        _write_bytes(fw / "day_20260102" / "unique.pkl", 5)

        _write_bytes(ms / "day_20260101" / "dup2.pkl", 3)
        _write_bytes(ms / "day_20260102" / "dup2.pkl", 9)  # winner

        # registry file must exist for update step
        (cfg / "local_backup_registry.json").write_text(json.dumps({}), encoding="utf-8")

        tool = (
            Path(__file__).resolve().parents[1] / "state" / "aggregate_state_dirs.py"
        )  # tools/state/aggregate_state_dirs.py
        target = "day_20990102"
        cmd = [
            "python3",
            str(tool),
            "--config-dir",
            str(cfg),
            "--framework-state-root",
            str(fw),
            "--model-state-root",
            str(ms),
            "--target",
            target,
        ]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        subprocess.check_call(cmd, env=env)

        # After aggregation: across all day_* dirs, each filename appears at most once.
        fw_names = [p.name for p in _all_day_files(fw)]
        ms_names = [p.name for p in _all_day_files(ms)]
        fw_counts = Counter(fw_names)
        ms_counts = Counter(ms_names)
        assert fw_counts["dup.pkl"] == 1, f"dup.pkl still duplicated: {fw_counts}"
        assert ms_counts["dup2.pkl"] == 1, f"dup2.pkl still duplicated: {ms_counts}"
        assert max(fw_counts.values(), default=0) == 1, f"still have duplicates: {fw_counts}"
        assert max(ms_counts.values(), default=0) == 1, f"still have duplicates: {ms_counts}"

        # Winners present in target
        assert (fw / target / "dup.pkl").stat().st_size == 100
        assert (ms / target / "dup2.pkl").stat().st_size == 9

    print("PASS: Task 2C (aggregation eliminates cross-day duplicates)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

