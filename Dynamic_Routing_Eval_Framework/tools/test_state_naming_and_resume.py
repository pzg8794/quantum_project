#!/usr/bin/env python3
"""
Backward-compatible wrapper.

The canonical test lives at:
  tools/tests/test_state_naming_and_resume.py
"""

from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    target = Path(__file__).resolve().parent / "tests" / "test_state_naming_and_resume.py"
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

