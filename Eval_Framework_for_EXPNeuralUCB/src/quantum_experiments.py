import gc, os, random, time, json, copy
import numpy as np
import torch
import inspect

from tqdm import tqdm
from quantum_environment import (
    AdversarialQuantumEnvironment,
    NoAttack,
    RandomAttack,
    MarkovAttack,
    AdaptiveAttack,
    OnlineAdaptiveAttack
)
from quantum_algorithms import (
    Oracle, 
    EXPNeuralUCB, 
    QuantumModel,
    validate_quantum_model,
    get_model_capabilities,
    create_model_registry
)

class QuantumExperimentRunner:
    """
    Next-Generation Dynamic Scientific Experiment Runner
    Features: QuantumModel OOP integration, automatic model type detection,
    enhanced error handling, comprehensive metadata tracking
    """

    def __init__(self, base_seed=12345, attack_type='markov', attack_intensity=1.0, enable_progress=True):
        self.base_seed = base_seed
        self.attack_type = attack_type
        self.attack_intensity = attack_intensity
        self.enable_progress = enable_progress
        self.environment = None
        self.experiment_seed = None

        # ENHANCED: QuantumModel-aware algorithm registry
        self.algorithms = {}
        self.algorithm_configs = {
            'Oracle': {
                'model_class': Oracle, 
                'seed_offset': 100, 
                'kwargs': {},
                'runner_type': 'step-wise'
            },
            'GNeuralUCB': {
                'model_class': EXPNeuralUCB, 
                'seed_offset': 200, 
                'kwargs': {'mode': 'neural', 'beta': 0.2},
                'runner_type': 'batch'
            },
            'EXPUCB': {
                'model_class': EXPNeuralUCB, 
                'seed_offset': 300, 
                'kwargs': {'mode': 'exp3', 'gamma_factor': 0.1, 'eta_factor': 0.005, 'beta': 0.2},
                'runner_type': 'batch'
            },
            'EXPNeuralUCB': {
                'model_class': EXPNeuralUCB, 
                'seed_offset': 400, 
                'kwargs': {'mode': 'hybrid', 'gamma_factor': 0.01, 'eta_factor': 0.05, 'beta': 0.2},
                'runner_type': 'batch'
            },
        }

        # cached per-run env data
        self.contexts = None
        self.reward_functions = None
        self.attack_pattern = None

        # experiment tracking
        self.experiment_metadata = []
        self.experiment_start_time = None

    # ---------- env / attack ----------
    def _make_attack(self):
        """
        Create attack strategy based on attack_type.
        
        Attack Types:
        - 'none': No attacks
        - 'random': RandomAttack with rate based on intensity
        - 'markov': MarkovAttack with Markov chain behavior
        - 'adaptive': AdaptiveAttack (offline batch adaptive)
        - 'online_adaptive': OnlineAdaptiveAttack (online real-time adaptive)
        """
        mapping = {
            'none': NoAttack(),
            
            'random': RandomAttack(
                attack_rate=0.25 * self.attack_intensity
            ),
            
            'markov': MarkovAttack(
                attack_rate=self.attack_intensity,
                k_attacks=max(1, min(2, int(round(2 * self.attack_intensity))))
            ),
            
            'adaptive': AdaptiveAttack(
                memory_window=50,
                attack_rate=self.attack_intensity,
                sticky_p=0.7
            ),
            
            'online_adaptive': OnlineAdaptiveAttack(
                memory_window=50,
                attack_rate=self.attack_intensity,
                k=max(1, min(2, int(round(2 * self.attack_intensity)))),
                decay=0.97,
                temperature=0.5
            )
        }
        
        if self.attack_type not in mapping:
            print(f"WARNING: Unknown attack_type='{self.attack_type}', falling back to 'markov'")
            print(f"Available attack types: {list(mapping.keys())}")
            return MarkovAttack(attack_rate=self.attack_intensity)
        
        return mapping[self.attack_type]


    def create_environment(self, frame_length, qubit_capacities=(8, 10, 8, 9)):
        # validate parameters before creating environment
        self._validate_params()

        attack_strategy = self._make_attack()
        self.environment = AdversarialQuantumEnvironment(
            qubit_capacities=qubit_capacities,
            frame_length=frame_length,
            attack=attack_strategy,
            seed=self.experiment_seed,
        )
        print(f"Environment: {self.attack_type} (intensity={self.attack_intensity})")

    # ---------- ENHANCED: main entry with intelligent model handling ----------
    def run_single_experiment(self, frame_count, experiment_id, qubit_capacities=(8, 10, 8, 9)):
        print(f"\nEXPERIMENT {experiment_id}: {frame_count} frames, quibit capacities: {qubit_capacities}")

        # track experiment timing
        self.experiment_start_time = time.time()
        self.experiment_seed = self.base_seed + experiment_id

        # seed all RNGs before building env/attacks for determinism
        self._set_all_seeds(self.experiment_seed)

        # build env (rebuild if horizon changes)
        if self.environment is None or getattr(self.environment, "frame_length", None) != frame_count:
            self.create_environment(frame_count)

        # fetch env info
        env_info = self.environment.get_environment_info()
        self.contexts = env_info['contexts']
        self.reward_functions = env_info['reward_functions']
        self.attack_pattern = env_info['attack_pattern']

        # sanity checks + dtype normalization
        self._assert_env_shapes(frame_count)

        # ENHANCED: run algorithms with automatic model type detection
        print(f"Running algorithms: {list(self.algorithm_configs.keys())}")
        for name, cfg in self.algorithm_configs.items():
            try:
                print(f"   Running {name}...")
                self._run_algorithm_intelligently(name, cfg, frame_count)
            except Exception as e:
                print(f"   ERROR: {name} failed: {e}")
                import traceback
                print(f"      Traceback: {traceback.format_exc()}")

        # record experiment metadata
        self._record_experiment_metadata(experiment_id, frame_count)

        self.print_experiment_summary()
        return self.get_results()

    # ---------- ENHANCED: intelligent algorithm execution ----------
    def _run_algorithm_intelligently(self, name, config, frame_count):
        # Set algorithm-specific seed
        self._set_all_seeds(self.experiment_seed + config['seed_offset'])

        # Instantiate model
        model_class = config['model_class']
        kwargs = dict(config.get('kwargs', {}))
        declared_runner_type = config.get('runner_type', 'auto')

        if model_class == Oracle:
            model = model_class(self.contexts, self.reward_functions, self.attack_pattern)
        elif model_class == EXPNeuralUCB:
            model = model_class(self.contexts, self.reward_functions, frame_count, **kwargs)
        else:
            # Generic best-effort: prefer (contexts, reward_list, frame_count, **kwargs)
            try:
                model = model_class(self.contexts, self.reward_functions, frame_count, **kwargs)
            except TypeError:
                model = model_class(**kwargs)

        # Validate QuantumModel
        if not validate_quantum_model(model):
            raise ValueError(f"Model {name} does not implement QuantumModel interface")

        # Capabilities + runner_type sanity
        capabilities = get_model_capabilities(model)
        actual_type = model.model_type
        if declared_runner_type != 'auto' and declared_runner_type != actual_type:
            print(f"   WARNING: {name}: declared runner_type='{declared_runner_type}' "
                f"but model reports '{actual_type}'. Using '{actual_type}'.")

        # Execute
        if capabilities['supports_batch_execution'] and actual_type == 'batch':
            model.run_experiment(self.attack_pattern, verbose=False)
        else:
            self._run_step_wise_model(name, model, frame_count)

        # Store
        self.algorithms[name] = model
        print(f"      COMPLETED: {name} ({actual_type}) completed successfully")

    def _get_appropriate_context_for_model(self, model, model_name):
        """
        Choose a context array that matches what the model expects.
        Prefers a (K, d) array whose d matches the model's own input dimension.
        Returns None for context-free models.
        """
        import inspect
        sig = inspect.signature(model.take_action)
        params = list(sig.parameters.values())

        # Case 1: take_action(self) -> no context
        if len(params) == 0:
            return None

        # Helper: try to infer expected d from model
        expected_d = None

        # LinUCB/LinTS: sigma_inv is (d, d)
        if hasattr(model, 'sigma_inv') and isinstance(getattr(model, 'sigma_inv'), np.ndarray):
            expected_d = model.sigma_inv.shape[0]

        # Neural* models: use first layer input size if available
        if expected_d is None and hasattr(model, 'net') and hasattr(model.net, 'affine1'):
            expected_d = getattr(model.net.affine1, 'in_features', None)

        # Fallback: if param looks like 'context'
        param_name = params[0].name if params else None
        expects_context_like = param_name and param_name.lower() in {'context', 'ctx', 'x', 'X'}

        # If this is one of your batch models (should not reach step-wise path)
        if model_name in {'GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB'}:
            return self.contexts[0]

        # Try to match on d across available path-contexts
        if expected_d is not None:
            for ctx in self.contexts:
                # ctx shape is (K, d); guard empty
                if hasattr(ctx, 'shape') and len(ctx.shape) == 2 and ctx.shape[1] == expected_d:
                    return ctx

        # Otherwise:
        if expects_context_like:
            return self.contexts[0]

        # Simple bandits (UCB/TS) often ignore context anyway
        if hasattr(model, 'q') and hasattr(model, 'N'):
            return None

        # Default
        return self.contexts[0]

    def _run_step_wise_model(self, name, model, frame_count):
        start_time = time.time()
        import inspect
        iterator = tqdm(range(frame_count),
                        desc=f"   {model.__class__.__name__}",
                        disable=not self.enable_progress or frame_count < 1000)

        total_reward, reward_trace = 0.0, []
        context_for_model = self._get_appropriate_context_for_model(model, name)
        needs_context = context_for_model is not None

        take_action_sig = inspect.signature(model.take_action)
        update_sig = inspect.signature(model.update)

        take_action_params = list(take_action_sig.parameters.values())
        update_params = list(update_sig.parameters.values())

        print(f"      Context strategy: {'context-aware' if needs_context else 'context-free'}")
        print(f"      take_action params: {len(take_action_params)}, update params: {len(update_params)}")

        # Helper: is first update param a context?
        def _update_wants_context():
            if not update_params:
                return False
            n = update_params[0].name.lower()
            return n in {'context', 'ctx', 'x'}

        update_expects_context_first = _update_wants_context()

        for t in iterator:
            try:
                # Action selection
                if len(take_action_params) == 0:
                    action_result = model.take_action()
                elif needs_context:
                    action_result = model.take_action(context_for_model)
                else:
                    action_result = model.take_action()

                # Normalize (path, action)
                if isinstance(action_result, tuple) and len(action_result) == 2:
                    path, action = action_result
                else:
                    path, action = 0, int(np.asarray(action_result).item())

                # Bounds check
                if not (0 <= path < len(self.reward_functions)):
                    print(f"      WARNING: Invalid path {path}, clipping to 0"); path = 0
                if not (0 <= action < len(self.reward_functions[path])):
                    print(f"      WARNING: Invalid action {action} for path {path}, clipping to 0"); action = 0

                # Reward
                base_reward = float(self.reward_functions[path][action])
                final_reward = base_reward * int(self.attack_pattern[t, path])

                # Update routing
                try:
                    if len(update_params) == 0:
                        pass  # no-op
                    elif len(update_params) >= 3:
                        if update_expects_context_first and needs_context:
                            model.update(self.contexts[path] if path < len(self.contexts) else context_for_model,
                                        action, final_reward)
                        else:
                            model.update(path, action, final_reward)
                    elif len(update_params) == 2:
                        # (action, reward) or (path, action)
                        try:
                            model.update(action, final_reward)
                        except TypeError:
                            model.update(path, action)
                    else:
                        # Fallbacks
                        try:
                            model.update(path, action, final_reward)
                        except Exception:
                            try:
                                model.update(action, final_reward)
                            except Exception:
                                pass
                except Exception as e:
                    print(f"      WARNING: update() failed: {e}")

                total_reward += final_reward
                reward_trace.append(total_reward)

            except Exception as e:
                print(f"      WARNING: Step {t} failed: {e}")
                reward_trace.append(total_reward)

        # Results (synthesize if needed)
        try:
            res = model.get_results()
            if not isinstance(res, dict):
                res = {}
        except Exception:
            res = {}

        res.setdefault('final_reward', total_reward)
        res.setdefault('reward_list', reward_trace)
        res.setdefault('regret_list', [0.0] * len(reward_trace))
        res.setdefault('path_action_list', [])
        res.setdefault('final_regret', 0.0)
        res.setdefault('mode', getattr(model, 'mode', getattr(model, 'model_type', 'step-wise')))

        # Ensure later calls return the synthesized payload
        setattr(model, 'get_results', (lambda r=res: r.copy()))

        print(f"      COMPLETED: {frame_count} steps, final reward: {total_reward:.2f}")
        model_time = time.time() - start_time
        print(f"      COMPLETED: in {model_time:.2f}s, final reward: {total_reward:.2f}")

    # ---------- reporting ----------
    def print_experiment_summary(self, oracle_efficiency_algorithm='EXPNeuralUCB'):
        results = self.get_results()
        execution_time = time.time() - self.experiment_start_time if self.experiment_start_time else 0
        
        print(f"\nRESULTS (completed in {execution_time:.2f}s):")
        print("=" * 60)

        for name, res in results.items():
            model = self.algorithms.get(name)
            model_type_str = f"({model.model_type})" if model and hasattr(model, 'model_type') else ""
            final = res.get('final_reward', float('nan'))
            print(f"   {name:<12} {model_type_str:<12}: {final:.2f}")

        if 'Oracle' in results:
            learners = [n for n in results if n != 'Oracle']
            if learners:
                winner = max(learners, key=lambda n: results[n].get('final_reward', float('-inf')))
                print(f"   WINNER: {winner}")
                if oracle_efficiency_algorithm in results:
                    eff = 100.0 * results[oracle_efficiency_algorithm].get('final_reward', 0.0) / \
                        max(1e-12, results['Oracle'].get('final_reward', 0.0))
                    print(f"   EFFICIENCY: {oracle_efficiency_algorithm} Oracle Efficiency: {eff:.1f}%")

        if hasattr(self.environment, "analyze_attacks"):
            stats = self.environment.analyze_attacks()
            if isinstance(stats, dict) and 'mean_attacks_per_frame' in stats:
                print(f"   ATTACKS: Mean attacks/frame: {stats['mean_attacks_per_frame']:.3f}")
        
        print("=" * 60)

    def get_results(self):
        """ENHANCED: Get results with model metadata"""
        results = {}
        for name, model in self.algorithms.items():
            model_results = model.get_results()
            # Add model metadata to results
            if hasattr(model, 'get_model_info'):
                model_results['model_info'] = model.get_model_info()
            results[name] = model_results
        return results

    # ---------- ENHANCED: mgmt with QuantumModel integration ----------
    def add_algorithm(self, name, model_class, seed_offset=500, runner_type='auto', **kwargs):
        """Add algorithm with automatic QuantumModel integration"""
        
        # ENHANCED: Validate model class
        if not issubclass(model_class, QuantumModel):
            raise ValueError(f"Model class {model_class.__name__} must inherit from QuantumModel")
        
        # ENHANCED: Auto-detect runner type if not specified
        if runner_type == 'auto':
            # Try to instantiate dummy model to detect type
            try:
                dummy_model = model_class(**kwargs) if kwargs else model_class()
                runner_type = dummy_model.model_type
            except:
                runner_type = 'step-wise'  # Safe default

        self.algorithm_configs[name] = {
            'model_class': model_class,
            'seed_offset': seed_offset,
            'kwargs': kwargs,
            'runner_type': runner_type
        }
        print(f"ADDED: algorithm: {name} ({runner_type} model)")

    def remove_algorithm(self, name):
        if name in self.algorithm_configs:
            del self.algorithm_configs[name]
            if name in self.algorithms:
                del self.algorithms[name]
            print(f"REMOVED: algorithm: {name}")

    def get_algorithm_names(self):
        return list(self.algorithm_configs.keys())

    def update_algorithm_params(self, name, **new_kwargs):
        """Update algorithm parameters without removing/adding"""
        if name in self.algorithm_configs:
            self.algorithm_configs[name]['kwargs'].update(new_kwargs)
            print(f"UPDATED: {name} params: {new_kwargs}")
        else:
            print(f"ERROR: Algorithm {name} not found")

    def get_algorithm_info(self, name=None):
        """ENHANCED: Get detailed algorithm information"""
        if name:
            if name in self.algorithm_configs:
                config = self.algorithm_configs[name]
                model = self.algorithms.get(name)
                info = {
                    'config': config,
                    'model_info': model.get_model_info() if model and hasattr(model, 'get_model_info') else None,
                    'capabilities': get_model_capabilities(model) if model else None
                }
                return info
            else:
                return None
        else:
            # Return info for all algorithms
            return {name: self.get_algorithm_info(name) for name in self.algorithm_configs}

    def full_experiment_cleanup(self):
        # ENHANCED: Reset models if they support it
        for name, model in self.algorithms.items():
            if hasattr(model, 'reset'):
                try:
                    model.reset()
                except:
                    pass  # Some models might not implement reset properly
        
        self.algorithms.clear()
        self.environment = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()

    # ---------- validation & metadata ----------
    def _validate_params(self):
        """ENHANCED: Validate algorithm parameters with QuantumModel awareness"""
        for name, cfg in self.algorithm_configs.items():
            kwargs = cfg.get('kwargs', {})
            model_class = cfg.get('model_class')

            # Validate model class
            if model_class and not issubclass(model_class, QuantumModel):
                raise ValueError(f"{name}: model_class must inherit from QuantumModel")

            # Standard parameter validation
            if 'beta' in kwargs:
                beta = kwargs['beta']
                if not (0 < beta <= 10):
                    raise ValueError(f"{name}: beta must be in (0,10], got {beta}")

            if 'gamma_factor' in kwargs:
                gamma = kwargs['gamma_factor']
                if not (0 < gamma <= 1):
                    raise ValueError(f"{name}: gamma_factor must be in (0,1], got {gamma}")

            if 'eta_factor' in kwargs:
                eta = kwargs['eta_factor']
                if not (0 < eta <= 1):
                    raise ValueError(f"{name}: eta_factor must be in (0,1], got {eta}")

        if not (0 <= self.attack_intensity <= 2):
            raise ValueError(f"attack_intensity must be in [0,2], got {self.attack_intensity}")

    def _record_experiment_metadata(self, experiment_id, frame_count):
        """ENHANCED: Record experiment metadata with QuantumModel info"""
        execution_time = time.time() - self.experiment_start_time if self.experiment_start_time else 0

        # ENHANCED: Include model information in metadata
        algorithm_info = {}
        for name, config in self.algorithm_configs.items():
            alg_info = copy.deepcopy(config)
            model = self.algorithms.get(name)
            if model:
                alg_info['model_metadata'] = model.get_model_info() if hasattr(model, 'get_model_info') else {}
                alg_info['model_capabilities'] = get_model_capabilities(model)
            algorithm_info[name] = alg_info

        metadata = {
            'experiment_id': experiment_id,
            'frame_count': frame_count,
            'base_seed': self.base_seed,
            'experiment_seed': self.experiment_seed,
            'attack_type': self.attack_type,
            'attack_intensity': self.attack_intensity,
            'algorithm_configs': algorithm_info,
            'execution_time': execution_time,
            'timestamp': time.time(),
            'quantum_model_version': 'enhanced_oop'  # Version tracking
        }

        self.experiment_metadata.append(metadata)

    def get_experiment_metadata(self):
        return self.experiment_metadata

    def save_metadata(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.experiment_metadata, f, indent=2, default=str)
        print(f"SAVED: Metadata saved to {filename}")

    def print_parameter_summary(self):
        """ENHANCED: Show model types and capabilities with clean output"""
        print(f"\nENHANCED EXPERIMENT CONFIGURATION:")
        print("=" * 60)
        print(f"| Base seed:        | {self.base_seed:<20} |")
        print(f"| Attack strategy:  | {self.attack_type:<20} |")
        print(f"| Attack intensity: | {self.attack_intensity:<20} |")
        print("-" * 60)
        print("| ALGORITHM CONFIGURATIONS:               |")
        print("-" * 60)

        for name, cfg in self.algorithm_configs.items():
            model_class = cfg.get('model_class')
            runner_type = cfg.get('runner_type', 'unknown')
            kwargs = cfg.get('kwargs', {})
            
            class_name = model_class.__name__ if model_class else 'Unknown'
            print(f"| {name:<12} | {class_name:<12} | {runner_type:<10} |")
            
            if kwargs:
                param_items = [f"{k}={v}" for k, v in kwargs.items()]
                param_str = ", ".join(param_items)
                # Wrap long parameter strings
                if len(param_str) > 50:
                    param_str = param_str[:47] + "..."
                print(f"|              | Parameters: {param_str:<25} |")
            else:
                print(f"|              | Parameters: default{'':<18} |")
            print("-" * 60)
        
        print("=" * 60)

    # ---------- utils ----------
    def _set_all_seeds(self, seed_value: int):
        random.seed(seed_value)
        os.environ['PYTHONHASHSEED'] = str(seed_value)
        np.random.seed(seed_value)
        torch.manual_seed(seed_value)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed_value)
            torch.cuda.manual_seed_all(seed_value)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

    def _assert_env_shapes(self, frame_count: int):
        assert frame_count > 0, "frame_count must be > 0"
        assert isinstance(self.contexts, (list, tuple)) and len(self.contexts) == 4, \
            "contexts must be list of 4 arrays"
        assert isinstance(self.reward_functions, (list, tuple)) and len(self.reward_functions) == 4, \
            "reward_list must be list of 4 lists"
        assert self.attack_pattern.shape == (frame_count, 4), \
            f"attack_pattern must be ({frame_count}, 4), got {self.attack_pattern.shape}"
        assert self.attack_pattern.dtype in (np.int8, np.int64, np.uint8, np.bool_), \
            "attack mask must be integer/bool dtype"
        self.attack_pattern = self.attack_pattern.astype(np.int8, copy=False)
        # NEW: ensure mask values are 0/1
        if not np.all((self.attack_pattern == 0) | (self.attack_pattern == 1)):
            raise ValueError("attack_pattern must be a 0/1 mask")

