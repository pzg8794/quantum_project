from daqr.core.network_environment        import NoAttack, RandomAttack, MarkovAttack, AdaptiveAttack, OnlineAdaptiveAttack
from daqr.core.network_environment        import AdversarialQuantumEnvironment, StochasticQuantumEnvironment, QuantumEnvironment

from daqr.algorithms.predictive_bandits    import iCEXP4, iCEpochGreedy, iCEpsilonGreedy, iCKernelUCB, iCThompsonSampling
from daqr.algorithms.predictive_bandits    import CEXP4, CEpochGreedy, CEpsilonGreedy, CKernelUCB, CThompsonSampling
from daqr.algorithms.predictive_bandits    import Oracle, GNeuralUCB, EXPUCB, EXPNeuralUCB, LinUCB, CEXPNeuralUCB 
from daqr.algorithms.predictive_bandits    import UCB, RandomAlg, TS, LinTS, LinUCB, iCPursuitNeuralUCB, NeuralTS
from daqr.algorithms.predictive_bandits    import CPursuitNeuralUCB, CPursuit, iCPursuit, QuantumModel, NeuralUCB
from daqr.core.qubit_allocator import *

import  copy, os
<<<<<<< HEAD
import  pathlib
import  pickle
import  shutil
=======
import pathlib
import  pickle
>>>>>>> origin/gcp-main
from pathlib import Path
from datetime import datetime
from .local_backup_manager import LocalBackupManager


class ExperimentConfiguration:
    """
    Configuration holder for quantum experiments.
    """
    def __init__(self, runs=1, seed_offset=100, env_type="stochastic", attack_type="markov", attack_intensity=1.0, attack_rate=0.25, models=None, scenarios=None, allocator=None, base_seed=12345, scale=2, base_capacity=True, overwrite=False, resume=True, use_last_backup=True, verbose=False):
        
        self.allocator = allocator if allocator else QubitAllocator()  # Default to fixed

        # =============================================================================
        # MODEL NAME COLLECTIONS FOR TESTING
        # =============================================================================
        self.verbose = verbose
        self.resume = resume
        self.base_model = None
        self._env_params = None
        self.environment = None
        self.overwrite = overwrite
        self.seed_offset = seed_offset
        self.dir = Path(os.path.dirname(os.path.abspath(__file__)))
<<<<<<< HEAD
=======

        self.in_share_drive         = True
        self.drive_datalake_base    = Path("/content/drive/Shareddrives/ai_quantum_computing")
        self.parent_dir             = self.dir.parent.parent.parent.parent
        self.quantum_logs_path      = self.parent_dir / "quantum_logs"
        if not self.quantum_logs_path.exists(): 
            self.drive_datalake_base= self.dir
            self.parent_dir         = self.dir
            self.in_share_drive     = False
        self.quantum_logs_path      = self.parent_dir / "quantum_logs"
        self.quantum_datalake_path  = self.parent_dir / "quantum_data_lake"

        # self.quantum_logs_path      = Path(self.normalize_path("quantum_logs", project_root=parent_dir))
        self.backup_registry_path   = self.quantum_datalake_path / "backup_registry.json"
        self.backup_pickle_path     = self.quantum_datalake_path / "backup_registry.pkl"
        self.framework_state_path   = self.quantum_datalake_path / "framework_state"
        self.model_state_path       = self.quantum_datalake_path / "model_state"
        
