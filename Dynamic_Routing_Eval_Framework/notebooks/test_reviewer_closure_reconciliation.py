"""Validator regression tests; no simulator execution or scientific rerun."""

import ast
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from reviewer_closure_reconciliation import EXPECTED_INPUTS, PRIMARY_EXPORT_SHA256, audit_primary_exports, audit_recorded_run_headers, compare_original_export_rows, decode_recorded_contexts, reconcile, summarize_original_receipt


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


@unittest.skipUnless(os.environ.get("QFT_SHARED_IMPLEMENTATION"), "Set QFT_SHARED_IMPLEMENTATION for shared source-contract checks")
class PrimarySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(os.environ["GA_WORK_ROOT"])
        cls.shared = Path(os.environ["QFT_SHARED_IMPLEMENTATION"])
        cls.result = audit_primary_exports(cls.workspace, cls.shared)

    def test_export_units_and_winners(self):
        self.assertEqual((self.result["total_rows"], self.result["learned_rows"], self.result["oracle_rows"]),
                         (10240, 8241, 1999))
        self.assertEqual(self.result["unique_learner_labels"], 15)
        self.assertEqual(self.result["experiment_winner_checks"], 1999)
        self.assertEqual(self.result["experiment_winner_mismatches"], 0)
        self.assertEqual(self.result["experiment_exact_reward_ties"], 0)
        self.assertEqual(len(self.result["scenario_summary_disagreements"]), 8)
        self.assertTrue(all(row["suite"] == "Hybrid" for row in self.result["scenario_summary_disagreements"]))

    def test_modified_export_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="qft-source-negative-") as directory:
            target = Path(directory) / "Validated_Logs/Master_Dataset_Hybrid.csv"
            target.parent.mkdir(parents=True)
            target.write_bytes((self.workspace / "Validated_Logs/Master_Dataset_Hybrid.csv").read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "Evidence hash mismatch"):
                audit_primary_exports(directory, self.shared)

    def test_logged_rates_are_not_summary_labels(self):
        result = audit_recorded_run_headers(self.workspace)
        self.assertEqual(result["configured_rates_by_attack"]["Random"], ["0.0625"])
        self.assertEqual(result["configured_rates_by_attack"]["Markov"], ["0.25"])
        self.assertGreater(result["fixed_budget_calls"], 0)

    def test_inconsistent_winner_cannot_receive_pass(self):
        with tempfile.TemporaryDirectory(prefix="qft-winner-negative-") as directory:
            root = Path(directory) / "Validated_Logs"
            root.mkdir()
            for suite in PRIMARY_EXPORT_SHA256:
                shutil.copy2(self.workspace / f"Validated_Logs/Master_Dataset_{suite}.csv", root)
            target = root / "Master_Dataset_Hybrid.csv"
            with target.open(newline="") as stream:
                reader = csv.DictReader(stream)
                fields, rows = reader.fieldnames, list(reader)
            rows[0]["winner"] = "INVALID_WINNER"
            with target.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            with patch.dict(PRIMARY_EXPORT_SHA256, {"Hybrid": hashlib.sha256(target.read_bytes()).hexdigest()}):
                with self.assertRaisesRegex(ValueError, "winner disagrees"):
                    audit_primary_exports(directory, self.shared)


