"""Read-only reconciliation of saved historical evidence; never runs a model."""

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
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

PRIMARY_EXPORT_SHA256 = {
    "Hybrid": EXPECTED_INPUTS["Validated_Logs/Master_Dataset_Hybrid.csv"],
    "CMABs": "26dbfbc3ab28ea53a6d35ebfabb3ccf557529ec95b0fedf3d930649f02d2e9b9",
    "iCMABs": "b879ddd6e98a4522b3acb6a6ab81dc0fb891184eb7190927ab4f47eb04a354df",
    "EXP3": "10afed56ddf8f5b095222b75cf38ebe37adf13016997858868a52f002dc1bdfa",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_primary_exports(workspace, shared_implementation):
    shared = Path(shared_implementation).resolve() / "Evaluation_Framework"
    require(shared.is_dir(), "The existing shared implementation is required")
    sys.path.insert(0, str(shared))
    from daqr.evaluation.source_dataset import ArtifactReference, ExperimentBinding, SourceInput
    from daqr.evaluation.state_reporting import StateReporting

    source_inputs, inventory, source_hashes = [], [], {}
    winner_checks, scenario_disagreements, learner_labels = [], [], set()
    for suite in ("Hybrid", "CMABs", "iCMABs", "EXP3"):
        relative = f"Validated_Logs/Master_Dataset_{suite}.csv"
        source_path = Path(workspace) / relative
        content = source_path.read_bytes()
        source_hashes[relative] = hashlib.sha256(content).hexdigest()
        require(source_hashes[relative] == PRIMARY_EXPORT_SHA256[suite], f"Evidence hash mismatch: {relative}")
        with source_path.open(newline="") as stream:
            data = list(csv.DictReader(stream))
        keys = [(row["source_file"], row["scenario"], row["experiment"], row["model"]) for row in data]
        require(len(set(keys)) == len(keys), f"Duplicate exported observation keys: {suite}")
        require(all(all(key) for key in keys), f"Missing exported observation identity: {suite}")
        bindings = tuple(ExperimentBinding(
            pointer=f"/rows/{index}",
            recorded_ids={"export_row": index + 2, "source_file": row["source_file"],
                          "experiment": row["experiment"], "model": row["model"]},
            conditions={key: row[key] for key in ("scenario", "runs", "frames", "allocator", "cap_type", "scale")},
            model_metadata={"model": row["model"]},
            evidence={"endpoint": (f"/rows/{index}",)},
        ) for index, row in enumerate(data))
        reference = ArtifactReference(
            artifact_id=relative, artifact_type="text/csv", role="existing-validation-export",
            path=str(source_path.resolve()), component="framework_state",
            storage_day="day_20261022", original_filename=source_path.name,
            content_sha256=source_hashes[relative], byte_length=len(content), content_type="text/csv",
        )
        source_inputs.append(SourceInput(reference, {"csv_text": content.decode(), "rows": data},
                                        experiments=bindings, field_coverage="partial"))
        oracle = sum(row["model"].upper() == "ORACLE" for row in data)
        learner_labels.update(row["model"] for row in data if row["model"].upper() != "ORACLE")
        groups, scenarios = {}, {}
        for row in data:
            groups.setdefault((row["source_file"], row["scenario"], row["experiment"]), []).append(row)
            if row["model"].upper() != "ORACLE":
                scenarios.setdefault((row["source_file"], row["scenario"]), []).append(row)
        for key, group in groups.items():
            require(sum(row["model"].upper() == "ORACLE" for row in group) == 1,
                    f"Expected one Oracle per exported comparison: {suite} {key}")
            learned = [row for row in group if row["model"].upper() != "ORACLE"]
            maximum = max(float(row["reward"]) for row in learned)
            leaders = [row["model"] for row in learned if float(row["reward"]) == maximum]
            labels = {row["winner"].upper() for row in group}
            winner_checks.append({"matches": len(labels) == 1 and next(iter(labels)) in leaders,
                                  "exact_tie": len(leaders) > 1})
        for key, group in scenarios.items():
            efficiencies = {}
            for row in group:
                efficiencies.setdefault(row["model"], []).append(float(row["eff_pct"]))
            means = {model: mean(values) for model, values in efficiencies.items()}
            maximum = max(means.values())
            leaders = [model for model, value in means.items() if abs(value - maximum) <= 1e-12]
            labels = sorted({row["scenario_winner"].upper() for row in group})
            if len(labels) != 1 or labels[0] not in leaders:
                scenario_disagreements.append({"suite": suite, "source_file": key[0], "scenario": key[1],
                                               "saved_labels": labels, "mean_efficiency_leaders": leaders,
                                               "mean_efficiency_pct": means})
        inventory.append({"suite": suite, "rows": len(data), "oracle_rows": oracle,
                          "learned_rows": len(data) - oracle,
                          "export_groups": len({key[:3] for key in keys}),
                          "source_filenames": len({row["source_file"] for row in data}),
                          "run_counts": dict(Counter(row["runs"] for row in data))})
    master = StateReporting().build_source_master_dataset(
        source_inputs, scope="GA primary historical CSV exports only; one binding per exported model result; intake day is not execution date")
    master.validate_revision()
    document = master.to_dict()
    total = sum(row["rows"] for row in inventory)
    require(total == 10240 and sum(row["learned_rows"] for row in inventory) == 8241
            and sum(row["oracle_rows"] for row in inventory) == 1999,
            "Pinned exported coverage changed")
    require(len(learner_labels) == 15, "Pinned policy coverage changed")
    require(len(winner_checks) == 1999 and all(row["matches"] for row in winner_checks),
            "Saved experiment winner disagrees with reward maximum")
    require(len(document["experiments"]) == total, "Shared assembly changed exported observation coverage")
    for original, assembled in zip(source_inputs, document["rawObjects"].values()):
        require(original.payload == assembled["payload"], "Shared assembly changed source content")
    implementation_hashes = {}
    for name in ("source_dataset.py", "state_reporting.py", "preparation_recipes.py", "dataset_pipeline.py", "source_intake.py"):
        path = shared / "daqr/evaluation" / name
        implementation_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"verdict": "PASS_EXPORT_ACCOUNTING", "sources_sha256": source_hashes,
            "shared_implementation_sha256": implementation_hashes,
            "master_revision": document["revision"], "inventory": inventory,
            "total_rows": total, "learned_rows": sum(row["learned_rows"] for row in inventory),
            "oracle_rows": sum(row["oracle_rows"] for row in inventory),
            "export_groups": sum(row["export_groups"] for row in inventory),
            "unique_learner_labels": len(learner_labels),
            "experiment_winner_checks": len(winner_checks),
            "experiment_winner_mismatches": sum(not row["matches"] for row in winner_checks),
            "experiment_exact_reward_ties": sum(row["exact_tie"] for row in winner_checks),
            "scenario_summary_disagreements": scenario_disagreements,
            "unit": "exported model-result row; not an independent episode or unique physical configuration",
            "coverage_boundary": "Four named CSV exports. Source filenames are provenance pointers, not proof their original state files are recovered. No archive-wide completeness claim.",
            "plan_boundary": "552 configurations, 5520 episodes and 380 GPU-hours are planning estimates, not an executed-count identity."}


