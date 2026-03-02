import os
import sys
import gc
import subprocess
import torch
import warnings
import networkx as nx
import numpy as np
import itertools
import traceback
import time

from pathlib import Path
from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.core.qubit_allocator import (
    QubitAllocator, 
    RandomQubitAllocator, 
    DynamicQubitAllocator, 
    ThompsonSamplingAllocator
)

warnings.filterwarnings('ignore')


class AllocatorRunner:
    """
    ✅ FIXED: Isolated runner for a single allocator with full resource cleanup.
    
    Now includes:
    - Proper testbed parameter passing
    - Consistent parameter handling for all allocators
    - Config validation
    - Capacity-agnostic design
    """

    def __init__(self, allocator_type, physics_models, framework_config, scales, runs, models, test_scenarios, config=None):
        """Initialize runner for specific allocator."""
        self.runs = runs
        self.run_count = 0
        self.scales = scales
        self.models = models
        self.evaluator = None
        self.allocator_obj = None
        self.custom_config = config
        self.allocator_type = allocator_type
        self.physics_models = physics_models
        self.test_scenarios = test_scenarios
        self.framework_config = framework_config

        print(f"\n{'='*70}")
        print(f"🎯 AllocatorRunner initialized: {allocator_type}")
        print('='*70)

    def _state_aggregation_enabled(self) -> bool:
        """
        Default behavior: ON.

        Toggle OFF via:
          - framework_config['aggregate_state'] = False, or
          - env var DAQR_AGGREGATE_STATE in {0,false,no,off}
        """
        cfg_flag = bool(self.framework_config.get("aggregate_state", True))
        env_val = os.getenv("DAQR_AGGREGATE_STATE", "1").strip().lower()
        env_flag = env_val not in {"0", "false", "no", "off"}
        return cfg_flag and env_flag

    def _plots_enabled(self) -> bool:
        """
        Default behavior: ON.

        Toggle OFF via:
          - framework_config['enable_plots'] = False, or
          - env var DAQR_ENABLE_PLOTS in {0,false,no,off}
        """
        cfg_flag = bool(self.framework_config.get("enable_plots", True))
        env_val = os.getenv("DAQR_ENABLE_PLOTS", "1").strip().lower()
        env_flag = env_val not in {"0", "false", "no", "off"}
        return cfg_flag and env_flag

    def _run_robustness_plots(self, comparison_results):
        """
        Generate the same robustness plots used by the older pipeline notebooks,
        but from inside the AllocatorRunner so notebooks don't need custom cells.
        """
        try:
            import importlib
            from daqr.evaluation import visualizer as visualizer_mod
            importlib.reload(visualizer_mod)
            from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer

            print("=" * 70)
            print("ROBUSTNESS ANALYSIS")
            print("=" * 70)

            allocator = self.allocator_obj
            custom_config = self.custom_config
            evaluator = self.evaluator
            test_scenarios = self.test_scenarios or {}

            viz = QuantumEvaluatorVisualizer(
                comparison_results,
                allocator=allocator,
                config=custom_config,
                framework_config=self.framework_config,
                output_dir=self.framework_config.get("plots_dir", "results"),
            )

            # Full comparison plot (all scenarios together)
            try:
                viz.plot_stochastic_vs_adversarial_comparison(eval_results=comparison_results)
            except Exception as e:
                print(f"⚠️ Plotting (stochastic vs adversarial) failed: {e}")

            # Plot each non-baseline scenario vs baseline
            for scenario in list(test_scenarios.keys()):
                if scenario.lower() in {"none", "baseline", "no_attack"}:
                    continue
                print(f"\n📊 Generating plots for scenario: {scenario.upper()}")
                try:
                    if evaluator is not None:
                        evaluator.calculate_scenario_performance(scenario=scenario)
                except Exception as e:
                    print(f"⚠️ Scenario performance calc failed for '{scenario}': {e}")

                try:
                    viz.plot_scenarios_comparison(eval_results=comparison_results, scenario=scenario)
                except Exception as e:
                    print(f"⚠️ Scenario plot failed for '{scenario}': {e}")

            print("\n✓ All scenario plots generated!")

            # Print stochastic metrics summary if available
            try:
                stoch_data = viz.get_viz_data("stochastic_data")
                if stoch_data and "averaged" in stoch_data:
                    stoch_results = stoch_data["averaged"]
                    winner = stoch_results.get("winner", "N/A")

                    print("\n" + "=" * 70)
                    print("STOCHASTIC PERFORMANCE METRICS")
                    print("=" * 70)

                    for alg in (self.models or []):
                        if alg not in stoch_results.get("results", {}):
                            continue
                        model_data = stoch_results["results"][alg]
                        stoch_reward = model_data.get("final_reward", 0)
                        efficiency = model_data.get("efficiency", 0)
                        gap = model_data.get("gap", float("inf"))

                        print(f"\n{alg}:")
                        print(f"  • Stochastic Performance: {stoch_reward:.3f}")
                        print(f"  • Oracle Efficiency: {efficiency:.1f}%")
                        print(f"  • Oracle Gap: {gap:.1f}%")

                        if efficiency > 90:
                            classification = "EXCELLENT"
                        elif efficiency > 80:
                            classification = "GOOD"
                        elif efficiency > 70:
                            classification = "MODERATE"
                        else:
                            classification = "NEEDS IMPROVEMENT"
                        print(f"  • Classification: {classification}")
                        if alg == winner:
                            print("  ★ WINNER ★")
                else:
                    print("⚠ No stochastic averaged results available")
            except Exception as e:
                print(f"⚠️ Metrics summary failed: {e}")

        except Exception as e:
            print(f"⚠️ Robustness plotting failed (continuing): {e}")

    def _aggregate_state_dirs(self) -> bool:
        """
        Aggregate local state day directories into the current run day folder
        BEFORE we build/resume evaluators, to stabilize scanning/resume.
        """
        if not self._state_aggregation_enabled():
            print("🧩 State aggregation: disabled")
            return False

        project_root = Path(__file__).resolve().parents[2]  # Dynamic_Routing_Eval_Framework/
        tool_path = project_root / "tools" / "state" / "aggregate_state_dirs.py"
        config_dir = project_root / "daqr" / "config"
        framework_state_root = config_dir / "framework_state"
        model_state_root = config_dir / "model_state"

        target = None
        if self.custom_config is not None:
            target = getattr(self.custom_config, "day_str", None)
        if not target:
            target = "today"

        print(f"🧩 State aggregation: enabled (target={target})")

        if not tool_path.exists():
            print(f"⚠️ State aggregation tool missing: {tool_path}")
            return False

        try:
            cmd = [
                sys.executable,
                str(tool_path),
                "--config-dir",
                str(config_dir),
                "--framework-state-root",
                str(framework_state_root),
                "--model-state-root",
                str(model_state_root),
                "--target",
                str(target),
            ]
            subprocess.run(cmd, cwd=str(project_root), check=True)
        except Exception as e:
            print(f"⚠️ State aggregation failed (continuing): {e}")
            return False

        # Refresh any already-instantiated backup manager registry in memory
        # so resuming in the same process sees the aggregated view.
        try:
            if self.custom_config is not None and hasattr(self.custom_config, "backup_mgr"):
                self.custom_config.backup_mgr.build_registry(
                    force=True, expected_keys=getattr(self.custom_config, "expected_keys", None)
                )
        except Exception as e:
            print(f"⚠️ Registry refresh failed (continuing): {e}")

        return True

    def create_allocator(self, physics_model):
        """
        ✅ FIXED: Create allocator with proper paper-specific config and testbed support.
        
        Now extracts and validates ALL required parameters including testbed.
        """
        # Get config for this physics model
        config = self.framework_config.get(physics_model, self.framework_config.get('default', {}))
        if self.custom_config is not None: self.custom_config.testbed_config = config
        
        # ✅ FIX 1: Extract ALL parameters with validation
        seed = config.get('seed', 42)
        num_paths = config.get('num_paths', 4)
        total_qubits = config.get('total_qubits', 35)
        initial_state = config.get('initial_state', None)
        min_qubits = config.get('min_qubits_per_route', 2)
        if initial_state is not None: total_qubits = config.get('state_total_qubits', {})[initial_state]

        
        # ✅ FIX 2: Extract testbed parameter (CRITICAL for Paper2)
        testbed = config.get('testbed', 'default')
        
        # Allocator-specific parameters
        epsilon = config.get('epsilon', 1.0)
        epsilon_decay = config.get('epsilon_decay', 1.0)
        min_epsilon = config.get('min_epsilon', 0.1)
        exploration = config.get('exploration_bonus', 2.0)
        alpha_prior = config.get('alpha_prior', 1.0)
        beta_prior = config.get('beta_prior', 1.0)
        
        # ✅ FIX 3: Log configuration being used
        print(f"\n📋 Allocator Config:")
        print(f"   Type: {self.allocator_type}")
        print(f"   Testbed: {testbed}")
        print(f"   Paths: {num_paths}")
        print(f"   Total Qubits: {total_qubits}")
        print(f"   Min per route: {min_qubits}")
        print(f"   Seed: {seed}")
        
        # ✅ FIX 4: Create allocators with ALL required parameters
        try:
            if self.allocator_type == 'Random':
                allocator = RandomQubitAllocator(
                    total_qubits=total_qubits,
                    num_paths=num_paths,  # ✅ Use num_paths consistently
                    min_qubits_per_route=min_qubits,  # ✅ ADDED
                    epsilon=epsilon,
                    epsilon_decay=epsilon_decay,  # ✅ ADDED
                    min_epsilon=min_epsilon,  # ✅ ADDED
                    seed=seed,
                    testbed=testbed,  # ✅ CRITICAL FIX
                    testbed_config=config
                )
                print(f"   Epsilon: {epsilon}, Decay: {epsilon_decay}")
            
            elif self.allocator_type == 'Dynamic':
                allocator = DynamicQubitAllocator(
                    total_qubits=total_qubits,
                    num_paths=num_paths,  # ✅ Use num_paths consistently
                    min_qubits_per_route=min_qubits,
                    exploration_bonus=exploration,
                    seed=seed,  # ✅ ADDED
                    testbed=testbed,  # ✅ CRITICAL FIX
                    testbed_config=config
                )
                print(f"   Exploration bonus: {exploration}")
            
            elif self.allocator_type == 'ThompsonSampling':
                allocator = ThompsonSamplingAllocator(
                    total_qubits=total_qubits,
                    num_paths=num_paths,  # ✅ Use num_paths consistently
                    min_qubits_per_route=min_qubits,
                    alpha_prior=alpha_prior,  # ✅ ADDED
                    beta_prior=beta_prior,  # ✅ ADDED
                    seed=seed,  # ✅ ADDED
                    testbed=testbed,  # ✅ CRITICAL FIX
                    testbed_config=config
                )
                print(f"   Priors: α={alpha_prior}, β={beta_prior}")
            
            else:  # Default Fixed allocator
                allocator = QubitAllocator(
                    total_qubits=total_qubits,
                    num_paths=num_paths,  # ✅ Use num_paths consistently
                    min_qubits_per_route=min_qubits,
                    testbed=testbed,  # ✅ CRITICAL FIX
                    testbed_config=config
                )
            
            # ✅ FIX 5: Validate allocator was created correctly
            test_allocation = allocator.allocate(timestep=0, route_stats={}, verbose=False)
            
            if len(test_allocation) != num_paths:
                raise ValueError(
                    f"Allocator created with wrong num_paths: "
                    f"expected {num_paths}, got {len(test_allocation)}"
                )
            
            if sum(test_allocation) != total_qubits:
                raise ValueError(
                    f"Allocator total qubits mismatch: "
                    f"expected {total_qubits}, got {sum(test_allocation)}"
                )
            
            print(f"✅ Allocator created: {test_allocation}")
            return allocator
        
        except Exception as e:
            print(f"❌ Error creating allocator: {e}")
            traceback.print_exc()
            raise

    def cleanup_evaluator(self, verbose=True):
        """Aggressive cleanup of evaluator resources."""
        cleanup_log = []

        if self.evaluator is not None:
            try:
                if hasattr(self.evaluator, 'configs') and hasattr(self.evaluator.configs, 'backup_mgr'):
                    backup_mgr = self.evaluator.configs.backup_mgr
                    if hasattr(backup_mgr, 'stop_logging_redirect'):
                        backup_mgr.stop_logging_redirect()
                    if hasattr(backup_mgr, 'backup_registry'):
                        backup_mgr.backup_registry.clear()
                cleanup_log.append("✅ Backup manager cleaned")
            except Exception as e:
                cleanup_log.append(f"⚠️ Backup cleanup: {e}")

            try:
                if hasattr(self.evaluator, 'configs') and hasattr(self.evaluator.configs, 'environment'):
                    env = self.evaluator.configs.environment
                    if hasattr(env, 'topology') and hasattr(env.topology, 'clear'):
                        env.topology.clear()
                        del env.topology
                    if hasattr(env, 'paths'):
                        env.paths = []
                cleanup_log.append("✅ Environment cleared")
            except Exception as e:
                cleanup_log.append(f"⚠️ Environment cleanup: {e}")

            try:
                if hasattr(self.evaluator, 'configs'):
                    if hasattr(self.evaluator.configs, 'backup_mgr'):
                        self.evaluator.configs.backup_mgr = None
                    if hasattr(self.evaluator.configs, 'environment'):
                        self.evaluator.configs.environment = None
                    self.evaluator.configs = None
                cleanup_log.append("✅ Circular refs broken")
            except Exception as e:
                cleanup_log.append(f"⚠️ Reference cleanup: {e}")

        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            cleanup_log.append("✅ Torch CUDA cleared")
        except:
            pass

        collected = [gc.collect() for _ in range(3)]
        cleanup_log.append(f"✅ GC: {sum(collected)} objects")

        self.evaluator = None
        self.custom_config = None

        if verbose:
            print("\n" + "="*70)
            print("🧹 CLEANUP COMPLETE")
            print("="*70)
            for log in cleanup_log:
                print(log)
            print("="*70)

        return True

    def run_single_evaluator(self, physics_model, scale, experiment_num, physics_params, current_frames, frame_step):
        """Run single experiment with full cleanup."""
        try:
            self.run_count += 1
            print(f"\n{'='*70}")
            print(f"RUN {self.run_count} | Scale: {scale} | Exp: {experiment_num}")
            print('='*70)
            
            if self.custom_config:
                self.custom_config.physics_params = physics_params
                self.custom_config.suffix = physics_model
                self.custom_config.runs = experiment_num
                self.custom_config.scale = scale
                self.custom_config.allocator = self.allocator_obj  # ← FIX!
            
            self.evaluator = MultiRunEvaluator(configs=self.custom_config, base_frames=current_frames, frame_step=frame_step)
            self.evaluator.configs.set_log_name(base_frames=current_frames, frame_step=frame_step)
            self.evaluator.configs.backup_mgr.init_logging_redirect(self.evaluator)

            print("⚙ Running evaluation...")
            comparison_results = self.evaluator.test_stochastic_environment(cal_winner=True, parellel=False)
            self.evaluator.calculate_scenarios_performance()
            print("✅ Evaluation completed!")

            if self._plots_enabled():
                self._run_robustness_plots(comparison_results)

            return True

        except Exception as e:
            print(f"❌ Error in experiment: {e}")
            traceback.print_exc()
            return False

        finally:
            if self.evaluator is not None:
                try:
                    self.evaluator.configs.backup_mgr.stop_logging_redirect()
                except:
                    pass
            self.cleanup_evaluator(verbose=False)
            time.sleep(1)

    def run(self, get_physics_params_func):
        """Main execution method."""
        print(f"\n{'='*70}")
        print(f"🚀 STARTING ALLOCATOR: {self.allocator_type}")
        print('='*70)
        
        try:
            # Consolidate day_* state directories up-front to stabilize resume/scanning.
            self._aggregate_state_dirs()

            for physics_model in self.physics_models:
                print(f"\n📊 Physics Model: {physics_model}")

                # ✅ Create allocator with proper config
                self.allocator_obj = self.create_allocator(physics_model)
                
                # ✅ Get configuration
                config = self.framework_config.get(physics_model, self.framework_config.get('default', {}))
                num_paths = config.get('num_paths', 4)
                
                print(f"✓ Allocator: {type(self.allocator_obj).__name__} ({num_paths} paths)")

                # Get experiment parameters
                frame_step = self.framework_config.get('frame_step', 100)
                current_frames = self.framework_config.get('base_frames', 1400)
                base_seed = self.framework_config.get('env_attrs', {}).get('base_seed', 42)
                
                # ✅ Get initial allocation (validates allocator works)
                qubit_cap = self.allocator_obj.allocate(
                    timestep=0, 
                    route_stats={}, 
                    verbose=False
                )
                print(f"   Initial allocation: {qubit_cap}")
                
                # Get physics parameters
                physics_params = get_physics_params_func(
                    physics_model=physics_model,
                    current_frames=current_frames,
                    base_seed=base_seed,
                    qubit_cap=qubit_cap
                )

                # Run experiments for all scales and runs
                for exp_num in self.runs:
                    for scale in self.scales:
                        success = self.run_single_evaluator(
                            physics_model=physics_model,
                            scale=scale,
                            experiment_num=exp_num,
                            physics_params=physics_params,
                            current_frames=current_frames,
                            frame_step=frame_step
                        )
                        if not success:
                            print(f"⚠️ Experiment failed, continuing...")

                # Cleanup after physics model
                self.allocator_obj = None
                gc.collect()

        except Exception as e:
            print(f"❌ Fatal error in {self.allocator_type}: {e}")
            traceback.print_exc()

        finally:
            print(f"\n🧹 Final cleanup for {self.allocator_type}")
            self.cleanup_evaluator(verbose=False)
            self.allocator_obj = None
            gc.collect()

            print(f"\n{'='*70}")
            print(f"✅ COMPLETED: {self.allocator_type}")
            print('='*70)

    def __del__(self):
        """Destructor ensures cleanup."""
        try:
            self.cleanup_evaluator(verbose=False)
        except:
            pass