class OriginalComparisonTests(unittest.TestCase):
    def setUp(self):
        self.saved = [{"source_file": "state.pkl", "scenario": "NONE", "experiment": "1", "model": "GNEURALUCB",
                       "reward": "0.125", "eff_pct": "", "winner": "GNeuralUCB"}]
        self.original = [{"source_file": "state.pkl", "scenario": "NONE", "experiment": 1, "model": "GNEURALUCB",
                          "reward": 0.125, "eff_pct": None, "winner": "GNeuralUCB"}]

    def test_original_values_reproduce_export(self):
        result = compare_original_export_rows(self.saved, self.original)
        self.assertEqual(result["matched_all_fields_rows"], 1)
        self.assertEqual(result["differences"], [])
        self.assertEqual(sum(result["field_checks"].values()), 6)

    def test_changed_original_value_does_not_pass(self):
        self.original[0]["reward"] = 0.25
        result = compare_original_export_rows(self.saved, self.original)
        self.assertEqual(result["matched_all_fields_rows"], 0)
        self.assertEqual(result["differences"][0]["field"], "reward")

    def test_missing_original_row_is_not_skipped(self):
        result = compare_original_export_rows(self.saved, [])
        self.assertEqual(result["matched_all_fields_rows"], 0)
        self.assertEqual(result["differences"][0]["issue"], "missing_original_row")

    def test_absent_original_column_is_not_a_present_null(self):
        del self.original[0]["eff_pct"]
        result = compare_original_export_rows(self.saved, self.original)
        self.assertEqual(result["matched_all_fields_rows"], 0)
        self.assertEqual(result["differences"][0]["issue"], "missing_original_field")

    def test_duplicate_original_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate original"):
            compare_original_export_rows(self.saved, self.original * 2)

    def test_duplicate_export_row_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate exported"):
            compare_original_export_rows(self.saved * 2, self.original)

    def test_recorded_context_string_is_decoded_without_execution(self):
        self.assertIsNone(decode_recorded_contexts("None"))
        self.assertEqual(decode_recorded_contexts("[array([[3., 0.5, 0.9], [3., 0.5, 0.9]])]"),
                         [[[3.0, 0.5, 0.9], [3.0, 0.5, 0.9]]])

    def test_invalid_context_expression_or_shape_is_rejected(self):
        for value in ("'abc'", "[['abc']]", "[array(['x'])]", "[array([[True]])]", "__import__('os').getcwd()"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode_recorded_contexts(value)


@unittest.skipUnless(os.environ.get("QFT_ORIGINAL_RECEIPT"), "Set QFT_ORIGINAL_RECEIPT for original-state verification")
class OriginalReceiptTests(unittest.TestCase):
    def test_original_receipt_coverage(self):
        result = summarize_original_receipt(os.environ["GA_WORK_ROOT"], os.environ["QFT_ORIGINAL_RECEIPT"])
        self.assertEqual(result["source_filenames"], 101)
        self.assertEqual(result["export_rows"], 10240)
        self.assertEqual(result["field_comparisons"], 296960)

    def test_missing_and_mutated_originals_cannot_pass(self):
        receipt = json.loads(Path(os.environ["QFT_ORIGINAL_RECEIPT"]).read_text())
        for mutation in ("remove", "checksum", "value", "scope", "errors", "fields", "string_boolean", "empty_digest", "zero_recovered", "no_errors", "count_type", "negative_wins", "stored_winner", "null_differences", "object_differences", "string_differences"):
            altered = json.loads(json.dumps(receipt))
            name = next(iter(altered["sources"]))
            entry = altered["sources"][name]
            comparison = next(iter(entry["export_comparisons"].values()))
            if mutation == "remove":
                del altered["sources"][name]
            elif mutation == "checksum":
                entry["sha256"] = "0" * 64
            elif mutation == "value":
                comparison["differences"] = [{"field": "reward", "export": 1, "original": 0}]
            elif mutation == "scope":
                comparison["matched_all_fields_rows"] -= 1
            elif mutation == "fields":
                comparison["field_checks"].pop("reward")
            elif mutation == "string_boolean":
                entry["strict_original_load"] = "false"
            elif mutation == "empty_digest":
                entry["sha256"] = None
                entry["metadata"].pop("sha256Checksum")
            elif mutation == "zero_recovered":
                comparison["recovered_rows"] = 0
            elif mutation == "no_errors":
                altered.pop("errors")
            elif mutation == "count_type":
                comparison["export_rows"] = float(comparison["export_rows"])
            elif mutation.endswith("_differences"):
                comparison["differences"] = {"null_differences": None, "object_differences": {}, "string_differences": ""}[mutation]
            elif mutation in ("negative_wins", "stored_winner"):
                original = next(item for source_name, item in altered["sources"].items()
                                if source_name.startswith("MultiRunEvaluator_100-Dynamic_Adversarial"))
                rule = original["scenario_summary_rules"]["markov"]
                if mutation == "negative_wins":
                    rule["experiment_winner_counts"] = {key: -1 for key in rule["experiment_winner_counts"]}
                else:
                    rule["stored_overall_winner"] = "CONTRADICTORY"
            else:
                altered["errors"] = {name: "download failed"}
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix="qft-original-negative-") as directory:
                path = Path(directory) / "receipt.json"
                path.write_text(json.dumps(altered))
                with self.assertRaises(ValueError):
                    summarize_original_receipt(os.environ["GA_WORK_ROOT"], path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
