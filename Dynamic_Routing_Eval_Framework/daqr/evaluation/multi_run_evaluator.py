from concurrent.futures import ThreadPoolExecutor, as_completed
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.experiment_runner import QuantumExperimentRunner

import pathlib
from pathlib import Path
import pickle
import threading
import numpy as np, copy
import time, gc, re, json


class MultiRunEvaluator:
    """
    Enhanced Multi-Run Evaluator for Comprehensive Model Evaluation

    Supports comprehensive model testing in realistic quantum network conditions
    with focus on stochastic environment analysis and baseline comparison.
    """
    def __init__(self, configs=None, base_frames=4000, frame_step=2000, base_seed=12345, 
                 runs=None, attack_type=None, models=None, scenarios=None,
                 attack_intensity=None, enable_progress=False, has_all=True):
        """
        Initialize the multi-run evaluator.
        Args:
            configs: Configuration object (QuantumConfig)
            base_seed: Base random seed for reproducibility
            base_frames: Starting frame count for experiments
            frame_step: Incremental step for frame counts
            attack_type: Type of environment to simulate
            attack_intensity: Intensity level of the attack/environmental effect
            enable_progress: If True, show progress bars during experiments
            models: List of models/algorithms to evaluate
            scenarios: Dictionary of scenarios to test {scenario_key: description}
        """
        self.configs = configs if configs else ExperimentConfiguration()
        self._save_lock = threading.Lock()  
        self.scenarios_stats = {}
        self.env_experiments = {}
        self.evaluation_results = {}

        self.base_seed = base_seed
        self.frame_step = frame_step
        self.frames_count = base_frames
        self.base_frames = base_frames
        self.component    = "framework_state"
        self.enable_progress = enable_progress
        self.models = models or self.configs.models
        self.physics_params = self.configs.physics_params
        
        # self.runner = None
        self.run_state = 0        # 0: not run, 1: completed, -1: failed
        self.total_time = 0
        self.start_time = None
        self.resumed = False
        self.key_attrs = {}
        self.file_name = None
        self.cal_winner = True
        self.is_complete = False
        self.env_type = 'stochastic'
        self.runner_qubit_caps = {}
        self.capacity = self.base_frames
        self.t_scale  = self.configs.scale
        self.is_base_t = self.configs.base_capacity

        # Set paths
        # self.save_to_dir = self.configs.framework_state_path / self.configs.day_str
        
        # Update configs FIRST
        self.update_configs(runs, models, attack_type, scenarios, attack_intensity)

        qubit_cap = (8, 10, 8, 9)  # legacy fallback to avoid breaking runs
        # Strongly prefer caller to pass allocator-derived qubit_cap
        if self.configs.allocator is not None and not self.configs.allocator.has_allocated():
            qubit_cap = tuple(self.configs.allocator.allocate(timestep=0, route_stats={}, verbose=False))

        # Build the environment ONCE per experiment, then reuse across all models
        mode = self.configs.backup_mgr.mode
        component_path = self.configs.backup_mgr.quantum_data_paths["obj"][self.component][mode]
        self.save_to_dir = component_path / self.configs.day_str
        self._build_environment_once(frames_count=self.frames_count, qubit_cap=qubit_cap)

        # Set filename AFTER configs are ready
        self.runs_id        = getattr(self.configs, "runs", "1")
        self.allocator_id   = str(getattr(self.configs, "allocator", "alloc"))
        self.env_id         = str(getattr(self.configs, "environment", "env")) if not has_all else "All"
        self.attack_id      = str(getattr(self.configs, "attack_strategy", "None")) if not has_all else "All"

        run_id_str          = str(self.runs_id)
        alloc_str           = "_".join(str(v) for v in qubit_cap)
        # if "random" in str(self.configs.allocator).lower(): run_id_str += f"_({re.sub(r'^_', '', alloc_str)})"
        self.cap_id         = int(float(int(self.base_frames if self.is_base_t else self.frames_count)*self.configs.scale))
        self.file_name      = f"{self}_{self.cap_id}-{self.allocator_id}_{self.env_id}_{self.attack_id}-{int(self.base_frames)}_{int(self.frame_step)}_{run_id_str}_S{str(self.configs.scale).replace(".", "_")}{'Tb' if self.is_base_t else 'T'}.pkl"
        
        # NOW resume can work
        try:    self.resume()
        except Exception as e:  print(f"⚠️ {self} Resume failed: {e}")

        if not self.resumed:
            self.configs.use_last_backup = False
            print("No state found for MultiRunEvaluator, disabling resume for Experiment Runners")

        print("Multi-Run Evaluator Initialized")
        print(f"Environment Type: {attack_type}")
        print(f"Frame Range: {base_frames} -> {base_frames + (self.configs.runs-1)*frame_step} (step: {frame_step})")

    def _build_environment_once(self, frames_count: float, qubit_cap: tuple):
        """
        Build ONE shared environment for the whole experiment (all models),
        with a seed that is independent of the model being run.
        """
        try:
            if frames_count: self.frames_count = frames_count
            # Seed independent of model to keep environment identical across algorithms
            # env_seed = self.configs.base_seed + (hash(f"{self.configs.attack_type}_{self.frames_count}") % 10000)
            base_seed = int(getattr(self.configs, "base_seed", 0))
            env_seed = base_seed + (hash(f"{self.configs.attack_type}_{self.frames_count}") % 10000)


            # Configure attack scenario if not already configured by MultiRun
            self.configs.set_attack_strategy(
                attack_type=self.configs.attack_type,
                attack_rate=self.configs.attack_rate,
                attack_intensity=self.configs.attack_intensity
            )

            # Configure environment core parameters
            self.configs.set_environment(
                qubit_cap=qubit_cap,
                frames_no=self.frames_count,
                seed=env_seed,
                attack_intensity=self.configs.attack_intensity,
                attack_type=self.configs.attack_type,
                **self.physics_params              # ✅ Injects Paper #2 physics!
            )
            self.key_attrs = getattr(self.configs, "get_key_attrs", lambda: {})()
        except Exception as e: print(f"\tError Building Environment:\n\t{e}")

    def _infer_models_from_state(self, state: dict):
        """
        Infer the set of models used in a saved evaluator state
        by inspecting experiment result structures.

        This does NOT rely on any explicit 'models' field in the backup.
        """
        # 1) Try env_experiments first (most direct)
        env_exps = state.get("env_experiments", {})
        if isinstance(env_exps, dict) and env_exps:
            for attack_type, experiments in env_exps.items():
                if not isinstance(experiments, dict) or not experiments: continue
                # take the first experiment for this attack_type
                for exp_id, exp_data in experiments.items():
                    if not isinstance(exp_data, dict): continue
                    results = exp_data.get("results", {})
                    if isinstance(results, dict) and results: return [m for m in results.keys()]

        # 2) Fallback: try evaluation_results if env_experiments is empty
        eval_res = state.get("evaluation_results", {})
        if isinstance(eval_res, dict) and eval_res:
            for scenario, exps in eval_res.items():
                if not isinstance(exps, dict) or not exps: continue
                for exp_id, exp_data in exps.items():
                    if not isinstance(exp_data, dict): continue
                    results = exp_data.get("results", {})
                    if isinstance(results, dict) and results: return [m for m in results.keys()]

        # If we can't infer anything, return None and skip model check
        return None

    def safe_json(self, obj):
        # If it's not a dict, stringify safely
        if not isinstance(obj, dict):
            if callable(obj):
                return f"<function {obj.__name__}>"
            return str(obj)

        def serialize(val):
            if callable(val):
                return f"<method {val.__name__}>"
            try:
                json.dumps(val)
                return val
            except TypeError:
                return str(val)

        return {k: serialize(v) for k, v in obj.items()}

    def __eq__(self, other):
        """Defines equality for evaluator or saved dict comparison."""
        # --- dict comparison (used in resume) ---
        copied_attrs= copy.deepcopy(self.key_attrs)
        other_attrs = other.get("key_attrs", {}).copy()
        if isinstance(other, dict):
            print("EQUAL METHOD")

            try:
                # -------------------------------------------------
                # TEMP SAFETY CHECK: ensure model sets are compatible
                # -------------------------------------------------
                saved_models            = self._infer_models_from_state(other)
                if saved_models:
                    current_set         = set(self.models or [])
                    saved_set           = set(saved_models)
                    # This prevents: using a 3-model run as if it were a 5-model run.
                    if not current_set.issubset(saved_set):
                        print("\n❌ MODEL SET MISMATCH — forcing rerun")
                        print(f"   Current models: {sorted(current_set)}")
                        print(f"   Saved models:   {sorted(saved_set)}")
                        return False
                else:   print("ℹ️ Could not infer models from saved state — skipping model check")
            except Exception as e: print(f"ERROR 1: {e}")

            try:
                temp_qubit_capacities = None
                non_dflt_attrs = ["qubit_capacities", "frame_length", "actk_type", "noise_model", "fidelity_calculator", "external_topology", "external_contexts", "external_rewards", "runs"]
 
                # if "random" in str(self.configs.allocator).lower(): 
                #     try:
                #         temp_qubit_capacities = other_attrs.get('qubit_capacities', None) or copied_attrs['qubit_capacities']
                #         if 'qubit_capacities' in copied_attrs:  del copied_attrs['qubit_capacities']
                #         if 'qubit_capacities' in other_attrs:   del other_attrs['qubit_capacities']
                #     except: pass

                if "seed" in other_attrs:                   del other_attrs["seed"]

                for check in non_dflt_attrs:
                    try:
                        if check in other_attrs:            del other_attrs[check]
                        if check in copied_attrs:           del copied_attrs[check]
                    except: pass
                # if 'runs' in other_attrs:                 del other_attrs['runs']
                # if 'runs' in copied_attrs:                del copied_attrs['runs']
                # if 'frame_length' in other_attrs:         del other_attrs['frame_length']
                # if 'frame_length' in copied_attrs:        del copied_attrs['frame_length']
            except Exception as e: print(f"ERROR 2: {e}")

            try:
                if (
                    # self.capacity == other.get("capacity") and
                    self.frame_step == other.get("frame_step") and 
                    self.base_frames == other.get("base_frames") and
                    self.allocator_id == other.get("allocator_id") and 
                    str(self.runs_id) <= str(other.get("runs_id")) and
                    # self.attack_id == other.get("attack_id") and 
                    # self.env_id == other.get("env_id") and
                    self.cap_id == other.get("cap_id") and
                    copied_attrs == other_attrs
                ):
                    if temp_qubit_capacities: 
                        copied_attrs.update(other.get("key_attrs", {}))
                        copied_attrs.update({'qubit_capacities':temp_qubit_capacities})
                        for attr, val in copied_attrs.items():
                            if attr in self.configs._env_params.keys(): self.configs._env_params[attr] = val
                        # reset environment with random found capacity
                        try: self._build_environment_once(frames_count=self.frames_count, qubit_cap=temp_qubit_capacities)
                        except: pass
                        self.key_attrs.update(copied_attrs)
                    return True
            except Exception as e: print(f"ERROR 3: {e}")
            
            try:
                print(f"\n❌ {str(self).upper()} comparison failed:")
                print(f"  Frame step: {self.frame_step} vs {other.get('frame_step')}")
                print(f"  Base frames: {self.base_frames} vs {other.get('base_frames')}")
                print(f"  Allocator: {self.allocator_id} vs {other.get('allocator_id')}")
                # print(f"  Environment: {self.env_id} vs {other.get('env_id')}")
                print(f"  Runs: {self.runs_id} vs {other.get('runs_id')}")
                # print(f"  Attack: {self.attack_id} vs {other.get('attack_id')}")
                print(f"  Capacity: {self.cap_id} vs {other.get('cap_id')}")
                print(f"  Current attrs:\n{json.dumps(copied_attrs, indent=2)}")
                print(f"  Loaded attrs:\n{json.dumps(other_attrs, indent=2)}")
            except: pass

            return False

        # --- evaluator comparison ---
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.frame_step == getattr(other, "frame_step", None) and
            self.base_frames == getattr(other, "base_frames", None) and
            self.allocator_id == getattr(other, "allocator_id", None) and
            int(self.runs_id) <= int(getattr(other, "runs_id", -1)) and
            self.attack_id == getattr(other, "attack_id", None) and
            self.env_id == getattr(other, "env_id", None) and
            self.cap_id == getattr(other, "cap_id", None) and
            copied_attrs == getattr(other, "key_attrs", None)
        )
    
    def save(self):
        # This now always writes to the config backup (safe, never corrupts data lake)
        return self.configs.save_obj(self)


    def _filter_models_from_experiments(self, experiments_dict, target_runs):
        """Filter experiments by runs and models - removes unwanted models from data."""
        for scenario, experiments in experiments_dict.items():
            for exp_id, exp_data in list(experiments.items()):
                if re.search(r"\d+$", str(exp_id)) and int(exp_id) > target_runs:
                    del experiments[exp_id]  # Remove experiment

                elif 'results' in exp_data:
                    # Remove models we DON'T want
                    for model in list(exp_data['results'].keys()):
                        if model not in self.models: del exp_data['results'][model]
        return experiments_dict

    def _subset_reconstruct(self, obj):
        """Reconstruct evaluator state from saved object, filtering by runs and models."""
        print("\n[Subset] Starting subset reconstruction...")
        target_runs = self.runs_id
        print(f"[Subset] target_runs: {target_runs}")
        print(f"[Subset] source obj type: {type(obj)}")

        # Extract source data
        if hasattr(obj, "env_experiments"):
            src_env_experiments = obj.env_experiments
            src_eval_results = getattr(obj, "evaluation_results", {})
            print("[Subset] Using attributes from obj")
        elif isinstance(obj, dict):
            src_env_experiments = obj.get("env_experiments", {})
            src_eval_results = obj.get("evaluation_results", {})
            print("[Subset] Using dict keys from obj")
        else:
            print("[Subset ERROR] obj has neither attributes nor dict keys")
            return False

        try:
            print(f"[Subset] src_env_experiments: {len(src_env_experiments) if hasattr(src_env_experiments, '__len__') else 'N/A'} scenarios")
            print(f"[Subset] src_eval_results: {len(src_eval_results) if hasattr(src_eval_results, '__len__') else 'N/A'} scenarios")
            
            # Filter both using same method
            self.env_experiments = self._filter_models_from_experiments(src_env_experiments, target_runs)
            self.evaluation_results = self._filter_models_from_experiments(src_eval_results, target_runs)

            print(f"[Subset] Reconstructed env_experiments: {list(self.env_experiments.keys())}")
            print(f"[Subset] Reconstructed evaluation_results: {list(self.evaluation_results.keys())}")
            print(f"[Subset] Filtered to models: {self.models}")
            print("[Subset] ✅ Subset reconstruction successful")
            return True

        except Exception as e:
            print(f"[Subset] ❌ Subset Reconstruction Failed: {e}")
            import traceback
            traceback.print_exc()
            return False


    def _resume_from_supersets(self, sub_registry):
        """
        Try to reconstruct this evaluator from any larger-horizon saved evaluator.
        Returns True if successful, False otherwise.
        
        MODIFIED: Iterates horizons sorted by FILE SIZE (largest first) instead of run number.
        """
        target_runs = self.runs_id
        print(f"[Resume-Supersets] target_runs={target_runs}, backups={sub_registry.keys()}")
        
        # ✅ NEW: Build list of (horizon, file_size) and sort by size
        horizon_sizes = []
        for horizon, file_name in sub_registry.items():
            try:
                file_path = Path(self.configs.backup_mgr.backup_registry[self.component][file_name])
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    horizon_sizes.append((horizon, file_size))
                    print(f"[Resume-Supersets] horizon={horizon}, size={file_size:,} bytes")
            except Exception as e:
                print(f"[Resume-Supersets] Could not get size for horizon={horizon}: {e}")
        
        # Sort by file size (largest first) instead of horizon number
        sorted_horizons = [h for h, s in sorted(horizon_sizes, key=lambda x: x[1], reverse=True)]
        print(f"[Resume-Supersets] Trying horizons in size order (largest first): {sorted_horizons}")
        
        # Iterate horizons from largest file to smallest file
        for horizon in sorted_horizons:
            try:
                file_name = sub_registry[horizon]
                
                print(f"\n[Resume-Supersets] ----- Checking horizon={horizon} -----")
                # Only supersets, skip exact match and insufficient horizons
                if horizon == target_runs:
                    print(f"[Resume-Supersets] Skipping {horizon} (equal than target_runs)")
                    continue
            
                if horizon not in sub_registry.keys(): continue
                print(f"[Superset] Superset file: {file_name}")
                print(f"[Superset] Trying horizon={horizon} for target_runs={target_runs}")

                file_path = Path(self.configs.backup_mgr.backup_registry[self.component][file_name])
                obj, loaded = self.configs._load_obj(self, file_path)

                print(f"[Superset] _load_obj returned loaded={loaded}")
                print(f"[Resume-Supersets] Horizon={horizon} loaded, attempting subset reconstruction...")
                if self._subset_reconstruct(obj):
                    print(f"[Resume-Supersets] ✅ Successfully resumed from horizon={horizon}")
                    self.resumed = True
                    return self.resumed
            except Exception as e:
                print(f"❌ Multi-run resume failed: {e}")
        
        self.resumed = False
        self.configs.use_last_backup = False    
        print("[Resume-Supersets] ❌ No valid supersets found for resume")
        return False


    def _get_superset_subregistry(self):
        """
        Parse backup_registry['framework_state'] once and build:
            { run_id: [file_paths] }

        Uses regex to strip trailing '_d+_d+_d+_d+' (qubit allocations)
        from each file name, then matches '<run>_runs' in the cleaned name.
        """
        registry = self.configs.backup_mgr.backup_registry.get(self.component, {})
        # pattern to strip trailing '_d+_d+_d+_d+' before the extension
        pattern = r"\d+_(\(\d+_\d+_\d+_\d+\)_)?"
        sub_registry = {}

        for file_name in registry.keys():
            if "evaluator" not in file_name.lower(): continue
            if self.configs.suffix and (not self.configs.suffix in file_name): continue
            
            # remove qubit allocation tail if present
            _file_name = re.sub(pattern, "", file_name)
            if self.configs.suffix: _file_name = _file_name.replace(f"_{self.configs.suffix}", "")
            if re.sub(pattern, "", self.file_name) == _file_name:
                part_with_runs = re.sub(r"(_\(\d+_\d+_\d+_\d+\))?(_S\d*(_\d*)?T\w*)?\.pkl", "", file_name)
                print(part_with_runs)
                runs = int(part_with_runs.split("_")[-1])
                sub_registry[runs] = file_name

        return sub_registry


    def resume(self):
        if not self.resumed: 
            if self.configs.resume_obj(self): 
                self.resumed = True
                return self.resumed
            if self.configs.use_last_backup:
                print("[Resume] exact failed → Looking for supersets")
                sub_registry = self._get_superset_subregistry()
                return self._resume_from_supersets(sub_registry)
        self.configs.use_last_backup = False
        self.resumed = False
        return self.resumed






    def run_experiments(self, runs=None, attack_type=None, models=None):
        """
        Run experiments for a specific environment type.
        """
        self.update_configs(runs, models, attack_type)

        try:
            print(f"\nSTARTING EXPERIMENTS: {self.configs.attack_type.upper()}")
            attack_category = self.configs.category_map.get(self.configs.attack_type, 'Unknown')
            print(f"Category: {attack_category}")
            print("="*60)

            self.start_time = time.time()

            for i in range(0, self.configs.runs):
                exp_id = i + 1
                # if (self.configs.attack_type in self.env_experiments and exp_id in self.env_experiments[self.configs.attack_type]):
                    # scaled_cap = self.capacity * self.configs.scale
                    # print(f"⏩ SKIPPING EXPERIMENT {exp_id}: ALREADY COMPLETED AND STORED")
                    # self.display_run_results(exp_id, self.env_experiments[self.configs.attack_type], scaled_cap)
                    # continue
                self.run_experiment(exp_no=i, attack_category=attack_category)

            self.total_time = time.time() - self.start_time
            self.save()

            print(f"Total experiment time: {self.total_time:05.1f}s")
            print(f"Experiments completed for {self.configs.attack_type}")
            return self.env_experiments[self.configs.attack_type]

        except Exception as e:
            print(f"❌ Multi-run failed: {e}")
            raise

        finally:
            pass

    def calculate_scenario_performance(self, scenario):
        """
        Calculate overall performance metrics for each scenario.
        """
        if scenario not in self.scenarios_stats: return

        print("\n" + "="*70)
        print(f"DETAILED SCENARIO PERFORMANCE: {scenario.upper()}")
        print("="*70)

        stats = self.scenarios_stats[scenario]
        if stats:
            description = self.configs.test_scenarios.get(str(scenario)).title() 
            print(f"SCENARIO: \t{description.upper()}")
            print("-" * 40)
            
            winner = stats.get('overall_winner', 'N/A')
            total_exps = stats.get('total_experiments', 0)
            winner_metrics = stats.get('winner_avg_metrics', {})
            print(f"Recommended Model: \t{winner} (Won {winner_metrics.get('wins', 0)}/{total_exps} experiments)")
            
            if winner_metrics:
                print(f"\tWinner Avg Gap: \t{winner_metrics.get('avg_gap', 0):05.1f}%")
                print(f"\tWinner Avg Efficiency: \t{winner_metrics.get('avg_efficiency', 0):05.1f}%")

            print("\nOverall Models Performance:")
            # Access the nested dictionary for all models' metrics
            all_metrics = stats.get('all_model_metrics', {})
            
            # Sort models by their true average efficiency for a ranked view
            sorted_models = sorted(
                all_metrics.items(), 
                key=lambda item: item[1].get('avg_efficiency', 0),
                reverse=True
            )

            for model_name, metrics in sorted_models:
                if model_name == 'Oracle': continue
                wins_str = f"(Won {metrics.get('wins', 0)}/{total_exps} experiments)"
                print(f"\t• {model_name:<15}: \t{metrics.get('avg_efficiency', 0):05.1f}% Efficiency \t{wins_str}")
            print("="*70)


    def calculate_scenarios_performance(self):
        """
        Calculate overall performance metrics for each scenario.
        """

        print("\n" + "="*70)
        print("COMPREHENSIVE SCENARIO PERFORMANCE ANALYSIS")
        print("="*70)

        for scenario, stats in self.scenarios_stats.items():
            print(f"SCENARIO: {scenario.upper()}")
            print(f"\t• Total Experiments: {stats['total_experiments']}")

            print(f"\t• Overall Winner: {stats['overall_winner']}")
            print(f"\t• Oracle Avg Reward: {stats['oracle_avg_reward']:07.2f}")

            print(f"\t• Winner Avg Gap: {stats['avg_gap']:07.2f}%")
            print(f"\t• Winner Avg Reward: {stats['avg_reward']:07.2f}")
            print(f"\t• Winner Avg Efficiency: {stats['avg_efficiency']:07.2f}%")
            
            print("\t• Win Counts:")
            for model, model_data in stats['all_model_metrics'].items():
                print(f"\t\t- {model}: {model_data['wins']} wins")
            print("-"*70)

            self.calculate_scenario_performance(scenario)

    def get_scenarios_stats(self, scenario=None):
        """
        Get the comprehensive scenarios statistics.
        """
        if scenario:
            if scenario not in self.scenarios_stats:
                print(f"Scenario '{scenario}' not found in statistics.")
                return {}
            
            return copy.deepcopy(self.scenarios_stats.get(scenario, {}))    
        
        return copy.deepcopy(self.scenarios_stats)
    
    # def calculate_scenario_winner(self, comparison_results, scenario, baseline_model='Oracle', update_results=True):
    #     """
    #     FIXED: Calculate efficiency per experiment, then average.
    #     """
    #     if scenario not in comparison_results: return {}
    #     all_experiments = comparison_results[scenario]
    #     if (not all_experiments) or  (len(all_experiments) == 0): return {}

    #     if scenario not in self.scenarios_stats:
    #         model_totals = {}
    #         scenarios_stats = {}
    #         winner_efficients = {}
    #         total_oracle_reward = 0
    #         exps_no = len(all_experiments)
    #         for exp_data in all_experiments.values():
    #             exp_oracle = exp_data['results'][baseline_model]['final_reward']
    #             for model_name, model_result in exp_data['results'].items():
    #                 if model_name not in model_totals:
    #                     model_totals[model_name] = {'avg_reward':0, 'avg_gap':0, 'efficiency_list':[], 'wins':0, 'avg_efficiency':0, 'reward_list':[], 'creward_list':[]}
                    
    #                 model_reward = model_result.get('final_reward', 0.0)
    #                 model_totals[model_name]['avg_reward'] += model_reward
    #                 model_totals[model_name]['reward_list'].append(model_reward)
    #                 model_totals[model_name]['avg_gap'] += model_result.get('gap', 0)
    #                 model_totals[model_name]['efficiency_list'].append(model_result.get('efficiency', 0.0))
    #                 model_totals[model_name]['creward_list'].extend(model_result['model_results']['reward_list'])

    #             total_oracle_reward = total_oracle_reward + exp_oracle    
    #             model_totals[exp_data.get('winner')]['wins'] = model_totals[exp_data.get('winner')]['wins'] + 1

    #         # Calculate final averages
    #         for model_name, totals in model_totals.items():
    #             avg_gap = totals['avg_gap'] / exps_no if totals['avg_gap'] > 0 else 0.0
    #             avg_reward = totals['avg_reward']/exps_no if totals['avg_reward'] > 0 else 0.0
    #             avg_efficiency = sum(totals['efficiency_list'])/exps_no if totals['efficiency_list'] else 0.0

    #             model_totals[model_name]['avg_gap'] = float(avg_gap)
    #             model_totals[model_name]['avg_reward'] = float(avg_reward)
    #             model_totals[model_name]['avg_efficiency'] = float(avg_efficiency)
                
    #             if model_name == 'Oracle': continue
    #             winner_efficients[model_name] = model_totals[model_name]['avg_efficiency'] 

    #         oracle_avg_reward = total_oracle_reward / exps_no if total_oracle_reward > 0 else float('nan')    
    #         efficiency_winner = max(winner_efficients, key=winner_efficients.get) if winner_efficients else "N/A"
            
    #         scenarios_stats[scenario] = {
    #             'total_experiments': exps_no,
    #             'win_counts': winner_efficients,
    #             'all_model_metrics': model_totals,
    #             'overall_winner': efficiency_winner,
    #             'oracle_avg_reward': float(oracle_avg_reward),
    #             'avg_gap': model_totals[efficiency_winner]['avg_gap'],
    #             'avg_reward': model_totals[efficiency_winner]['avg_reward'],
    #             'winner_avg_metrics': model_totals.get(efficiency_winner, {}),
    #             'avg_efficiency': model_totals[efficiency_winner]['avg_efficiency']
    #         }
    #         print(f"Scenario '{scenario}' evaluation completed.")

    #         if update_results:
    #             self.scenarios_stats[scenario] = scenarios_stats[scenario]
    #             self.evaluation_results[scenario].update({'avg_efficiency_stats':self.scenarios_stats[scenario]})
        
    #     return self.scenarios_stats

    def calculate_scenario_winner(self, comparison_results, scenario, baseline_model='Oracle', update_results=True):
        """
        FIXED: Calculate efficiency per experiment, then average.
        Recalculates winner if None is found in experiment data.
        """
        if scenario not in comparison_results: 
            return {}
        
        all_experiments = comparison_results[scenario]
        if (not all_experiments) or (len(all_experiments) == 0): 
            return {}

        if scenario not in self.scenarios_stats:
            self.scenarios_stats[scenario] = {}
        
        win_counts = {}
        model_totals = {}
        scenarios_stats = {}
        winner_efficients = {}
        total_oracle_reward = 0
        exps_no = len(all_experiments)
        
        # Track how many winners were recalculated
        recalculated_count = 0
        
        for exp_data in all_experiments.values():
            exp_oracle = exp_data['results'][baseline_model]['final_reward']
            
            # === RECALCULATE WINNER IF NONE ===
            winner = exp_data.get('winner')
            if winner is None:
                # Recalculate winner based on final_reward
                max_reward = -float('inf')
                recalculated_winner = None
                
                for model_name, model_result in exp_data['results'].items():
                    if model_name == baseline_model:  # Skip Oracle in winner calculation
                        continue
                    model_reward = model_result.get('final_reward', 0.0)
                    if model_reward > max_reward:
                        max_reward = model_reward
                        recalculated_winner = model_name
                
                winner = recalculated_winner
                exp_data['winner'] = winner  # Update the experiment data
                recalculated_count += 1
                print(f"  ⚠️  Recalculated winner for experiment: {recalculated_winner} (reward: {max_reward:.2f})")
            
            # === ACCUMULATE MODEL STATISTICS ===
            for model_name, model_result in exp_data['results'].items():
                if model_name not in model_totals:
                    model_totals[model_name] = {
                        'avg_reward': 0, 
                        'avg_gap': 0, 
                        'efficiency_list': [], 
                        'wins': 0, 
                        'avg_efficiency': 0, 
                        'reward_list': [], 
                        'creward_list': []
                    }
                
                model_reward = model_result.get('final_reward', 0.0)
                model_totals[model_name]['avg_reward'] += model_reward
                model_totals[model_name]['reward_list'].append(model_reward)
                model_totals[model_name]['avg_gap'] += model_result.get('gap', 0)
                model_totals[model_name]['efficiency_list'].append(model_result.get('efficiency', 0.0))
                model_totals[model_name]['creward_list'].extend(model_result['model_results']['reward_list'])

            total_oracle_reward = total_oracle_reward + exp_oracle
            
            # === INCREMENT WIN COUNT (NOW SAFE) ===
            if winner is not None and winner in model_totals:
                model_totals[winner]['wins'] = model_totals[winner]['wins'] + 1
            else:
                print(f"  ⚠️  Warning: Could not determine valid winner for experiment")

        # Print recalculation summary
        if recalculated_count > 0:
            print(f"  ℹ️  Recalculated {recalculated_count}/{exps_no} experiment winners in scenario '{scenario}'")

        # === CALCULATE FINAL AVERAGES ===
        for model_name, totals in model_totals.items():
            avg_gap = totals['avg_gap'] / exps_no if totals['avg_gap'] > 0 else 0.0
            avg_reward = totals['avg_reward'] / exps_no if totals['avg_reward'] > 0 else 0.0
            avg_efficiency = sum(totals['efficiency_list']) / exps_no if totals['efficiency_list'] else 0.0

            model_totals[model_name]['avg_gap'] = float(avg_gap)
            model_totals[model_name]['avg_reward'] = float(avg_reward)
            model_totals[model_name]['avg_efficiency'] = float(avg_efficiency)
            
            if model_name == baseline_model:  # Skip Oracle
                continue
            winner_efficients[model_name] = model_totals[model_name]['avg_efficiency']
            win_counts[model_name] = model_totals[model_name]['wins']

        oracle_avg_reward = total_oracle_reward / exps_no if total_oracle_reward > 0 else float('nan')
        efficiency_winner = max(winner_efficients, key=winner_efficients.get) if winner_efficients else "N/A"
        
        scenarios_stats[scenario] = {
            'win_counts': win_counts,
            'total_experiments': exps_no,
            'all_model_metrics': model_totals,
            'overall_winner': efficiency_winner,
            'winner_efficients':winner_efficients,
            'oracle_avg_reward': float(oracle_avg_reward),
            'avg_gap': model_totals[efficiency_winner]['avg_gap'] if efficiency_winner in model_totals else 0.0,
            'avg_reward': model_totals[efficiency_winner]['avg_reward'] if efficiency_winner in model_totals else 0.0,
            'winner_avg_metrics': model_totals.get(efficiency_winner, {}),
            'avg_efficiency': model_totals[efficiency_winner]['avg_efficiency'] if efficiency_winner in model_totals else 0.0
        }
        
        print(f"✓ Scenario '{scenario}' evaluation completed.")

        if update_results:
            self.scenarios_stats[scenario] = scenarios_stats[scenario]
            self.evaluation_results[scenario].update({'avg_efficiency_stats': self.scenarios_stats[scenario]})
        
        return self.scenarios_stats


    def calculate_scenarios_winner(self, comparison_results, scenarios=None):
        """
        Wrapper to calculate winner stats for all specified scenarios.
        """
        self.update_configs(scenarios=scenarios)
        
        for scenario in self.configs.test_scenarios.keys():
            if scenario in comparison_results:
                self.calculate_scenario_winner(comparison_results, scenario)
        
        self.evaluation_results.update({'scenarios_results':self.scenarios_stats})
        # print(json.dumps(self.evaluation_results, indent=2, default=str))
        # print(self.evaluation_results.keys())
        self.calculate_scenarios_performance()
        self.generate_key_insights()
        self.save()


    def get_evaluation_results(self, scenario=None, exp_id=-1):
        """
        Get the comprehensive evaluation results, filtered by scenario and/or experiment ID.
        
        Supports:
        - Full scenario results (averaged stats + all experiments)
        - Single experiment (e.g., last run for isolated plotting)
        - Maintains structure for visualization (e.g., peak/last run via exp_id=-1)
        
        Args:
            scenario (str): Target scenario (e.g., 'stochastic', 'none').
            exp_id (int): Specific experiment ID; -1 for last (highest frame) run.
        
        Returns:
            dict: Filtered results with {scenario: {exp_id: data, 'avg_efficiency_stats': stats}}.
        """
        try:
            if scenario is None:
                # Return all scenarios if none specified
                return copy.deepcopy(self.evaluation_results)
            
            if scenario not in self.evaluation_results:
                raise ValueError(f"Scenario '{scenario}' not found in evaluation results.")
            
            scenario_results = copy.deepcopy(self.evaluation_results[scenario])
            if exp_id is None: return scenario_results
            
            # Handle exp_id filtering
            exp_keys = [key for key in scenario_results.keys() if key != 'avg_efficiency_stats']  
            if exp_id not in exp_keys and exp_id > 0:
                raise ValueError(f"Experiment ID '{exp_id}' not found in scenario '{scenario}' results.")
            
            if exp_id < 0: exp_id = exp_keys[-1]
            # Build filtered results for single exp_id
            filtered_results = {scenario: {exp_id: copy.deepcopy(scenario_results[exp_id])}}
            # Recalculate stats for this single experiment (no averaging needed, but for consistency)
            single_stats = self.calculate_scenario_winner(filtered_results, scenario, update_results=False)
            filtered_results[scenario]['avg_efficiency_stats'] = single_stats[scenario]  # Use single-run as "avg"
            # Add scenarios_results for framework compatibility (e.g., plotting)
            filtered_results['scenarios_results'] = single_stats
            
            return filtered_results
        except Exception as e:
            print(f"Error retrieving evaluation results: {e}")

        return {}

    def run_scenario_model_evaluation(self, runs=None, models=None, attack_type=None, threaded=False):
        """
        Wrapper to run comprehensive evaluation for a single scenario.
        """
        # ✅ KEEP: Update configs
        self.update_configs(runs, models, attack_type)

        # ✅ FIX: Get scenario name safely (handles both dict and string)
        scenario_value = self.configs.test_scenarios.get(self.configs.attack_type)
        
        if isinstance(scenario_value, dict):
            scenario_name = self.configs.attack_type.upper()
        elif isinstance(scenario_value, str):
            scenario_name = scenario_value.upper()
        else:
            scenario_name = str(self.configs.attack_type).upper()
        
        print(f"\n\n\nTESTING ENVIRONMENT SCENARIO: {scenario_name}")
        print("="*50)
        
        # ✅ KEEP: The actual execution logic (CRITICAL!)
        if threaded: 
            print("\tRUNNING EXPERIMENTS IN PARALLEL")
            return self.run_experiments_parallel()
        else: 
            return self.run_experiments()  # ✅ THIS WAS MISSING - CRITICAL!


    def generate_key_insights(self):
        """
        Generate key insights from the evaluation results.
        """
        print("KEY INSIGHTS:")
        # Performance retention analysis if both stochastic and baseline exist
        exp_ran = 0
        models_length = 0
        if 'stochastic' in self.scenarios_stats and self.scenarios_stats['stochastic'] and 'none' in self.scenarios_stats and self.scenarios_stats['none']:

            baseline_stats = self.scenarios_stats['none']['avg_efficiency_stats'] if 'avg_efficiency_stats' in self.scenarios_stats['none'] else self.scenarios_stats['none']
            stoch_stats = self.scenarios_stats['stochastic']['avg_efficiency_stats'] if 'avg_efficiency_stats' in self.scenarios_stats['stochastic'] else self.scenarios_stats['stochastic']

            exp_ran = stoch_stats['total_experiments']
            models_length = len(self.configs.models)

            best_model = stoch_stats['overall_winner']
            stoch_performance = stoch_stats['avg_reward']
            baseline_performance = baseline_stats['avg_reward']
            
            # Calculate realistic performance retention
            perf_retention = (stoch_performance / baseline_performance * 100) if baseline_performance > 0 else 100
            
            print(f"Best Performing Model Analysis ({best_model}):")
            print(f"\t• Stochastic Performance:    \t{stoch_performance:.3f}")
            print(f"\t• Baseline Performance:      \t{baseline_performance:.3f}")
            print(f"\t• Performance Retention:     \t{perf_retention:05.1f}%")
            
            if perf_retention   > 95: 
                print(f"\tEXCELLENT:          \tMinimal performance loss under realistic conditions")
            elif perf_retention > 85: 
                print(f"\tGOOD:               \tAcceptable performance under stochastic conditions")
            elif perf_retention > 75: 
                print(f"\tMODERATE:           \tSome degradation under realistic network conditions")
            else:                     
                print(f"\tNEEDS IMPROVEMENT:  \tSignificant performance loss in stochastic environment")

        elif 'stochastic' in self.scenarios_stats and self.scenarios_stats['stochastic']:
            # Stochastic-only analysis
            exp_ran = self.scenarios_stats['stochastic']['total_experiments']
            models_length = len(self.configs.models)
            
            stoch_stats = self.scenarios_stats['stochastic']
            print(f"Stochastic Environment Analysis:")
            print(f"\t• Best Model:         \t{stoch_stats['overall_winner']}")
            print(f"\t• Oracle Efficiency:  \t{stoch_stats['avg_efficiency']:05.1f}%")
            print(f"\t• Performance under realistic quantum network conditions validated")

        # Statistical significance and ranking
        print(f"Statistical Analysis:")
        print(f"\t• Total models evaluated:     \t{models_length}")
        print(f"\t• Experiments per environment:\t{exp_ran}")
        print(f"\t• Quantum network simulation: \tComprehensive stochastic modeling")
        
        print("="*70)


    def run_scenarios_model_evaluation(self, runs=None, models=None, attack_type=None, scenarios=None, cal_winner=True, parallel=False):
        """
        Run comprehensive model evaluation in realistic quantum network conditions.

        This method provides thorough analysis of:
        - Model performance under natural stochastic conditions
        - Oracle efficiency and convergence analysis
        - Statistical significance and ranking
        - Baseline comparison for validation
        """
        print("="*70)
        print("SCENARIOS MODEL EVALUATION")
        print("="*70)
        print("Testing algorithm performance against:")
        print("\t• Stochastic:  \tNatural quantum decoherence and network failures")
        print("\t• Baseline:    \tOptimal conditions for validation")
        print("="*70)
        self.update_configs(runs, models, attack_type, scenarios)

        print(f"Models to Test:             \t{', '.join(self.configs.models)}")

        # ✅ NEW:
        if isinstance(list(self.configs.test_scenarios.values())[0], dict):
            # test_scenarios values are dicts - use keys instead
            scenarios_str = ', '.join(self.configs.test_scenarios.keys())
        else:
            # test_scenarios values are strings - use values
            scenarios_str = ', '.join(self.configs.test_scenarios.values())

        print(f"Experiments per Scenario:   \t{self.configs.runs}")
        print("="*70)

        # Run experiments for all specified scenarios
        self.evaluation_results = {}
        for attack_type in self.configs.test_scenarios.keys():
            self.configs.attack_type = attack_type
            experiment_results = self.run_scenario_model_evaluation(threaded=parallel)
            self.evaluation_results[attack_type] = copy.deepcopy(experiment_results)
        
        if cal_winner: self.calculate_scenarios_winner(self.evaluation_results)
        return self.evaluation_results

    def print_summary(self, attack_type=None, baseline_model='Oracle'):
        """Print comprehensive results summary."""
        self.update_configs(attack_type=attack_type)

        if attack_type: target_type = attack_type
        else: target_type = self.configs.attack_type

        if target_type not in self.env_experiments:
            print(f"No results found for attack_type='{target_type}'")
            return

        experiments = self.env_experiments[target_type]

        print("="*60)
        print(f"COMPREHENSIVE SUMMARY: {target_type.upper()}")
        print("="*60)

        # Get all algorithms from first experiment
        first_exp = next(iter(experiments.values()))
        for alg in first_exp['results'].keys():
            if alg == baseline_model: continue
            rewards = [exp['results'][alg]['final_reward'] for exp in experiments.values()]
            gaps = [exp['results'][alg]['gap']  for exp in experiments.values()]

            print(f"{alg}:")
            print(f"\tRewards:  \t{np.mean(rewards):05.1f} ± {np.std(rewards):05.1f}")
            print(f"\tAvg Gap:  \t{np.mean(gaps):05.1f}%")
            print(f"\tWins:     \t{sum(1 for exp in experiments.values() if exp['winner'] == alg)}/{len(experiments)}")

        # Oracle efficiency analysis
        oracle_rewards = [exp['results'][baseline_model]['final_reward'] for exp in experiments.values()]
        print(f"Oracle Performance: \t{np.mean(oracle_rewards):05.1f} ± {np.std(oracle_rewards):05.1f}")

        # Best performing algorithm
        winner_counts = {}
        for exp in experiments.values():
            winner = exp['winner']
            winner_counts[winner] = winner_counts.get(winner, 0) + 1

        best_algorithm = max(winner_counts, key=winner_counts.get)
        print(f"Best Overall Algorithm: \t{best_algorithm} ({winner_counts[best_algorithm]}/{len(experiments)} wins)")
        
    def cleanup(self, verbose=False, cooldown_seconds=1):
        """
        Clean up multi-run evaluator resources.

        This is critical for long-running batch experiments that create
        many evaluators sequentially.

        Args:
            verbose: If True, print detailed cleanup information
        """
        try:
            cleanup_items = []
            try: 
                if cooldown_seconds > 0: time.sleep(cooldown_seconds) 
            except: pass
            
            # 1. Deep clean env_experiments (nested dictionaries with results)
            if hasattr(self, 'env_experiments'):
                for attack_type, experiments in self.env_experiments.items():
                    if isinstance(experiments, dict):
                        for exp_id, exp_data in experiments.items():
                            if isinstance(exp_data, dict):
                                exp_data.clear()
                        experiments.clear()
                    cleanup_items.append(f"env_experiments[{attack_type}]")
                self.env_experiments.clear()
            
            # 2. Clear all_results (list of result dictionaries)
            if hasattr(self, 'all_results'):
                if isinstance(self.all_results, list):
                    self.all_results.clear()
                cleanup_items.append("all_results")
            
            # 3. Clear gap_analysis (algorithm performance tracking)
            if hasattr(self, 'gap_analysis'):
                if isinstance(self.gap_analysis, dict):
                    for alg_name, gaps in self.gap_analysis.items():
                        if isinstance(gaps, list):
                            gaps.clear()
                    self.gap_analysis.clear()
                cleanup_items.append("gap_analysis")
            
            # 4. Clear evaluation results (from comprehensive evaluation)
            if hasattr(self, 'evaluation_results'):
                if isinstance(self.evaluation_results, dict):
                    self.evaluation_results.clear()
                cleanup_items.append("evaluation_results")
            
            # 5. Clear scenario statistics
            if hasattr(self, 'scenarios_stats'):
                if isinstance(self.scenarios_stats, dict):
                    self.scenarios_stats.clear()
                cleanup_items.append("scenarios_stats")
            
            # 6. Reset timing information
            if hasattr(self, 'start_time'):
                self.start_time = None
            if hasattr(self, 'total_time'):
                self.total_time = 0
            
            # 7. PyTorch CUDA cleanup (in case models were cached)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    cleanup_items.append("CUDA cache")
            except ImportError:
                pass
            
            # 8. Force garbage collection
            if gc:
                collected = gc.collect()
                cleanup_items.append(f"GC:{collected} objects")
            
            # Mandatory cooldown
            cleanup_items.append(f"cooldown:{cooldown_seconds}s")
            try: 
                if cooldown_seconds > 0: time.sleep(cooldown_seconds) 
            except: pass
            if verbose:
                print(f"✓ MultiRunEvaluator cleaned: \t{', '.join(cleanup_items)}")
        except Exception as e:
            print(f"\t[WARNING] Cleanup failed: {e}")
            import traceback
            traceback.print_exc()
    
    def __del__(self):
        """Destructor to ensure cleanup on deletion."""
        try:
            self.cleanup(verbose=False)
        except Exception as e:
            print(f"Error during MultiRunEvaluator cleanup: {e}")
    

    def update_configs(self, runs=None, models=None, scenarios=None, attack_type=None, intensity=None, attack_rate=None):
        self.configs.update_configs(runs, models, scenarios, attack_rate, intensity, attack_rate)
        if self.configs.attack_type not in self.env_experiments:
            self.env_experiments[self.configs.attack_type] = {}
        
    # Usage functions
    def test_stochastic_environment(self, runs=None, models=None, scenarios=None, attack_type='stochastic', cal_winner=True, parellel=False):
        """
        Main function to test models in stochastic quantum network conditions.
        
        Provides comprehensive model evaluation for research purposes.
        """
        self.update_configs(runs, models, attack_type, scenarios)
        
        # if len(self.evaluation_results) == 0:
        # Run the comprehensive evaluation
        self.run_scenarios_model_evaluation(cal_winner=cal_winner, parallel=parellel)

        return self.evaluation_results


    def test_individual_environment(self, attack_type="stochastic", threaded=False):
        """Test a single environment type."""
        self.update_configs(attack_type=attack_type)

        if threaded:
            # self.run_threaded_experiments()
            return self.run_experiments_parallel()
        else:
            self.run_experiments()
        
        self.print_summary()
        return self

    def display_run_results(self, exp_id, experiment_results, scaled_capacity):
        """
        Pretty-print model results for a completed experiment.
        Matches the Runner's formatting style exactly.
        """
        results = experiment_results[exp_id].get('results', {})
        winner  = experiment_results[exp_id].get('winner', 'NA')
        gap     = results.get(winner, {}).get('gap', 100)

        print("\n\t📊 EXPERIMENT RESULTS SUMMARY")
        print("\t" + "="*120)

        for alg_name, r in results.items():
            if alg_name == 'Oracle':
                continue

            final_reward  = r.get('final_reward', 0.0)
            efficiency    = r.get('efficiency', 0.0)
            fa            = r.get('failed_attempts', {})

            retries       = fa.get('total', 0)
            failed        = fa.get('failed', 0)
            under_thr     = fa.get('under_threshold', 0)
            threshold     = fa.get('threshold', 0)

            print(
                f"\tEXP {exp_id} {alg_name.upper():<20}: "
                f"Reward={final_reward:07.2f}, "
                f"Efficiency={efficiency:05.1f}% "
                f"[Retries={retries}, Failed={failed}, < Threshold={under_thr}, "
                f"SCapacity={scaled_capacity}, Threshold={threshold}]"
            )

        print("\t" + "="*120)

        # Winner line (same style as runner)
        print(
            f"\t-->🏆 EXP{exp_id} Winner:{winner:<20}"
            f"(Gap:{gap:05.1f}%) "
            f"[Env:{self.configs.environment}, "
            f"Attack:{self.configs.attack_strategy} X Rate:{self.configs.attack_rate}, "
            f"Frames:{self.frames_count}, "
            f"SCapacity={scaled_capacity}, "
            f"Alloc={self.configs.allocator}]"
        )
        print()


    def run_experiment(self, exp_no, offset=100, models=None, attack_category="Stochastic", attack_rate=0.25):
        self.update_configs(models=models, attack_rate=attack_rate)

        self.frames_count = self.base_frames + (exp_no * self.frame_step)
        self.capacity = self.base_frames if self.configs.base_capacity else self.frames_count
        exp_id = exp_no + 1

        print("-" * 100)
        print(f"EXPERIMENT {exp_id}: {self.frames_count} frames  <>  SCALED-CAPACITY: "
            f"{self.capacity*self.configs.scale} frames (CAPACITY:{self.capacity} X SCALE:{self.configs.scale})")
        print("-" * 100)

        # Configure attack scenario
        self.configs.set_attack_strategy(
            attack_rate=self.configs.attack_rate,
            attack_type=self.configs.attack_type,
            attack_intensity=self.configs.attack_intensity
        )

        # ✅ Allocator (routing layer)
        route_stats = {}
        if hasattr(self.configs, "allocator") and self.configs.allocator is not None:
            qubit_cap = tuple(self.configs.allocator.allocate(
                timestep=exp_no,
                route_stats=route_stats
            ))
        else: 
            qubit_cap = (8, 10, 8, 9)
        
        # ✅ STORE qubit_cap at SCENARIO LEVEL - Don't overwrite!
        if self.configs.attack_type not in self.runner_qubit_caps:
            self.runner_qubit_caps[self.configs.attack_type] = {}
        
        # Store this experiment's qubit allocation
        self.runner_qubit_caps[self.configs.attack_type][str(exp_id)] = str(qubit_cap)
        
        print(f"🔧 Allocated qubits for {self.configs.attack_type.upper()} Exp {exp_id}: {qubit_cap}")

        # Create runner
        runner = QuantumExperimentRunner(
            id = exp_id,
            config=self.configs,
            capacity=self.capacity,
            frames_count=self.frames_count,
            enable_progress=self.enable_progress,
            attack_type=self.configs.attack_type,
            base_seed=self.base_seed + exp_no * offset,
            attack_intensity=self.configs.attack_intensity,
        )

        try:
            # Skip if already completed (resume-safe)
            if (self.configs.attack_type in self.env_experiments and exp_id in self.env_experiments[self.configs.attack_type]):
                print(f"⏩ SKIPPING EXPERIMENT {exp_id}: ALREADY COMPLETED AND STORED")
                self.display_run_results(exp_id, self.env_experiments[self.configs.attack_type], self.capacity * self.configs.scale)
                return self.env_experiments[self.configs.attack_type][exp_id]
            else:
                experiment_results = runner.run_experiment(
                    frames_count=self.frames_count,
                    models=self.configs.models,
                    qubit_cap=qubit_cap
                )
                experiment_results["exp_id"] = exp_id
                experiment_results["attack_category"] = attack_category
                if self.configs.attack_type not in self.env_experiments.keys():
                     self.env_experiments[self.configs.attack_type] = {}
                self.env_experiments[self.configs.attack_type][exp_id] = experiment_results
                print(f"✓ Experiment {exp_id} completed successfully.")
        except Exception as e:
            print(f"❌ Experiment {exp_id} failed: {e}")
            raise

        finally:
            self.configs.use_last_backup = runner.resumed
            del runner
            if gc: gc.collect()
            self.save()

        return self.env_experiments[self.configs.attack_type][exp_id]

    
    def run_threaded_experiment(self, exp_no, offset=100, models=None, attack_category="Stochastic", attack_rate=0.25, max_workers=2):
        self.update_configs(models=models, attack_rate=attack_rate)

        self.frames_count = self.base_frames + (exp_no * self.frame_step)
        self.capacity = self.base_frames if self.configs.base_capacity else self.frames_count
        exp_id = exp_no + 1

        
        print("\n\n", "-" * 100)
        print(f"EXPERIMENT {exp_id}: {self.frames_count} frames  <>  SCALED-CAPACITY: {self.capacity*self.configs.scale} frames")
        print("-" * 100)

        self.configs.set_attack_strategy(
            attack_rate=self.configs.attack_rate,
            attack_type=self.configs.attack_type,
            attack_intensity=self.configs.attack_intensity
        )

        route_stats = {}
        if hasattr(self.configs, 'allocator') and self.configs.allocator is not None:
            qubit_cap = tuple(self.configs.allocator.allocate(route_stats=route_stats, timestep=exp_no))
        else: qubit_cap = (8, 10, 8, 9)

        runner = QuantumExperimentRunner(
            id= exp_id,
            config=self.configs,
            capacity=self.capacity,
            frames_count=self.frames_count,
            enable_progress=self.enable_progress,
            attack_type=self.configs.attack_type,
            base_seed=self.base_seed + exp_no * offset,
            attack_intensity=self.configs.attack_intensity,
        )

        try:
            # Skip if already completed (resume-safe)
            if (self.configs.attack_type in self.env_experiments and exp_id in self.env_experiments[self.configs.attack_type]):
                print(f"⏩ SKIPPING EXPERIMENT {exp_id}: ALREADY COMPLETED AND STORED")
                scaled_cap = self.capacity * self.configs.scale
                self.display_run_results(exp_id, self.env_experiments[self.configs.attack_type], scaled_cap)
                return self.env_experiments[self.configs.attack_type][exp_id]
            else:
                #  USE PARALLEL VERSION HERE
                experiment_results = runner.run_experiment_parallel(
                    frames_count=self.frames_count,
                    models=self.configs.models,
                    max_workers=max_workers,  # Models run in parallel within this experiment
                    qubit_cap=qubit_cap
                )
                
                experiment_results['exp_id'] = exp_id
                experiment_results['attack_category'] = attack_category
                if self.configs.attack_type not in self.env_experiments.keys():
                     self.env_experiments[self.configs.attack_type] = {}
                self.env_experiments[self.configs.attack_type][exp_id] = experiment_results
                # print(f"Experiment {exp_id} completed successfully")
        except Exception as e:
            print(f"Experiment {exp_id} failed: {e}")
            raise
        finally:
            print(exp_id, ": ", runner.key_attrs['qubit_capacities'])
            self.runner_qubit_caps.update({self.configs.attack_type:{exp_id:runner.key_attrs['qubit_capacities']}})
            del runner
            if gc: gc.collect()
            self.save()
        return self.env_experiments[self.configs.attack_type][exp_id]


    def run_threaded_experiments(self, runs=None, attack_type=None, models=None):
        """
        Run experiments for a specific environment type.

        Args:
            attack_type: Override default attack type
            exps_num: Number of frame count experiments (default: 3)
            algorithms: List of algorithms to test
        """
        self.update_configs(runs, models, attack_type)

        print(f"\nSTARTING EXPERIMENTS: {self.configs.attack_type.upper()}")
        attack_category = self.configs.category_map.get(self.configs.attack_type, 'Unknown')
        print(f"Category: {attack_category}")
        print("="*60)

        self.start_time = time.time()
        for i in range(0, self.configs.runs):
            self.run_threaded_experiment(exp_no=i, attack_category=attack_category)
        self.total_time = time.time() - self.start_time
        self.save()

        print(f"Total experiment time: {self.total_time:05.1f}s")
        print(f"Experiments completed for {self.configs.attack_type}")
        return self.env_experiments[self.configs.attack_type]


    def run_experiments_parallel(self, runs=None, attack_type=None, models=None, max_workers=1):
        """
        Run experiments in parallel at the multi-run level.
        
        Args:
            runs: Number of experiments
            attack_type: Override default attack type
            models: List of algorithms to test
            max_workers: Number of parallel experiments
        """
        self.update_configs(runs, models, attack_type)

        print(f"\nSTARTING PARALLEL MULTI-RUN EXPERIMENTS: {self.configs.attack_type.upper()}")
        attack_category = self.configs.category_map.get(self.configs.attack_type, 'Unknown')
        print(f"Category: {attack_category}")
        print(f"\tRunning {self.configs.runs} experiments with {max_workers} parallel workers")
        print("="*60)

        self.start_time = time.time()
        
        # Execute experiments in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all experiments
            future_to_exp = {
                executor.submit(self.run_threaded_experiment, exp_no=i, attack_category=attack_category): i 
                for i in range(self.configs.runs)
            }
            
            # Process as they complete
            for future in as_completed(future_to_exp):
                exp_no = future_to_exp[future]
                exp_id = exp_no + 1
                try:
                    future.result()
                    # print(f"✅ Experiment {exp_id} completed (frames: {self.base_frames + exp_no * self.frame_step})")
                except Exception as e:
                    print(f"❌ Experiment {exp_id} failed: {e}")
                finally:
                    self.save()
        self.total_time = time.time() - self.start_time

        print(f"\n\t⏱️  Total multi-run time: {self.total_time:05.1f}s")
        print(f"\tExperiments completed for {self.configs.attack_type}")
        return self.env_experiments[self.configs.attack_type]
    
    def __repr__(self):
        return self.__class__.__name__