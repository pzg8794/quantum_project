#!/usr/bin/env python3
"""
Backward-compatible wrapper.

The canonical tool lives at:
  tools/state/aggregate_state_dirs.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    target = Path(__file__).resolve().parent / "state" / "aggregate_state_dirs.py"
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

