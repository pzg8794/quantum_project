#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.local_backup_manager import (
    create_pattern_drive_manager,
    migrate_files_by_pattern,
)


def _print_status(message: str) -> None:
    print(message, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Drive uploads/checks by filename or testbed pattern.")
    parser.add_argument("--pattern", required=True, help="Regex pattern to match filenames/testbeds.")
    parser.add_argument(
        "--components",
        nargs="+",
        choices=["framework_state", "model_state"],
        default=["framework_state", "model_state"],
        help="Components to operate on.",
    )
    parser.add_argument(
        "--date",
        dest="date_str",
        default=None,
        help="Optional day folder like day_20260321. Omit to scan all day_* folders.",
    )
    parser.add_argument(
        "--config-dir",
        default=str(PROJECT_ROOT / "daqr" / "config"),
        help="Path to daqr/config.",
    )
    parser.add_argument(
        "--mode",
        choices=["check", "migrate"],
        default="migrate",
        help="Check remote status only, or upload and optionally delete local files.",
    )
    parser.add_argument(
        "--delete-local",
        action="store_true",
        help="Delete verified local files after migration.",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run components in parallel.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of per-file upload workers per component. Keep modest for Drive API stability.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=25,
        help="Emit progress after this many files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final summary as JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_dir = Path(args.config_dir)

    if args.mode == "check":
        mgr = create_pattern_drive_manager(args.date_str, config_dir, verbose=False)
        summary = mgr.check_drive_files_by_pattern(
            args.pattern,
            components=args.components,
            date_str=args.date_str,
        )
    else:
        summary = migrate_files_by_pattern(
            date_str=args.date_str,
            config_dir=config_dir,
            pattern=args.pattern,
            components=args.components,
            delete_local=args.delete_local,
            parallel=args.parallel,
            verbose=False,
            status_callback=_print_status,
            progress_every=args.progress_every,
            workers=args.workers,
        )

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        compact = {}
        for component, data in summary.items():
            compact[component] = {
                "matched": len(data.get("matched", data.get("local_matches", []))),
                "verified_remote": len(data.get("verified_remote", [])),
                "remote_missing": len(data.get("remote_missing", data.get("missing_after_upload", []))),
                "failed": len(data.get("failed", [])),
                "deleted_local": len(data.get("deleted_local", [])),
            }
        print(json.dumps(compact, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
