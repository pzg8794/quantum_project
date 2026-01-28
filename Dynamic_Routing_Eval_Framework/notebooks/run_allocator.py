"""
AllocatorRunner: OOP Wrapper for Isolated Allocator Execution
Each allocator gets its own instance with clean state
"""
import os
import sys
import gc
import weakref
import warnings
import importlib
import torch
import networkx as nx
import numpy as np
import itertools
import traceback
from pathlib import Path

warnings.filterwarnings('ignore')


class AllocatorRunner:
    """
    Isolated runner for a single allocator.
    Each instance manages its own state and cleanup.
    """

    def __init__(self, allocator_type, physics_models, framework_config, 
                 scales, runs, models, test_scenarios):
        """Initialize runner for specific allocator"""
        self.allocator_type = allocator_type
        self.physics_models = physics_models
        self.framework_config = framework_config
        self.scales = scales
        self.runs = runs
        self.models = models
        self.test_scenarios = test_scenarios

        # State tracking
        self.evaluator = None
        self.allocator_obj = None
        self.custom_config = None
        self.run_count = 0

        print(f"\n{'='*70}")
        print(f"🎯 Initialized AllocatorRunner for: {allocator_type}")
        print('='*70)

    def create_allocator(self, physics_model):
        """Create allocator with paper-specific config."""
        config = self.framework_config.get(physics_model, self.framework_config['default'])
        
        num_routes  = config['num_paths']         # ✅ Gets 8 for paper2
        seed        = config.get('seed', 42)
        epsilon     = config.get('epsilon', 1.0)
        total_qubits= config.get('total_qubits', 35)
        exploration = config.get('exploration_bonus', 2.0)
        min_qubits  = config.get('min_qubits_per_route', 2)
        
        if self.allocator_type == 'Random':
            return RandomQubitAllocator(
                total_qubits, 
                num_routes,           # ✅ Passes 8
                epsilon=epsilon, 
                seed=seed,
                testbed='paper2'       # ✅ Enable paper2 logic
            )
        elif self.allocator_type == 'Dynamic':
            return DynamicQubitAllocator(
                total_qubits, 
                num_routes,           # ✅ Passes 8
                min_qubits_per_route=min_qubits, 
                exploration_bonus=exploration,
                testbed='paper2'       # ✅ Enable paper2 logic
            )
        elif self.allocator_type == 'ThompsonSampling':
            return ThompsonSamplingAllocator(
                total_qubits=total_qubits, 
                num_routes=num_routes, # ✅ Passes 8
                min_qubits_per_route=min_qubits,
                testbed='paper2'       # ✅ Enable paper2 logic
            )
        return QubitAllocator(
            total_qubits=total_qubits, 
            num_routes=num_routes,     # ✅ Passes 8
            testbed='paper2'           # ✅ Enable paper2 logic
        )


    def cleanup_evaluator(self, verbose=True):
        """Aggressive cleanup of evaluator resources"""
        cleanup_log = []

        if self.evaluator is not None:
            try:
                # 1. Stop backup manager
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
                # 2. Clear environment
                if hasattr(self.evaluator, 'configs') and hasattr(self.evaluator.configs, 'environment'):
                    env = self.evaluator.configs.environment

                    if hasattr(env, 'topology'):
                        if hasattr(env.topology, 'clear'):
                            env.topology.clear()
                        del env.topology

                    if hasattr(env, 'paths'):
                        env.paths = []

                    cleanup_log.append("✅ Environment cleared")
            except Exception as e:
                cleanup_log.append(f"⚠️ Environment cleanup: {e}")

            try:
                # 3. Break circular references
                if hasattr(self.evaluator, 'configs'):
                    if hasattr(self.evaluator.configs, 'backup_mgr'):
                        self.evaluator.configs.backup_mgr = None
                    if hasattr(self.evaluator.configs, 'environment'):
                        self.evaluator.configs.environment = None
                    self.evaluator.configs = None

                cleanup_log.append("✅ Circular refs broken")
            except Exception as e:
                cleanup_log.append(f"⚠️ Reference cleanup: {e}")

        # 4. Torch cleanup
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            cleanup_log.append("✅ Torch CUDA cleared")
        except:
            pass

        # 5. Garbage collection (3 passes)
        collected = [gc.collect() for _ in range(3)]
        cleanup_log.append(f"✅ GC: {collected}")

        # 6. Delete references
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

    def run_single_experiment(self, physics_model, scale, experiment_num, 
                            physics_params, current_frames, frame_step):
        """Run single experiment with full cleanup"""
        try:
            # Import evaluator locally
            from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
            from daqr.config.experiment_config import ExperimentConfiguration

            self.run_count += 1
            print(f"\n{'='*70}")
            print(f"RUN {self.run_count} | Scale: {scale} | Exp: {experiment_num}")
            print('='*70)

            # Create config
            self.custom_config = ExperimentConfiguration(
                runs=experiment_num,
                allocator=self.allocator_obj,
                scenarios=self.test_scenarios,
                use_last_backup=False,
                physics_params=physics_params,
                attack_intensity=0.25,
                base_capacity=False,
                overwrite=False,
                models=self.models,
                scale=scale,
                suffix=physics_model.replace("default", "")
            )

            # Create evaluator
            self.evaluator = MultiRunEvaluator(
                configs=self.custom_config,
                base_frames=current_frames,
                frame_step=frame_step
            )

            self.evaluator.configs.set_log_name(
                base_frames=current_frames,
                frame_step=frame_step
            )

            self.evaluator.configs.backup_mgr.init_logging_redirect(self.evaluator)

            # Run evaluation
            print("⚙ Running evaluation...")
            comparison_results = self.evaluator.test_stochastic_environment(
                cal_winner=True,
                parellel=False
            )

            self.evaluator.calculate_scenarios_performance()
            print("✅ Evaluation completed!")

            return True

        except Exception as e:
            print(f"❌ Error in experiment: {e}")
            traceback.print_exc()
            return False

        finally:
            # Always cleanup
            if self.evaluator is not None:
                try:
                    self.evaluator.configs.backup_mgr.stop_logging_redirect()
                except:
                    pass

            self.cleanup_evaluator(verbose=False)

            # Extra sleep for OS
            import time
            time.sleep(1)

    def run(self, get_physics_params_func):
        """
        Main execution method

        Args:
            get_physics_params_func: Function to get physics parameters
        """
        print(f"\n{'='*70}")
        print(f"🚀 STARTING ALLOCATOR: {self.allocator_type}")
        print('='*70)

        try:
            for physics_model in self.physics_models:
                print(f"\n📊 Physics Model: {physics_model}")

                # Create allocator for this physics model
                self.allocator_obj = self.create_allocator(physics_model)
                num_paths = self.framework_config[physics_model]["num_paths"]
                print(f"✓ Allocator: {type(self.allocator_obj).__name__} ({num_paths} paths)")

                # Get initial allocation
                qubit_cap = self.allocator_obj.allocate(timestep=0, route_stats={}, verbose=False)

                # Get physics params
                frame_step = self.framework_config['frame_step']
                base_seed = self.framework_config['env_attrs']['base_seed']
                current_frames = (
                    self.framework_config['base_frames'] 
                    if self.framework_config['test_mode'] 
                    else self.framework_config['prod_frames']
                )
                current_experiments = (
                    self.framework_config['exp_num'] 
                    if self.framework_config['test_mode'] 
                    else self.framework_config['prod_experiments']
                )

                physics_params = get_physics_params_func(
                    physics_model=physics_model,
                    current_frames=current_frames,
                    base_seed=base_seed,
                    qubit_cap=qubit_cap,
                )

                # Run experiments
                for scale in self.scales:
                    for exp_num in self.runs:
                        success = self.run_single_experiment(
                            physics_model=physics_model,
                            scale=scale,
                            experiment_num=exp_num,
                            physics_params=physics_params,
                            current_frames=current_frames,
                            frame_step=frame_step
                        )

                        if not success:
                            print(f"⚠️ Experiment failed, continuing...")

                # Cleanup allocator
                self.allocator_obj = None
                gc.collect()

        except Exception as e:
            print(f"❌ Fatal error in {self.allocator_type}: {e}")
            traceback.print_exc()

        finally:
            # Final cleanup
            print(f"\n🧹 Final cleanup for {self.allocator_type}")
            self.cleanup_evaluator(verbose=False)
            self.allocator_obj = None
            gc.collect()

        print(f"\n{'='*70}")
        print(f"✅ COMPLETED: {self.allocator_type}")
        print('='*70)

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup_evaluator(verbose=False)
        except:
            pass


