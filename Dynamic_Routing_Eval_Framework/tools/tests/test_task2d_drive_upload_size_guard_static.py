#!/usr/bin/env python3
"""
Audit Target D regression test (static):
Ensure GoogleDriveBackupManager upload logic only overwrites when the local file
is larger than the existing Drive file, and skips when the remote file is the same
size or larger.
"""

from __future__ import annotations

from pathlib import Path


def _framework_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    framework = _framework_root()
    src = framework / "daqr" / "config" / "gd_backup_manager.py"
    text = src.read_text(encoding="utf-8")

    required_markers = [
        'fields="files(id,name,size)"',
        'remote_size',
        'local_size',
        'remote size',
        'remote_size >= local_size',
        'return True',
    ]
    for marker in required_markers:
        assert marker in text, f"missing marker in Drive upload guard logic: {marker}"

    print("PASS: Task 2D static (Drive upload size guard present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
