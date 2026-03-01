#!/usr/bin/env python3
"""
Task 2 regression test: AllocatorRunner is wired to run state aggregation by
default, with a toggle to disable.

This test is intentionally dependency-free (no torch/numpy/etc). It performs a
static check against the AllocatorRunner source to verify:
  - the toggle env var is referenced (`DAQR_AGGREGATE_STATE`),
  - the aggregation helper exists (`_aggregate_state_dirs`),
  - aggregation is invoked at the start of `run()`.
"""

from __future__ import annotations

from pathlib import Path


def _framework_root() -> Path:
    # .../Dynamic_Routing_Eval_Framework/tools/tests/this_file.py
    return Path(__file__).resolve().parents[2]


def main() -> int:
    framework = _framework_root()
    src = framework / "daqr" / "evaluation" / "allocator_runner.py"
    text = src.read_text(encoding="utf-8")

    assert "DAQR_AGGREGATE_STATE" in text, "toggle env var not present"
    assert "def _aggregate_state_dirs" in text, "_aggregate_state_dirs helper missing"
    assert "def _state_aggregation_enabled" in text, "_state_aggregation_enabled helper missing"

    # Ensure aggregation is invoked near the start of run()
    run_idx = text.find("def run(")
    assert run_idx != -1, "run() not found"
    call_idx = text.find("self._aggregate_state_dirs()", run_idx)
    assert call_idx != -1, "aggregation call missing inside run()"

    print("PASS: Task 2 (AllocatorRunner aggregation hook + toggle)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
