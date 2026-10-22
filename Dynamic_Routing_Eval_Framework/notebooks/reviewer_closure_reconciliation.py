"""Read-only reconciliation of saved historical evidence; never runs a model."""

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from statistics import mean

EXPECTED_INPUTS = {
    "paper_validation/snapshots/20260315_001835/agg_used__rq3d_default.csv": "cd0a95a0c3d56e3cffb3ca1fe3f00d2e411b01813aa91b0697baef63b0fe698b",
    "paper_validation/snapshots/20260315_001835/agg_used__rq3d_reported_eff.csv": "2415996928bb50807ae75ee0d2acb5e93dbe1ea6b4e85a9965da9904562a131f",
    "Validated_Logs/Master_Dataset_Hybrid.csv": "8a2838bfd969cf97c50a21bde92dadc0d58cb7cab0f520adb25870047c48658b",
    "Validated_Logs/native/Master_Dataset_paper2_4000_2000.csv": "b065fc0daff0be17ff296d78c01abc60f5263ebd506f7f266483cf6590de4cd5",
    "Validated_Logs/native/Master_Dataset_paper7_50_50.csv": "f0260e04d7def8760c8978c916f96368b916a98a251b2232956ee23689c5fe50",
    "Validated_Logs/native/Master_Dataset_paper12_1500_500.csv": "7ff376588bdd7c4e352f1d3397b19ed6c6498ec9a6764069a2b2d3d28a598173",
    "Validated_Logs/native/Master_Dataset_paper8_1000_1000.csv": "11cdf26fa5d14e9d3cebbdd751a21950c7f8cb7c5675a2ed67b0c4e9d6e782ad",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def reconcile(workspace, paper):
    workspace, paper = Path(workspace), Path(paper)
    inputs = {}

    def rows(relative):
        path = workspace / relative
        if not path.is_file():
            raise FileNotFoundError(f"Required existing evidence unavailable: {path}")
        inputs[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        require(inputs[relative] == EXPECTED_INPUTS[relative], f"Evidence hash mismatch: {relative}")
        with path.open(newline="") as stream:
            return list(csv.DictReader(stream))

    snapshot = "paper_validation/snapshots/20260315_001835/"
    baseline = {row["scenario"]: float(row["eff_pct"]) for row in
                rows(snapshot + "agg_used__rq3d_default.csv")}
    switches = rows(snapshot + "agg_used__rq3d_reported_eff.csv")
    switching = []
    for row in switches:
        scenario = row["Scenario"]
        selected = float(row["Actual Eff (%)"])
        switching.append({"scenario": scenario, "configuration": row["Reported config"],
                          "baseline": baseline[scenario], "selected": selected,
                          "gain_pp": selected - baseline[scenario]})
    require(len(switching) == 5, "Expected five threat comparisons")
    require(round(mean(baseline.values()), 1) == 96.0, "Three-run baseline mean mismatch")
    require(round(min(baseline.values()), 1) == 92.8, "Three-run baseline floor mismatch")
    adaptive = next(row for row in switching if row["scenario"] == "ADAPTIVE")
    require(adaptive["configuration"] == "ThompsonSampling + (T, s=1.0)", "Adaptive configuration mismatch")
    require(round(adaptive["gain_pp"], 1) == 2.9, "Adaptive gain mismatch")
    hybrid = rows("Validated_Logs/Master_Dataset_Hybrid.csv")
    adaptive_source = [row for row in hybrid if row["model"].upper() == "ICPURSUITNEURALUCB"
                       and float(row["runs"]) == 3 and float(row["frames"]) == 6000
                       and row["scenario"] == "ADAPTIVE" and row["allocator"] == "ThompsonSampling"
                       and row["cap_type"] == "T" and float(row["scale"]) == 1]
    require(len(adaptive_source) == 1, "Adaptive source row is not unique")
    require(abs(float(adaptive_source[0]["eff_pct"]) - adaptive["selected"]) < 0.0005, "Snapshot/master mismatch")
    external = []
    for name in ["paper2_4000_2000", "paper7_50_50", "paper12_1500_500", "paper8_1000_1000"]:
        data = rows(f"Validated_Logs/native/Master_Dataset_{name}.csv")
        oracle = [row for row in data if row["model"].upper() == "ORACLE"]
        for model in ["GNEURALUCB", "EXPNEURALUCB", "CPURSUITNEURALUCB", "ICPURSUITNEURALUCB"]:
            for scope in ["all_allocators", "Default_only"]:
                selected = [row for row in data if row["model"].upper() == model
                            and (scope == "all_allocators" or row["allocator"] == "Default")]
                comparator = [row for row in oracle if scope == "all_allocators" or row["allocator"] == "Default"]
                external.append({"testbed": name, "model": model, "scope": scope,
                                 "rows": len(selected),
                                 "mean_saved_eff_pct": mean(float(row["eff_pct"]) for row in selected),
                                 "ratio_of_mean_rewards_pct": 100 * mean(float(row["reward"]) for row in selected)
                                 / mean(float(row["reward"]) for row in comparator)})
    checks = {
        "feedback_interface": ("ICNP_2026_venue_draft.tex", "model-specific feedback record", "observes only the realized reward"),
        "rq_questions_only": ("ICNP_2026_venue_draft.tex", "independent route-availability disruption?", "Stochastic decoherence alone"),
        "rq3_switch_scope": ("ICNP_VENUE_PREP/RESULTS_VALIDATED_STAGING.tex", "switching analysis uses the Hybrid three-run slice", "Hybrid corpus 3/5-suite mean used for switching"),
        "external_aggregation": ("ICNP_VENUE_PREP/APPENDIX_CROSS_TESTBED_TABLES.tex", "averages of the saved per-configuration percentages", "model average reward divided by Oracle average reward"),
        "external_scope": ("ICNP_VENUE_PREP/APPENDIX_CROSS_TESTBED_TABLES.tex", "Default-allocator subset of the native", "standardized external-testbed corpus where available"),
        "policy_label": ("ICNP_VENUE_PREP/APPENDIX_CROSS_TESTBED_TABLES.tex", "Simple-UCB, not EXP3", "strongest EXP-family representative"),
    }
    manuscript_checks = {}
    manuscript_hashes = {}
    for name, (relative, required, forbidden) in checks.items():
        source = (paper / relative).read_text()
        manuscript_hashes[relative] = hashlib.sha256((paper / relative).read_bytes()).hexdigest()
        active = re.sub(r"(?<!\\)%[^\n]*", "", source)
        manuscript_checks[name] = required in active and forbidden not in active
    figure_path = "figures/icnp/rq3_switching_reconciled.tex"
    figure = (paper / figure_path).read_text()
    manuscript_hashes[figure_path] = hashlib.sha256((paper / figure_path).read_bytes()).hexdigest()
    coordinates = re.findall(r"coordinates\s*\{([^}]+)\}", figure)
    expected_order = ["NONE", "STOCHASTIC", "MARKOV", "ADAPTIVE", "ONLINEADAPTIVE"]
    selected_by_scenario = {row["scenario"]: row["selected"] for row in switching}
    figure_ok = len(coordinates) == 2
    if figure_ok:
        for group, expected in zip(coordinates, [baseline, selected_by_scenario]):
            points = re.findall(r"\(([\d.]+),([\d.]+)\)", group)
            figure_ok &= len(points) == 5 and all(
                int(float(position)) == index and abs(float(value) - expected[expected_order[index]]) <= 0.000051
                for index, (value, position) in enumerate(points)
            )
    manuscript_checks["switching_figure_values"] = bool(figure_ok)
    return {
        "verdict": "PASS_WITH_EXPLICIT_HOLDS" if all(manuscript_checks.values()) else "FAIL_MANUSCRIPT_CHECKS",
        "scope": "Existing historical evidence and manuscript reconciliation only; Q07 remains closed.",
        "inputs_sha256": inputs,
        "checked_manuscript_sha256": manuscript_hashes,
        "baseline_mean": mean(baseline.values()), "baseline_floor": min(baseline.values()),
        "switching": switching, "adaptive_source_file": adaptive_source[0]["source_file"],
        "external": external, "manuscript_checks": manuscript_checks,
        "unresolved": [
            "Historical source-to-run allocator cadence, attack settings, effective training/predictive overrides and some external contexts.",
            "Paper8 saved percentages average 67.84637%, whereas the manuscript prints 67.9%; the aggregation-order defect is resolved, but exact rounding/source-revision parity is not certified.",
            "Old snapshot/current native evidence contains small historical table differences; this reconciliation does not replace the entire validated corpus or approve wholesale numeric changes.",
            "8241 tests versus planned 552 configurations/5520 episodes/380 GPU-hours: executed unit/scope crosswalk unavailable.",
            "Historical bootstrap resampling unit and win/tie conventions must be tied to their individual outputs.",
            "Venue page count, human author fields, external integration review and Overleaf reconciliation remain separate release gates.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args()
    result = reconcile(arguments.workspace, arguments.paper)
    rendered = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(rendered)
    else:
        print(rendered)
    if result["verdict"].startswith("FAIL"):
        raise SystemExit(1)
