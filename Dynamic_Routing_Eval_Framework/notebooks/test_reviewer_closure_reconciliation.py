"""Validator regression tests; no simulator execution or scientific rerun."""

import ast
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

from reviewer_closure_reconciliation import EXPECTED_INPUTS, reconcile


HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "H-MABs_MasterDataset_VerificationHub.ipynb"


class AuditStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        notebook = json.loads(NOTEBOOK.read_text())
        source = next("".join(cell["source"]) for cell in notebook["cells"]
                      if cell.get("id") == "8eee88aa")
        namespace = {"pd": pd}
        exec(compile(source, str(NOTEBOOK), "exec"), namespace)
        cls.functions = namespace

    def audit(self, expected, actual, solved=False):
        table = self.functions["annotate_audit"](pd.DataFrame({"Expected": [expected], "Actual": [actual]}))
        return self.functions["add_discrepancy_status"](table, solved=solved)

    def test_exact_match_passes(self):
        self.assertEqual(self.audit(10, 10).iloc[0]["Status"], "PASS")

    def test_solved_flag_cannot_hide_mismatch(self):
        row = self.audit(10, 12, solved=True).iloc[0]
        self.assertEqual(row["Status"], "MISMATCH")
        self.assertEqual(row["Historical disposition"], "Recorded solved")

    def test_small_difference_not_rounded_away(self):
        row = self.audit(1, 1.00001).iloc[0]
        self.assertEqual(row["Status"], "MISMATCH")
        self.assertGreater(row["|B - A|"], 0)

    def test_zero_denominator_is_undefined_for_nonzero_error(self):
        self.assertTrue(math.isnan(self.audit(0, 1).iloc[0]["|B - A| / Expected"]))
        self.assertEqual(self.audit(0, 0).iloc[0]["Status"], "PASS")

    def test_missing_or_nonfinite_evidence_cannot_pass(self):
        for actual in [None, float("nan"), float("inf"), "missing"]:
            with self.subTest(actual=actual):
                self.assertEqual(self.audit(1, actual, solved=True).iloc[0]["Status"], "UNAVAILABLE")

    def test_priority_without_calculation_cannot_pass(self):
        result = self.functions["add_discrepancy_status"](pd.DataFrame({"Priority": [None]}), solved=True)
        self.assertEqual(result.iloc[0]["Status"], "UNAVAILABLE")

    def test_manual_override_does_not_change_numeric_result(self):
        table = self.audit(10, 12)
        table["Item"] = "example"
        result = self.functions["apply_status_overrides"](table, ["Item"], solved_keys={("example",)})
        self.assertEqual(result.iloc[0]["Status"], "MISMATCH")
        self.assertEqual(result.iloc[0]["Historical disposition"], "Recorded solved")

    def test_all_notebook_code_parses(self):
        notebook = json.loads(NOTEBOOK.read_text())
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]), filename=f"cell-{index}")


class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(os.environ["GA_WORK_ROOT"])
        cls.paper = Path(os.environ["QFT_PAPER_ROOT"])
        cls.result = reconcile(cls.workspace, cls.paper)

    def test_real_sources_and_expected_scope(self):
        self.assertEqual(self.result["verdict"], "PASS_WITH_EXPLICIT_HOLDS")
        self.assertEqual(self.result["inputs_sha256"], EXPECTED_INPUTS)
        self.assertEqual(len(self.result["switching"]), 5)
        self.assertEqual(len(self.result["external"]), 32)
        self.assertAlmostEqual(self.result["baseline_mean"], 96.03743950688312, places=10)
        self.assertAlmostEqual(self.result["baseline_floor"], 92.78325983727036, places=10)
        self.assertTrue(self.result["unresolved"])

    def test_missing_evidence_fails(self):
        with tempfile.TemporaryDirectory(prefix="qft-validator-") as directory:
            with self.assertRaises(FileNotFoundError):
                reconcile(directory, self.paper)

    def test_altered_evidence_fails_hash_check(self):
        with tempfile.TemporaryDirectory(prefix="qft-validator-") as directory:
            relative = next(iter(EXPECTED_INPUTS))
            target = Path(directory) / relative
            target.parent.mkdir(parents=True)
            target.write_bytes((self.workspace / relative).read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Evidence hash mismatch"):
                reconcile(directory, self.paper)

    def test_bad_manuscript_is_not_green(self):
        with tempfile.TemporaryDirectory(prefix="qft-validator-") as directory:
            root = Path(directory)
            for relative in self.result["checked_manuscript_sha256"]:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.paper / relative, target)
            main = root / "ICNP_2026_venue_draft.tex"
            main.write_text(main.read_text().replace("model-specific feedback record", "obsolete feedback assertion")
                            + "\nPlaceholder % model-specific feedback record\n")
            result = reconcile(self.workspace, root)
            self.assertEqual(result["verdict"], "FAIL_MANUSCRIPT_CHECKS")
            self.assertFalse(result["manuscript_checks"]["feedback_interface"])
            command = [sys.executable, "-O", str(HERE / "reviewer_closure_reconciliation.py"),
                       "--workspace", str(self.workspace), "--paper", str(root)]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_wrong_plot_value_fails(self):
        with tempfile.TemporaryDirectory(prefix="qft-validator-") as directory:
            root = Path(directory)
            for relative in self.result["checked_manuscript_sha256"]:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.paper / relative, target)
            figure = root / "figures/icnp/rq3_switching_reconciled.tex"
            figure.write_text(figure.read_text().replace("99.8851", "96.0000"))
            self.assertFalse(reconcile(self.workspace, root)["manuscript_checks"]["switching_figure_values"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
