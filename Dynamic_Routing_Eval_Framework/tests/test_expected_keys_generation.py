import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_IMPORT_ERROR = None
try:
    from daqr.config.expected_keys import (
        generate_expected_state_keys,
        parse_multirun_evaluator_filename,
    )
except Exception as exc:
    generate_expected_state_keys = None
    parse_multirun_evaluator_filename = None
    _IMPORT_ERROR = exc


class TestExpectedKeyGenerationStatic(unittest.TestCase):
    def test_generate_expected_keys_uses_state_naming_helpers(self):
        src = _read(PROJECT_ROOT / "daqr" / "config" / "experiment_config.py")
        self.assertIn("generate_expected_state_keys", src)
        self.assertIn("parse_multirun_evaluator_filename", src)


@unittest.skipIf(_IMPORT_ERROR is not None, f"optional dependency missing for expected-key tests: {_IMPORT_ERROR}")
class TestExpectedKeyGenerationRuntime(unittest.TestCase):
    def test_generate_expected_keys_matches_runner_and_model_naming(self):
        from daqr.config.state_naming import runner_state_filename, model_state_filename

        class _DummyModel:
            pass

        evaluator = "MultiRunEvaluator_4000-Default_All_All-4000_2000_2_S1T_paper12.pkl"
        parsed = parse_multirun_evaluator_filename(evaluator)
        self.assertIsNotNone(parsed)
        results = generate_expected_state_keys(
            evaluator_filename=evaluator,
            parsed=parsed,
            runs=2,
            models=["Dummy"],
            algorithm_configs={"Dummy": {"model_class": _DummyModel, "kwargs": {"mode": "base"}}},
            scale=1,
            base_capacity=True,
        )

        fw = results["framework_state"]
        ms = results["model_state"]

        self.assertIn(evaluator, fw)
        self.assertGreater(len(fw), 1)
        self.assertGreater(len(ms), 1)

        # For run 1 (runner_id=1), first frame is base_frames=4000, cap_id is base_frames (Tb semantics).
        expected_runner = runner_state_filename(
            runner_id=1,
            cap_id=4000,
            allocator_id="Default",
            env_id="Baseline (None)",
            attack_id="No",
            frames_count=4000,
            runtime_suffix="_paper12",
        )
        self.assertIn(expected_runner, fw)

        expected_model = model_state_filename(
            model_id=_DummyModel.__name__,
            mode="base",
            cap_id=4000,
            allocator_id="Default",
            env_id="Baseline (None)",
            attack_id="No",
            frame_no=4000,
            runtime_suffix="_paper12",
        )
        self.assertIn(expected_model, ms)

        # Ensure allocation-agnostic keys (no legacy qubit suffix).
        offenders = [k for k in list(fw.keys()) + list(ms.keys()) if "_(" in k]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
