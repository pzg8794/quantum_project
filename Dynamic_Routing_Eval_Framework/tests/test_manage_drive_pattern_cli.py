import json
import runpy
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(
    "/Users/pitergarcia/DataScience/Semester4/GA-Work/hybrid_variable_framework/Dynamic_Routing_Eval_Framework/tools/state/manage_drive_pattern.py"
)


class TestManageDrivePatternCli(unittest.TestCase):
    def test_migrate_mode_uses_standalone_helper(self):
        with tempfile.TemporaryDirectory() as td:
            argv = [
                str(SCRIPT_PATH),
                "--pattern",
                "paper12",
                "--components",
                "model_state",
                "--config-dir",
                td,
                "--json",
            ]
            fake_summary = {
                "model_state": {
                    "matched": ["a.pkl"],
                    "verified_remote": ["a.pkl"],
                    "missing_after_upload": [],
                    "failed": [],
                    "deleted_local": ["a.pkl"],
                }
            }

            stdout = StringIO()
            with patch.object(sys, "argv", argv), \
                 patch("daqr.config.local_backup_manager.migrate_files_by_pattern", return_value=fake_summary) as migrate_mock, \
                 patch("sys.stdout", stdout):
                with self.assertRaises(SystemExit) as ctx:
                    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")

            self.assertEqual(ctx.exception.code, 0)
            migrate_mock.assert_called_once()
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["model_state"]["verified_remote"], ["a.pkl"])

    def test_check_mode_uses_manager_check_method(self):
        with tempfile.TemporaryDirectory() as td:
            argv = [
                str(SCRIPT_PATH),
                "--mode",
                "check",
                "--pattern",
                "paper12",
                "--components",
                "framework_state",
                "--config-dir",
                td,
                "--json",
            ]

            fake_summary = {
                "framework_state": {
                    "local_matches": ["b.pkl"],
                    "remote_present": ["b.pkl"],
                    "remote_missing": [],
                }
            }

            class _FakeManager:
                def check_drive_files_by_pattern(self, pattern, components=None, date_str=None):
                    return fake_summary

            stdout = StringIO()
            with patch.object(sys, "argv", argv), \
                 patch("daqr.config.local_backup_manager.create_pattern_drive_manager", return_value=_FakeManager()), \
                 patch("sys.stdout", stdout):
                with self.assertRaises(SystemExit) as ctx:
                    runpy.run_path(str(SCRIPT_PATH), run_name="__main__")

            self.assertEqual(ctx.exception.code, 0)
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["framework_state"]["remote_present"], ["b.pkl"])


if __name__ == "__main__":
    unittest.main()
