import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.config.local_backup_manager import LocalBackupManager, migrate_files_by_pattern


class TestLocalBackupManagerPatternDriveOps(unittest.TestCase):
    def _make_manager(self, config_dir: Path, date_str: str):
        manager = LocalBackupManager.__new__(LocalBackupManager)
        manager.dir = config_dir
        manager.date_str = date_str
        manager.remote_available = True
        manager.drive = object()
        manager.drive_folder_id = "drive-id"
        return manager

    def test_check_drive_files_by_pattern_reports_present_and_missing(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            date_str = "day_20990101"
            for component in ["framework_state", "model_state"]:
                day_dir = config_dir / component / date_str
                day_dir.mkdir(parents=True, exist_ok=True)

            (config_dir / "framework_state" / date_str / "Runner_paper12.pkl").write_text("a")
            (config_dir / "framework_state" / date_str / "Runner_paper8.pkl").write_text("b")
            (config_dir / "model_state" / date_str / "Model_paper12.pkl").write_text("c")

            manager = self._make_manager(config_dir, date_str)

            remote_map = {
                "framework_state": {"Runner_paper12.pkl"},
                "model_state": set(),
            }
            manager._list_remote_state_names = lambda component, date_str=None: remote_map[component]

            summary = manager.check_drive_files_by_pattern(r"paper12")

            self.assertEqual(summary["framework_state"]["remote_present"], ["Runner_paper12.pkl"])
            self.assertEqual(summary["framework_state"]["remote_missing"], [])
            self.assertEqual(summary["model_state"]["remote_present"], [])
            self.assertEqual(summary["model_state"]["remote_missing"], ["Model_paper12.pkl"])

    def test_check_drive_files_by_pattern_scans_all_dates_when_date_not_provided(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            for component in ["framework_state", "model_state"]:
                for date_str in ["day_20990101", "day_20990102"]:
                    (config_dir / component / date_str).mkdir(parents=True, exist_ok=True)

            (config_dir / "framework_state" / "day_20990101" / "Runner_paper12.pkl").write_text("a")
            (config_dir / "framework_state" / "day_20990102" / "Runner2_paper12.pkl").write_text("b")

            manager = self._make_manager(config_dir, "day_20990102")
            remote_map = {
                ("framework_state", "day_20990101"): {"Runner_paper12.pkl"},
                ("framework_state", "day_20990102"): set(),
                ("model_state", "day_20990101"): set(),
                ("model_state", "day_20990102"): set(),
            }
            manager._list_remote_state_names = lambda component, date_str=None: remote_map[(component, date_str)]

            summary = manager.check_drive_files_by_pattern(r"paper12", components="framework_state")

            self.assertEqual(
                summary["framework_state"]["local_matches"],
                ["Runner_paper12.pkl", "Runner2_paper12.pkl"],
            )
            self.assertEqual(summary["framework_state"]["remote_present"], ["Runner_paper12.pkl"])
            self.assertEqual(summary["framework_state"]["remote_missing"], ["Runner2_paper12.pkl"])
            self.assertIn("day_20990101", summary["framework_state"]["by_date"])
            self.assertIn("day_20990102", summary["framework_state"]["by_date"])

    def test_upload_files_by_pattern_uploads_and_verifies_both_components(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            date_str = "day_20990101"
            for component in ["framework_state", "model_state"]:
                day_dir = config_dir / component / date_str
                day_dir.mkdir(parents=True, exist_ok=True)

            fw = config_dir / "framework_state" / date_str / "Runner_paper12.pkl"
            model = config_dir / "model_state" / date_str / "Oracle_paper12.pkl"
            other = config_dir / "model_state" / date_str / "Oracle_paper8.pkl"
            fw.write_text("fw")
            model.write_text("model")
            other.write_text("other")

            manager = self._make_manager(config_dir, date_str)

            uploaded_calls = []
            remote_names = {"framework_state": set(), "model_state": set()}

            def fake_upload(component, date_str, local_path, filename, parent_dir="quantum_data_lake"):
                uploaded_calls.append((component, filename))
                remote_names[component].add(filename)
                return True

            manager._upload_file_to_drive = fake_upload
            manager._list_remote_state_names = lambda component, date_str=None: set(remote_names[component])

            summary = manager.upload_files_by_pattern(r"paper12")

            self.assertEqual(
                uploaded_calls,
                [
                    ("framework_state", "Runner_paper12.pkl"),
                    ("model_state", "Oracle_paper12.pkl"),
                ],
            )
            self.assertEqual(summary["framework_state"]["verified_remote"], ["Runner_paper12.pkl"])
            self.assertEqual(summary["model_state"]["verified_remote"], ["Oracle_paper12.pkl"])
            self.assertEqual(summary["framework_state"]["failed"], [])
            self.assertEqual(summary["model_state"]["failed"], [])
            self.assertEqual(summary["model_state"]["matched"], ["Oracle_paper12.pkl"])

    def test_upload_files_by_pattern_reports_status(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            date_str = "day_20990101"
            (config_dir / "model_state" / date_str).mkdir(parents=True, exist_ok=True)
            model = config_dir / "model_state" / date_str / "Oracle_paper12.pkl"
            model.write_text("model")

            manager = self._make_manager(config_dir, date_str)
            remote_names = {("model_state", date_str): set()}

            def fake_upload(component, date_str, local_path, filename, parent_dir="quantum_data_lake"):
                remote_names[(component, date_str)].add(filename)
                return True

            manager._upload_file_to_drive = fake_upload
            manager._list_remote_state_names = lambda component, date_str=None: set(remote_names[(component, date_str)])

            messages = []
            manager.upload_files_by_pattern(
                r"paper12",
                components="model_state",
                status_callback=messages.append,
                progress_every=1,
            )

            self.assertTrue(any(msg.startswith("START model_state") for msg in messages))
            self.assertTrue(any(msg.startswith("PROGRESS model_state") for msg in messages))
            self.assertTrue(any(msg.startswith("DONE model_state") for msg in messages))

    def test_upload_files_by_pattern_scans_all_dates_when_date_not_provided(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            for date_str in ["day_20990101", "day_20990102"]:
                (config_dir / "model_state" / date_str).mkdir(parents=True, exist_ok=True)

            first = config_dir / "model_state" / "day_20990101" / "Oracle_paper12.pkl"
            second = config_dir / "model_state" / "day_20990102" / "Oracle2_paper12.pkl"
            first.write_text("a")
            second.write_text("b")

            manager = self._make_manager(config_dir, "day_20990102")
            uploaded_calls = []
            remote_names = {
                ("model_state", "day_20990101"): set(),
                ("model_state", "day_20990102"): set(),
            }

            def fake_upload(component, date_str, local_path, filename, parent_dir="quantum_data_lake"):
                uploaded_calls.append((component, date_str, filename))
                remote_names[(component, date_str)].add(filename)
                return True

            manager._upload_file_to_drive = fake_upload
            manager._list_remote_state_names = lambda component, date_str=None: set(remote_names[(component, date_str)])

            summary = manager.upload_files_by_pattern(r"paper12", components="model_state")

            self.assertEqual(
                uploaded_calls,
                [
                    ("model_state", "day_20990101", "Oracle_paper12.pkl"),
                    ("model_state", "day_20990102", "Oracle2_paper12.pkl"),
                ],
            )
            self.assertEqual(
                summary["model_state"]["verified_remote"],
                ["Oracle_paper12.pkl", "Oracle2_paper12.pkl"],
            )
            self.assertEqual(sorted(summary["model_state"]["by_date"].keys()), ["day_20990101", "day_20990102"])

    def test_standalone_migrate_files_by_pattern_runs_in_parallel_and_deletes_verified_local(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            date_str = "day_20990101"
            fw_day = config_dir / "framework_state" / date_str
            model_day = config_dir / "model_state" / date_str
            fw_day.mkdir(parents=True, exist_ok=True)
            model_day.mkdir(parents=True, exist_ok=True)
            (fw_day / "Runner_paper12.pkl").write_text("fw")
            (model_day / "Oracle_paper12.pkl").write_text("model")

            class _FakeManager:
                def upload_files_by_pattern(self, pattern, components=None, date_str=None, status_callback=None, progress_every=25):
                    component = components[0]
                    name = "Runner_paper12.pkl" if component == "framework_state" else "Oracle_paper12.pkl"
                    return {
                        component: {
                            "date_str": date_str,
                            "pattern": str(pattern),
                            "matched": [name],
                            "uploaded": [name],
                            "failed": [],
                            "verified_remote": [name],
                            "missing_after_upload": [],
                            "by_date": {
                                "day_20990101": {
                                    "matched": [name],
                                    "uploaded": [name],
                                    "failed": [],
                                    "verified_remote": [name],
                                    "missing_after_upload": [],
                                }
                            },
                        }
                    }

            with patch(
                "daqr.config.local_backup_manager.create_pattern_drive_manager",
                return_value=_FakeManager(),
            ):
                summary = migrate_files_by_pattern(
                    date_str=date_str,
                    config_dir=config_dir,
                    pattern=r"paper12",
                    delete_local=True,
                    parallel=True,
                )

            self.assertEqual(summary["framework_state"]["verified_remote"], ["Runner_paper12.pkl"])
            self.assertEqual(summary["model_state"]["verified_remote"], ["Oracle_paper12.pkl"])
            self.assertEqual(summary["framework_state"]["deleted_local"], ["Runner_paper12.pkl"])
            self.assertEqual(summary["model_state"]["deleted_local"], ["Oracle_paper12.pkl"])
            self.assertFalse((fw_day / "Runner_paper12.pkl").exists())
            self.assertFalse((model_day / "Oracle_paper12.pkl").exists())

    def test_standalone_migrate_files_by_pattern_deletes_verified_files_across_dates(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            first_day = config_dir / "model_state" / "day_20990101"
            second_day = config_dir / "model_state" / "day_20990102"
            first_day.mkdir(parents=True, exist_ok=True)
            second_day.mkdir(parents=True, exist_ok=True)
            (first_day / "Oracle_paper12.pkl").write_text("a")
            (second_day / "Oracle2_paper12.pkl").write_text("b")

            class _FakeManager:
                def upload_files_by_pattern(self, pattern, components=None, date_str=None, status_callback=None, progress_every=25):
                    return {
                        "model_state": {
                            "date_str": date_str,
                            "pattern": str(pattern),
                            "matched": ["Oracle_paper12.pkl", "Oracle2_paper12.pkl"],
                            "uploaded": ["Oracle_paper12.pkl", "Oracle2_paper12.pkl"],
                            "failed": [],
                            "verified_remote": ["Oracle_paper12.pkl", "Oracle2_paper12.pkl"],
                            "missing_after_upload": [],
                            "by_date": {
                                "day_20990101": {
                                    "matched": ["Oracle_paper12.pkl"],
                                    "uploaded": ["Oracle_paper12.pkl"],
                                    "failed": [],
                                    "verified_remote": ["Oracle_paper12.pkl"],
                                    "missing_after_upload": [],
                                },
                                "day_20990102": {
                                    "matched": ["Oracle2_paper12.pkl"],
                                    "uploaded": ["Oracle2_paper12.pkl"],
                                    "failed": [],
                                    "verified_remote": ["Oracle2_paper12.pkl"],
                                    "missing_after_upload": [],
                                },
                            },
                        }
                    }

            with patch(
                "daqr.config.local_backup_manager.create_pattern_drive_manager",
                return_value=_FakeManager(),
            ):
                summary = migrate_files_by_pattern(
                    date_str=None,
                    config_dir=config_dir,
                    pattern=r"paper12",
                    components="model_state",
                    delete_local=True,
                    parallel=False,
                )

            self.assertEqual(
                sorted(summary["model_state"]["deleted_local"]),
                ["Oracle2_paper12.pkl", "Oracle_paper12.pkl"],
            )
            self.assertFalse((first_day / "Oracle_paper12.pkl").exists())
            self.assertFalse((second_day / "Oracle2_paper12.pkl").exists())

    def test_standalone_migrate_files_by_pattern_reports_summary_status(self):
        with tempfile.TemporaryDirectory() as td:
            config_dir = Path(td)
            day = config_dir / "model_state" / "day_20990101"
            day.mkdir(parents=True, exist_ok=True)
            (day / "Oracle_paper12.pkl").write_text("a")

            class _FakeManager:
                def upload_files_by_pattern(self, pattern, components=None, date_str=None, status_callback=None, progress_every=25):
                    if status_callback is not None:
                        status_callback("START model_state day_20990101 matched=1")
                        status_callback("PROGRESS model_state day_20990101 1/1 uploaded=1 failed=0")
                        status_callback("DONE model_state day_20990101 verified_remote=1 missing_after_upload=0 failed=0")
                    return {
                        "model_state": {
                            "date_str": date_str,
                            "pattern": str(pattern),
                            "matched": ["Oracle_paper12.pkl"],
                            "uploaded": ["Oracle_paper12.pkl"],
                            "failed": [],
                            "verified_remote": ["Oracle_paper12.pkl"],
                            "missing_after_upload": [],
                            "by_date": {
                                "day_20990101": {
                                    "matched": ["Oracle_paper12.pkl"],
                                    "uploaded": ["Oracle_paper12.pkl"],
                                    "failed": [],
                                    "verified_remote": ["Oracle_paper12.pkl"],
                                    "missing_after_upload": [],
                                }
                            },
                        }
                    }

            messages = []
            with patch(
                "daqr.config.local_backup_manager.create_pattern_drive_manager",
                return_value=_FakeManager(),
            ):
                migrate_files_by_pattern(
                    date_str=None,
                    config_dir=config_dir,
                    pattern=r"paper12",
                    components="model_state",
                    delete_local=True,
                    parallel=False,
                    status_callback=messages.append,
                )

            self.assertTrue(any(msg.startswith("START model_state") for msg in messages))
            self.assertTrue(any(msg.startswith("DELETE model_state") for msg in messages))
            self.assertTrue(any(msg.startswith("SUMMARY model_state") for msg in messages))


if __name__ == "__main__":
    unittest.main()
