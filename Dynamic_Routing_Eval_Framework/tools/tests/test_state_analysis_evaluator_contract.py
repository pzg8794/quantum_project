#!/usr/bin/env python3
"""
Small contract tests for state_analysis.py versus saved MultiRunEvaluator states.

Goal:
  - Verify the evaluator payload still satisfies the documented analysis contract.
  - Detect brittle extraction behavior caused by placeholder scenarios such as `n/a`.

Run:
  python3 tools/tests/test_state_analysis_evaluator_contract.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


DAQR_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = DAQR_ROOT / "daqr" / "config" / "framework_state"

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(DAQR_ROOT))


EXPECTED_TOP_KEYS = {
    "env_experiments",
    "evaluation_results",
    "runner_qubit_caps",
    "key_attrs",
    "capacity",
    "t_scale",
    "is_base_t",
    "runs_id",
    "base_frames",
    "frame_step",
    "file_name",
}

REAL_SCENARIOS = {"none", "stochastic", "markov", "adaptive", "onlineadaptive"}
EXPECTED_SUMMARY_KEYS = {
    "win_counts",
    "total_experiments",
    "all_model_metrics",
    "overall_winner",
    "winner_efficients",
    "oracle_avg_reward",
    "avg_gap",
    "avg_reward",
    "winner_avg_metrics",
    "avg_efficiency",
}
EXPECTED_WINNER_KEYS = {
    "avg_reward",
    "avg_gap",
    "efficiency_list",
    "wins",
    "avg_efficiency",
    "reward_list",
    "creward_list",
}

REPRESENTATIVE_STATE_NAMES = [
    "MultiRunEvaluator_4000-Default_All_All-4000_2000_5_S1T.pkl",
    "MultiRunEvaluator_4000-Default_All_All-4000_2000_5_S1T_paper2.pkl",
    "MultiRunEvaluator_1500-Default_All_All-1500_500_5_S1T_paper12.pkl",
    "MultiRunEvaluator_8000-Default_All_All-4000_2000_5_S2T_paper8.pkl",
]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _can_import_runtime_modules() -> bool:
    try:
        global state_analysis
        import state_analysis as state_analysis_module

        state_analysis = state_analysis_module
        return True
    except Exception as exc:
        print(f"SKIP: state-analysis runtime deps not available: {exc}")
        return False


def _find_state(filename: str) -> Path | None:
    matches = list(STATE_ROOT.rglob(filename))
    if not matches:
        return None
    matches.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0]


def _load_state(path: Path):
    state = state_analysis._load_any_pickle(path)
    _assert(state is not None, f"Could not load evaluator state: {path.name}")
    return state


def _iter_representative_states() -> list[Path]:
    found = []
    for filename in REPRESENTATIVE_STATE_NAMES:
        path = _find_state(filename)
        if path is not None:
            found.append(path)
    _assert(found, "No representative evaluator states were found under framework_state/.")
    return found


def _expected_rows_tolerant(state: dict) -> int:
    total = 0
    env_experiments = state.get("env_experiments", {})
    scenarios_results = state.get("evaluation_results", {}).get("scenarios_results", {})

    for scenario_name, experiments in env_experiments.items():
        if scenario_name not in scenarios_results:
            continue
        if not isinstance(experiments, dict):
            continue
        for exp_id_str, exp_data in experiments.items():
            try:
                int(exp_id_str)
            except (TypeError, ValueError):
                continue
            if not isinstance(exp_data, dict):
                continue
            results = exp_data.get("results", {})
            if isinstance(results, dict):
                total += len(results)
    return total


def test_evaluator_contract_smoke() -> None:
    failures = []
    for path in _iter_representative_states():
        state = _load_state(path)
        state_keys = set(state.keys())
        missing_top = sorted(EXPECTED_TOP_KEYS - state_keys)
        if missing_top:
            failures.append(f"{path.name}: missing top-level keys {missing_top}")
            continue

        env_experiments = state.get("env_experiments", {})
        scenarios_results = state.get("evaluation_results", {}).get("scenarios_results", {})

        for scenario_name in sorted(REAL_SCENARIOS):
            if scenario_name not in env_experiments:
                failures.append(f"{path.name}: missing env_experiments[{scenario_name!r}]")
                continue
            if scenario_name not in scenarios_results:
                failures.append(f"{path.name}: missing scenarios_results[{scenario_name!r}]")
                continue

            scenario_summary = scenarios_results[scenario_name]
            missing_summary = sorted(EXPECTED_SUMMARY_KEYS - set(scenario_summary.keys()))
            if missing_summary:
                failures.append(
                    f"{path.name}: scenario {scenario_name!r} missing summary keys {missing_summary}"
                )
                continue

            winner_metrics = scenario_summary.get("winner_avg_metrics", {})
            missing_winner = sorted(EXPECTED_WINNER_KEYS - set(winner_metrics.keys()))
            if missing_winner:
                failures.append(
                    f"{path.name}: scenario {scenario_name!r} missing winner_avg_metrics keys {missing_winner}"
                )

    _assert(not failures, "Evaluator contract smoke test failed:\n" + "\n".join(failures))


def test_placeholder_scenario_tolerance() -> None:
    failures = []
    for path in _iter_representative_states():
        state = _load_state(path)
        expected_rows = _expected_rows_tolerant(state)
        actual_rows = len(state_analysis.extract_data_from_state_file(path))
        if actual_rows != expected_rows:
            failures.append(
                f"{path.name}: extractor rows={actual_rows}, tolerant expected rows={expected_rows}"
            )

    _assert(
        not failures,
        "Placeholder scenario tolerance test failed:\n" + "\n".join(failures),
    )


def test_evaluator_summary_repair_and_normalization() -> None:
    from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator

    def _model_result(final_reward: float, efficiency: float, gap: float):
        return {
            "final_reward": final_reward,
            "efficiency": efficiency,
            "gap": gap,
            "model_results": {"reward_list": [final_reward]},
        }

    def _experiment(winner: str, model_reward: float):
        return {
            "winner": winner,
            "results": {
                "Oracle": _model_result(final_reward=10.0, efficiency=100.0, gap=0.0),
                "ModelA": _model_result(final_reward=model_reward, efficiency=80.0, gap=20.0),
            },
        }

    evaluator = MultiRunEvaluator.__new__(MultiRunEvaluator)
    evaluator.configs = SimpleNamespace(
        test_scenarios={"stochastic": "Stochastic", "none": "Baseline"},
        models=["Oracle", "ModelA"],
    )
    evaluator.models = ["Oracle", "ModelA"]
    evaluator.env_experiments = {
        "n/a": {"junk": {}},
        "stochastic": {1: _experiment("ModelA", 8.0)},
        "none": {1: _experiment("ModelA", 9.0)},
    }
    evaluator.evaluation_results = {
        "n/a": {"junk": {}},
        "stochastic": {1: _experiment("ModelA", 8.0)},
        "none": {1: _experiment("ModelA", 9.0)},
    }
    evaluator.runner_qubit_caps = {"n/a": {}, "stochastic": {"1": "(1, 1)"}, "none": {"1": "(1, 1)"}}
    evaluator.scenarios_stats = {}

    changed = evaluator.ensure_summary_contract(save_if_changed=False)

    _assert(changed, "Expected evaluator summary repair to report changes")
    _assert("n/a" not in evaluator.env_experiments, "Expected stray env_experiments['n/a'] to be removed")
    _assert("n/a" not in evaluator.evaluation_results, "Expected stray evaluation_results['n/a'] to be removed")
    _assert("n/a" not in evaluator.runner_qubit_caps, "Expected stray runner_qubit_caps['n/a'] to be removed")

    scenarios_results = evaluator.evaluation_results.get("scenarios_results", {})
    for scenario_name in ("stochastic", "none"):
        _assert(scenario_name in scenarios_results, f"Missing rebuilt scenarios_results[{scenario_name!r}]")
        summary = scenarios_results[scenario_name]
        _assert(EXPECTED_SUMMARY_KEYS.issubset(summary.keys()), f"Incomplete rebuilt summary for {scenario_name!r}")
        _assert(
            EXPECTED_WINNER_KEYS.issubset(summary.get("winner_avg_metrics", {}).keys()),
            f"Incomplete rebuilt winner metrics for {scenario_name!r}",
        )


def main() -> int:
    if not _can_import_runtime_modules():
        return 0

    failed = 0
    tests = [
        test_evaluator_contract_smoke,
        test_placeholder_scenario_tolerance,
        test_evaluator_summary_repair_and_normalization,
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
        print("PASS: state-analysis evaluator contract tests")
        return 0
    print(f"FAIL: {failed} state-analysis evaluator contract test(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
