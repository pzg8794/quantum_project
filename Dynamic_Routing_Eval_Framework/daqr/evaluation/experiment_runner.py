from    concurrent.futures import ThreadPoolExecutor, as_completed
from    daqr.config.experiment_config import ExperimentConfiguration
import pathlib
from    pathlib import Path
from    tqdm    import tqdm
import  re
import  pickle
import  torch
import  gc, time
import  threading, json  
import  numpy as np, copy
import  multiprocessing as mp




class QuantumExperimentRunner:
    """
    The central orchestrator for running quantum bandit experiments. This class
    leverages the ExperimentConfiguration factory to set up and execute tests
    across various scenarios and models.
    """
    
    def __init__(self, id=0, config: ExperimentConfiguration | None = None, frames_count=4000, base_seed=12345, 
             attack_type=None, attack_intensity=None, enable_progress=False, use_locks=False, 
             capacity=None, max_workers=None):
        
        self._save_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self.configs = config if config is not None else ExperimentConfiguration()
        self.configs.base_seed = base_seed
        self.use_locks = use_locks
        
        self.id = id
        self.results = {}
        # self.model = None
        self.winner = None
        self.resumed = False
        self.environment = None
        self.is_complete = True
        self.experiment_seed = None
        self.frames_count = frames_count
        self.component    = "framework_state"
        self.enable_progress = enable_progress
        self.physics_params = self.configs.physics_params
        self.algorithm_configs = self.configs.get_models_configs()
        self.capacity = capacity if capacity else self.frames_count
        
        # ADD these new parallel execution attributes
        self.max_workers = max_workers if max_workers else min(4, mp.cpu_count())
        self._model_cache = {}  # Cache for model reuse
        self._execution_stats = {'total_time': 0, 'parallel_efficiency': 0}

        # Set paths
        self.key_attrs = {}
        # self.save_to_dir = self.configs.framework_state_path / self.configs.day_str
        self.configs.update_configs(attack_type=attack_type, attack_intensity=attack_intensity)


        qubit_cap = (8, 10, 8, 9)  # legacy fallback to avoid breaking runs
        # Strongly prefer caller to pass allocator-derived qubit_cap
        if self.configs.allocator is not None:
            qubit_cap = tuple(self.configs.allocator.allocate(timestep=0, route_stats={}, verbose=False))

        # Build the environment ONCE per experiment, then reuse across all models
        mode = self.configs.backup_mgr.mode
        component_path = self.configs.backup_mgr.quantum_data_paths["obj"][self.component][mode]
        self.save_to_dir = component_path / self.configs.day_str
        self._build_environment_once(frames_count=self.frames_count, qubit_cap=qubit_cap)

        self.allocator_id = str(getattr(self.configs, "allocator", "alloc"))
        self.env_id       = str(getattr(self.configs, "environment", "env"))
        self.attack_id    = str(getattr(self.configs, "attack_strategy", "None"))
        self.cap_id       = int(self.capacity*self.configs.scale)
        
        id_str            = str(self.id)
        alloc_str         = "_".join(str(v) for v in qubit_cap)
        if "random" in str(self.configs.allocator).lower(): id_str += f"_({re.sub(r'^_', '', alloc_str)})"
        self.file_name    = f"{self}_{self.cap_id}-{self.allocator_id}_{self.env_id }_{self.attack_id}-{self.frames_count}_{id_str}.pkl"

        # Resume previous evaluator state if configured
        try:                    self.resume()
        except Exception as e:  print(f"⚠️ {self} Resume failed: {e}")
    
    def _infer_saved_models(self, state: dict):
        """
        Infer which models were actually run in a saved Runner backup.
        Uses the 'results' dict structure, which always contains model outputs.
        """
        try:
            results = state.get("results", {})
            if isinstance(results, dict) and results: return [m for m in results.keys()]
            return None
        except Exception: return None

    def __eq__(self, other):
        """Defines equality for evaluator or saved dict comparison."""
        if isinstance(other, dict):
            other_attrs = other.get("key_attrs", {}).copy()
            
            # Model check - set flag if models differ
            needs_filtering = False
            saved_models = self._infer_saved_models(other)
            current_models = set(self.configs.models)
            if saved_models:
                saved_set = set(saved_models)
                if not current_models.issubset(saved_set):
                    print("\n❌ MODEL SET MISMATCH in Runner — forcing rerun")
                    print(f"   Current models: {sorted(current_models)}")
                    print(f"   Saved models:   {sorted(saved_set)}")
                    return False
                # If current is subset but not equal, we need to filter
                if current_models != saved_set:
                    needs_filtering = True
                    print(f"ℹ️  Will filter saved models to: {sorted(current_models)}")

            # temp fix
            temp_qubit_capacities = None
            non_dflt_checks = ["runs", "actk_type", "noise_model", "fidelity_calculator", "external_topology", "external_contexts", "external_rewards"]

            if "seed" in other_attrs:                       del other_attrs["seed"]
            for check in non_dflt_checks:
                if check in other_attrs:                    del other_attrs[check]
                if check in self.key_attrs:                 del self.key_attrs[check]
            # if 'runs' in other_attrs:   del other_attrs['runs']
            # if 'runs' in self.key_attrs: del self.key_attrs['runs']
            if "random" in str(self.configs.allocator).lower(): 
                temp_qubit_capacities = other_attrs['qubit_capacities']
                del other_attrs['qubit_capacities']
                del self.key_attrs['qubit_capacities']

            if (
                self.id == other.get("id") and
                self.allocator_id == other.get("allocator_id") and
                self.env_id == other.get("env_id") and
                self.attack_id == other.get("attack_id") and
                self.cap_id == other.get("cap_id") and
                self.key_attrs == other_attrs
            ):
                if temp_qubit_capacities: 
                    self.key_attrs['qubit_capacities'] = temp_qubit_capacities
                
                # Filter results if needed
                if needs_filtering and 'results' in other:
                    for model in list(other['results'].keys()):
                        if model not in self.configs.models:
                            del other['results'][model]
                    print(f"✅ Filtered results to: {list(other['results'].keys())}")
                
                return True
            
            print(f"\n❌ {str(self).upper()} comparison failed:")
            print(f"  ID: {self.id} vs {other.get('id')}")
            print(f"  Allocator: {self.allocator_id} vs {other.get('allocator_id')}")
            print(f"  Environment: {self.env_id} vs {other.get('env_id')}")
            print(f"  Attack: {self.attack_id} vs {other.get('attack_id')}")
            print(f"  Capacity: {self.cap_id} vs {other.get('cap_id')}")
            print(f"  Current attrs:\n{json.dumps(self.key_attrs, indent=2)}")
            print(f"  Loaded attrs:\n{json.dumps(other_attrs, indent=2)}")
            return False

        # --- evaluator comparison ---
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == getattr(other, "id", None) and
            self.frames_count == getattr(other, "frames_count", None) and
            self.allocator_id == getattr(other, "allocator_id", None) and
            self.env_id == getattr(other, "env_id", None) and
            self.attack_id == getattr(other, "attack_id", None) and
            self.cap_id == getattr(other, "cap_id", None) and
            self.key_attrs == getattr(other, "key_attrs", None)
        )

    def save(self):
        return self.configs.save_obj(self)
    
    def _resume_from_registry_set(self, registry_set, allow_same_runs=False):
        """
        Attempt to resume from any compatible evaluator in registry_set.

        Args:
            registry_set (dict): Mapping from qubits_alloc → file_name.
            allow_same_runs (bool): Whether to allow resume from same run count.

        Returns:
            bool: True if resumed successfully, False otherwise.
            
        MODIFIED: Iterates registry_set sorted by FILE SIZE (largest first).
        """
        print(f"\t[Resume-RegistrySet] candidates={registry_set.keys()}")
        
        # ✅ NEW: Build list of (qubits_alloc, file_size) and sort by size
        alloc_sizes = []
        for qubits_alloc, file_name in registry_set.items():
            try:
                file_path_str = self.configs.backup_mgr.backup_registry.get(self.component, {}).get(file_name, None)
                if file_path_str:
                    file_path = Path(file_path_str)
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        alloc_sizes.append((qubits_alloc, file_size))
                        print(f"\t[Resume-RegistrySet] qubits={qubits_alloc}, size={file_size:,} bytes")
            except Exception as e:
                print(f"\t[Resume-RegistrySet] Could not get size for {qubits_alloc}: {e}")
        
        # Sort by file size (largest first)
        sorted_allocs = [alloc for alloc, size in sorted(alloc_sizes, key=lambda x: x[1], reverse=True)]
        print(f"\t[Resume-RegistrySet] Trying allocations in size order (largest first): {sorted_allocs}")
        
        # Iterate allocations from largest file to smallest file
        for qubits_alloc in sorted_allocs:
            file_name = registry_set[qubits_alloc]
            print(f"\n\t\t[Resume-RegistrySet] Trying file with qubits {qubits_alloc}: {file_name}")
            try:
                # Lookup full path from backup_registry
                file_path = self.configs.backup_mgr.backup_registry.get(self.component, {}).get(file_name, None)
                if not file_path:
                    print(f"\t\t❌ Not found in registry or fallback locations")
                    continue

                file_path = Path(file_path)
                obj, loaded = self.configs._load_obj(self, file_path)
                if loaded:
                    print(f"\t\t[Resume-RegistrySet] ✅ Successfully resumed from: {file_name}")
                    self.resumed = True
                    return True
            except Exception as e: 
                print(f"\t\t❌ {e}")
        
        print("\t[Resume-RegistrySet] ❌ No valid matches found in registry set.")
        return False


    def _get_relative_set_registry(self):
        """
        Builds a relative registry of files that match this runner's
        core experiment config but differ only by qubit allocation.

        Returns:
            dict[str, str] → {qubits_alloc: file_name}
        """
        registry = self.configs.backup_mgr.backup_registry.get(self.component, {})
        # pattern to strip trailing '_d+_d+_d+_d+' before the extension
        pattern = r"_\(\d+_\d+_\d+_\d+\)|\s+"
        sub_registry = {}

        for file_name in registry.keys():
            if "runner" not in file_name.lower() or not re.search(r"_\(\d+_\d+_\d+_\d+\)", file_name): continue
            if self.configs.suffix and (not self.configs.suffix in file_name): continue
            # print(file_name)
            if file_name == self.file_name: continue
            # print(file_name)
            
            # remove qubit allocation tail if present
            _file_name = re.sub(pattern, "", file_name)
            if self.configs.suffix: _file_name = _file_name.replace(f"_{self.configs.suffix}", "")
            if re.sub(pattern, "", self.file_name) == _file_name:
                # part_with_runs = re.sub(r"(_\(\d+_\d+_\d+_\d+\))?\.pkl", "", file_name)
                match = re.search(r"\((\d+_\d+_\d+_\d+)\)\.pkl", file_name)
                qubits_alloc = match.group(1) if match else None
                if qubits_alloc:
                    print(f"\t\tExtracted qubits_alloc: {qubits_alloc}")
                    sub_registry[qubits_alloc] = file_name
        return sub_registry


    def resume(self):
        if not self.resumed: 
            if self.configs.resume_obj(self): 
                self.resumed = True
                return self.resumed
            if self.configs.use_last_backup:
                print("\t[Resume] exact failed → Looking for relative match")
                sub_registry = self._get_relative_set_registry()
                return self._resume_from_registry_set(sub_registry)
        return self.resumed


    
    def remove_model(self, model_name):
        if model_name in self.algorithm_configs.keys():
            # remove model_name from 
            del self.algorithm_configs[model_name]

    def display_experiment_conditions(self):
        "Display Experiment Conditions"
        scaled_capacity = int(self.capacity*self.configs.scale)
        if self.environment:
            print(f"\n{str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Env:{str(self.environment)}, Attack:{str(self.environment.attack)}, Rate:{self.environment.attack_rate}, Frames:{self.environment.frame_length}, QubitAlloc={str(self.configs.allocator)}, SC:{scaled_capacity} (Scale={self.configs.scale} x Cap={self.capacity}), Seed: {self.experiment_seed}")

    def _build_environment_once(self, frames_count: float, qubit_cap: tuple):
        """
        Build ONE shared environment for the whole experiment (all models),
        with a seed that is independent of the model being run.
        """
        if frames_count: self.frames_count =frames_count
        # Seed independent of model to keep environment identical across algorithms
        self.experiment_seed = self.configs.base_seed + (hash(f"{self.configs.attack_type}_{self.frames_count}") % 10000)

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
            seed=self.experiment_seed,
            attack_intensity=self.configs.attack_intensity,
            attack_type=self.configs.attack_type,
            **self.physics_params              # ✅ Injects Paper #2 physics!
        )

        # Build and store the environment
        self.environment = self.configs.get_environment()
        self.key_attrs = getattr(self.configs, "get_key_attrs", lambda: {})()

        print("="*150)
        self.display_experiment_conditions()
        print("="*150)


    def run_step_wise_oracle(self, env_info, model, frames_count=4000, alg_name='Oracle'):
        if frames_count: self.frames_count = frames_count
        total_reward = 0.0
        for t in tqdm(range(self.frames_count), desc=f"{alg_name}", disable=not self.enable_progress):
            if t >= env_info['attack_pattern'].shape[0]:
                print(f"\t⚠️ Frame {t} exceeds attack pattern size {env_info['attack_pattern'].shape[0]}")
                break
            
            # ✅ FIX: Handle both return types (tuple or int)
            action_result = model.take_action()
            
            if isinstance(action_result, tuple) and len(action_result) == 2:
                path, action = action_result  # Oracle returns (path, action)
            else:
                path = int(action_result)  # LinUCB returns just action
                action = 0
            
            base_reward = env_info['reward_functions'][path][action]
            attack_modifier = env_info['attack_pattern'][t][path]
            observed_reward = base_reward * attack_modifier
            model.update(path, action, observed_reward)
            total_reward += observed_reward
        
        oracle_results = model.get_results()
        if oracle_results and 'final_reward' in oracle_results:
            total_reward = oracle_results['final_reward']
        return float(total_reward)

    
    def run_algorithm(self, alg_name: str, enable_progress=False, base_model="Oracle"):
        """
        Run a single algorithm assuming the environment has already been built
        for this experiment with the provided qubit_cap.
        """
        if alg_name not in self.algorithm_configs: raise ValueError(f"Unknown algorithm: {alg_name}")
        
        config = self.algorithm_configs[alg_name]
        env_info = self.environment.get_environment_info()
        model_class = config['model_class']
        seed_offset = config['seed_offset']
        runner_type = config['runner_type']
        model_kwargs = config['kwargs']

        # 🆕 NEW: Add transition parameters to model_kwargs
        transition_trigger = getattr(self.configs, 'transition_trigger', False)
        if transition_trigger and  'trigger_state_transition' in env_info:
            model_kwargs['transition_trigger'] = env_info['trigger_state_transition']
            model_kwargs['transition_interval'] = getattr(self.configs, 'paper2_transition_interval', 50)

        algorithm_seed = self.experiment_seed + seed_offset
        torch.manual_seed(algorithm_seed)
        np.random.seed(algorithm_seed)

        results = {'final_reward': 0.0}
        total_reward, attempts = 0.0, 0
        model = None

        if alg_name in self.results.keys(): 
            # if self.configs.overwrite: 
            # print(f"\t{alg_name} already processed")
            # if alg_name == base_model:
                # model = model_class(
                #     configs=self.configs,
                #     X_n=env_info['contexts'],
                #     reward_list=env_info['reward_functions'],
                #     frame_number=self.frames_count,
                #     attack_list=env_info['attack_pattern'],
                #     capacity=self.capacity, 
                #     **model_kwargs
                # )
                # Resume previous evaluator state if configured
                # try:                    model.resume()
                # except Exception as e:  print(f"\t⚠️ {self}-{alg_name} Resume failed: {e}")
            return self.results[alg_name], None
        else:
            try:
                retry_count = 0
                max_retries = 3  # Prevent infinite loops
                while total_reward <= 0.0 and retry_count < max_retries:
                    # model_kwargs['verbose'] = enable_progress
                    self.configs.verbose = enable_progress
                    
                    # Debug Paper7 reward structure
                    if alg_name == 'Oracle' and retry_count == 0:
                        reward_funcs = env_info.get('reward_functions', [])
                        if reward_funcs:
                            print(f"\t📊 Reward structure for Oracle:")
                            print(f"\t   Type: {type(reward_funcs)}")
                            print(f"\t   Length: {len(reward_funcs)}")
                            if len(reward_funcs) > 0:
                                print(f"\t   First reward: {reward_funcs[0]}, type: {type(reward_funcs[0])}")
                                if hasattr(reward_funcs[0], '__len__'):
                                    print(f"\t   First reward length: {len(reward_funcs[0])}")
                        else:
                            print(f"\t⚠️ WARNING: reward_functions is empty or None!")
                    
                    model = model_class(
                        configs=self.configs,
                        X_n=env_info['contexts'],
                        reward_list=env_info['reward_functions'],
                        frame_number=self.frames_count,
                        attack_list=env_info['attack_pattern'],
                        capacity=self.capacity, 
                        **model_kwargs
                    )
                
                    try:
                        result = None
                        if enable_progress: self.validate_quantum_model(model)
                        if runner_type == 'step-wise': total_reward = float(self.run_step_wise_oracle(env_info, model, self.frames_count, alg_name))
                        else: result = model.run(attack_list=env_info['attack_pattern'], verbose=enable_progress)
                        if result is None:
                            mr = model.get_results() if hasattr(model, 'get_results') else {}
                            if mr and 'final_reward' in mr: total_reward = float(mr['final_reward'])
                        
                        retry_count += 1
                        if retry_count >= max_retries and total_reward <= 0.0:
                            # Break out to avoid infinite loop - allow zero rewards for context-aware modes
                            print(f"\t⚠️ Max retries ({max_retries}) reached. Proceeding with total_reward={total_reward}")
                            break

                        enable_progress = False
                        avg_reward = total_reward / self.frames_count if (self.frames_count > 0 and total_reward > 0) else 0.0

                        results = {
                            'final_reward': float(total_reward),
                            'avg_reward': float(avg_reward),
                            'algorithm': alg_name,
                            'seed': algorithm_seed,
                            'frames_count': self.frames_count,
                            'attack_type': self.configs.attack_type,
                            'model_results': model.get_results(),
                            'retries': attempts
                        }
                        if model.resumed: break
                    except Exception as e: 
                        model = None
                        attempts += 1
                        print(f"\t❌ Runtime error in {alg_name}: {e}")
                    finally:
                        # model.state = 1
                        pass
                        # del model
                        # gc.collect()
            except Exception as e:
                print(f"\t❌ Failed to create {alg_name}: {e}")
                results = {'final_reward': 0.0, 'error': str(e)}
        return results, model

    def _get_min_efficiency(self, model_name, env_type='stochastic') -> float:
        """Return expected minimum reward thresholds for retry decisions"""
        if model_name not in self.configs.thresholds:
            return 0.5

        # Always retry 0% (return 0.0 if not in dict or as fallback)
        return self.configs.thresholds[model_name].get(env_type, 0.50)  # Fallback 50%

    def cleanup(self, verbose=False, cooldown_seconds=1):
        """Enhanced cleanup with parallel execution support."""
        import gc
        try:
            cleanup_items = []
            if cooldown_seconds > 0: time.sleep(cooldown_seconds)

            # Clean up environment
            if hasattr(self, 'environment') and self.environment:
                if hasattr(self.environment, 'cleanup'):
                    try:
                        self.environment.cleanup(verbose=verbose)
                    except Exception as e:
                        if verbose:
                            print(f"\t[WARN] Environment cleanup failed: {e}")
                del self.environment
                self.environment = None
                cleanup_items.append("environment")
            
            # Clean up model cache
            if hasattr(self, '_model_cache'):
                for model_name, model in self._model_cache.items():
                    if hasattr(model, 'cleanup'):
                        try:
                            model.cleanup(verbose=verbose)
                        except Exception as e:
                            if verbose:
                                print(f"\t[WARN] Model {model_name} cleanup failed: {e}")
                self._model_cache.clear()
                cleanup_items.append("model_cache")
            
            # PyTorch/GC cleanup (keep as-is)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    cleanup_items.append("CUDA cache")
            except ImportError:
                pass
            
            if gc:
                collected = gc.collect()
                cleanup_items.append(f"GC:{collected} objects")
            cleanup_items.append(f"cooldown:{cooldown_seconds}s")
            if cooldown_seconds > 0: time.sleep(cooldown_seconds)
            if verbose:
                print(f"\t✓ ExperimentRunner cleaned: \t{', '.join(cleanup_items)}")
        except Exception as e:
            print(f"\t[WARNING] Cleanup failed: {e}")
            import traceback
            traceback.print_exc()


    def __del__(self):
        """YOUR ORIGINAL destructor"""
        try:
            self.cleanup()
        except Exception as e:
            print(f"❌ Error during QuantumExperimentRunner cleanup: {e}")

    # ONLY ADDITION: Simple stochastic vs adversarial comparison
    def compare_stochastic_vs_adversarial(self, frames_count=4000):
        """Compare performance in stochastic vs adversarial settings"""
        if frames_count: self.frames_count =frames_count

        print("=" * 70)
        print("STOCHASTIC vs ADVERSARIAL COMPARISON")
        print("=" * 70)
        
        original_attack_type = self.configs.attack_type
        try:
            print("\n\t🔬 TESTING: \tStochastic (Natural Random Failures)")
            self.configs.attack_type = 'stochastic'
            stochastic_results = self.run_experiment(self.frames_count)
            
            print("\n\t🔬 TESTING: \tAdversarial (Strategic Attacks)")  
            self.configs.attack_type = 'adaptive'
            adversarial_results = self.run_experiment(self.frames_count)
            
            print("\n\t📊 COMPARISON SUMMARY:")
            print("=" * 50)
            
            for alg in ['GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']:
                if alg in stochastic_results['results'] and alg in adversarial_results['results']:
                    stoch_reward = stochastic_results['results'][alg]['final_reward']
                    adv_reward = adversarial_results['results'][alg]['final_reward']
                    performance_loss = ((stoch_reward - adv_reward) / stoch_reward * 100) if stoch_reward > 0 else 0
                    
                    print(f"\t{alg:<20} \t| Stoch: \t{stoch_reward:07.2f} \t| Adv: \t{adv_reward:07.2f} \t| Loss: \t{performance_loss:05.1f}%")
            
            return {
                'stochastic': stochastic_results,
                'adversarial': adversarial_results
            }
        
        finally:
            self.configs.attack_type = original_attack_type


    # =============================================================================
    # Enhanced Utility Functions for Model Management
    # =============================================================================

    def validate_quantum_model(self, model) -> bool:
        """Enhanced validation that an object implements QuantumModel interface"""
        if not isinstance(model, self.configs.algorithm_configs.get('Quantum', {}).get('model_class', object)):
            return False
        
        # Check that take_action is implemented
        if not hasattr(model, 'take_action') or not callable(getattr(model, 'take_action')):
            return False
        
        return True

    def get_model_capabilities(self, model) -> dict:
        """Get comprehensive model capabilities and metadata"""
        if not isinstance(model, self.configs.algorithm_configs.get('Quantum', {}).get('model_class', object)):
            return {
                'is_quantum_model': False,
                'name': getattr(model.__class__, '__name__', 'Unknown')
            }
        
        info = model.get_model_info()
        info['is_quantum_model'] = True
        
        # Test method availability
        info['methods_available'] = {
            'take_action': hasattr(model, 'take_action') and callable(getattr(model, 'take_action')),
            'update': hasattr(model, 'update') and callable(getattr(model, 'update')),
            'run': model.supports_batch_execution,
            'reset': hasattr(model, 'reset') and callable(getattr(model, 'reset')),
            'get_results': hasattr(model, 'get_results') and callable(getattr(model, 'get_results')),
        }
        
        return info

    def print_model_summary(self, models):
        """Print a comprehensive summary of model capabilities in clean tabular format"""
        print("\nQUANTUM MODEL REGISTRY SUMMARY")
        print("=" * 60)
        
        step_wise_models = []
        batch_models = []
        
        for name, model in models.items():
            if isinstance(model, dict) and 'metadata' in model:
                metadata = model['metadata']
                model_type = metadata.get('model_type', 'unknown')
                if model_type == 'step-wise':
                    step_wise_models.append(name)
                elif model_type == 'batch':
                    batch_models.append(name)
            elif isinstance(model, self.configs.algorithm_configs.get('Quantum', {}).get('model_class', object)):
                if model.model_type == 'step-wise':
                    step_wise_models.append(model.__class__.__name__)
                elif model.model_type == 'batch':
                    batch_models.append(model.__class__.__name__)
        
        print("\nMODEL CATEGORIES:")
        print("-" * 40)
        print(f"| Step-wise Models  | {len(step_wise_models):<2} | {', '.join(step_wise_models)}")
        print(f"| Batch Models      | {len(batch_models):<2} | {', '.join(batch_models)}")
        print("-" * 40)
        
        print("\nFEATURES:")
        print("-" * 40)
        print("| Interface         | QuantumModel (ABC)          |")
        print("| Error Handling    | Enhanced Messages           |")
        print("| Metadata System   | Comprehensive Info          |")
        print("| Capability Detection | Automatic                |")
        print("=" * 60)



    def run_single_model(self, alg_name, base_model="Oracle", is_parallel=True):
        """Run a single model with retry logic, preserving and saving the best run."""
        model = None
        prev_model = None
        threshold = -1
        efficiency = -1
        final_reward = -1
        best_threshold = threshold
        best_reward = final_reward
        best_efficiency = efficiency
        if self.winner is None: self.winner = alg_name
        failed_attempts = {
            'total': 0, 'failed': 0, 'under_threshold': 0,
            'threshold': self._get_min_efficiency(alg_name)
        }
        oracle_reward = self.results[base_model].get('final_reward', 0.0)

        if alg_name == base_model: return base_model
        print(f"\n\t🔄 {str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Starting {alg_name:<20} in {'parallel' if is_parallel else 'sequence'}...")

        overwrite = self.configs.overwrite
        if alg_name not in self.results or self.results[alg_name]["final_reward"] <= 0:
            # self.configs.overwrite = True
            # results, model = self.run_algorithm(alg_name)
            # model = None  # don't keep this reference
        # else:
            while (threshold - failed_attempts['threshold'] <= 0) or efficiency <= 0:
                self.configs.overwrite = False  # always False during retries
                alg_result, temp_model = self.run_algorithm(alg_name)
                final_reward = alg_result.get('final_reward', 0.0)
                failed_attempts['failed'] += alg_result['retries']
                failed_attempts['total'] += alg_result['retries']
                threshold = final_reward / oracle_reward if oracle_reward > 0 else 0
                efficiency = threshold * 100 if oracle_reward > 0 else self.get_oracle_reward(reset=True)
                gap = 100 - efficiency

                # Retry logic and backup if it's worse
                if threshold < failed_attempts['threshold']:
                    failed_attempts['under_threshold'] += 1 if threshold > 0 else 0
                    failed_attempts['failed'] += 1 if threshold == 0 else 0
                    failed_attempts['total'] += 1
                    if threshold < best_threshold:
                        final_reward = best_reward
                        threshold = best_threshold
                        efficiency = best_efficiency
                        gap = 100 - efficiency

                # Save best results so far
                if threshold >= best_threshold:
                    best_threshold = threshold
                    best_reward = final_reward
                    best_efficiency = efficiency
                    self.results[alg_name] = alg_result
                    model = temp_model  # Save the best reference

                self.results[alg_name].update({'failed_attempts': failed_attempts})
                self.results[alg_name]['final_reward'] = final_reward
                self.results[alg_name]['efficiency'] = efficiency
                self.results[alg_name]['gap'] = gap

                if failed_attempts['under_threshold'] >= 3 or (hasattr(temp_model, 'resumed') and temp_model.resumed): break
                # if failed_attempts['under_threshold'] >= 3 or temp_model.state == 1:break

        # 🔐 Save best model after loop (not last model)
        if model is not None:
            try:
                self.configs.overwrite = True
                model.save()
                # print(f"\tBest model for {alg_name} saved.")
            except Exception as e: print(f"⚠️ Could not save best model: {e}")
            del model
            if gc: gc.collect()
        self.configs.overwrite = overwrite

        # Determine if this is the new winner
        alg_rewards = self.results[alg_name]["final_reward"]
        winner_rewards = self.results[self.winner]["final_reward"]
        if alg_rewards > winner_rewards: self.winner = alg_name

        self.save()
        return alg_name


    def get_oracle_reward(self, base_model, oracle_reward=0.0, reset=False):
        # if base_model in self.results: return self.results[base_model].get('final_reward', 0.0)
        print(f"\t{'Getting' if not reset else 'Resetting'} Oracle Rewards ...")
        model = None
        overwrite = self.configs.overwrite
        while oracle_reward <= 0:
            self.configs.overwrite = False
            self.results[base_model], model = self.run_algorithm(base_model)
            oracle_reward = self.results[base_model].get('final_reward', 0.0)
        
        if model is not None:
            self.configs.overwrite = True
            # Store only Oracle results in configs (lightweight)
            self.configs.base_model = model
            # Save and cleanup
            model.save()
            del model
            if gc: gc.collect()
            
        self.configs.overwrite = overwrite

        if oracle_reward == 0.0:
            raise RuntimeError(
                "[FATAL] Oracle returned zero total reward. "
                "This indicates reward generation or attack pattern is invalid."
            )

        return oracle_reward
    
    def run_experiment(self, frames_count=None, models=None, base_model='Oracle', attack_type=None, qubit_cap=None, neuralUCB='GNeuralUCB'):
        if attack_type is not None: self.configs.attack_type = attack_type
        if models is None: models = set(self.algorithm_configs.keys())
        if frames_count: self.frames_count = frames_count

        self.get_oracle_reward(base_model)
        scaled_capacity = int(self.capacity * self.configs.scale)
        # self.run_single_model(neuralUCB, base_model, is_parallel=False)

        for alg_name in models:
            if alg_name == base_model: continue
            if alg_name in self.results.keys(): print(f"\t{alg_name} WAS ALREADY PROCESSED")

            self.run_single_model(alg_name, base_model, is_parallel=False)
            under_thr = self.results[alg_name]['failed_attempts']['under_threshold']
            threshold = self.results[alg_name]['failed_attempts']['threshold']
            failed = self.results[alg_name]['failed_attempts']['failed']
            total = self.results[alg_name]['failed_attempts']['total']
            final_reward = self.results[alg_name]['final_reward']
            efficiency = self.results[alg_name]['efficiency']

            # NEEDS TO GO TO A HELPER METHOD
            print(f"\tEXP {self.id} {alg_name.upper():<20}: Reward={final_reward:07.2f}, Efficiency={efficiency:05.1f}% [Retries={total}, Failed={failed}, < Threshold={under_thr}, SCapacity={scaled_capacity}, Threshold={threshold}]")

        # NEEDS TO GO TO A HELPER METHOD
        self.display_experiment_conditions()
        winner_name = self.winner if self.winner else "NA"
        gap = self.results.get(self.winner, {}).get('gap', 100)
        print(f"\t-->🏆 EXP{self.id} Winner:{winner_name:<20}(Gap:{gap:05.1f}%) [Env:{str(self.environment)}, Attack:{str(self.environment.attack)} X Rate:{self.environment.attack_rate}, Frames:{self.environment.frame_length}, SCapacity={scaled_capacity}, Alloc={str(self.configs.allocator)}]")

        return {'results': self.results, 'winner': self.winner}


    def run_experiment_parallel(self, frames_count=None, models=None, base_model='Oracle', attack_type=None, qubit_cap=None, max_workers=None):
        """Enhanced parallel execution of multiple models simultaneously"""
        if attack_type is not None: self.configs.attack_type = attack_type
        if models is None: models = set(self.algorithm_configs.keys())
        if frames_count: self.frames_count =frames_count
        if max_workers is None: max_workers = min(len(models), mp.cpu_count())

        # self.results = {}
        # best_reward = -1.0
        self.get_oracle_reward(base_model)
        scaled_capacity = int(self.capacity*self.configs.scale)
        parallel_models = [m for m in models if m != base_model]

        # Execute models in parallel with controlled concurrency
        print(f"\n\t🚀{str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Running {len(parallel_models)} models in parallel (max_workers={max_workers})")
        print("\t", "="*100)
        
        self.winner = None
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all model tasks
            future_to_model = {
                executor.submit(self.run_single_model, model_name): model_name 
                for model_name in parallel_models if model_name != base_model
            }
            
            # Process results as they complete (live progress)
            for future in as_completed(future_to_model):
                alg_name = future.result()
                if len(self.results[alg_name]) == 0: continue
                try:
                    efficiency = self.results[alg_name]['efficiency']
                    final_reward = self.results[alg_name]['final_reward']
                    failed_attempts = self.results[alg_name]['failed_attempts']
                    
                    total = failed_attempts.get('total', 0)
                    failed = failed_attempts.get('failed', 0)
                    threshold = failed_attempts.get('threshold', 0)
                    under_thr= failed_attempts.get('under_threshold', 0)

                    # NEEDS TO GO TO A HELPER METHOD
                    print(f"\tEXP {self.id} {alg_name.upper():<20}: Reward={final_reward:07.2f}, Efficiency={efficiency:05.1f}% [Retries={total}, Failed={failed}, < Threshold={under_thr}, SCapacity={scaled_capacity}, Threshold={threshold}]")
                        
                except Exception as e:
                    print(f"❌ Parallel execution failed for {alg_name}: {e}")
                    self.results[alg_name] = {'final_reward': 0.0, 'error': str(e)}

        # NEEDS TO GO TO A HELPER METHOD
        self.display_experiment_conditions()
        print(f"\t-->🏆 EXP{self.id} Winner:{self.winner:<20}(Gap:{self.results.get(self.winner, {}).get('gap', 100):05.1f}%) [Env:{str(self.environment)}, Attack:{str(self.environment.attack)} X Rate:{self.environment.attack_rate}, Frames:{self.environment.frame_length}, SCapacity={scaled_capacity}, Alloc={str(self.configs.allocator)}]")
        return {'results': self.results, 'winner': self.winner}



    def get_or_create_model(self, alg_name, env_info, algorithm_seed):
        """Thread-safe model creation with caching"""
        cache_key = f"{alg_name}_{algorithm_seed}_{self.frames_count}"
        
        with self._model_lock:
            if cache_key in self._model_cache:
                model = self._model_cache[cache_key]
                if hasattr(model, 'reset'):
                    model.reset()  # Reset state but reuse instance
                return model
            
            # Create new model
            config = self.algorithm_configs[alg_name]
            model_class = config['model_class']
            model_kwargs = config['kwargs'].copy()
            model = model_class(
                configs=self.configs,
                X_n=env_info['contexts'],
                reward_list=env_info['reward_functions'],
                frame_number=self.frames_count,
                attack_list=env_info['attack_pattern'],
                capacity=self.capacity, 
                **model_kwargs
            )
            # model.set_capacity(self.capacity)
            
            # Cache for reuse (if stateless or has reset capability)
            if hasattr(model, 'reset') or getattr(model, 'stateless', False):
                self._model_cache[cache_key] = model
                
            return model


    async def run_experiments_async(self, experiment_configs):
        """Run multiple complete experiments asynchronously"""
        import asyncio
        
        async def run_single_experiment_async(config):
            """Async wrapper for single experiment"""
            loop = asyncio.get_event_loop()
            
            # Run in thread pool to avoid blocking
            result = await loop.run_in_executor(
                None,  # Use default thread pool
                self.run_experiment,
                config.get('frames_count'),
                config.get('models'),
                config.get('base_model', 'Oracle'),
                config.get('attack_type'),
                config.get('qubit_cap')
            )
            
            return config['experiment_id'], result
        
        # Execute all experiments concurrently
        tasks = [
            run_single_experiment_async(config) 
            for config in experiment_configs
        ]
        
        results = {}
        for task in asyncio.as_completed(tasks):
            exp_id, result = await task
            results[exp_id] = result
            print(f"\n\tExperiment {exp_id} completed")
        
        return results


    def optimize_parallel_execution(self, models, system_resources=None):
        """Determine optimal parallel execution strategy"""
        if system_resources is None:
            system_resources = {
                'cpu_cores': mp.cpu_count(),
                'memory_gb': self.estimate_available_memory(),
                'gpu_available': torch.cuda.is_available() if 'torch' in globals() else False
            }
        
        # Model complexity estimation
        model_complexity = {
            'Oracle': 1,      # Lightweight
            'EXPUCB': 2,      # Medium
            'GNeuralUCB': 4,  # Neural network intensive
            'EXPNeuralUCB': 5, # Most complex
            'CEXPNeuralUCB': 4,
            # 'EXPUCB':2,
            # 'LinUCB':2,
            # 'CPursuit':2, 
            # 'CEXPNeuralUCB':5,
            'CPursuitNeuralUCB':5,
            'iCPursuitNeuralUCB':5
        }
        
        total_complexity = sum(model_complexity.get(m, 3) for m in models)
        
        # Adaptive worker count based on complexity and resources
        if total_complexity <= system_resources['cpu_cores']:
            max_workers = len(models)  # Run all in parallel
        else:
            # Limit based on estimated resource usage
            max_workers = max(1, system_resources['cpu_cores'] // 2)
        
        return {
            'max_workers': max_workers,
            'batch_size': min(max_workers, len(models)),
            'memory_per_worker': system_resources['memory_gb'] // max_workers,
            'use_gpu': system_resources['gpu_available'] and any(
                'Neural' in m for m in models
            )
        }

    def estimate_available_memory(self):
        """Estimate available system memory in GB"""
        try:
            import psutil
            return psutil.virtual_memory().available // (1024**3)
        except ImportError:
            return 8  # Conservative default


    def run_experiment_with_live_progress(self, frames_count=None, models=None, **kwargs):
        """Enhanced experiment runner with live parallel progress tracking"""
        from tqdm import tqdm
        import time
        
        if models is None:  models = set(self.algorithm_configs.keys())
        print(f"\n🎯 PARALLEL QUANTUM EXPERIMENT")
        print(f"📊 Models: {len(models)} | Frames: {frames_count}")
        print("="*60)
        
        # Progress tracking
        model_progress = {model: 0 for model in models}
        completed_models = set()
        
        def update_progress_callback(model_name, progress_percent):
            """Callback for model progress updates"""
            model_progress[model_name] = progress_percent
            
            # Update display
            overall_progress = sum(model_progress.values()) / len(models)
            active_models = len([m for m in models if m not in completed_models])
            
            print(f"\t🔄 Overall: {overall_progress:05.1f}% | Active: {active_models}/{len(models)}")
        
        # Enhanced execution with progress
        start_time = time.time()
        results = self.run_experiment_parallel(
            frames_count=frames_count, 
            models=models,
            progress_callback=update_progress_callback,
            **kwargs
        )
        execution_time = time.time() - start_time
        
        print(f"\n\t⏱️  Total execution time: {execution_time:07.2f}s")
        print(f"\t-->🏆 Winner: {results['winner']}")
        
        return results

    def __repr__(self):
        return f"{self.__class__.__name__}_{self.id}"
