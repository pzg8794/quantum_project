import os
import sys
import pickle
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator


class _DummyBackupMgr:
    def __init__(self, backup_registry):
        self.backup_registry = backup_registry


class _DummyConfigs:
    """
    Minimal config stub for exercising MultiRunEvaluator resume logic without running experiments.
    """

    def __init__(self, backup_registry):
        self.use_last_backup = True
        self.suffix = None
        self.backup_mgr = _DummyBackupMgr(backup_registry)
        self.allocator = "Default"
        self.scale = 1

        # Used by run_experiments test
        self.runs = 1
        self.models = ["Oracle"]
        self.test_scenarios = {"stochastic": "Stochastic"}
        self.attack_type = "stochastic"
        self.category_map = {"stochastic": "Stochastic (Natural Random Failures)"}

    def update_configs(self, runs=None, models=None, scenarios=None, attack_type=None, attack_intensity=None, attack_rate=None):
        if isinstance(runs, int):
            self.runs = runs
        if isinstance(models, list):
            self.models = models
        if isinstance(scenarios, dict):
            self.test_scenarios = scenarios
        if isinstance(attack_type, str):
            self.attack_type = attack_type

    def resume_obj(self, _obj):
        # Force exact resume to fail so evaluator uses superset/subset search.
        return False

    def _load_obj(self, obj, state_path: Path):
        with open(state_path, "rb") as f:
            loaded_dict = pickle.load(f)
        # Use the evaluator's equality logic to decide whether to accept the state.
        eq_result = bool(obj == loaded_dict)
        return loaded_dict, eq_result


def _make_saved_state(*, runs_id: int, allocator_id="Default", cap_id=8000, base_frames=4000, frame_step=2000, key_attrs=None, models=None):
    if key_attrs is None:
        # Intentionally omit "test_bed" to test default-compatible comparisons.
        key_attrs = {
            "attack": "None",
            "qubit_capacities": "(8, 10, 8, 9)",
            "allocator": "Default",
            "env_type": "stochastic",
            "entanglement_success_factor": "None",  # test legacy normalization
        }

    if models is None:
        models = ["Oracle", "Other"]

    def _exp(exp_id: int):
        return {
            "exp_id": exp_id,
            "results": {m: {"final_reward": float(exp_id)} for m in models},
            "winner": "Oracle",
        }

    env_experiments = {"stochastic": {i: _exp(i) for i in range(1, runs_id + 1)}}
    evaluation_results = {"stochastic": {i: _exp(i) for i in range(1, runs_id + 1)}}

    return {
        "frame_step": frame_step,
        "base_frames": base_frames,
        "allocator_id": allocator_id,
        "runs_id": runs_id,
        "cap_id": cap_id,
        "key_attrs": dict(key_attrs),
        "env_experiments": env_experiments,
        "evaluation_results": evaluation_results,
        "runner_qubit_caps": {},
        "scenarios_stats": {},
        "run_state": 1,
        "total_time": 0.0,
    }


def _make_evaluator(*, runs_id: int, configs: _DummyConfigs, cap_id=8000, base_frames=4000, frame_step=2000, key_attrs=None, models=None):
    if key_attrs is None:
        key_attrs = {
            "attack": "None",
            "qubit_capacities": "(8, 10, 8, 9)",
            "allocator": "Default",
            "env_type": "stochastic",
            "entanglement_success_factor": "100",
        }

    if models is None:
        models = ["Oracle"]

    ev = MultiRunEvaluator.__new__(MultiRunEvaluator)
    ev.configs = configs
    ev.component = "framework_state"
    ev.models = list(models)

    ev.base_seed = 12345
    ev.frame_step = frame_step
    ev.base_frames = base_frames
    ev.capacity = base_frames
    ev.frames_count = base_frames

    ev.allocator_id = "Default"
    ev.env_id = "All"
    ev.attack_id = "All"
    ev.cap_id = cap_id

    ev.runs_id = runs_id
    ev.key_attrs = dict(key_attrs)

    ev.scenarios_stats = {}
    ev.env_experiments = {}
    ev.evaluation_results = {}
    ev.runner_qubit_caps = {}

    ev.resumed = False
    ev.run_state = 0
    ev.is_complete = False
    ev.enable_progress = False
    return ev


