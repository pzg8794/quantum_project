#!/usr/bin/env python3
"""
Naming + resume sanity checks (framework state).

Goal: protect the Random-allocator policy:
  - New filenames should NOT encode qubit allocations in runner/model filenames.
  - Random resume should be allocation-agnostic but remain backward compatible with
    legacy state files that include a `_(d_d_d_d)` suffix.

Run:
  python3 tools/tests/test_state_naming_and_resume.py
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


QUBIT_SUFFIX_RE = re.compile(r"_\(\d+_\d+_\d+_\d+\)")

# Ensure `import daqr` works when executing from any directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _can_import_runtime_modules() -> bool:
    """
    Some environments run these tests without the project venv activated.
    In that case, heavy deps (numpy/torch/networkx) may be missing.
    We still want fast, valuable checks, so we always run static tests
    and only run runtime-import tests when deps are available.
    """
    try:
        # Importing ExperimentConfiguration pulls in most heavy deps.
        from daqr.config.experiment_config import ExperimentConfiguration  # noqa: F401

        return True
    except Exception:
        return False


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        raise AssertionError(msg)


def _write_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"x" * size)


def test_static_no_random_qubit_suffix_in_runner_or_model_filenames() -> None:
    runner_py = PROJECT_ROOT / "daqr" / "evaluation" / "experiment_runner.py"
    model_py = PROJECT_ROOT / "daqr" / "algorithms" / "base_bandit.py"

    runner_src = _read(runner_py)
    model_src = _read(model_py)

    _assert(
        "id_str +=" not in runner_src or "_(" not in runner_src,
        "Runner appears to still append qubit tuple suffix into filenames for Random allocator.",
    )
    _assert(
        'if "random" in str(self.configs.allocator).lower(): id_str +=' not in runner_src,
        "Runner still contains Random filename suffix append logic.",
    )
    _assert(
        'if "random" in str(self.configs.allocator).lower(): frame_no_str +=' not in model_src,
        "Model still contains Random filename suffix append logic.",
    )
    _assert(
        "del self.key_attrs['qubit_capacities']" not in runner_src,
        "Runner __eq__ appears to delete key_attrs['qubit_capacities'] (state mutation risk).",
    )


def test_static_random_resolve_is_stem_based_and_legacy_compatible() -> None:
    cfg_py = PROJECT_ROOT / "daqr" / "config" / "experiment_config.py"
    src = _read(cfg_py)

    _assert(
        "_stem_key" in src and r"_\(\d+_\d+_\d+_\d+\)" in src,
        "Expected stem-based Random resolver (strip legacy qubit tuple) not found in experiment_config.py.",
    )
    _assert(
        "item_v.replace" not in src or "file_qubits" not in src,
        "experiment_config.py still appears to be doing suffix substitution instead of stem match.",
    )


def test_expected_keys_no_qubit_suffix_for_random_runtime() -> None:
    from daqr.config.experiment_config import ExperimentConfiguration
    from daqr.algorithms.predictive_bandits import Oracle

    cfg = ExperimentConfiguration.__new__(ExperimentConfiguration)
    cfg.runs = 3
    cfg.models = ["Oracle"]
    cfg.algorithm_configs = {"Oracle": {"model_class": Oracle, "kwargs": {"mode": "base"}}}
    cfg.attack_rate = 0.25
    cfg.attack_intensity = 1.0
    cfg.scale = 1
    cfg.base_capacity = True
    cfg.expected_keys = {}

    evaluator = "MultiRunEvaluator_4000-Random_All_All-4000_2000_3_S1T_paper12.pkl"
    cfg.generate_expected_keys(evaluator)

    fw = cfg.expected_keys["framework_state"]
    ms = cfg.expected_keys["model_state"]

    all_keys = list(fw.keys()) + list(ms.keys())
    offenders = [k for k in all_keys if QUBIT_SUFFIX_RE.search(k)]
    _assert(
        len(offenders) == 0,
        "Expected no legacy qubit suffix in generated keys, but found:\n"
        + "\n".join(offenders[:20]),
    )


def test_resolve_random_filename_prefers_largest_legacy_match() -> None:
    from daqr.config.experiment_config import ExperimentConfiguration

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)

        # New expected filename (no qubit suffix)
        expected = "QuantumExperimentRunner_1_4000-Random_Stochastic_Random-4000_1_paper12.pkl"

        # Two legacy candidates with different sizes
        legacy_small = "QuantumExperimentRunner_1_4000-Random_Stochastic_Random-4000_1_(1_2_3_4)_paper12.pkl"
        legacy_large = "QuantumExperimentRunner_1_4000-Random_Stochastic_Random-4000_1_(5_6_7_8)_paper12.pkl"

        small_path = td_path / "framework_state" / legacy_small
        large_path = td_path / "framework_state" / legacy_large
        _write_file(small_path, size=10)
        _write_file(large_path, size=20)

        cfg = ExperimentConfiguration.__new__(ExperimentConfiguration)
        cfg.backup_registry = {
            "framework_state": {
                legacy_small: str(small_path),
                legacy_large: str(large_path),
            }
        }

        resolved = cfg._resolve_random_filename(expected)
        _assert(
            resolved == legacy_large,
            f"Expected largest legacy match to be selected.\nExpected: {legacy_large}\nGot:      {resolved}",
        )


def test_resolve_random_filename_noop_for_nonrandom() -> None:
    from daqr.config.experiment_config import ExperimentConfiguration

    cfg = ExperimentConfiguration.__new__(ExperimentConfiguration)
    cfg.backup_registry = {"framework_state": {}}
    item = "QuantumExperimentRunner_1_4000-Default_Stochastic_Random-4000_1_paper2.pkl"
    _assert(cfg._resolve_random_filename(item) == item, "Non-random filename should be unchanged.")


@dataclass
class _DummyConfigs:
    allocator: str
    models: list[str]


def test_runner_eq_does_not_mutate_key_attrs_for_random() -> None:
    from daqr.evaluation.experiment_runner import QuantumExperimentRunner

    runner = QuantumExperimentRunner.__new__(QuantumExperimentRunner)
    runner.configs = _DummyConfigs(allocator="Random", models=["Oracle"])
    runner.id = 1
    runner.allocator_id = "Random"
    runner.env_id = "Stochastic"
    runner.attack_id = "Random"
    runner.cap_id = 4000
    runner.key_attrs = {"qubit_capacities": "(5, 5, 5, 4)", "entanglement_success_factor": "100"}

    other = {
        "id": 1,
        "allocator_id": "Random",
        "env_id": "Stochastic",
        "attack_id": "Random",
        "cap_id": 4000,
        "key_attrs": {"qubit_capacities": "(9, 9, 9, 8)", "entanglement_success_factor": "100"},
        "results": {"Oracle": {}},
    }

    ok = runner.__eq__(other)
    _assert(ok is True, "Runner __eq__ should ignore qubit_capacities for Random allocator.")
    _assert(
        "qubit_capacities" in runner.key_attrs,
        "Runner __eq__ must not delete/mutate runner.key_attrs['qubit_capacities']",
    )


def main() -> int:
    os.environ.setdefault("PYTHONHASHSEED", "0")

    static_tests = [
        test_static_no_random_qubit_suffix_in_runner_or_model_filenames,
        test_static_random_resolve_is_stem_based_and_legacy_compatible,
    ]

    runtime_tests = [
        test_expected_keys_no_qubit_suffix_for_random_runtime,
        test_resolve_random_filename_prefers_largest_legacy_match,
        test_resolve_random_filename_noop_for_nonrandom,
        test_runner_eq_does_not_mutate_key_attrs_for_random,
    ]

    failed = 0
    for t in static_tests:
        name = t.__name__
        try:
            t()
            print(f"✅ PASS | {name}")
        except Exception as e:
            failed += 1
            print(f"❌ FAIL | {name}: {e}")

    if _can_import_runtime_modules():
        for t in runtime_tests:
            name = t.__name__
            try:
                t()
                print(f"✅ PASS | {name}")
            except Exception as e:
                failed += 1
                print(f"❌ FAIL | {name}: {e}")
    else:
        print("⏭️  SKIP | runtime-import tests (project deps not available in current environment)")

    print("-" * 60)
    if failed == 0:
        print("✅ ALL NAMING/RESUME TESTS PASSED")
        return 0
    print(f"❌ {failed} TEST(S) FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
