from daqr.core.attack_strategy             import NoAttack, RandomAttack, MarkovAttack, AdaptiveAttack, OnlineAdaptiveAttack
from daqr.core.network_environment         import AdversarialQuantumEnvironment, StochasticQuantumEnvironment, QuantumEnvironment
from daqr.algorithms.predictive_bandits    import iCEXP4, iCEpochGreedy, iCEpsilonGreedy, iCKernelUCB, iCThompsonSampling
from daqr.algorithms.predictive_bandits    import CEXP4, CEpochGreedy, CEpsilonGreedy, CKernelUCB, CThompsonSampling
from daqr.algorithms.predictive_bandits    import Oracle, GNeuralUCB, EXPUCB, EXPNeuralUCB, LinUCB, CEXPNeuralUCB 
from daqr.algorithms.predictive_bandits    import CPursuitNeuralUCB, CPursuit, iCPursuit, QuantumModel, NeuralUCB
from daqr.algorithms.predictive_bandits    import UCB, RandomAlg, TS, LinTS, iCPursuitNeuralUCB, NeuralTS
from daqr.core.qubit_allocator             import *

import networkx as nx
import numpy as np
import itertools
import  copy, os, re
import  pathlib
import  pickle
import  shutil, random
from pathlib import Path
from datetime import datetime
from .local_backup_manager import LocalBackupManager


