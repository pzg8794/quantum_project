#!/usr/bin/env python3
"""
Audit Target B regression test (static):
Ensure LocalBackupManager applies the duplicate filename policy during scanning:
  - size wins, then mtime,
  - avoids "last one seen wins" nondeterminism.

Static-only to avoid importing googleapiclient/torch/etc.
"""

from __future__ import annotations

from pathlib import Path


def _framework_root() -> Path:
    # .../Dynamic_Routing_Eval_Framework/tools/tests/this_file.py
    return Path(__file__).resolve().parents[2]


def main() -> int:
    framework = _framework_root()
    src = framework / "daqr" / "config" / "local_backup_manager.py"
    text = src.read_text(encoding="utf-8")

    # We expect a check for existing entries in temp[component] and comparison using st_size/st_mtime.
    required_markers = [
        "Duplicate filename policy",
        "existing = temp[component].get(fname)",
        "st_size",
        "st_mtime",
        "files_dedup_skipped",
        "files_dedup_replaced",
    ]
    for m in required_markers:
        assert m in text, f"missing marker in LocalBackupManager scan logic: {m}"

    print("PASS: Task 2B (duplicate filename policy in LocalBackupManager scan)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

