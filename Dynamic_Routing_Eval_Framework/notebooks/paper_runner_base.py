"""
Base Runner Class for Paper-Specific Evaluations
"""
import os
import sys
import gc
import subprocess
import warnings
import importlib
import torch
import networkx as nx
import numpy as np
import itertools
import traceback
from pathlib import Path
from abc import ABC, abstractmethod

warnings.filterwarnings("ignore")


class PaperRunner(ABC):
    """Base class for running paper-specific experiments"""

    def __init__(self, testbed_name: str, test_mode: bool = True):
        self.testbed_name = testbed_name
        self.test_mode = test_mode
        self.setup_environment()
        self.load_modules()
        self.configure()

    def setup_environment(self):
        """Setup paths and environment"""
        curdir = os.getcwd()
        print(f"Current working directory: {curdir.split('/')[-1]}")

        try:
            import google.colab
            from google.colab import drive
            drive.mount('/content/drive')
            project_dir = '/content/drive/MyDrive/GA-Work/hybrid_variable_framework/DynamicRoutingEvalFramework'
            os.chdir(project_dir)
            print("Running in Google Colab")
            project_code_dir = os.path.join(project_dir, 'src')
            sys.path.insert(0, project_code_dir)
        except ImportError:
            print("Running locally (not in Colab)")

        PARENT_DIR = os.path.abspath("..")
        if PARENT_DIR not in sys.path:
            sys.path.insert(0, PARENT_DIR)
        print(f"Now working from: {os.getcwd().split('/')[-1]}")

    def load_modules(self):
        """Import and reload all necessary modules"""
        from daqr.core import attack_strategy
        from daqr.config import experiment_config, gd_backup_manager, local_backup_manager
        from daqr.core import network_environment, qubit_allocator
        from daqr.algorithms import neural_bandits, predictive_bandits, base_bandit
        from daqr.evaluation import multi_run_evaluator, visualizer, experiment_runner

        # Reload modules
        for module in [experiment_config, network_environment, qubit_allocator, attack_strategy,
                      base_bandit, neural_bandits, predictive_bandits, experiment_runner,
                      multi_run_evaluator, visualizer]:
            importlib.reload(module)

        # Import classes
        from daqr.evaluation.multi_run_evaluator import MultiRunEvaluator
        from daqr.config.experiment_config import ExperimentConfiguration
        from daqr.core.qubit_allocator import (QubitAllocator, RandomQubitAllocator, 
                                               DynamicQubitAllocator, ThompsonSamplingAllocator)
        from daqr.core.topology_generator import (Paper2TopologyGenerator, Paper7ASTopologyGenerator,
                                                  Paper12WaxmanTopologyGenerator)
        from daqr.core.quantum_physics import (FusionNoiseModel, FiberLossNoiseModel, 
                                              CascadedFidelityCalculator, FusionFidelityCalculator,
                                              QuARCRewardFunction, MemoryNoiseModel,
                                              FullPaper2FidelityCalculator, Paper2RewardFunction,
                                              Paper7RewardFunction, Paper12RetryFidelityCalculator)

        # Store for later use
        self.MultiRunEvaluator = MultiRunEvaluator
        self.ExperimentConfiguration = ExperimentConfiguration
        self.QubitAllocator = QubitAllocator
        self.RandomQubitAllocator = RandomQubitAllocator
        self.DynamicQubitAllocator = DynamicQubitAllocator
        self.ThompsonSamplingAllocator = ThompsonSamplingAllocator

        # Store topology generators
        self.Paper2TopologyGenerator = Paper2TopologyGenerator
        self.Paper7ASTopologyGenerator = Paper7ASTopologyGenerator
        self.Paper12WaxmanTopologyGenerator = Paper12WaxmanTopologyGenerator

        # Store physics classes
        self.FusionNoiseModel = FusionNoiseModel
        self.FiberLossNoiseModel = FiberLossNoiseModel
        self.CascadedFidelityCalculator = CascadedFidelityCalculator
        self.FusionFidelityCalculator = FusionFidelityCalculator
        self.QuARCRewardFunction = QuARCRewardFunction
        self.MemoryNoiseModel = MemoryNoiseModel
        self.FullPaper2FidelityCalculator = FullPaper2FidelityCalculator
        self.Paper2RewardFunction = Paper2RewardFunction
        self.Paper7RewardFunction = Paper7RewardFunction
        self.Paper12RetryFidelityCalculator = Paper12RetryFidelityCalculator

        print("All modules loaded successfully!")

    @abstractmethod
    def configure(self):
        """Configure paper-specific parameters - must be implemented by subclass"""
        pass

    @abstractmethod
    def get_physics_params(self, seed, qubit_cap):
        """Get paper-specific physics parameters - must be implemented by subclass"""
        pass

    def create_allocator(self, allocator_type: str):
        """Create allocator for this paper"""
        config = self.config

        if allocator_type == 'Random':
            return self.RandomQubitAllocator(
                total_qubits=config['total_qubits'],
                num_routes=config['num_paths'],
                epsilon=config.get('epsilon', 1.0),
                seed=config.get('seed', 42),
                testbed=self.testbed_name
            )
        elif allocator_type == 'Dynamic':
            return self.DynamicQubitAllocator(
                total_qubits=config['total_qubits'],
                num_routes=config['num_paths'],
                min_qubits_per_route=config.get('min_qubits_per_route', 2),
                exploration_bonus=config.get('exploration_bonus', 2.0),
                testbed=self.testbed_name
            )
        elif allocator_type == 'ThompsonSampling':
            return self.ThompsonSamplingAllocator(
                total_qubits=config['total_qubits'],
                num_routes=config['num_paths'],
                min_qubits_per_route=config.get('min_qubits_per_route', 2),
                testbed=self.testbed_name
            )
        else:  # Default
            return self.QubitAllocator(
                total_qubits=config['total_qubits'],
                num_routes=config['num_paths'],
                testbed=self.testbed_name
            )

    def deep_cleanup(self):
        """Aggressive memory cleanup"""
        to_clear = ['oracle', 'gneuralucb', 'expneuralucb', 'cpursuit_neuralucb',
                   'icpursuit_neuralucb', 'evaluator', 'results']

        for name in to_clear:
            if name in globals():
                obj = globals().get(name, None)
                try:
                    if hasattr(obj, 'cleanup'):
                        obj.cleanup(verbose=False)
                except:
                    pass
                globals().pop(name, None)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        gc.collect()
        torch.set_default_dtype(torch.float32)
        print("Deep cleanup complete - memory cleared")

    def run(self, allocators=None, scales=None, runs=None):
        """Run experiments for this paper"""
        if allocators is None:
            allocators = ['Random', 'Dynamic', 'ThompsonSampling', 'Default']
        if scales is None:
            scales = [1.0]
        if runs is None:
            runs = [3]

        print("=" * 70)
        print(f"RUNNING {self.testbed_name.upper()} TESTBED")
        print("=" * 70)
        print(f"Allocators: {allocators}")
        print(f"Scales: {scales}")
        print(f"Runs: {runs}")
        print("=" * 70)

        for allocator_type in allocators:
            self.deep_cleanup()

            print(f"\n{'='*70}")
            print(f"ALLOCATOR: {allocator_type}")
            print('='*70)

            # Create allocator
            allocator = self.create_allocator(allocator_type)
            print(f"Created allocator: {allocator.__class__.__name__}")

            # Get initial allocation
            qubit_cap = allocator.allocate(timestep=0, route_stats={}, verbose=False)

            # Get physics params
            physics_params = self.get_physics_params(
                seed=self.base_seed,
                qubit_cap=qubit_cap
            )

            # Create config
            custom_config = self.ExperimentConfiguration(
                runs=self.current_experiments,
                allocator=allocator,
                scenarios=self.test_scenarios,
                use_last_backup=False,
                physics_params=physics_params,
                attack_intensity=self.attack_intensity,
                base_capacity=False,
                overwrite=False,
                models=self.models,
                scale=0,
                suffix=self.testbed_name
            )

            # Run experiments
            for scale in scales:
                custom_config.scale = scale

                for run_count in runs:
                    print(f"\nScale: {scale}, Runs: {run_count}")

                    try:
                        evaluator = self.MultiRunEvaluator(
                            configs=custom_config,
                            base_frames=self.current_frames,
                            frame_step=self.frame_step
                        )

                        evaluator.configs.set_log_name(
                            base_frames=self.current_frames,
                            frame_step=self.frame_step
                        )

                        evaluator.configs.backup_mgr.init_logging_redirect(evaluator)

                        print("Running evaluation...")
                        comparison_results = evaluator.test_stochastic_environment(
                            calc_winner=True,
                            parellel=False
                        )

                        evaluator.calculate_scenarios_performance()
                        print(f"✅ Evaluation completed for {allocator_type}!")

                    except Exception as e:
                        print(f"❌ Error in evaluation: {e}")
                        traceback.print_exc()

                    finally:
                        if 'evaluator' in locals():
                            try:
                                evaluator.configs.backup_mgr.load_new_entries()
                                evaluator.configs.backup_mgr.stop_logging_redirect()
                            except:
                                pass

                        # Cleanup
                        self.deep_cleanup()

            print(f"✅ Completed all runs for {allocator_type}")

        print(f"\n{'='*70}")
        print(f"✅ ALL EXPERIMENTS COMPLETE FOR {self.testbed_name.upper()}!")
        print('='*70)