class ExperimentConfiguration:
    """
    Configuration holder for quantum experiments.
    """
    def __init__(self, runs=1, physics_params={}, seed_offset=100, env_type="stochastic", attack_type="n/a", suffix=None, attack_intensity=1.0, attack_rate=0.25, models=None, scenarios=None, allocator=None, base_seed=12345, scale=2, base_capacity=True, overwrite=False, resume=True, use_last_backup=True, verbose=False, testbed_id=None, testbed_config={}):
        
        self.allocator = allocator if allocator else QubitAllocator()  # Default to fixed

        # =============================================================================
        # MODEL NAME COLLECTIONS FOR TESTING
        # =============================================================================
        self.suffix = suffix
        self.resumed = resume
        self.verbose = verbose
        self.base_model = None
        self._env_params = None
        self.environment = None
        self.overwrite = overwrite
        self.testbed_id = testbed_id
        self.seed_offset = seed_offset
        self.testbed_config = testbed_config
        self.physics_params = physics_params
        if not self.suffix and self.testbed_id: self.suffix = ""
        if self.testbed_id: self.suffix+="_"+f"{self.testbed_id}"
        self.dir = Path(os.path.dirname(os.path.abspath(__file__)))
        
        self.runs               = runs
        self.scale              = scale
        self.env_type           = env_type
        self.base_seed          = base_seed
        self.attack_rate        = attack_rate
        self.base_capacity      = base_capacity
        self.day_str            = f"day_{datetime.now().strftime('%Y%m%d')}"

        self.attack_mapping     = {}
        self.environ_mapping    = {}
        self.attack_strategy    = None
        self.attack_type        = attack_type.lower()
        self.attack_intensity   = attack_intensity
        
        self.st = ""
        self.log_name = ""
        self.random_runtime_qubits = (18, 9, 6, 2)
        self.is_random_alloc    =   False
        self.eval_file_name = ""

        # Single unified manager - handles everything
        self.backup_mgr = LocalBackupManager(date_str=self.day_str, config_dir=self.dir, verbose=self.verbose)

        self.category_map = {
            'none': 'Baseline (No Attacks)',
            'markov': 'Structured (Markov Chain Based)',
            'adaptive': 'Adaptive (Reactive Strategic)',
            'random': 'Stochastic (Natural Random Failures)',
            'stochastic': 'Stochastic (Natural Random Failures)', 
            'onlineadaptive': 'Online Adaptive (Real-time Strategic)'
        }


        self.models = models if models else ["EXPNeuralUCB", 'GNeuralUCB', 'CPursuitNeuralUCB', 'iCPursuitNeuralUCB', 'Oracle']
        self.test_scenarios = scenarios if scenarios else {'stochastic': 'Stochastic Environment (Natural Network Conditions)', 'none': 'Baseline (Optimal Conditions)'}


        self.thresholds = {
                'EXPNeuralUCB': {'stochastic': 0.628, 'adversarial': 0.598},
                'CPursuitNeuralUCB': {'stochastic': 0.634, 'adversarial': 0.614},
                'GNeuralUCB': {'stochastic': 0.582, 'adversarial': 0.509},  # Added; higher stochastic for grouping
                'iCPursuitNeuralUCB': {'stochastic': 0.712, 'adversarial': 0.689}
            }

        # Core Quantum Models (Original Research Models)
        self.NEURAL_MODELS = [
            'Oracle',
            'GNeuralUCB', 
            # 'EXPUCB',
            'EXPNeuralUCB',
            # 'LinUCB',
            # 'CEXPNeuralUCB',
            # 'CPursuit', 
            'CPursuitNeuralUCB',
            'iCPursuitNeuralUCB'
        ]

        # Contextual Multi-Armed Bandit Models (CMAB)
        self.CONTEXTUAL_MODELS = [
            'CEpsilonGreedy',
            'CEXP4',
            'CPursuit', 
            'CEpochGreedy',
            'CThompsonSampling',
            'CKernelUCB'
        ]

        # Informed Contextual Multi-Armed Bandit Models (iCMAB with ARIMA)
        self.INFORMED_CONTEXTUAL_MODELS = [
            'iCEpsilonGreedy',
            'iCEXP4', 
            'iCPursuit',
            'iCEpochGreedy',
            'iCThompsonSampling',
            # 'iCKernelUCB'
        ]

        # Custom/Hybrid Models (Research Extensions)
        self.CUSTOM_MODELS = [
            'CEXPNeuralUCB',  # Hybrid of CMAB + Neural UCB approach
            'LinUCB'
        ]

        # =============================================================================
        # COMPREHENSIVE MODEL GROUPS
        # =============================================================================

        # All CMAB-based models (Standard + Informed)
        self.ALL_CMAB_MODELS = self.CONTEXTUAL_MODELS + self.INFORMED_CONTEXTUAL_MODELS

        # All models for comprehensive testing
        self.ALL_QUANTUM_MODELS = self.NEURAL_MODELS + self.CONTEXTUAL_MODELS + self.INFORMED_CONTEXTUAL_MODELS + self.CUSTOM_MODELS

        # Step-wise models (for step-wise runner)
        self.STEP_WISE_MODELS = self.CONTEXTUAL_MODELS + self.INFORMED_CONTEXTUAL_MODELS + ['LinUCB']

        # Batch models (for batch runner)
        self.BATCH_MODELS = ['Oracle', 'GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB', 'CEXPNeuralUCB']

        # Models with prediction capabilities
        self.PREDICTIVE_MODELS = self.INFORMED_CONTEXTUAL_MODELS + ['EXPNeuralUCB', 'CEXPNeuralUCB']

        # =============================================================================
        # TESTING PRESETS
        # =============================================================================

        # Quick test subset (representative models)
        self.QUICK_TEST_MODELS = [
            'Oracle', 
            'EXPNeuralUCB',
            'CEpsilonGreedy', 
            'iCEpsilonGreedy'
        ]

        # Performance comparison set
        self.PERFORMANCE_COMPARISON_MODELS = [
            'Oracle',
            'GNeuralUCB',
            'EXPNeuralUCB', 
            'CEXPNeuralUCB',
            'CEpsilonGreedy',
            'CEXP4',
            'iCEpsilonGreedy',
            'iCEXP4'
        ]

        # Research models for paper/publication
        self.RESEARCH_MODELS = [
            'Oracle',
            'EXPNeuralUCB',
            'CEXPNeuralUCB', 
            'iCEpsilonGreedy',
            'iCEXP4',
            'iCKernelUCB'      # <<< FIX: was written as 'iC' 'KernelUCB' (implicit concat)
        ]

        self.algorithm_configs = {
            'Quantum': {
                'model_class': QuantumModel,     'seed_offset': seed_offset * 1, 'kwargs': {'mode': 'base'}, 'runner_type': 'step-wise'},
            'Oracle': {
                'model_class': Oracle,           'seed_offset': seed_offset * 2, 'kwargs': {'mode': 'base'}, 'runner_type': 'step-wise'},
            'NeuralUCB': {
                'model_class': NeuralUCB,        'seed_offset': seed_offset * 22,'kwargs': {'mode': 'neural', 'beta': 1.0, 'lamb': 1,
                'hidden_size': 128, 'lr': 1e-4, 'reg': 0.000625},
                'runner_type': 'batch'},
            'GNeuralUCB': {
                'model_class': GNeuralUCB,       'seed_offset': seed_offset * 3, 'kwargs': {'mode': 'neural', 'beta': 1.0}, 'runner_type': 'batch'},
            'EXPUCB': {
                'model_class': EXPUCB,           'seed_offset': seed_offset * 4, 'kwargs': {'mode': 'exp3', 'gamma_factor': 0.1, 'eta_factor': 0.005, 'beta':1.0},'runner_type': 'batch'},
            'EXPNeuralUCB': {
                'model_class': EXPNeuralUCB,     'seed_offset': seed_offset * 5, 'kwargs': {'mode': 'hybrid', 'gamma_factor': 0.01, 'eta_factor': 0.05, 'beta': 1.0},'runner_type': 'batch'},
            'CPursuitNeuralUCB': {
                'model_class': CPursuitNeuralUCB,'seed_offset': seed_offset * 6, 'kwargs': {'mode': 'neural', 'beta': 1.0}, 'runner_type': 'batch'},
            'iCPursuitNeuralUCB': {
                'model_class':iCPursuitNeuralUCB,'seed_offset': seed_offset * 7, 'kwargs': {'mode': 'neural', 'beta': 1.0, 'gamma_factor': 0.1,'eta_factor' : 0.005, 'obs': None}, 'runner_type': 'batch'},
            'CEpsilonGreedy': {
                'model_class': CEpsilonGreedy,   'seed_offset': seed_offset * 8, 'kwargs': {'mode': 'hybrid'}, 'runner_type':  'step-wise'},
            'CEXP4': {
                'model_class': CEXP4,            'seed_offset': seed_offset * 9, 'kwargs': {'mode': 'hybrid'}, 'runner_type':  'step-wise'},
            'CPursuit': {
                'model_class': CPursuit,         'seed_offset': seed_offset * 10,'kwargs': {'mode': 'hybrid'}, 'runner_type':  'step-wise'},
            'CEpochGreedy': {
                'model_class': CEpochGreedy,     'seed_offset': seed_offset * 11,'kwargs': {'mode': 'hybrid'}, 'runner_type': 'step-wise'},
            'CThompsonSampling': {
                'model_class': CThompsonSampling,'seed_offset': seed_offset * 12,'kwargs': {'mode': 'hybrid'}, 'runner_type': 'step-wise'},
            'CKernelUCB': {
                'model_class': CKernelUCB,       'seed_offset': seed_offset * 13,'kwargs': {'mode': 'hybrid'}, 'runner_type': 'step-wise'},
            'iCEpsilonGreedy': {
                'model_class': iCEpsilonGreedy,  'seed_offset': seed_offset * 14,'kwargs': {'mode': 'hybrid','n_experts': 4}, 'runner_type':  'step-wise'},
            'iCEXP4': {
                'model_class': iCEXP4,           'seed_offset': seed_offset * 15,'kwargs': {'mode': 'hybrid','n_experts': 4}, 'runner_type':  'step-wise'},
            'iCPursuit': {
                'model_class': iCPursuit,        'seed_offset': seed_offset * 16,'kwargs': {'mode': 'hybrid','n_experts': 4}, 'runner_type':  'step-wise'},
            'iCEpochGreedy': {
                'model_class': iCEpochGreedy,    'seed_offset': seed_offset * 17,'kwargs': {'mode': 'hybrid','n_experts': 4}, 'runner_type': 'step-wise'},
            'iCThompsonSampling': {
                'model_class':iCThompsonSampling,'seed_offset': seed_offset * 18,'kwargs': {'mode': 'hybrid','n_experts': 4}, 'runner_type': 'step-wise'},
            'iCKernelUCB': {
                'model_class': iCKernelUCB,      'seed_offset': seed_offset * 19,'kwargs': {'mode': 'hybrid','eta': 1.0}, 'runner_type':  'step-wise'},
            'LinUCB': {
                'model_class': LinUCB,           'seed_offset': seed_offset * 20,'kwargs': {'mode': 'neural', 'K':4, 'd':2, 'beta': 1.0}, 'runner_type': 'step-wise'},
            'CEXPNeuralUCB': {
                'model_class': CEXPNeuralUCB,    'seed_offset': seed_offset * 21,'kwargs': {'mode': 'neural', 'beta': 1.0}, 'runner_type': 'batch'},
        }

        self.PAPER_CONFIGS = {
            2: {
                "name": "Paper2_UCB_2023",
                "n_arms": 8,
                "total_frames": 1400,
                "noise_mode": "depolarizing",
                # Model-only parameters (passed into Paper2UCBBandit)
                "model_params": {
                    "n_nodes": 15,
                    "fidelity_threshold": 0.582,
                    "synchronized_swapping": True
                }
            },

            5: {
                "name": "Paper5_Feedback_2025",
                "n_arms": 10,
                "total_frames": 2000,
                "model_params": {
                    "feedback_type": "combined"
                }
            },

            7: {
                "name": "Paper7QBGP2024",
                "narms": 15,
                "totalframes": 2000,
                "modelparams": {
                    "k": 5,
                    "n_qisps": 3,
                    "networkscale": "large"
                }
            },

            8: {
                "name": "Paper8_DQN_2025",
                "n_arms": 8,
                "total_frames": 1500,
                "model_params": {
                    "learning_rate": 0.01
                }
            },

            12: {
                "name": "Paper12_QuARC_2024",
                "n_arms": 10,
                "total_frames": 2000,
                "model_params": {
                    "n_clusters": 3
                }
            },
            99: {
                "name": "TESTBED_TINY",
                "n_arms": 2,
                "base_frames": 10,
                "model_params": {
                    "K": 2,               # EXPNeuralUCB param
                    "alpha": 0.8
                }
            },
            'paper12_quarc': {
                # Paper: Wang et al. "Efficient Routing on Quantum Networks using 
                #        Adaptive Clustering" (ICNP 2024)
                
                # Topology
                'topology_type': 'waxman',
                'n_nodes': 100,              # Network size (vary: 100-800)
                'avg_degree': 6,             # Ed (average degree)
                'waxman_alpha': 0.4,         # Link probability scaling
                'waxman_beta': 0.2,          # Distance decay factor
                
                # Physical parameters
                'entanglement_prob': 0.6,    # Ep (average p)
                'fusion_prob': 0.9,          # q (fusion success)
                'qubits_per_node': 12,       # Memory capacity (varies by node degree)
                'channel_width': 3,          # Links per edge
                
                # Simulation parameters
                'total_timeslots': 7000,     # T
                'num_sd_pairs': 10,          # nsd (concurrent requests)
                'epoch_length': 500,         # Reconfiguration interval
                'request_cutoff': 10**9,     # Timeout (effectively infinite)
                
                # QuARC-specific
                'enable_clustering': True,   # Adaptive clustering
                'split_constant': 4,         # k (Girvan-Newman)
                'threshold_type': '2d_grid', # or 'topology_specific'
                'enable_secondary_fusions': True,
                
                # Framework mapping
                'num_paths': 8,              # For bandit comparison (not used by QuARC)
                'use_fusion_rewards': True,  # Use QuARCRewardFunction
            }
        }

        self.use_last_backup = use_last_backup
        self.backup_registry = {}
        self.expected_keys = {}
        
        self._build_backup_registry(force=self.overwrite)
        # print( self.backup_registry.keys())

    def get_testbed_config(self):
        print(f"\n[TESTBED] Applying testbed params CONFIG")
        if hasattr(self, "testbed_id") and self.testbed_id in self.PAPER_CONFIGS:
            return self.PAPER_CONFIGS[self.testbed_id]
        return None

    def set_log_name(self, base_frames, frame_step):
        scenarios_no        = len(self.test_scenarios)
        # has_stochastic_env  = "stochastic" in self.test_scenarios
        # has_adversarial_env = "Adversarial" in self.test_scenarios
        attack_id           = f"{scenarios_no}_attacks" if scenarios_no > 0 else self.attack_type
        allocator_or_exp    = str(self.allocator) if not self.suffix else f"{self.allocator}({self.suffix})"
        # env_id              = "all_envs" if (has_stochastic_env and has_adversarial_env) else self.environment 
        self.log_name       = f"quantum_exps-{allocator_or_exp}_alloc-{'all_envs'}-{attack_id}-{base_frames}_{int(frame_step)}-{self.runs}_runs-S{self.scale}{'Tb' if self.base_capacity else 'T'}"
        print(self.log_name)
        return True

    def generate_expected_keys(self, evaluator_filename: str):
        """
        Given an evaluator filename, parse its components and generate the full set
        of expected runner and model state filenames for all runs.
        """
        print("\n=====================================================")
        print("🔍 GENERATING EXPECTED KEYS FROM EVALUATOR")
        print("=====================================================")
        print(f"  • Evaluator filename: {evaluator_filename}")

        # ---------------------------------------------------------------
        # Strip extension & split prefix
        # ---------------------------------------------------------------
        core = evaluator_filename.replace(".pkl", "")
        prefix, rest = core.split("_", 1)

        # print(f"  • Core (no .pkl): {core}")
        # print(f"  • Prefix: {prefix}")
        # print(f"  • Remainder: {rest}")

        # ---------------------------------------------------------------
        # Example rest:
        #   800-alloc0_env_stochastic-16000_200_1
        # ---------------------------------------------------------------
        file_qubits = ""
        parts = rest.split("-")
        
        # Safety check for split
        if len(parts) < 3:
            print(f"  ⚠️ Filename format unexpected: {rest}")
            return {}, {}

        alloc_env_attack = parts[1].split("_")
        cap_id = int(round(float(parts[0])))
        
        # Detect Random Allocator
        self.is_random_alloc = True if "random" in alloc_env_attack[0].lower() else False
        pattern = re.compile(r"\(\d+_\d+_\d+_\d+\)(_S\d*(_\d*)?T\w*)?|(_S\d*(_\d*)?T\w*)")
        last_params = parts[-1]
        
        # Initial ST extraction (suffix)
        if "_" in last_params: self.st = last_params.split("_")[-1]
        else: self.st = ""

        # if not self.is_random_alloc: 
            # match = pattern.search(parts[2])
            # if match:  file_qubits = match.group(0)
            # # Remove the qubit tuple from parameters string for parsing
            # if file_qubits:
            #     last_params = last_params.replace(f"_{file_qubits}", '').strip()
            #     # Clean up ST to remove any tuple remnants
            #     self.st = re.sub(r'_?\(.*\)_?', "", file_qubits)
            
            # # If we found qubits in the filename, set them as the runtime qubits
            # if file_qubits: self.random_runtime_qubits = file_qubits
            #     # Normalize formatting if needed, usually it keeps parens in filename
        # else:
            # match = pattern.search(parts[2])
            # if match: file_qubits = match.group(0)
            
            # if file_qubits:
            #     last_params = last_params.replace(f"{file_qubits}", '').strip()
            #     self.st = re.sub(r'_?\(.*\)_?', "", file_qubits)

        allocator_id, env_id, attack_id = alloc_env_attack
        
        try: 
            base_frames, frame_step, runs_id = map(int, last_params.split("_")[:3])
        except ValueError as e:
            print(f"  ❌ Error parsing parameters '{last_params}': {e}")
            return {}, {}

        print("\n🧩 PARSED COMPONENTS")
        print(f"  • cap_id:        {cap_id}")
        print(f"  • allocator_id:  {allocator_id}")
        print(f"  • env_id:        {env_id}")
        print(f"  • attack_id:     {attack_id}")
        print(f"  • base_frames:   {base_frames}")
        print(f"  • frame_step:    {frame_step}")
        print(f"  • runs_id:       {runs_id}")
        # print(f"  • Qubit Caps:    {file_qubits or 'N/A'}")
        
        runtime_qubits = ""
        # # If Random and no qubits in filename, try to find them in registry
        # if self.is_random_alloc and not runtime_qubits:
        #     # Pass the ORIGINAL full filename to the helper
        #     runtime_qubits = self._get_random_runtime_qubits(evaluator_filename, file_qubits)
        #     if not runtime_qubits: print("  ⚠️ No qubit allocation found for Random allocator. The system may fail if files are not found.")
        
        attack_mapping = {
            'none': NoAttack(),
            'random': RandomAttack(attack_rate=self.attack_rate * self.attack_intensity),
            'stochastic': RandomAttack(attack_rate=self.attack_rate * self.attack_intensity),
            'markov': MarkovAttack(attack_rate=self.attack_intensity),
            'adaptive': AdaptiveAttack(attack_rate=self.attack_intensity),
            'onlineadaptive': OnlineAdaptiveAttack(attack_rate=self.attack_intensity)
        }
        framework_state = {}
        model_state  = {}

        print("\n=====================================================")
        print("🧪 GENERATING KEYS FOR EACH RUN")
        print("=====================================================")

        # ---------------------------------------------------------------
        # SINGLE LOOP — everything happens here
        # ---------------------------------------------------------------
        framework_state[evaluator_filename] = evaluator_filename
        for run_idx in range(self.runs):
            print(f"\n--- Run {run_idx+1}/{self.runs} -----------------------")
            for env_cls in [StochasticQuantumEnvironment, AdversarialQuantumEnvironment]:

                env = env_cls.__name__.replace("QuantumEnvironment", "")
                env_id = env if env else "Baseline (None)"

                for attack in attack_mapping.values():
                    attack_id = str(attack)
                    frame_no = base_frames + (frame_step * run_idx) 
                    cap_id = frame_no * self.scale if not self.base_capacity else base_frames * self.scale
                    print(f"  • Frame number: {frame_no}")

                    # -----------------------------------------------------------
                    # RUNNER KEY (framework_state)
                    # -----------------------------------------------------------
                    runner_key = (
                        f"QuantumExperimentRunner_{run_idx+1}_{cap_id}-"
                        f"{allocator_id}_{env_id}_{attack_id}-"
                        f"{frame_no}_{run_idx+1}{runtime_qubits}.pkl"
                    )
                    framework_state[runner_key] = runner_key
                    print(f"  → Runner key: {runner_key}")

                    # -----------------------------------------------------------
                    # MODEL KEYS (model_state)
                    # -----------------------------------------------------------
                    print("  • Generating model keys:")

                    for model_name in self.models:
                        model_class = self.algorithm_configs[model_name]["model_class"].__name__
                        mode = self.algorithm_configs[model_name]["kwargs"]["mode"]

                        model_key = (
                            f"{model_class}({mode})_{cap_id}-"
                            f"{allocator_id}_{env_id}_{attack_id}-"
                            f"{frame_no}{runtime_qubits}.pkl"
                        )
                        model_state[model_key] = model_key
                        print(f"    → {model_key}")

            print("\n=====================================================")
            print("📦 FINAL EXPECTED KEYS")
            print("=====================================================")
            print(f"  • Runner keys: {len(framework_state)}")
            for rk in framework_state.keys():
                print(f"    - {rk}")

            print(f"\n  • Model keys: {len(model_state)}")
            for mk in model_state.keys():
                print(f"    - {mk}")

        # ---------------------------------------------------------------
        # Save internally & return
        # ---------------------------------------------------------------
        self.expected_keys = {"framework_state": framework_state, "model_state": model_state}
        results = {
            "components": self.expected_keys,    
            "parsed": {
                "cap_id": cap_id,
                "allocator_id": allocator_id,
                "env_id": env_id,
                "attack_id": attack_id,
                "base_frames": base_frames,
                "frame_step": frame_step,
                "runs_id": runs_id,
            }
        }

        print("\nEXPECTED KEY GENERATION COMPLETE\n")
        if len(self.backup_registry) != 0: self._build_backup_registry(force=False)
        return results

    def generate_paper7_paths(
        topology: nx.Graph, 
        k: int, 
        n_qisps: int, 
        seed: int
    ) -> list[list[int]]:
        """
        Generate k-shortest paths between n_qisps ISP nodes in the topology.
        Returns list of paths, each path is a list of node IDs.
        """
        rng = np.random.default_rng(seed)
        nodes = list(topology.nodes())
        
        # Randomly select n_qisps nodes as ISP endpoints
        if len(nodes) < n_qisps:
            raise ValueError(f"Topology has {len(nodes)} nodes, need {n_qisps} for ISPs")
        
        isp_nodes = rng.choice(nodes, size=n_qisps, replace=False)
        
        all_paths = []
        for src, dst in itertools.combinations(isp_nodes, 2):
            try:
                # Generate k shortest paths between src and dst
                path_generator = nx.shortest_simple_paths(topology, src, dst, weight="distance")
                paths = list(itertools.islice(path_generator, k))
                all_paths.extend(paths)
            except nx.NetworkXNoPath:
                # Skip if no path exists between these nodes
                continue
        
        return all_paths

    def generate_paper7_contexts(
        paths: list[list[int]], 
        topology: nx.Graph
    ) -> list[list[np.ndarray]]:
        """
        Generate context vectors for each path in Paper7 format.
        Context includes: hop count, average node degree, path length.
        """
        contexts = []
        for path in paths:
            hop_count = len(path) - 1
            
            # Calculate average node degree along path
            degrees = [topology.degree(node) for node in path]
            avg_degree = sum(degrees) / len(degrees) if degrees else 0
            
            # Calculate total path length (sum of edge distances)
            path_length = 0.0
            for i in range(len(path) - 1):
                edge_data = topology.get_edge_data(path[i], path[i + 1])
                path_length += edge_data.get("distance", 1.0)
            
            # Create context vector [hop_count, avg_degree, path_length]
            context_vector = np.array([hop_count, avg_degree, path_length])
            contexts.append([context_vector])
        
        return contexts

    
    def set_paper7_environment(self, frames_no: int, seed: int, qubit_cap: tuple):
        """
        Configure environment specifically for Paper7 QBGP experiments.
        """
        from daqr.core.physics_factory import get_physics_params
        
        # Get Paper7 physics parameters
        physics_kwargs = get_physics_params(
            physics_model="paper7",
            current_frames=frames_no,
            base_seed=seed,
            topology_path="topology_data/as20000101.txt",
            topology_max_nodes=None,  # Use config default
            topology_largest_cc_only=True,
            topology_relabel_to_int=True,
        )
        
        # Set environment with Paper7 topology and contexts
        self.setenvironment(
            qubitcap=qubit_cap,
            frames_no=frames_no,
            seed=seed,
            attack_intensity=self.attackintensity,
            env_type="stochastic",
            attack_type=self.attacktype,
        )
        
        # Override with Paper7-specific parameters
        self.envparams.update(physics_kwargs)
        
        # Build the environment
        self.environment = self.get_environment()

    # def generate_paper7_paths(topology: nx.Graph, k: int = 5):
    #     """
    #     Generate k-shortest paths for Paper7 QBGP experiments.
    #     For each source-dest pair in n_qisps ISPs, find k paths.
    #     """
    #     import itertools
        
    #     # Get n_qisps random nodes as ISP endpoints
    #     nodes = list(topology.nodes())
    #     n_qisps = 3  # from config
    #     rng = np.random.default_rng(seed)
    #     isp_nodes = rng.choice(nodes, size=n_qisps, replace=False)
        
    #     all_paths = []
    #     for src, dst in itertools.combinations(isp_nodes, 2):
    #         try:
    #             paths_gen = nx.shortest_simple_paths(
    #                 topology, src, dst, weight="distance"
    #             )
    #             paths = list(itertools.islice(paths_gen, k))
    #             all_paths.extend(paths)
    #         except nx.NetworkXNoPath:
    #             continue
        
    #     return all_paths

    def _get_random_runtime_qubits(self, filename=None, file_qubits=None, component_type="MultiRunEvaluator"):
        """
        Scans the registry for a matching Random file (Evaluator or Runner) with the same
        run parameters (stem) and picks the LARGEST valid file by size.
        
        MODIFIED: Sorts candidates by file size (largest first) instead of random choice.
        """
        # If this is an Evaluator and we already have a global choice, stick to it to ensure consistency.
        if self.random_runtime_qubits and component_type == "MultiRunEvaluator": return f"_{self.random_runtime_qubits}"
        if not filename: return f"_{self.random_runtime_qubits}" if self.random_runtime_qubits else ""
        print(f"\n\t⚡ Random {component_type} detected → scanning registry for substitute")

        candidates = {}  # ✅ CHANGED: dict to store qubit_alloc → file_name
        eval_suffix = f"_{self.st}" if "evaluator" in component_type.lower() else ""
        pattern = re.compile(fr"\(\d+_\d+_\d+_\d+\){eval_suffix}")

        try:
            # 1. Generate 'Search Stem' by stripping the qubit tuple from the filename
            if file_qubits: search_stem = filename.replace(f"_{file_qubits}", "").replace(file_qubits, "")
            else:
                match = pattern.search(filename)
                if match: search_stem = filename.replace(f"_{match.group(0)}", "").replace(match.group(0), "")
                else: search_stem = filename
            
            search_stem = search_stem.replace(".pkl", "")

        except Exception as e:
            print(f"\t  ⚠️ Error parsing filename {filename}: {e}")
            return ""

        # 2. Scan registry for candidates matching the stem
        registry_section = "framework_state"
        
        if registry_section in self.backup_registry:
            for fname, path in self.backup_registry[registry_section].items():
                # Must match the component type (Evaluator vs Runner)
                if component_type not in fname: continue
                
                # Must be Random allocator
                if "Random" not in fname and "random" not in fname.lower(): continue
                
                # Must contain a valid qubit tuple
                match = pattern.search(fname)
                if not match: continue
                
                # Create candidate stem to compare
                candidate_qubits = match.group(0)
                candidate_stem = fname.replace(f"_{candidate_qubits}", "").replace(candidate_qubits, "").replace(".pkl", "")
                
                # Fuzzy match: check if stems are effectively identical
                if search_stem == candidate_stem: 
                    candidates[candidate_qubits] = fname  # ✅ Store as dict

        # 3. Select a candidate - sort by file size (largest first)
        if candidates:
            print(f"\t  🔍 Found {len(candidates)} matching candidates")
            
            # ✅ NEW: Build list of (qubits, file_size) and sort by size
            candidate_sizes = []
            for qubits, fname in candidates.items():
                try:
                    file_path_str = self.backup_registry[registry_section].get(fname)
                    if file_path_str:
                        file_path = Path(file_path_str)
                        if file_path.exists():
                            file_size = file_path.stat().st_size
                            candidate_sizes.append((qubits, file_size, fname))
                            print(f"\t    - {qubits}: {file_size:,} bytes")
                except Exception as e:
                    print(f"\t    - {qubits}: Could not get size - {e}")
            
            if candidate_sizes:
                # Sort by size (largest first) and pick the biggest
                candidate_sizes.sort(key=lambda x: x[1], reverse=True)
                selected = candidate_sizes[0][0]  # Get qubit allocation from largest
                print(f"\t  ✅ Selected LARGEST: {selected} ({candidate_sizes[0][1]:,} bytes)")
            else:
                # Fallback to random if size check fails for all
                print(f"\t  ⚠️ Size check failed for all candidates, using random fallback")
                selected = random.choice(list(candidates.keys()))
                print(f"\t  🎲 Random fallback: {selected}")
            
            # If this was the Evaluator, lock it in globally for this session
            if component_type == "MultiRunEvaluator": self.random_runtime_qubits = selected
            return f"_{selected}"
        else:
            print(f"\t  ❌ No matching {component_type} found in registry.")
            # Fallback: return the original one (if it existed) or empty
            return f"_{file_qubits}{eval_suffix}" if file_qubits else ""


    def _resolve_random_filename(self, item_v):
        """
        If using Random Allocator, reconstruct the filename to match a valid 
        random file from the registry (handling missing Runners or Evaluators).
        """
        if not self.is_random_alloc:
            return item_v
            
        # Determine component type
        if "MultiRunEvaluator" in item_v: comp_type = "MultiRunEvaluator"
        elif "QuantumExperimentRunner" in item_v: comp_type = "QuantumExperimentRunner"
        else: return item_v # Models don't need this logic yet
            
        # Extract existing qubits from item_v if present
        eval_suffix = f"_{self.st}" if "evaluator" in comp_type.lower() else ""
        pattern = re.compile(fr"\(\d+_\d+_\d+_\d+\){eval_suffix}")
        match = pattern.search(item_v)
        file_qubits = match.group(0) if match else None
        
        # Get a valid tuple (either existing global, or new random substitute)
        resolved_suffix = self._get_random_runtime_qubits(item_v, file_qubits, comp_type)
        
        # Construct new filename
        if not resolved_suffix: return item_v # Failed to resolve, try original

        # if file_qubits: 
        new_item_v = item_v.replace(f"_{file_qubits}", resolved_suffix)
        # else: new_item_v = item_v.replace(".pkl", f"{resolved_suffix}.pkl")
            
        # Cleanup potential double underscores
        return re.sub(r"__", "_", new_item_v)


    def get_latest_state(self, item_k, item_v):
        """
        Retrieves the latest available file path for a given item.
        Reconstructs paths to work in current environment (Drive or local).
        """
        if not self.use_last_backup: return None
        
        # 1) Generate expected keys if needed (for MultiRunEvaluator)
        if len(self.expected_keys) == 0 and "multirunevaluator" in item_v.lower():
            self.generate_expected_keys(item_v)
            self.backup_mgr.restore_from_drive(self.day_str, self.expected_keys)
        
        # 2) Handle Random Allocator filename resolution (Evaluators AND Runners)
        item_v = self._resolve_random_filename(item_v)

        # 3) Try Registry Lookup
        if item_k not in self.backup_registry.keys(): self._build_backup_registry(force=True)
        component_paths = self.backup_mgr.quantum_data_paths["obj"][item_k]
        
        try:
            # Only proceed if item is in registry
            if item_v in self.backup_registry[item_k]:
                registry_path = self.backup_registry[item_k][item_v]
                registry_path_obj = Path(registry_path)
                
                # 3a. Direct check
                if registry_path_obj.exists(): return str(registry_path_obj)
                
                # 3b. Cross-environment reconstruction
                for mode in ["local", "drive"]:
                    try:
                        base_path = component_paths[mode]
                        if base_path in registry_path_obj.parents:
                            relative = registry_path_obj.relative_to(base_path)
                            other_mode = "drive" if self.backup_mgr.in_share_drive else "local"
                            reconstructed_path = component_paths[other_mode] / relative
                            
                            if reconstructed_path.exists():
                                print(f"\t✅ Registry hit (reconstructed {mode}->{other_mode}): {reconstructed_path}")
                                self.backup_registry[item_k][item_v] = str(reconstructed_path)
                                return str(reconstructed_path)
                    except Exception: continue

                # 3c. Filesystem check (registry path might be stale, but file exists in day dir)
                for mode in ["local", "drive"]:
                    try:
                        current_path = component_paths[mode] / self.day_str / item_v
                        if current_path.exists():
                            print(f"\t✅ Found via {mode} filesystem: {current_path}")
                            self.backup_registry[item_k][item_v] = str(current_path)
                            return str(current_path)
                    except Exception: continue
        except Exception as e: print(f"\t⚠️ Registry lookup error: {e}")

        # 4) Try Filesystem Direct Search (Current Mode)
        search_path = component_paths[self.backup_mgr.mode] / self.day_str / item_v
        
        if search_path.exists():
            print(f"\t✓ Found via filesystem: {search_path}")
            self.backup_registry.setdefault(item_k, {})[item_v] = str(search_path)
            return str(search_path)
        
        # 5) Drive Fallback (Download)
        print(f"\t☁️ Attempting Drive download: {item_k}/{item_v}")
        drive_path = self.backup_mgr.download_any_date(component=item_k, filename=item_v)
        
        if drive_path is not None:
            print(f"\t☁️ Recovered from Drive → {drive_path}")
            self.backup_registry.setdefault(item_k, {})[item_v] = drive_path
            return str(drive_path)
        
        # 6) Not Found
        print(f"\t❌ Not found anywhere: {item_k}/{item_v}")
        return None




    def _build_backup_registry(self, force=False):
        """
        Builds backup registry using the configured backup manager (GCP or local).
        Delegates to backup_mgr which handles deduplication and returns only
        the most recent version of each file.
        
        Args:
            force (bool): If True, forces rebuild; if False, uses cached registry
        
        Returns:
            bool: True on success
        """
        if self.use_last_backup is None: return False
        if len(self.backup_registry) == 0 or force:
            print(f"BUILDING REGISTRY WITH {len(self.expected_keys)} EXPECTED COMPONENTS KEYS")
            self.backup_registry = self.backup_mgr.build_registry(force=force, expected_keys=self.expected_keys)
        return True


    def save(self):
        """
        Saves the backup registry. Delegates to the backup manager's save logic.
        Skips saving if use_last_backup is True (read-only mode).
        
        Returns:
            bool: True if saved, False if skipped
        """
        # if self.use_last_backup:  return False
        # Delegate to backup manager
        self.backup_mgr.save_registry(self.backup_registry)
        if self.verbose: print(f"\t{self} 📦 Registry saved via backup manager")
        return True



    def get_key_attrs(self):
        key_attrs = {}
        for key, attr in self._env_params.items():
            key_attrs[key] = str(attr)
        
        del key_attrs["seed"]
        if self.base_capacity: key_attrs["runs"] = self.runs
        return key_attrs

    def __eq__(self, other):
        """
        Defines equality between two ExperimentConfiguration objects.
        Only considers core experiment-defining parameters, ignoring
        runtime attributes like environment instances or file paths.
        """
        if not isinstance(other, ExperimentConfiguration):
            return NotImplemented

        return (
            self.runs == other.runs and
            self.env_type == other.env_type and
            self.attack_type == other.attack_type and
            self.attack_intensity == other.attack_intensity and
            self.attack_rate == other.attack_rate and
            self.scale == other.scale and
            self.base_capacity == other.base_capacity and
            self.test_scenarios == other.test_scenarios and
            self.allocator == other.allocator
        )

    def save_neural_core(self, model, performance, frames_no, allocator_tag, overwrite=True):
        """Save a NeuralUCB checkpoint tagged by frame + allocator name."""
        file_name = f"neuralucb_{allocator_tag}_frames{frames_no}.pkl"
        model_dir = os.path.join(str(self.dir), "models")
        file_path = os.path.join(model_dir, file_name)
        os.makedirs(model_dir, exist_ok=True)

        # If file exists, compare performance before overwriting
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                saved = pickle.load(f)
            prev_perf = saved.get("performance", -1)
            if (not overwrite) or performance <= prev_perf:
                print(f"\t⚠️ Existing NeuralUCB ({prev_perf:.2f}) Performance is Better than New ({performance:.2f}) → Skipped.")
                return file_path

        # Save new version
        with open(file_path, "wb") as f:
            pickle.dump({"model": model, "performance": performance}, f)
        print(f"\t--> Saved NeuralUCB: {file_name} ({performance:.2f})")
        return file_path


    def load_neural_core(self, frames_no, allocator_tag):
        """Load a NeuralUCB checkpoint by frame + allocator name."""
        file_name = f"neuralucb_{allocator_tag}_frames{frames_no}.pkl"
        model_dir = os.path.join(str(self.dir), "models")
        file_path = os.path.join(model_dir, file_name)

        if not os.path.exists(file_path):
            print(f"⚠️ No NeuralUCB found for allocator={allocator_tag}, frames={frames_no}")
            return None

        with open(file_path, "rb") as f:
            data = pickle.load(f)
        print(f"\tLoaded NeuralUCB ({data['performance']:.2f}) → {file_name}")
        return data['model']  # Return just the model object

    def update_configs(self, runs=None, models=None, scenarios=None, attack_type=None, attack_intensity=None, attack_rate=None):
        if runs and type(runs) == int: self.runs = runs
        if models and type(models) == list: self.models = models
        if scenarios and type(scenarios) == dict: self.test_scenarios = scenarios
        if attack_rate and type(attack_rate) == int: self.attack_rate = attack_rate
        if attack_type and type(attack_type) == str: self.attack_type = attack_type
        if attack_intensity and type(attack_intensity) == int: self.attack_intensity = attack_intensity

    # Add a setter method:
    def set_allocator(self, allocator):
        """Set the qubit allocator for dynamic routing"""
        self.allocator = allocator

    def get_cleanup_wait_time(self, frames_count=1000, cooldown_base=3, cooldown_scale_factor=1, cooldown_max=15):
        """
        Calculate frame-scaled cleanup wait time.
        
        Args:
            frames_count: Number of frames (if None, uses self.frames_count)
        
        Returns:
            float: Wait time in seconds
        """

        # Frame-scaled timing formula
        scale = (frames_count / 1000.0) * cooldown_scale_factor
        wait_time = cooldown_base + scale
        
        return min(wait_time, cooldown_max)
    
    def get_models(self):
        """Return the list of model names to be used in experiments"""
        return self.models

    def set_environment_object(self, environment):
        """
        Directly set a pre-built environment object.
        
        Args:
            environment: Fully constructed QuantumEnvironment (or subclass)
        
        This bypasses all internal environment building logic and uses the
        provided environment directly. Perfect for custom physics/topology.
        """
        if "QuantumEnvironment" not in str(environment.__class__.__name__):
            raise ValueError(f"Expected QuantumEnvironment subclass, got {type(environment)}")
        
        self.environment = environment
        print(f"✓ Set custom environment: {environment.__class__.__name__}")
        print(f"  Physics: {getattr(environment, 'noise_model', 'default')}")
        print(f"  Attack: {getattr(environment, 'attack', 'none').__class__.__name__}")

    def set_environment(self, qubit_cap, frames_no, seed, attack_intensity, 
                    env_type='stochastic', attack_type='stochastic', metadata = {},
                    noise_model=None,              # ✅ NEW
                    fidelity_calculator=None,      # ✅ NEW
                    external_topology=None,        # ✅ NEW
                    external_contexts=None,        # ✅ NEW
                    external_rewards=None):        # ✅ NEW
        """
        Stores the core parameters needed to build any environment.
        Now supports custom physics via quantum objects.
        """
        try:
            self.attack_type = attack_type  # ✅ This was missing
            self._env_params = {
                'attack': None,
                'qubit_capacities': tuple(qubit_cap),
                'frame_length': int(frames_no),
                'seed': int(seed),
                'allocator': self.allocator,
                'env_type': env_type,
                'actk_type': attack_type,
                # ✅ NEW: Quantum physics objects
                'noise_model': noise_model,
                'entanglement_success_factor': self.testbed_config.get('entanglement_success_factor', 100),
                'fidelity_calculator': fidelity_calculator,
                'external_topology': external_topology,
                'external_contexts': external_contexts,
                'external_rewards': external_rewards
            }

            env_params = copy.deepcopy(self._env_params)
            del env_params['env_type']
            del env_params['actk_type']
            params = env_params.copy()

            if self.attack_strategy is None:
                self.set_attack_strategy(attack_type=attack_type, attack_intensity=attack_intensity)

            # Determine which environment to create based on the strategy object type
            params['attack'] = self.attack_strategy
            try:
                if isinstance(self.attack_strategy, NoAttack):
                    # Baseline scenario -> QuantumEnvironment
                    self.environment = QuantumEnvironment(**params)
                
                elif isinstance(self.attack_strategy, RandomAttack):
                    # Stochastic scenario -> StochasticQuantumEnvironment
                    self.environment =  StochasticQuantumEnvironment(**params)
                
                else:
                    # All other strategies (Markov, Adaptive, etc.) -> AdversarialQuantumEnvironment
                    self.environment = AdversarialQuantumEnvironment(**params)
            except Exception as e: print(f"\t Error Creating Environment for {self.attack_strategy}\n\t\t{e}")
        except Exception as e: print(f"\t Error Setting Environment for {self.attack_strategy}\n\t\t{e}")
    

    def get_environment(self):
        """
        return environment object
        """
        return self.environment


    def get_environment_config(self, environment_type='adversarial'):
        """Return environment configuration based on type"""
        if environment_type not in self.environ_mapping.keys():
            raise ValueError("Environment not set. Please call set_environment() first.")
        return self.environ_mapping[environment_type.lower()]
    
    def get_models_configs(self, model_names = None):
        """Retrieve configurations for specified models or all models if none specified"""
        if model_names is None:
            return self.algorithm_configs
        else:
            return {name: self.algorithm_configs[name] for name in model_names if name in self.algorithm_configs}


    def set_attack_strategy(self, attack_type: str, **kwargs):
        """
        Configures the attack strategy based on a scenario name.
        Supports Paper #2 path-dependent attacks.
        """        
        try:
            self.attack_type = attack_type.lower()
            # Paper #2 path-dependent stochastic attack
            if attack_type.lower() == 'paper2_stochastic' and kwargs.get('paths'):
                paths = kwargs['paths']
                attack_intensity = kwargs.get('attack_intensity', self.attack_intensity)
                attack_rates = [attack_intensity + (len(p)-2) * 0.05 for p in paths]
                self.attack_strategy = RandomAttack(per_path_rates=attack_rates)
                print(f"✓ Paper #2 path-dependent attack: rates={attack_rates}")
                return
            
            # Your existing mapping
            self.attack_mapping = {
                'none': NoAttack(),
                'random': RandomAttack(attack_rate=kwargs.get('attack_rate', self.attack_rate) * self.attack_intensity),
                'stochastic': RandomAttack(attack_rate=kwargs.get('attack_rate', self.attack_rate) * self.attack_intensity),
                'markov': MarkovAttack(attack_rate=self.attack_intensity),
                'adaptive': AdaptiveAttack(attack_rate=self.attack_intensity),
                'onlineadaptive': OnlineAdaptiveAttack(attack_rate=self.attack_intensity)
            }
            self.attack_strategy = self.attack_mapping.get(self.attack_type, NoAttack())
            # self.attack_type = str(self.attack_strategy)
        except Exception as e: print(f"\t Error Setting Attack Strategy {e}")


    def get_attack_strategy(self, attack_type=None):
        """Return the configured attack strategy or default to MarkovAttack"""
        try:
            if attack_type and attack_type.lower() not in self.attack_mapping:
                print(f"⚠️  WARNING: Unknown attack_type='{self.attack_type}', defaulting to 'markov'")
                return MarkovAttack(attack_rate=self.attack_intensity)
            elif attack_type:
                return self.attack_mapping[attack_type.lower()]
        except Exception as e: print(f"\t Error Getting Attack Strategy {e}")

    def create_model_registry(self):
        """Create a registry of available quantum models with metadata"""
        models = {
            'Oracle': Oracle,
            'RandomAlg': RandomAlg, 
            'UCB': UCB,
            'LinUCB': LinUCB,
            'TS': TS,
            'LinTS': LinTS,
            'NeuralTS': NeuralTS,
            'NeuralUCB': NeuralUCB,
            'EXPNeuralUCB': EXPNeuralUCB
        }
        
        # Add metadata for each model class
        registry = {}
        for name, model_class in models.items():
            # Try to create a dummy instance to get metadata
            try:
                # For models that need parameters, use minimal viable parameters
                if name == 'Oracle':                    continue  # Skip Oracle as it needs specific parameters
                elif name in ['UCB', 'TS', 'RandomAlg']:dummy_model = model_class(K=2)
                elif name in ['LinUCB', 'LinTS']:       dummy_model = model_class(d=2, K=2)
                elif name in ['NeuralUCB', 'NeuralTS']: dummy_model = model_class(d=2, K=2)
                elif name == 'EXPNeuralUCB':            continue  # Skip EXPNeuralUCB as it needs specific parameters
                else:                                   continue
                
                registry[name] = {'class': model_class, 'metadata': dummy_model.get_model_info()}
            except:
                registry[name] = {
                    'class': model_class,
                    'metadata': {'name': name, 'model_type': 'unknown', 'error': 'Could not instantiate'}
                }
        return registry

    def get_attack_mapping(self):
        """Return the full attack mapping dictionary"""
        return self.attack_mapping

    def get_attack(self, attack_type=None):
        """Return the configured attack strategy"""
        if attack_type  and self.attack_type.lower() not in self.attack_mapping:
            print(f"⚠️  WARNING: Unknown attack_type='{self.attack_type}', defaulting to 'markov'")
            return MarkovAttack(attack_rate=self.attack_intensity)
        elif attack_type:
            return self.attack_mapping[self.attack_type.lower()]
        return {}
    
    # =============================================================================
    # UTILITY FUNCTIONS
    # =============================================================================
    def get_model_category(self, model_name):
        """Return the category of a given model"""
        if model_name in self.NEURAL_MODELS:                return 'Neural'
        elif model_name in self.CONTEXTUAL_MODELS:          return 'Contextual'
        elif model_name in self.INFORMED_CONTEXTUAL_MODELS: return 'Informed_Contextual'
        elif model_name in self.CUSTOM_MODELS:              return 'Custom'
        else:                                               return 'Unknown'

    def get_models_by_category(self, category):
        """Get all models in a specific category"""
        category_map = {
            'neural': self.NEURAL_MODELS,
            'contextual': self.CONTEXTUAL_MODELS,
            'informed': self.INFORMED_CONTEXTUAL_MODELS,
            'custom': self.CUSTOM_MODELS,
            'all_cmab': self.ALL_CMAB_MODELS,
            'all': self.ALL_QUANTUM_MODELS,
            'quick': self.QUICK_TEST_MODELS,
            'performance': self.PERFORMANCE_COMPARISON_MODELS,
            'research': self.RESEARCH_MODELS,
            'stepwise': self.STEP_WISE_MODELS,
            'batch': self.BATCH_MODELS,
            'predictive': self.PREDICTIVE_MODELS
        }
        return category_map.get(category.lower(), [])

    def print_model_summary(self):
        """Print summary of all available models"""
        print("=" * 60)
        print("QUANTUM MODEL SUMMARY")
        print("=" * 60)
        print(f"Neural Models ({len(self.NEURAL_MODELS)}): {', '.join(self.NEURAL_MODELS)}")
        print(f"Contextual Models ({len(self.CONTEXTUAL_MODELS)}): {', '.join(self.CONTEXTUAL_MODELS)}")
        print(f"Informed Contextual Models ({len(self.INFORMED_CONTEXTUAL_MODELS)}): {', '.join(self.INFORMED_CONTEXTUAL_MODELS)}")
        print(f"Custom Models ({len(self.CUSTOM_MODELS)}): {', '.join(self.CUSTOM_MODELS)}")
        print(f"Total Models: {len(self.ALL_QUANTUM_MODELS)}")
        print("=" * 60)

    def _build_save_dict(self, obj):
        """
        Build a pickleable dict from obj.__dict__, tracking unpickleable fields.
        """
        save_dict = {}
        unpickleable = []
        for attr, value in obj.__dict__.items():
            try:
                pickle.dumps(value)
                save_dict[attr] = value
            except Exception: unpickleable.append(attr)
        if unpickleable and self.verbose: print(f"\t⚠️ {obj} Excluded unpickleable fields: {', '.join(unpickleable)}")
        return save_dict

    def _should_overwrite(self, save_path, save_dict):
        """
        Decide whether it's safe to overwrite an existing file at save_path.

        Rules:
        - If existing file size > new serialized size → do NOT overwrite.
        - If existing file size < new serialized size → overwrite.
        - If equal → follow self.overwrite flag.
        """
        # File must exist to reach here
        existing_size = save_path.stat().st_size
        new_bytes = pickle.dumps(save_dict)
        new_size = len(new_bytes)

        if self.verbose: print(f"\tℹ️ Existing size: {existing_size}, new size: {new_size}")
        # existing is larger → skip
        if existing_size > new_size:
            if self.verbose: print("\t⊘ Skip overwrite: existing file is larger")
            return False, None  # no overwrite, no payload reuse

        # new is larger → overwrite
        if existing_size < new_size:
            if self.verbose: print("\t↻ Overwriting: new file is larger")
            return True, new_bytes  # overwrite with these bytes

        # sizes equal → follow overwrite flag
        if self.overwrite:
            if self.verbose: print("\t↻ Overwriting: sizes equal, overwrite=True")
            return True, new_bytes
        else:
            if self.verbose: print("\t⊘ Skip overwrite: sizes equal, overwrite=False")
            return False, None

    def save_obj(self, obj):
        """
        Save object state to config/data lake with safety checks:
        - Never overwrite a larger existing file.
        - Prefer overwriting when new version is larger.
        """
        save_dict = self._build_save_dict(obj)
        comp = obj.component
        mode = self.backup_mgr.mode
        file_name = obj.file_name.replace("1.5", "1_5")
        if self.suffix: file_name = file_name.replace(".pkl", f"_{self.suffix}.pkl")
        component_path = self.backup_mgr.quantum_data_paths["obj"][comp]
        save_path = component_path[mode] / self.day_str / file_name

        try:
            # # Fix corrupt directory-at-path case
            # if save_path.exists() and save_path.is_dir():
            #     print(f"\t Corrupted directory found at {save_path}, removing...")
            #     shutil.rmtree(save_path)
            #     print("\t✓ Cleaned up")
            # CREATE DIRECTORY IF IT DOESN'T EXIST
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If file exists → apply safety logic
            if save_path.exists():
                do_overwrite, new_bytes = self._should_overwrite(save_path, save_dict)
                # CHECK IF WE SHOULD ACTUALLY OVERWRITE
                if not do_overwrite:
                    if self.verbose:
                        print(f"\t⊘ {obj} Skipping save (existing file is larger)")
                    return str(save_path)  # Return existing path, don't write
                
                # Only write if do_overwrite is True
                with open(save_path, "wb") as f: f.write(new_bytes)
                if self.verbose:
                    print(f"\t✓ {obj} State overwritten")
                    print(f"\t  → {save_path}")
                return str(save_path)
            else:
                new_bytes = pickle.dumps(save_dict)
                with open(save_path, "wb") as f:
                    f.write(new_bytes)
                if self.verbose:
                    print(f"\t✓ {obj} New state saved")
                    print(f"\t  → {save_path}")
                return str(save_path)
        except Exception as e: 
            # print(save_path)
            print(save_dict)
            print(f"❌ {obj} Save failed: {e}")
        return False

    
    def _validate_path(self, obj, config_path):
        """
        Validate that config_path can be converted to a Path object.
        
        Args:
            obj: Object being resumed (for logging)
            config_path: Path string or Path object to validate
        
        Returns:
            bool: True if valid Path, False otherwise
        """
        try:
            Path(config_path)
            print(f"\t✓ {obj} Path validated: {config_path!r}")
            return True
        except Exception as e:
            print(f"\t❌ Failed converting path to Path object: {e}")
            return False


    def _load_obj(self, obj, state_path):
        """
        Load and validate pickle file from disk with triple-fallback strategy.
        Handles:
        1. Standard pickle
        2. cloudpickle (cross-environment)
        3. SafeUnpickler (ignores missing module imports like pathlib._local)
        """
        print(f"\t   Loading from: {state_path}")

        exists = state_path.exists()
        size = state_path.stat().st_size if exists else "N/A"
        print(f"\t   File exists: {exists}, size: {size}")

        if not exists or size == 0:
            print("\t⚠️  File missing or empty")
            return None, False

        loaded_dict = None
        eq_result = False

        # ============================================================
        # 1) Standard pickle
        # ============================================================
        try:
            with open(state_path, "rb") as f:
                loaded_dict = pickle.load(f)
            # print("\t✓ Pickle loaded (standard pickle)")
            if loaded_dict is not None:
                eq_result = (obj == loaded_dict)
                # print(f"\t   Equality check: {eq_result}")
            return loaded_dict, eq_result
        except Exception as e:
            print(f"\t⚠️  Standard pickle failed: {e}")

        # ============================================================
        # 2) cloudpickle fallback
        # ============================================================
        try:
            import cloudpickle
            with open(state_path, "rb") as f:
                loaded_dict = cloudpickle.load(f)
            print("\t✓ Pickle loaded (cloudpickle fallback)")
            if loaded_dict is not None:
                eq_result = (obj == loaded_dict)
                print(f"\t   Equality check: {eq_result}")
            return loaded_dict, eq_result
        except ImportError:
            print("\t⚠️  cloudpickle not installed, skipping")
        except Exception as e:
            print(f"\t⚠️  cloudpickle failed: {e}")

        # ============================================================
        # 3) SafeUnpickler — FIXES corrupted module references
        # ============================================================
        print("\t🔄 Attempting SafeUnpickler (ignore missing modules)...")

        class Dummy:
            def __init__(self, *args, **kwargs):
                pass

        class SafeUnpickler(pickle.Unpickler):
            """Custom Unpickler that replaces missing module references with Dummy()."""
            def find_class(self, module, name):
                try:
                    return super().find_class(module, name)
                except Exception:
                    # print(f"\t   → Replacing missing: {module}.{name}")
                    return Dummy

        try:
            with open(state_path, "rb") as f:
                loaded_dict = SafeUnpickler(f).load()

            # print(f"\t✓ Pickle loaded (SafeUnpickler recovered import errors)")

            if loaded_dict is not None:
                eq_result = (obj == loaded_dict)
                # print(f"\t   Equality check: {eq_result}")

            return loaded_dict, eq_result

        except Exception as e:
            print(f"\t❌ SafeUnpickler failed: {e}")

        print("\t❌ All load attempts failed")
        return None, False

    def can_resume(self, obj):
        # Get path from registry
        if not self.use_last_backup: return None
        file_name = obj.file_name.replace("1.5", "1_5")
        if self.suffix: file_name = file_name.replace(".pkl", f"_{self.suffix}.pkl")
        config_path = self.get_latest_state(obj.component, file_name)
        if not config_path:
            print(f"\t❌ Not found in registry or fallback locations")
            return None
        return config_path

    def resume_obj(self, obj, component="model_state"):
        """
        Resume object state from data lake.
        
        Strategy:
        - Looks up path in registry (points to data lake)
        - Loads from: quantum_datalake_path (source of truth)
        - Deletes corrupted files
        
        Args:
            obj: Object to resume (must have __dict__, __eq__, file_name, configs)
            component (str): Component type ("model_state" or "framework_state")
        
        Returns:
            bool: True if successfully resumed, False otherwise
        """
        if not self.use_last_backup: return None
        if obj.resumed: return obj.resumed

        print(f"\n\t🔄 Resume: {obj}")
        has_path = self.can_resume(obj) 
        # Validate path
        if not self.can_resume(obj) or not self._validate_path(obj, has_path): return False
        
        state_path = Path(has_path)
        
        # Load and validate
        loaded_dict, eq_result = self._load_obj(obj, state_path)
        if not loaded_dict: return False
        
        # Update or delete
        if eq_result:
            # print(f"\t✅ Resuming state")
            try:
                configs = obj.configs
                old_file_name = obj.file_name
                obj.__dict__.update(loaded_dict)
                obj.configs = configs
                obj.file_name = old_file_name
                obj.resumed = True
                return True
            except Exception as e:
                print(f"\t❌ Update failed: {e}")
                return False
        else:
            print(f"\t❌ Corrupted—deleting")
            # self.delete_file(state_path, obj)
            return False


    def delete_file(self, state_path, obj):
        """
        Deletes a corrupted or mismatched state file both locally and remotely (if applicable).

        Args:
            state_path (Path): Full path to the corrupted file (local or drive)
            component (str): "model_state" or "framework_state"
            filename (str): exact file name (e.g., runner_key or model_key)
        """
        print(f"\t❌ Corrupted state detected → deleting: {state_path}")

        # =============================
        # 1) DELETE LOCAL FILE
        # =============================
        try:
            if state_path.exists() and state_path.is_file():
                state_path.unlink()
                print(f"\t🗑️  Deleted local file: {state_path}")
            elif state_path.is_dir():
                # Safety: remove directory that should never exist
                shutil.rmtree(state_path)
                print(f"\t🗑️  Deleted corrupted directory: {state_path}")
        except Exception as e:
            print(f"\t[ERROR] Failed to delete local file: {e}")

        # =============================
        # 2) DELETE REMOTE (GOOGLE DRIVE DATA LAKE)
        # =============================
        try:
            if self.backup_mgr.remote_available:
                removed = self.backup_mgr.delete_from_drive(obj.component, obj.file_name)
                if removed: print(f"\t☁️  Deleted remote datalake copy of {obj.file_name}")
        except Exception as e:
            print(f"\t[ERROR] Failed Drive delete for {obj.file_name}: {e}")

        # =============================
        # 3) REMOVE FROM REGISTRY
        # =============================
            try:
                if obj.component in self.backup_registry:
                    if obj.file_name in self.backup_registry[obj.component]:
                        del self.backup_registry[obj.component][obj.file_name]
                        print(f"\t🗑️  Removed registry entry for {obj.file_name}")
            except Exception as e:
                print(f"\t[ERROR] Removing registry entry failed: {e}")

        # =============================
        # 4) SAVE UPDATED REGISTRY
        # =============================
        try:
            self.save()
        except Exception as e:
            print(f"\t[ERROR] Saving registry after deletion failed: {e}")

        print(f"\t✅ Cleanup complete.\n")
        return True