class TestMultiRunResumeBehavior(unittest.TestCase):
    def test_exact_resume_does_not_override_target_runs(self):
        """
        Regression test: exact resume (configs.resume_obj) updates obj.__dict__ and can overwrite
        any in-memory "target" fields. We must ALWAYS keep the caller's intended run horizon.
        """

        class _ExactResumeCfg(_DummyConfigs):
            def __init__(self, backup_registry, loaded_dict):
                super().__init__(backup_registry)
                self._loaded_dict = loaded_dict

            def resume_obj(self, obj):
                # Mimic ExperimentConfiguration.resume_obj behavior: update obj.__dict__ but preserve configs + file_name.
                configs = obj.configs
                old_file_name = getattr(obj, "file_name", None)
                obj.__dict__.update(self._loaded_dict)
                obj.configs = configs
                if old_file_name is not None:
                    obj.file_name = old_file_name
                obj.resumed = True
                return True

        # Caller intends 5 runs
        loaded = _make_saved_state(runs_id=1, models=["Oracle"])
        # Simulate that the pickle contains stale control fields that must NOT win.
        loaded["_target_runs"] = 1
        loaded["runs_id"] = 1

        cfg = _ExactResumeCfg({"framework_state": {}}, loaded)
        cfg.runs = 5
        ev = _make_evaluator(runs_id=5, configs=cfg, models=["Oracle"])
        ev._target_runs = 5
        ev.file_name = "dummy.pkl"

        ok = ev.resume()
        self.assertTrue(ok)
        self.assertTrue(ev.resumed)
        self.assertEqual(cfg.runs, 5)
        self.assertEqual(ev.runs_id, 5)

    def test_resume_from_superset_filters_down_to_target_runs(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            superset_state = _make_saved_state(runs_id=8)
            superset_file = td_path / "evaluator_8.pkl"
            with open(superset_file, "wb") as f:
                pickle.dump(superset_state, f)

            backup_registry = {"framework_state": {superset_file.name: str(superset_file)}}
            cfg = _DummyConfigs(backup_registry)
            cfg.runs = 5
            ev = _make_evaluator(runs_id=5, configs=cfg)
            ev._target_runs = 5

            # Pretend the registry parsing found a horizon=8 backup.
            ev._get_superset_subregistry = lambda: {8: superset_file.name}

            ok = ev.resume()
            self.assertTrue(ok)
            self.assertTrue(ev.resumed)
            self.assertEqual(cfg.runs, 5)

            # Ensure we kept only experiments 1..5 and only the target model(s).
            self.assertIn("stochastic", ev.env_experiments)
            kept = ev.env_experiments["stochastic"]
            self.assertEqual(set(kept.keys()), {1, 2, 3, 4, 5})
            for exp in kept.values():
                self.assertEqual(set(exp["results"].keys()), {"Oracle"})

    def test_resume_prefers_highest_horizon_even_if_smaller_pickle(self):
        """
        Contract test: if both a 3-run and 8-run evaluator state exist for the same key,
        resume must attempt the highest horizon first (8 → 3), regardless of on-disk pickle size.
        """
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            # Make the 3-run file artificially large so a size-based ordering would pick it first.
            subset_state = _make_saved_state(runs_id=3)
            subset_state["_padding"] = "x" * 200_000
            subset_file = td_path / "evaluator_3.pkl"
            with open(subset_file, "wb") as f:
                pickle.dump(subset_state, f)

            superset_state = _make_saved_state(runs_id=8)
            superset_file = td_path / "evaluator_8.pkl"
            with open(superset_file, "wb") as f:
                pickle.dump(superset_state, f)

            backup_registry = {
                "framework_state": {
                    subset_file.name: str(subset_file),
                    superset_file.name: str(superset_file),
                }
            }
            cfg = _DummyConfigs(backup_registry)
            cfg.runs = 5
            ev = _make_evaluator(runs_id=5, configs=cfg)
            ev._target_runs = 5

            # Provide both candidates.
            ev._get_superset_subregistry = lambda: {3: subset_file.name, 8: superset_file.name}

            ok = ev.resume()
            self.assertTrue(ok)
            self.assertTrue(ev.resumed)
            self.assertIn("stochastic", ev.env_experiments)
            # If we resumed from the 8-run superset, subset reconstruction keeps runs 1..5.
            self.assertEqual(set(ev.env_experiments["stochastic"].keys()), {1, 2, 3, 4, 5})

    def test_resume_falls_back_when_highest_incompatible(self):
        """
        Contract test: if the highest-horizon candidate is incompatible, resume should
        fall back to the next candidate.
        """
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            subset_state = _make_saved_state(runs_id=3, cap_id=8000)
            subset_file = td_path / "evaluator_3.pkl"
            with open(subset_file, "wb") as f:
                pickle.dump(subset_state, f)

            # Make the 8-run candidate incompatible (cap_id mismatch).
            superset_state = _make_saved_state(runs_id=8, cap_id=9999)
            superset_file = td_path / "evaluator_8.pkl"
            with open(superset_file, "wb") as f:
                pickle.dump(superset_state, f)

            backup_registry = {
                "framework_state": {
                    subset_file.name: str(subset_file),
                    superset_file.name: str(superset_file),
                }
            }
            cfg = _DummyConfigs(backup_registry)
            cfg.runs = 5
            ev = _make_evaluator(runs_id=5, configs=cfg, cap_id=8000)
            ev._target_runs = 5

            ev._get_superset_subregistry = lambda: {3: subset_file.name, 8: superset_file.name}

            ok = ev.resume()
            self.assertTrue(ok)
            self.assertTrue(ev.resumed)
            self.assertIn("stochastic", ev.env_experiments)
            # Should have resumed from the 3-run candidate (1..3 only).
            self.assertEqual(set(ev.env_experiments["stochastic"].keys()), {1, 2, 3})

    def test_resume_from_subset_and_extend_runs(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)

            subset_state = _make_saved_state(runs_id=3, models=["Oracle"])
            subset_file = td_path / "evaluator_3.pkl"
            with open(subset_file, "wb") as f:
                pickle.dump(subset_state, f)

            backup_registry = {"framework_state": {subset_file.name: str(subset_file)}}
            cfg = _DummyConfigs(backup_registry)
            cfg.runs = 5
            ev = _make_evaluator(runs_id=5, configs=cfg, models=["Oracle"])
            ev._target_runs = 5

            ev._get_superset_subregistry = lambda: {3: subset_file.name}

            ok = ev.resume()
            self.assertTrue(ok)
            self.assertTrue(ev.resumed)
            self.assertIn("stochastic", ev.env_experiments)
            self.assertEqual(set(ev.env_experiments["stochastic"].keys()), {1, 2, 3})

            # Now prove extension works: run_experiments should add runs 4 and 5
            created = []

            def _run_experiment(exp_no, attack_category=None, **_kwargs):
                exp_id = exp_no + 1
                created.append(exp_id)
                exp_data = {
                    "exp_id": exp_id,
                    "results": {"Oracle": {"final_reward": float(exp_id)}},
                    "winner": "Oracle",
                    "attack_category": attack_category,
                }
                ev.env_experiments[ev.configs.attack_type][exp_id] = exp_data
                return exp_data

            ev.run_experiment = _run_experiment
            ev.save = lambda: None
            ev.display_run_results = lambda *_args, **_kwargs: None

            out = ev.run_experiments(runs=5, attack_type="stochastic", models=["Oracle"])
            self.assertEqual(created, [4, 5])
            self.assertEqual(set(out.keys()), {1, 2, 3, 4, 5})


if __name__ == "__main__":
    unittest.main()