# =============================================================================
# ENHANCED: Usage examples with QuantumModel integration
# =============================================================================

def enhanced_basic_usage_example(qubit_capacities=(8, 10, 8, 9)):
    """ENHANCED: Basic usage with QuantumModel OOP"""
    print("ENHANCED BASIC USAGE EXAMPLE")
    print("=" * 50)

    runner = QuantumExperimentRunner(base_seed=42, attack_type='markov', attack_intensity=1.0)
    runner.print_parameter_summary()

    results = runner.run_single_experiment(frame_count=2000, experiment_id=1, qubit_capacities=qubit_capacities)
    
    # ENHANCED: Show detailed algorithm information
    print(f"\nAlgorithm Details:")
    print("-" * 40)
    for name, alg_info in runner.get_algorithm_info().items():
        if alg_info and alg_info['model_info']:
            model_info = alg_info['model_info']
            print(f"   {name}: {model_info['model_type']} model, batch support: {model_info['supports_batch_execution']}")

    runner.full_experiment_cleanup()
    return results

def enhanced_custom_model_example():
    """ENHANCED: Adding custom QuantumModel"""
    from quantum_algorithms import UCB  # Assuming UCB is available
    
    print("\nENHANCED CUSTOM MODEL EXAMPLE")
    print("=" * 50)

    runner = QuantumExperimentRunner()
    
    # ENHANCED: Add custom model with automatic type detection
    try:
        runner.add_algorithm('CustomUCB', UCB, seed_offset=600, K=4, c=1.5)
        
        runner.print_parameter_summary()
        results = runner.run_single_experiment(frame_count=1000, experiment_id=1)
        
    except Exception as e:
        print(f"Custom model example failed: {e}")
        print("This is expected if UCB is not available in quantum_algorithms")

    runner.full_experiment_cleanup()
    return None

def quantum_model_validation_example():
    """ENHANCED: Demonstrate QuantumModel validation"""
    print("\nQUANTUM MODEL VALIDATION EXAMPLE")
    print("=" * 50)
    
    runner = QuantumExperimentRunner()
    
    # Try to add a non-QuantumModel class
    try:
        class BadModel:
            def __init__(self):
                pass
        
        runner.add_algorithm('BadModel', BadModel)
    except ValueError as e:
        print(f"VALIDATION SUCCESS: Caught invalid model class: {e}")
    
    # Show model registry
    registry = create_model_registry()
    print(f"AVAILABLE: QuantumModel classes: {list(registry.keys())}")

# # Backward compatibility alias
# ExperimentRunner = QuantumExperimentRunner

# if __name__ == "__main__":
#     print("ENHANCED EXPERIMENT RUNNER WITH QUANTUM MODEL OOP")
#     print("=" * 60)

#     enhanced_basic_usage_example()
#     enhanced_custom_model_example()
#     quantum_model_validation_example()

#     print("\nAll enhanced examples completed successfully!")
#     print("=" * 60)