def audit_recorded_run_headers(workspace):
    relative = "Validated_Logs/Hybrid_Tests/3Runs/3HybridRuns_S1-2T_all_logs_combined.txt"
    path = Path(workspace) / relative
    content = path.read_bytes()
    text = content.decode()
    pattern = r"^([^\n]+?) EXP (\d+): Env:([^,]+), Attack:([^,]+), Rate:([\d.]+), Frames:(\d+), QubitAlloc=([^,]+),.*Seed:\s*(\d+)"
    headers = [dict(zip(("label", "experiment", "environment", "attack", "configured_rate", "frames", "allocator", "seed"), match))
               for match in re.findall(pattern, text, re.MULTILINE)]
    require(bool(headers), "No recorded run headers recovered")
    return {"source": relative, "sha256": hashlib.sha256(content).hexdigest(),
            "header_count": len(headers),
            "configured_rates_by_attack": {attack: sorted({row["configured_rate"] for row in headers if row["attack"] == attack})
                                           for attack in sorted({row["attack"] for row in headers})},
            "fixed_budget_calls": len(re.findall(r"\[FixedAllocator\] timestep=\d+.*allocation=\(8, 10, 8, 9\)", text)),
            "scope": "Recorded headers in this combined log only; resumed results and repeated output are retained. Header values do not certify missing data-producing code or nested learner settings.",
            "summary_boundary": "Use the experiment header's rate, not the inconsistent Stochastic summary X Rate:0.25 label."}


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
            "Display-rounding differences alone are not scientific closure blockers; dataset scope and calculation definitions determine material discrepancies.",
            "Eight saved Hybrid scenario-summary labels differ from recomputed mean-efficiency leaders; their historical export/summary rule remains unresolved. The manuscript now reports descriptive statistics without unsupported bootstrap inference.",
            "Venue page count, human author fields and external integration review remain separate release gates; GitHub main supports the owner's normal Overleaf pull.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--paper", required=True)
    parser.add_argument("--output")
    parser.add_argument("--shared-implementation")
    arguments = parser.parse_args()
    result = reconcile(arguments.workspace, arguments.paper)
    if arguments.shared_implementation:
        result["primary_export_audit"] = audit_primary_exports(arguments.workspace, arguments.shared_implementation)
        result["recorded_run_headers"] = audit_recorded_run_headers(arguments.workspace)
    rendered = json.dumps(result, indent=2) + "\n"
    if arguments.output:
        Path(arguments.output).write_text(rendered)
    else:
        print(rendered)
    if result["verdict"].startswith("FAIL"):
        raise SystemExit(1)
