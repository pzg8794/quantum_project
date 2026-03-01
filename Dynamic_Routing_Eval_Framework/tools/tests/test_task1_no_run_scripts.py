#!/usr/bin/env python3
"""
Task 1 regression test: ensure the duplicate `run_scripts/` directory stays removed
and that primary docs don't reference it.

This is intentionally small and fast.
"""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # .../hybrid_variable_framework/Dynamic_Routing_Eval_Framework/tools/tests/this_file.py
    return Path(__file__).resolve().parents[3]


def main() -> int:
    repo = _repo_root()

    run_scripts_dir = repo / "run_scripts"
    assert not run_scripts_dir.exists(), f"run_scripts/ should not exist: {run_scripts_dir}"

    scripts_dir = repo / "scripts"
    assert scripts_dir.exists(), f"scripts/ missing: {scripts_dir}"
    assert (scripts_dir / "run_exp_test.sh").exists(), "scripts/run_exp_test.sh missing"

    for doc in [repo / "README.md", repo / "REPOSITORY_STRUCTURE.md"]:
        text = doc.read_text(encoding="utf-8")
        assert "run_scripts" not in text, f"{doc} still references run_scripts/"

    print("PASS: Task 1 (no run_scripts directory)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