# ============================================================================
# USAGE IN MAIN SCRIPT
# ============================================================================

def run_all_allocators(ALLOCATORS, PHYSICS_MODELS, FRAMEWORK_CONFIG, 
                       SCALES, RUNS, models, test_scenarios, get_physics_params_func):
    """
    Run all allocators using isolated AllocatorRunner instances
    """
    print("\n" + "="*70)
    print("🎯 QUANTUM ROUTING TESTBED - ALLOCATOR EVALUATION")
    print("="*70)
    print(f"Allocators: {ALLOCATORS}")
    print(f"Physics Models: {PHYSICS_MODELS}")
    print(f"Scales: {SCALES}")
    print(f"Runs: {RUNS}")
    print("="*70)

    for allocator_type in ALLOCATORS:
        # Create isolated runner for this allocator
        runner = AllocatorRunner(
            allocator_type=allocator_type,
            physics_models=PHYSICS_MODELS,
            framework_config=FRAMEWORK_CONFIG,
            scales=SCALES,
            runs=RUNS,
            models=models,
            test_scenarios=test_scenarios
        )

        # Run this allocator
        runner.run(get_physics_params_func)

        # Explicit cleanup
        del runner
        gc.collect()

        # Sleep between allocators
        import time
        time.sleep(2)

    print("\n" + "="*70)
    print("✅ ALL ALLOCATORS COMPLETE!")
    print("="*70)


# ============================================================================
# REPLACE YOUR MAIN LOOP WITH THIS
# ============================================================================
"""
if __name__ == "__main__":
    # Your existing config
    ALLOCATORS = ['Default', 'Random', 'Dynamic', 'ThompsonSampling']
    PHYSICS_MODELS = ['paper12', 'default']
    SCALES = [1.0]
    RUNS = [1]

    # Run all allocators
    run_all_allocators(
        ALLOCATORS=ALLOCATORS,
        PHYSICS_MODELS=PHYSICS_MODELS,
        FRAMEWORK_CONFIG=FRAMEWORK_CONFIG,
        SCALES=SCALES,
        RUNS=RUNS,
        models=models,
        test_scenarios=test_scenarios,
        get_physics_params_func=get_physics_params  # Your existing function
    )
"""