>>>>>>> origin/gcp-main
        
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
            'Quantum': {'model_class': QuantumModel, 'seed_offset': seed_offset * 1, 'kwargs': {'mode': 'hybrid'}, 'runner_type': 'step-wise'},
            'Oracle': {'model_class': Oracle, 'seed_offset': seed_offset * 2, 'kwargs': {'mode': 'hybrid'}, 'runner_type': 'step-wise'},
            'GNeuralUCB': {'model_class': GNeuralUCB, 'seed_offset': seed_offset * 3, 'kwargs': {'mode': 'neural', 'beta': 1.0}, 'runner_type': 'batch'},
            'EXPUCB': {'model_class': EXPUCB, 'seed_offset': seed_offset * 4, 'kwargs': {'mode': 'exp3', 'gamma_factor': 0.1, 'eta_factor': 0.005, 'beta': 1.0}, 'runner_type': 'batch'},
            'EXPNeuralUCB': {'model_class': EXPNeuralUCB, 'seed_offset': seed_offset * 5, 'kwargs': {'mode': 'hybrid', 'gamma_factor': 0.01, 'eta_factor': 0.05, 'beta': 1.0}, 'runner_type': 'batch'},
            'CPursuitNeuralUCB': {'model_class': CPursuitNeuralUCB, 'seed_offset': seed_offset * 6, 'kwargs': {'mode': 'neural', 'learning_rate': 0.1, 'beta': 1.0}, 'runner_type': 'batch'},
            'iCPursuitNeuralUCB': {'model_class': iCPursuitNeuralUCB, 'seed_offset': seed_offset * 7, 'kwargs': {'mode': 'neural', 'learning_rate': 0.1, 'beta': 1.0, 'gamma_factor': 0.1, 'eta_factor': 0.005, 'obs': None}, 'runner_type': 'batch'},
            'CEpsilonGreedy': {'model_class': CEpsilonGreedy, 'seed_offset': seed_offset * 8, 'kwargs': {'mode': 'hybrid', 'epsilon': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CEXP4': {'model_class': CEXP4, 'seed_offset': seed_offset * 9, 'kwargs': {'mode': 'hybrid', 'gamma': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CPursuit': {'model_class': CPursuit, 'seed_offset': seed_offset * 10, 'kwargs': {'mode': 'hybrid', 'learning_rate': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CEpochGreedy': {'model_class': CEpochGreedy, 'seed_offset': seed_offset * 11, 'kwargs': {'mode': 'hybrid', 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CThompsonSampling': {'model_class': CThompsonSampling, 'seed_offset': seed_offset * 12, 'kwargs': {'mode': 'hybrid', 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CKernelUCB': {'model_class': CKernelUCB, 'seed_offset': seed_offset * 13, 'kwargs':{'mode': 'hybrid',  'gamma': 0.1, 'eta': 1.0, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCEpsilonGreedy': {'model_class': iCEpsilonGreedy, 'seed_offset': seed_offset * 14, 'kwargs':{'mode': 'hybrid',  'epsilon': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCEXP4': {'model_class': iCEXP4, 'seed_offset': seed_offset * 15, 'kwargs': {'mode': 'hybrid', 'gamma': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCPursuit': {'model_class': iCPursuit, 'seed_offset': seed_offset * 16, 'kwargs': {'mode': 'hybrid', 'learning_rate': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCEpochGreedy': {'model_class': iCEpochGreedy, 'seed_offset': seed_offset * 17, 'kwargs': {'mode': 'hybrid','n_experts': 4}, 'runner_type': 'step-wise'},
            'iCThompsonSampling': {'model_class': iCThompsonSampling, 'seed_offset': seed_offset * 18, 'kwargs': {'mode': 'hybrid', 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCKernelUCB': {'model_class': iCKernelUCB, 'seed_offset': seed_offset * 19, 'kwargs': {'mode': 'hybrid','gamma': 0.1, 'eta': 1.0, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'LinUCB': {'model_class': LinUCB, 'seed_offset': seed_offset * 20, 'kwargs': {'mode': 'hybrid', 'alpha': 1.0, 'lambda_reg': 1.0, 'n_features': 6, 'quantum_state_dim': 6, 'entanglement_aware': True, 'prediction_window': 10, 'anomaly_threshold': 0.2}, 'runner_type': 'step-wise'},
            'CEXPNeuralUCB': {'model_class': CEXPNeuralUCB, 'seed_offset': seed_offset * 21, 'kwargs': {'mode': 'neural', 'beta': 1.0, 'n_experts': 4}, 'runner_type': 'batch'}
        }

        self.use_last_backup = use_last_backup
        self.backup_registry = {}
        self.expected_keys = {}
        
        self._build_backup_registry(force=self.overwrite)
        # print( self.backup_registry.keys())

        
        # self.runs_id      = self.runs
        # self.allocator_id = str(self.allocator)
        # self.env_id       = str(self.environment)
        # self.attack_id    = self.attack_strategy
        # self.cap_id       = (int(self.base_frames if self.configs.base_capacity else self.frames_count)*self.configs.scale)
        # self.file_name = f"{self}_{self.cap_id}-{self.allocator_id}_{self.env_id}_{self.attack_id}-{self.base_frames}_{int(self.frame_step)}_{self.runs_id}.pkl"


    def generate_expected_keys(self, evaluator_filename: str):
        """
        Given an evaluator filename, parse its components and generate the full set
        of expected runner and model state filenames for all runs.

        ✓ No structure changes
        ✓ No new folders
        ✓ Uses EXACT filename formats you already use
        ✓ Includes PRINT STATEMENTS for full transparency
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

        print(f"  • Core (no .pkl): {core}")
        print(f"  • Prefix: {prefix}")
        print(f"  • Remainder: {rest}")

        # ---------------------------------------------------------------
        # Example rest:
        #   800-alloc0_env_stochastic-16000_200_1
        # ---------------------------------------------------------------
        parts = rest.split("-")

        cap_id = int(round(float(parts[0])))
        alloc_env_attack = parts[1]
        base_frames, frame_step, runs_id = map(int, parts[2].split("_"))
        allocator_id, env_id, attack_id = alloc_env_attack.split("_")

        print("\n🧩 PARSED COMPONENTS")
        print(f"  • cap_id:        {cap_id}")
        print(f"  • allocator_id:  {allocator_id}")
        print(f"  • env_id:        {env_id}")
        print(f"  • attack_id:     {attack_id}")
        print(f"  • base_frames:   {base_frames}")
        print(f"  • frame_step:    {frame_step}")
        print(f"  • runs_id:       {runs_id}")
        print(f"  • Total runs:    {self.runs}")


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
                        f"{frame_no}_{run_idx+1}.pkl"
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
                            f"{frame_no}.pkl"
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


    def get_latest_state(self, item_k, item_v):
<<<<<<< HEAD
        """
        Retrieves the latest available file path for a given item.
        Reconstructs paths to work in current environment (Drive or local).
        """
        
=======
        # DEBUG PRINT
        # print(f"🔎 Looking for: {item_k}/{item_v}")

>>>>>>> origin/gcp-main
        # 1) Generate expected keys if needed
        if len(self.expected_keys) == 0 and "multirunevaluator" in item_v.lower():
            self.generate_expected_keys(item_v)
            self.backup_mgr.restore_from_drive(self.day_str, self.expected_keys)
        
<<<<<<< HEAD
        # 2) Try registry lookup - reconstruct path for current environment
        # Get both local and drive base paths for this component
        component_paths = self.backup_mgr.quantum_data_paths["obj"][item_k]
        try:
            registry_path = self.backup_registry[item_k][item_v]
            registry_path_obj = Path(registry_path)
            
            # If path exists as-is, return it
            if registry_path_obj.exists(): return str(registry_path_obj)
            
            # Try to determine which base the registry path is relative to
            for mode in ["local", "drive"]:
                try:
                    # Try to make registry path relative to this mode's base
                    base_path = component_paths[mode]
                    relative = registry_path_obj.relative_to(base_path)
                    
                    # Now try reconstructing with the OTHER mode
                    other_mode = "drive" if self.backup_mgr.in_share_drive else "local"
                    reconstructed_path = component_paths[other_mode] / relative
                    
                    if reconstructed_path.exists():
                        print(f"\t✅ Registry hit (reconstructed from {mode} to {other_mode}): {reconstructed_path}")
                        # Update registry with correct path
                        self.backup_registry[item_k][item_v] = str(reconstructed_path)
                        return str(reconstructed_path)
                        
                except ValueError:
                    # relative_to() failed - path not under this base
                    continue
            
            # Also try with current day appended (filesystem direct path)
            for mode in ["local", "drive"]:
                current_path = component_paths[mode] / self.day_str / item_v
                if current_path.exists():
                    print(f"\t✅ Found via {mode} filesystem: {current_path}")
                    self.backup_registry[item_k][item_v] = str(current_path)
                    return str(current_path)
            
            print(f"\t⚠️ Registry path doesn't exist and couldn't reconstruct: {registry_path}")
            
        except KeyError:
            print(f"\t⚠️ Not in registry: {item_k}/{item_v}")
        
        # 3) Try filesystem direct search with current mode
        search_path = component_paths[self.backup_mgr.mode] / self.day_str / item_v
        print(f"\tChecking FS ({self.backup_mgr.mode}): {search_path} | Exists? {search_path.exists()}")
        
        if search_path.exists():
            print(f"\t✓ Found via filesystem: {search_path}")
            self.backup_registry.setdefault(item_k, {})[item_v] = str(search_path)
=======
        # 2) Try registry lookup
        try:
            path = self.backup_registry[item_k][item_v]
            if Path(path).exists(): 
                print(f"\t✅ Registry hit: {path}")
                return str(path)
            else:
                print(f"\t⚠️ Registry path invalid: {path}")
        except KeyError as e: 
            print(f"\t⚠️ Registry path invalid: {e}")
            pass
        
        # 3) Try filesystem direct search (NEW)
        search_path = None
        if item_k == "model_state": 
            search_path = self.model_state_path / self.day_str / item_v
        else:
            search_path = self.framework_state_path / self.day_str / item_v
        
        # DEBUG PRINT
        print(f"\tChecking FS: {search_path} | Exists? {search_path.exists()}")
        
        if search_path and search_path.exists():
            print(f"\t✓ Found via filesystem: {search_path}")
            # Update registry for future lookups
            self.backup_registry.setdefault(item_k, {})[item_v] = str(Path(search_path).resolve())
>>>>>>> origin/gcp-main
            return str(search_path)
        
        # 4) Drive fallback
        print(f"\t☁️ Attempting Drive download: {item_k}/{item_v}")
        drive_path = self.backup_mgr.download_any_date(component=item_k, filename=item_v)
        
        if drive_path is not None:
            print(f"\t☁️ Recovered from Drive → {drive_path}")
            self.backup_registry.setdefault(item_k, {})[item_v] = drive_path
            return str(drive_path)
        
        # 5) Not found
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
        if len(self.backup_registry) == 0:
            print(f"BUILDING REGISTRY WITH {len(self.expected_keys)} EXPECTED KEYS")
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

    def set_environment(self, qubit_cap, frames_no, seed, attack_intensity, env_type='stochastic', attack_type= 'stochastic'):
        """
        Stores the core parameters needed to build any environment.
        """
        self._env_params = {
            'attack': None,
            'qubit_capacities': tuple(qubit_cap),
            'frame_length': int(frames_no),
            'seed': int(seed),
            'allocator': self.allocator,
            'env_type': env_type,
            'actk_type': attack_type
        }

        env_params = copy.deepcopy(self._env_params)
        del env_params['env_type']
        del env_params['actk_type']
        params = env_params.copy()

        if self.attack_strategy is None:
            self.set_attack_strategy(
                attack_type=attack_type,
                attack_intensity=attack_intensity,
            )

        # Determine which environment to create based on the strategy object type
        params['attack'] = self.attack_strategy
        if isinstance(self.attack_strategy, NoAttack):
            # Baseline scenario -> QuantumEnvironment
            self.environment = QuantumEnvironment(**params)
        
        elif isinstance(self.attack_strategy, RandomAttack):
            # Stochastic scenario -> StochasticQuantumEnvironment
            self.environment =  StochasticQuantumEnvironment(**params)
        
        else:
            # All other strategies (Markov, Adaptive, etc.) -> AdversarialQuantumEnvironment
            self.environment = AdversarialQuantumEnvironment(**params)
    

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
        Configures the attack strategy based on a scenario name. This method
        instantiates the correct AttackStrategy object.
        """
        self.attack_type = attack_type.lower()
        self.attack_mapping = {
            'none': NoAttack(),
            'random': RandomAttack(attack_rate=kwargs.get('attack_rate', self.attack_rate) * self.attack_intensity),
            'stochastic': RandomAttack(attack_rate=kwargs.get('attack_rate', self.attack_rate) * self.attack_intensity),
            'markov': MarkovAttack(attack_rate=self.attack_intensity),
            'adaptive': AdaptiveAttack(attack_rate=self.attack_intensity),
            'onlineadaptive': OnlineAdaptiveAttack(attack_rate=self.attack_intensity)
        }
        self.attack_strategy = self.attack_mapping.get(self.attack_type, NoAttack())

    def get_attack_strategy(self, attack_type=None):
        """Return the configured attack strategy or default to MarkovAttack"""
        if attack_type and attack_type.lower() not in self.attack_mapping:
            print(f"⚠️  WARNING: Unknown attack_type='{self.attack_type}', defaulting to 'markov'")
            return MarkovAttack(attack_rate=self.attack_intensity)
        elif attack_type:
            return self.attack_mapping[attack_type.lower()]

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


<<<<<<< HEAD
    def save_obj(self, obj):
        """
        Save object state to config backup directory.
        
        Strategy:
        - Reads lookups from: quantum_datalake_path (via get_latest_state)
        - Writes copies to: config backup (self.config_backup_path)
        - This protects the shared data lake from corrupted files during development
        
        Args:
            obj: Object to save (model, runner, evaluator)
            save_to_dir: Original path where object would be saved in data lake
            file_name: Name of the pickle file
        
        Returns:
            str: Path where file was saved
        """
        # Build pickleable dict
        save_dict = {}
        unpickleable = []
        for attr, value in obj.__dict__.items():
            try:
                pickle.dumps(value)
                save_dict[attr] = value
            except: 
                unpickleable.append(attr)
        
        if unpickleable and self.verbose:
            print(f"\t⚠️ {obj} Excluded unpickleable fields: {', '.join(unpickleable)}")  

        comp = obj.component
        mode = self.backup_mgr.mode
        component_path = self.backup_mgr.quantum_data_paths["obj"][comp]
        save_path = component_path[mode] / self.day_str / obj.file_name
        # ensure parent directory (NOT the file) exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        try:

            if save_path.exists() and save_path.is_dir():
                print(f"\t⚠️ Corrupted directory found (from previous failed save): {save_path}")
                print(f"\t🗑️ Removing directory...")
                shutil.rmtree(save_path)
                print(f"\t✅ Cleaned up!")

            # Only save if overwrite=True OR file doesn't exist
            if self.overwrite or not save_path.exists():
                with open(save_path, 'wb') as f: pickle.dump(save_dict, f)
                if self.verbose:
                    print(f"\t✓ {obj} State saved to config backup")
                    print(f"\t  → {save_path}")
            elif self.verbose: print(f"\t⊘ {obj} Save skipped (exists + overwrite=False)")
                    
        except Exception as e:
            print(f"❌ {obj} Save failed: {e}")
            raise
            
        return str(save_path)

    def resume_obj(self, obj, component="model_state"):
        """
        Resume object state from data lake.
        
        Strategy:
        - Looks up path in registry (points to data lake)
        - Loads from: quantum_datalake_path (the source of truth)
        - Falls back to: config backup if data lake file missing
        
        Args:
            obj: Object to resume (must have __dict__ and __eq__)
            file_name: Name of the pickle file to resume from
            component: Component type ("model_state" or "framework_state")
        
        Returns:
            bool: True if resumed successfully, False otherwise
        """
        # print(self.file_name)
        config_path  = self.get_latest_state(obj.component, obj.file_name)
        mode = self.backup_mgr.mode
        if not config_path: config_path = self.backup_mgr.quantum_data_paths[mode] / obj.component / obj.file_name
        
        state_path = None
        # print(config_path)
        if config_path:
            # print(f"\t\t[TRACE] config_path = {config_path!r} (type={type(config_path)})")
            # --- TRACE 2: STATE PATH CONSTRUCTION ---
            try:
                print(f"\t {obj} Path Found = {config_path!r} (type={type(config_path)})")
                state_path = Path(config_path)
            except Exception as e:
                print(f"\t[ERROR] Failed converting config_path to Path: {e}")
                print(f"\t\t[TRACE] config_path was: {config_path!r}")

            print(f"\t\t[TRACE] state_path = {state_path!r} (type={type(state_path)})")
            # --- TRACE 3: FILE EXISTENCE ---
            try:
                exists = state_path.exists()
                size = state_path.stat().st_size if exists else "N/A"
                print(f"\t\t[TRACE] state_path.exists() = {exists}, size = {size}")
                if not exists or size == 0: print(f"\t[WARN] No saved state at {state_path} or Empty ({size})")
                
                # --- TRACE 4: LOAD PICKLE ---
                eq_result = None
                try:
                    with open(state_path, "rb") as f:
                        loaded_dict = pickle.load(f)
                        print(f"\t\t[TRACE] loaded_dict type: {type(loaded_dict)}")
                        # --- TRACE 5: EQUALITY CHECK ---
                        try:
                            eq_result = (obj == loaded_dict)
                            print(f"\t\t[TRACE] self == loaded_dict → {eq_result!r} (type={type(eq_result)})")
                        except Exception as e:  print(f"\t[ERROR] Equality comparison failed: {e}")
                except Exception as e:  print(f"\t[ERROR] Failed loading pickle from {state_path}: {e}")

                # --- TRACE 6: UPDATE ---
                if eq_result:
                    print(f"\t🔄 {obj} Resuming state from: {state_path}")
                    try:
                        configs = obj.configs
                        obj.__dict__.update(loaded_dict)
                        obj.configs = configs
                        return True
                    except Exception as e:
                        print(f"\t[ERROR] __dict__.update failed: {e}")
                        print(f"\t\t[TRACE] loaded_dict = {loaded_dict!r}")
                else:   self.delete_file(state_path, obj)
            except Exception as e:  print(f"\t[ERROR] Checking path existence failed: {e}")

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

=======
    def save_obj(self, obj, save_to_dir, file_name):
        """Save evaluator state for the current day."""
        if self.overwrite and self.in_share_drive:
            save_dir_relative = save_to_dir.relative_to(self.drive_datalake_base)
            if not self.in_share_drive: save_to_dir = self.parent_dir / save_dir_relative
            save_to_dir.mkdir(parents=True, exist_ok=True)

            # Build pickleable dict
            save_dict = {}
            unpickleable = []
            for attr, value in obj.__dict__.items():
                try:
                    pickle.dumps(value)
                    save_dict[attr] = value
                except: unpickleable.append(attr)
            if unpickleable and self.verbose:print(f"\t⚠️ {self} Excluded unpickleable fields:{', '.join(unpickleable)}")   

            save_path = save_to_dir / file_name
            try:
                # ───────────────────────────────────────────────
                # Only save if overwrite=True OR file doesn't exist
                # ───────────────────────────────────────────────
                if self.overwrite or not save_path.exists():
                    with open(save_path, 'wb') as f:
                        pickle.dump(save_dict, f)

                    if self.verbose:
                        print(f"\t{self} State saved successfully")

                    # print(save_path)
                    # print(f"\t{self} Saved Successfully")
                    # Save registry (unchanged)
                    # self.configs.save()
                else:
                    if self.verbose: print(f"\t{self} Skipped save (exists + overwrite=False)")
            except Exception as e:
                print(f"❌ {self} Save failed: {e}")
                raise
        return False
    
    def resume_obj(self, component, file_name, verbose=False):
        if verbose: print("\n================ RESUME TRACE ================\n")
        # --- TRACE 1: CONFIG PATH ---
        # print(self.file_name)
        config_path = self.get_latest_state(component, file_name)
        if config_path: 
            if verbose: print(f"[TRACE] state_path = {config_path!r} (type={type(config_path)})")
            # --- TRACE 2: STATE PATH CONSTRUCTION ---
            try:
                if verbose: print(f"[TRACE] config_path = {config_path!r} (type={type(config_path)})")
                save_dir_relative = Path(config_path).relative_to(self.drive_datalake_base)
                if not self.in_share_drive: config_path = self.dir / save_dir_relative
                config_path = Path(config_path)
            except Exception as e:
                print(f"[ERROR] Failed converting config_path to Path: {e}")
                print(f"[TRACE] config_path was: {config_path!r}")
                return None, False
            
            # --- TRACE 3: FILE EXISTENCE ---
            try:
                exists = config_path.exists()
                size = config_path.stat().st_size if exists else "N/A"
                if verbose: print(f"[TRACE] state_path.exists() = {exists}, size = {size}")
                if not exists or size == 0:
                    print(f"\t[WARN] No saved state at {config_path}")
                    return None, False
            except Exception as e:
                print(f"[ERROR] Checking path existence failed: {e}")
                return None, False

            # --- TRACE 4: LOAD PICKLE ---
            eq_result = None
            try:
                with open(config_path, "rb") as f:
                    loaded_dict = pickle.load(f)
                    # print(f"\t[TRACE] loaded_dict type: {type(loaded_dict)}")
                    # if isinstance(loaded_dict, dict): print(f"[TRACE] loaded_dict keys: {list(loaded_dict.keys())}")
                    # --- TRACE 5: EQUALITY CHECK ---
                    try:
                        eq_result = (self == loaded_dict)
                        # print(f"\t[TRACE] self == loaded_dict → {eq_result!r} (type={type(eq_result)})")
                    except Exception as e:
                        print(f"[ERROR] Equality comparison failed: {e}")
                        return None, False   
                    return loaded_dict, eq_result             
            except Exception as e:
                print(f"[ERROR] Failed loading pickle from {config_path}: {e}")
                return None, False
            
        return None, False
>>>>>>> origin/gcp-main
