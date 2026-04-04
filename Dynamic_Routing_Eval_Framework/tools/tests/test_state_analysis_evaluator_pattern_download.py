#!/usr/bin/env python3
"""Unit tests for pattern-based evaluator state downloads in state_analysis.

These are deterministic tests that do NOT hit the real Drive API.

Run:
  python3 tools/tests/test_state_analysis_evaluator_pattern_download.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


DAQR_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(DAQR_ROOT))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _can_import_state_analysis() -> bool:
    try:
        global state_analysis
        import state_analysis as state_analysis_module

        state_analysis = state_analysis_module
        return True
    except Exception as exc:
        print(f"SKIP: state_analysis not importable: {exc}")
        return False


class _StubDriveManager:
    remote_available = True
    drive = object()

    def __init__(self, *, index: dict[str, dict], download_dir: Path):
        self._index = index
        self._download_dir = Path(download_dir)
        self.download_calls: list[tuple[str, str]] = []

    def ensure_drive_state_index(self, component: str, build_if_missing: bool = True):
        _assert(component == "framework_state", f"Unexpected component: {component}")
        return self._index

    def download_any_date(self, *, component: str, filename: str):
        self.download_calls.append((component, filename))
        _assert(component == "framework_state", f"Unexpected download component: {component}")

        local_path = self._download_dir / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"stub")
        return str(local_path)


def test_downloads_all_pattern_matches() -> None:
    os.environ["DAQR_STATE_ANALYSIS_ALLOW_DRIVE_DOWNLOADS"] = "1"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        framework_state_root = tmp_dir_path / "framework_state"
        framework_state_root.mkdir(parents=True, exist_ok=True)

        index = {
            "MultiRunEvaluator_1000-Default_All_All-1000_1000_1_S1T_paper8.pkl": {"drive_id": "id1", "day": "day_20260101"},
            "MultiRunEvaluator_1000-Default_All_All-1000_1000_1_S2T_paper8.pkl": {"drive_id": "id2", "day": "day_20260102"},
            "NotAnEvaluator_1000-Default.pkl": {"drive_id": "id3", "day": "day_20260103"},
            "MultiRunEvaluator_1000-Default_All_All-1000_1000_1_S1T_paper7.pkl": {"drive_id": "id4", "day": "day_20260104"},
        }

        mgr = _StubDriveManager(index=index, download_dir=framework_state_root)

        original_get_drive_manager = state_analysis._get_drive_manager
        try:
            state_analysis._get_drive_manager = lambda *_args, **_kwargs: mgr

            paths = state_analysis.download_evaluator_states_for_pattern(
                framework_state_root=framework_state_root,
                pattern=r"(?=.*paper8)(?=.*\.pkl)",
                verbose=False,
            )
        finally:
            state_analysis._get_drive_manager = original_get_drive_manager

        _assert(len(paths) == 2, f"Expected 2 downloads, got {len(paths)}")
        _assert(all(Path(p).exists() for p in paths), "Expected all returned paths to exist")

        called_filenames = [filename for _component, filename in mgr.download_calls]
        _assert(
            called_filenames == [
                "MultiRunEvaluator_1000-Default_All_All-1000_1000_1_S1T_paper8.pkl",
                "MultiRunEvaluator_1000-Default_All_All-1000_1000_1_S2T_paper8.pkl",
            ],
            f"download_any_date was not called for all matches: {called_filenames}",
        )


def test_raises_on_no_matches() -> None:
    os.environ["DAQR_STATE_ANALYSIS_ALLOW_DRIVE_DOWNLOADS"] = "1"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        framework_state_root = tmp_dir_path / "framework_state"
        framework_state_root.mkdir(parents=True, exist_ok=True)

        index = {
            "MultiRunEvaluator_1000-Default_All_All-1000_1000_1_S1T_paper7.pkl": {"drive_id": "id4", "day": "day_20260104"},
        }

        mgr = _StubDriveManager(index=index, download_dir=framework_state_root)

        original_get_drive_manager = state_analysis._get_drive_manager
        try:
            state_analysis._get_drive_manager = lambda *_args, **_kwargs: mgr

            try:
                state_analysis.download_evaluator_states_for_pattern(
                    framework_state_root=framework_state_root,
                    pattern=r"paper8",
                    verbose=False,
                )
            except RuntimeError as exc:
                _assert("No evaluator states matched" in str(exc), f"Unexpected error: {exc}")
            else:
                raise AssertionError("Expected RuntimeError for no matches")
        finally:
            state_analysis._get_drive_manager = original_get_drive_manager


def main() -> int:
    if not _can_import_state_analysis():
        return 0

    failed = 0
    tests = [
        test_downloads_all_pattern_matches,
        test_raises_on_no_matches,
    ]

    for test in tests:
        try:
            test()
            print(f"PASS | {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL | {test.__name__}: {exc}")

    print("-" * 60)
    if failed == 0:
        print("PASS: state-analysis pattern-download unit tests")
        return 0
    print(f"FAIL: {failed} state-analysis pattern-download unit test(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
