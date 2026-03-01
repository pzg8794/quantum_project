#!/usr/bin/env python3
"""
Small, fast test for the state-dir aggregation tool.

This does NOT run any quantum experiments. It only verifies:
  - aggregation target selection via --target,
  - collision resolution: largest (then newest) wins,
  - day_* source dirs are removed when empty.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path


def _write_bytes(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * n)


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        cfg = root / "daqr" / "config"
        fw = cfg / "framework_state"
        ms = cfg / "model_state"

        # day_1 has small file; day_2 has larger file with same name -> day_2 wins.
        _write_bytes(fw / "day_20260101" / "A.pkl", 10)
        _write_bytes(fw / "day_20260102" / "A.pkl", 100)
        _write_bytes(ms / "day_20260101" / "B.pkl", 7)
        _write_bytes(ms / "day_20260102" / "C.pkl", 9)

        # registry file must exist for update step
        (cfg / "local_backup_registry.json").write_text(json.dumps({}), encoding="utf-8")

        tool = Path(__file__).resolve().parents[1] / "state" / "aggregate_state_dirs.py"
        target = "day_20990101"
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

        # Winner exists in target
        assert (fw / target / "A.pkl").exists(), "A.pkl missing in target"
        assert (fw / target / "A.pkl").stat().st_size == 100, "largest version did not win"
        assert not (fw / "day_20260101").exists(), "empty day dir should be removed"
        assert not (fw / "day_20260102").exists(), "empty day dir should be removed"

        # model_state target has both files
        assert (ms / target / "B.pkl").exists()
        assert (ms / target / "C.pkl").exists()

        # registry updated with absolute paths
        reg = json.loads((cfg / "local_backup_registry.json").read_text(encoding="utf-8"))
        assert "framework_state" in reg and "model_state" in reg
        assert "A.pkl" in reg["framework_state"]
        assert "B.pkl" in reg["model_state"]
        assert str((fw / target / "A.pkl").resolve()) == reg["framework_state"]["A.pkl"]

    print("PASS: state dir aggregation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

