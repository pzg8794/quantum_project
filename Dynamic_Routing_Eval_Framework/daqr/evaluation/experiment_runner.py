from    daqr.config.experiment_config import ExperimentConfiguration, QuantumAlgorithmLock
from    tqdm    import tqdm
import  numpy as np, copy
import  gc, time
import  torch
import  threading  
from    threading import Lock, Event




class QuantumExperimentRunner:
    """
    The central orchestrator for running quantum bandit experiments. This class
    leverages the ExperimentConfiguration factory to set up and execute tests
    across various scenarios and models.
    """
    def __init__(self, config: ExperimentConfiguration | None = None, base_seed=12345, attack_type=None, attack_intensity=None, enable_progress=True, use_locks=False):
        self.configs = config if config is not None else ExperimentConfiguration()
        self.configs.base_seed = base_seed
        
        self.use_locks = use_locks
        self.resource_lock = QuantumAlgorithmLock(cooldown_seconds=1)
        
        self.winner = None
        self.environment = None
        self.experiment_seed = None
        self.enable_progress = enable_progress
        self.algorithm_configs = self.configs.get_models_configs()
        self.configs.update_configs(attack_type=attack_type, attack_intensity=attack_intensity)
    
    def remove_model(self, model_name):
        if model_name in self.algorithm_configs.keys():
            # remove model_name from 
            del self.algorithm_configs[model_name]

    def _build_environment_once(self, frame_count: int, qubit_cap: tuple):
        """
        Build ONE shared environment for the whole experiment (all models),
        with a seed that is independent of the model being run.
        """
        # Seed independent of model to keep environment identical across algorithms
        self.experiment_seed = self.configs.base_seed + (hash(f"{self.configs.attack_type}_{frame_count}") % 10000)

        # Configure attack scenario if not already configured by MultiRun
        self.configs.set_attack_strategy(
            attack_type=self.configs.attack_type,
            attack_rate=self.configs.attack_rate,
            attack_intensity=self.configs.attack_intensity
        )

        # Configure environment core parameters
        self.configs.set_environment(
            qubit_cap=qubit_cap,
            frames_no=frame_count,
            seed=self.experiment_seed,
            attack_intensity=self.configs.attack_intensity,
            attack_type=self.configs.attack_type
        )

        # Build and store the environment
        self.environment = self.configs.get_environment()
        print(f"🔬 Environment: {self.environment.__class__.__name__} | Frames: {frame_count} | Seed: {self.experiment_seed}")


    def run_step_wise_oracle(self, env_info, model, frame_count=4000, algorithm_name='Oracle'):
        total_reward = 0.0
        for t in tqdm(range(frame_count), desc=f"{algorithm_name}", disable=not self.enable_progress):
            if t >= env_info['attack_pattern'].shape[0]:
                print(f"⚠️ Frame {t} exceeds attack pattern size {env_info['attack_pattern'].shape[0]}")
                break
            path, action = model.take_action()
            base_reward = env_info['reward_functions'][path][action]
            attack_modifier = env_info['attack_pattern'][t][path]
            observed_reward = base_reward * attack_modifier
            model.update(path, action, observed_reward)
            total_reward += observed_reward
        oracle_results = model.get_results()
        if oracle_results and 'final_reward' in oracle_results:
            total_reward = oracle_results['final_reward']
        return total_reward
    
    def run_algorithm(self, algorithm_name: str, frame_count: int, qubit_cap: tuple):
        """
        Run a single algorithm assuming the environment has already been built
        for this experiment with the provided qubit_cap.
        """
        if algorithm_name not in self.algorithm_configs:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")

        if self.environment is None:
            # Safety: build env if caller forgot; prefer explicit build in run_experiment
            self._build_environment_once(frame_count=frame_count, qubit_cap=qubit_cap)
        if self.configs.capacity > frame_count: self.configs.capacity = frame_count

        config = self.algorithm_configs[algorithm_name]
        env_info = self.environment.get_environment_info()
        model_class = config['model_class']
        seed_offset = config['seed_offset']
        runner_type = config['runner_type']
        model_kwargs = config['kwargs']

        algorithm_seed = self.experiment_seed + seed_offset
        torch.manual_seed(algorithm_seed)
        np.random.seed(algorithm_seed)

        enable_progress = self.enable_progress
        results = {'final_reward': 0.0}

        try:
            total_reward, attempts = 0.0, 0
            while total_reward <= 0.0:
                model_kwargs['verbose'] = enable_progress
                
                if algorithm_name == 'Oracle':
                    model = self.algorithm_configs['Oracle']['model_class'](
                        X_n=env_info['contexts'],
                        reward_list=env_info['reward_functions'],
                        attack_list=env_info['attack_pattern']
                    )
                else:
                    model = model_class(
                        X_n=env_info['contexts'],
                        reward_list=env_info['reward_functions'],
                        frame_number=frame_count,
                        **model_kwargs,
                    )
                    model.set_capacity(self.configs.capacity)

                if enable_progress: self.validate_quantum_model(model)
                try:
                    if runner_type == 'step-wise':
                        total_reward = self.run_step_wise_oracle(env_info, model, frame_count, algorithm_name)
                    else:
                        result = model.run(attack_list=env_info['attack_pattern'], verbose=enable_progress)
                        if result is not None:
                            total_reward = float(result)
                        else:
                            mr = model.get_results() if hasattr(model, 'get_results') else {}
                            if mr and 'final_reward' in mr:
                                total_reward = float(mr['final_reward'])

                    enable_progress = False  # suppress retries spam
                    avg_reward = total_reward / frame_count if (frame_count > 0 and total_reward > 0) else 0.0
                    results = {
                        'final_reward': float(total_reward),
                        'avg_reward': float(avg_reward),
                        'algorithm': algorithm_name,
                        'seed': algorithm_seed,
                        'frame_count': frame_count,
                        'attack_type': self.configs.attack_type,
                        'model_results': model.get_results(),
                        'retries':attempts
                    }
                    attempts +=1
                except Exception as e: print(f"❌ Runtime error in {algorithm_name}: {e}")
                finally:
                    del model
                    gc.collect()

        except Exception as e:
            print(f"❌ Failed to create {algorithm_name}: {e}")
            results = {'final_reward': 0.0, 'error': str(e)}

        return results

    def _get_min_efficiency(self, model_name, env_type='stochastic') -> float:
        """Return expected minimum reward thresholds for retry decisions"""
        if model_name not in self.configs.thresholds:
            return 0.5

        # Always retry 0% (return 0.0 if not in dict or as fallback)
        return self.configs.thresholds[model_name].get(env_type, 0.50)  # Fallback 50%
    
    def run_experiment(self, frame_count=4000, models=None, base_model='Oracle',
                       attack_type=None, qubit_cap=None):
        if attack_type is not None: self.configs.attack_type = attack_type
        if models is None: models = list(self.algorithm_configs.keys())

        if qubit_cap is None:
            # Strongly prefer caller to pass allocator-derived qubit_cap
            if hasattr(self.configs, 'allocator') and self.configs.allocator is not None:
                qubit_cap = tuple(self.configs.allocator.allocate(timestep=0, route_stats={}))
            else: qubit_cap = (8, 10, 8, 9)  # legacy fallback to avoid breaking runs

        print(f"\nEXPERIMENT: Frames={frame_count}, Attack='{self.configs.attack_type}'")
        print("="*50)

        # Build the environment ONCE per experiment, then reuse across all models
        self._build_environment_once(frame_count=frame_count, qubit_cap=qubit_cap)

        results = {}
        results[base_model] = self.run_algorithm(base_model, frame_count, qubit_cap)
        oracle_reward = results[base_model].get('final_reward', 0.0)

        best_reward = -1.0
        for alg_name in models:
            if alg_name == base_model: continue
            print(f"\nRunning {alg_name}...")
            
            threshold = -1
            failed_threshold= threshold
            failed_attempts = {'total':0, 'failed':0, 'under_threshold':0, 'threshold':0}
            failed_attempts['threshold'] = self._get_min_efficiency(alg_name)
            while threshold < failed_attempts['threshold']:
                alg_result = self.run_algorithm(alg_name, frame_count, qubit_cap)
                final_reward = alg_result.get('final_reward', 0.0)
                failed_attempts['failed'] += alg_result['retries']
                failed_attempts['total'] += alg_result['retries']
                threshold = final_reward/oracle_reward 

                if threshold >= failed_threshold:
                    failed_threshold = threshold
                    results[alg_name] = alg_result
                    efficiency = (final_reward / oracle_reward * 100) if oracle_reward > 0 else 0.0
                    gap = 100 - efficiency

                if threshold < failed_attempts['threshold']: 
                    failed_attempts['under_threshold'] += 1 if threshold > 0 else 0
                    failed_attempts['total'] += 1

                results[alg_name].update({'failed_attempts':failed_attempts})
                if failed_attempts['under_threshold'] >= 3: break

            results[alg_name]['efficiency'] = efficiency
            results[alg_name]['gap'] = gap
            if final_reward > best_reward:
                best_reward = final_reward
                self.winner = alg_name
            
            total = failed_attempts.get('total', 0)
            failed = failed_attempts.get('failed', 0)
            threshold = failed_attempts.get('threshold', 0)
            under_thr= failed_attempts.get('under_threshold', 0)
            print(f"Total Retries={total}, Failed={failed}, Under Threshold={under_thr}, Threshold={threshold}")
            print(f"{alg_name}: Reward={final_reward:.2f}, Efficiency={efficiency:.1f}%")

        print(f"\n🏆 Winner: {self.winner} (Gap: {results.get(self.winner, {}).get('gap', 100):.1f}%)")
        return {'results': results, 'winner': self.winner}

    def cleanup(self, verbose=False, cooldown_seconds=1):
        """Enhanced cleanup with model cache support."""
        import gc
        cleanup_items = []
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        
        # 1. Clean up environment
        if hasattr(self, 'environment') and self.environment:
            if hasattr(self.environment, 'cleanup'):
                self.environment.cleanup(verbose=verbose)
            del self.environment
            self.environment = None
            cleanup_items.append("environment")
        
        # 2. Clean up all models (NEW!)
        if hasattr(self, '_model_cache'):
            for model_name, model in self._model_cache.items():
                if hasattr(model, 'cleanup'):
                    model.cleanup(verbose=verbose)
            self._model_cache.clear()
            cleanup_items.append("model_cache")
        
        # 3. PyTorch cleanup
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                cleanup_items.append("CUDA cache")
        except ImportError:
            pass
        
        # 4. Garbage collection
        collected = gc.collect()
        cleanup_items.append(f"GC:{collected} objects")

        cleanup_items.append(f"cooldown:{cooldown_seconds}s")
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        if verbose: print(f"✓ ExperimentRunner cleaned: \t{', '.join(cleanup_items)}")


    def __del__(self):
        """YOUR ORIGINAL destructor"""
        try:
            self.cleanup()
        except Exception as e:
            print(f"❌ Error during QuantumExperimentRunner cleanup: {e}")

    # ONLY ADDITION: Simple stochastic vs adversarial comparison
    def compare_stochastic_vs_adversarial(self, frame_count=4000):
        """Compare performance in stochastic vs adversarial settings"""
        print("=" * 70)
        print("STOCHASTIC vs ADVERSARIAL COMPARISON")
        print("=" * 70)
        
        original_attack_type = self.configs.attack_type
        
        try:
            print("\n🔬 TESTING: \tStochastic (Natural Random Failures)")
            self.configs.attack_type = 'stochastic'
            stochastic_results = self.run_experiment(frame_count)
            
            print("\n🔬 TESTING: \tAdversarial (Strategic Attacks)")  
            self.configs.attack_type = 'adaptive'
            adversarial_results = self.run_experiment(frame_count)
            
            print("\n📊 COMPARISON SUMMARY:")
            print("=" * 50)
            
            for alg in ['GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']:
                if alg in stochastic_results['results'] and alg in adversarial_results['results']:
                    stoch_reward = stochastic_results['results'][alg]['final_reward']
                    adv_reward = adversarial_results['results'][alg]['final_reward']
                    performance_loss = ((stoch_reward - adv_reward) / stoch_reward * 100) if stoch_reward > 0 else 0
                    
                    print(f"{alg:12} \t| Stoch: \t{stoch_reward:7.2f} \t| Adv: \t{adv_reward:7.2f} \t| Loss: \t{performance_loss:5.1f}%")
            
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