from    daqr.config.experiment_config import ExperimentConfiguration, QuantumAlgorithmLock
from    tqdm    import tqdm
import  numpy as np, copy
import  gc, time
import  torch
import  threading  
from    threading import Lock, Event
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp
import psutil  # for memory estimation (optional)



class QuantumExperimentRunner:
    """
    The central orchestrator for running quantum bandit experiments. This class
    leverages the ExperimentConfiguration factory to set up and execute tests
    across various scenarios and models.
    """
    
    def __init__(self, id=0, config: ExperimentConfiguration | None = None, frames_count=4000, base_seed=12345, 
             attack_type=None, attack_intensity=None, enable_progress=False, use_locks=False, 
             capacity=None, max_workers=None):
        self.configs = config if config is not None else ExperimentConfiguration()
        self.configs.base_seed = base_seed
        
        self.use_locks = use_locks
        self.resource_lock = QuantumAlgorithmLock(cooldown_seconds=1)
        
        self.id = id
        self.results = {}
        self.winner = None
        self.environment = None
        self.experiment_seed = None
        self.frames_count = frames_count
        self.enable_progress = enable_progress
        self.algorithm_configs = self.configs.get_models_configs()
        self.capacity = capacity if capacity else self.frames_count
        self.configs.update_configs(attack_type=attack_type, attack_intensity=attack_intensity)
        
        # ADD these new parallel execution attributes
        self.max_workers = max_workers if max_workers else min(4, mp.cpu_count())
        self._model_cache = {}  # Cache for model reuse
        self._parallel_lock = threading.RLock()  # Thread-safe operations
        self._execution_stats = {'total_time': 0, 'parallel_efficiency': 0}
    
    
    def remove_model(self, model_name):
        if model_name in self.algorithm_configs.keys():
            # remove model_name from 
            del self.algorithm_configs[model_name]

    def display_experiment_conditions(self):
        "Display Experiment Conditions"
        print(f"\n{str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Env:{str(self.environment)}, Attack:{str(self.environment.attack)}, Rate:{self.environment.attack_rate}, Frames:{self.environment.frame_length}, QubitAlloc={str(self.configs.allocator)}, SC:{self.capacity*self.configs.scale} (Cap={self.capacity} x Scale={self.configs.scale}), Seed: {self.experiment_seed}")

    def _build_environment_once(self, frames_count: int, qubit_cap: tuple):
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
            attack_type=self.configs.attack_type
        )

        # Build and store the environment
        self.environment = self.configs.get_environment()
        print("="*150)
        self.display_experiment_conditions()
        print("="*150)


    def run_step_wise_oracle(self, env_info, model, frames_count=4000, algorithm_name='Oracle'):
        if frames_count: self.frames_count = frames_count
        total_reward = 0.0
        for t in tqdm(range(self.frames_count), desc=f"{algorithm_name}", disable=not self.enable_progress):
            if t >= env_info['attack_pattern'].shape[0]:
                print(f"\t⚠️ Frame {t} exceeds attack pattern size {env_info['attack_pattern'].shape[0]}")
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
    
    def run_algorithm(self, algorithm_name: str, enable_progress=False):
        """
        Run a single algorithm assuming the environment has already been built
        for this experiment with the provided qubit_cap.
        """
        if algorithm_name not in self.algorithm_configs: raise ValueError(f"Unknown algorithm: {algorithm_name}")

        config = self.algorithm_configs[algorithm_name]
        env_info = self.environment.get_environment_info()
        model_class = config['model_class']
        seed_offset = config['seed_offset']
        runner_type = config['runner_type']
        model_kwargs = config['kwargs']

        algorithm_seed = self.experiment_seed + seed_offset
        torch.manual_seed(algorithm_seed)
        np.random.seed(algorithm_seed)

        results = {'final_reward': 0.0}
        total_reward, attempts = 0.0, 0

        try:
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
                        frame_number=self.frames_count,
                        **model_kwargs,
                    )
                    model.set_capacity(self.capacity)

                if enable_progress: self.validate_quantum_model(model)
                try:
                    if runner_type == 'step-wise':
                        total_reward = self.run_step_wise_oracle(env_info, model, self.frames_count, algorithm_name)
                    else:
                        result = model.run(attack_list=env_info['attack_pattern'], verbose=enable_progress)
                        if result is not None:
                            total_reward = float(result)
                        else:
                            mr = model.get_results() if hasattr(model, 'get_results') else {}
                            if mr and 'final_reward' in mr:
                                total_reward = float(mr['final_reward'])

                    enable_progress = False  # suppress retries spam
                    avg_reward = total_reward / self.frames_count if (self.frames_count > 0 and total_reward > 0) else 0.0
                    results = {
                        'final_reward': float(total_reward),
                        'avg_reward': float(avg_reward),
                        'algorithm': algorithm_name,
                        'seed': algorithm_seed,
                        'frames_count': self.frames_count,
                        'attack_type': self.configs.attack_type,
                        'model_results': model.get_results(),
                        'retries':attempts
                    }
                except Exception as e: 
                    attempts +=1
                    print(f"\t❌ Runtime error in {algorithm_name}: {e}")
                finally:
                    del model
                    gc.collect()

        except Exception as e:
            print(f"\t❌ Failed to create {algorithm_name}: {e}")
            results = {'final_reward': 0.0, 'error': str(e)}

        return results

    def _get_min_efficiency(self, model_name, env_type='stochastic') -> float:
        """Return expected minimum reward thresholds for retry decisions"""
        if model_name not in self.configs.thresholds:
            return 0.5

        # Always retry 0% (return 0.0 if not in dict or as fallback)
        return self.configs.thresholds[model_name].get(env_type, 0.50)  # Fallback 50%

    def cleanup(self, verbose=False, cooldown_seconds=1):
        """Enhanced cleanup with parallel execution support."""
        import gc
        cleanup_items = []
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        
        # YOUR EXISTING CLEANUP (keep as-is)
        if hasattr(self, 'environment') and self.environment:
            if hasattr(self.environment, 'cleanup'):
                self.environment.cleanup(verbose=verbose)
            del self.environment
            self.environment = None
            cleanup_items.append("environment")
        
        # ADD: Clean up model cache
        if hasattr(self, '_model_cache'):
            for model_name, model in self._model_cache.items():
                if hasattr(model, 'cleanup'):
                    model.cleanup(verbose=verbose)
            self._model_cache.clear()
            cleanup_items.append("model_cache")
        
        # YOUR EXISTING PYTORCH/GC CLEANUP (keep as-is)
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                cleanup_items.append("CUDA cache")
        except ImportError:
            pass
        
        collected = gc.collect()
        cleanup_items.append(f"GC:{collected} objects")
        cleanup_items.append(f"cooldown:{cooldown_seconds}s")
        
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        if verbose: print(f"\t✓ ExperimentRunner cleaned: \t{', '.join(cleanup_items)}")



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





    def run_experiment(self, frames_count=None, models=None, base_model='Oracle',
                       attack_type=None, qubit_cap=None):
        if attack_type is not None: self.configs.attack_type = attack_type
        if models is None: models = list(self.algorithm_configs.keys())
        if frames_count: self.frames_count =frames_count

        if qubit_cap is None:
            # Strongly prefer caller to pass allocator-derived qubit_cap
            if self.configs.allocator is not None and not self.configs.allocator.has_allocated():
                qubit_cap = tuple(self.configs.allocator.allocate(timestep=0, route_stats={}, verbose=False))
            else: qubit_cap = (8, 10, 8, 9)  # legacy fallback to avoid breaking runs

        # Build the environment ONCE per experiment, then reuse across all models
        self._build_environment_once(frames_count=self.frames_count, qubit_cap=qubit_cap)

        def get_oracle_reward(base_model, oracle_reward=0.0):
            print("\tGetting Oracle Rewards ...")
            while oracle_reward <= 0:
                self.results[base_model] = self.run_algorithm(base_model)
                oracle_reward = self.results[base_model].get('final_reward', 0.0)
            return oracle_reward

        # setting capacity at the experiment level
        self.capacity = self.capacity*self.configs.scale

        self.results = {}
        best_reward = -1.0
        oracle_reward = get_oracle_reward(base_model)
        for alg_name in models:
            if alg_name == base_model: continue
            print(f"\n\t{str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Running {alg_name:<20}...")
            
            threshold = -1
            efficiency = -1
            final_reward = -1
            best_threshold= threshold
            best_reward = final_reward
            best_efficiency = efficiency
            failed_attempts = {'total':0, 'failed':0, 'under_threshold':0, 'threshold':0}
            oracle_reward = self.results[base_model].get('final_reward', 0.0)
            failed_attempts['threshold'] = self._get_min_efficiency(alg_name)

            while (threshold-failed_attempts['threshold'] <= 0)  or efficiency <= 0:
                alg_result = self.run_algorithm(alg_name)
                final_reward = alg_result.get('final_reward', 0.0)
                failed_attempts['failed'] += alg_result['retries']
                failed_attempts['total'] += alg_result['retries']
                threshold = final_reward/oracle_reward 
                efficiency = (threshold * 100) if oracle_reward > 0 else self.get_oracle_reward(reset=True)
                gap = 100 - efficiency

                if threshold < failed_attempts['threshold']: 
                    # print(f"\t\tEXP {self.id} {alg_name.upper()} Threshold: {threshold} \t", f"Expected Threshold: {failed_attempts['threshold']}", f"Efficiency: {efficiency}")
                    failed_attempts['under_threshold'] += 1 if threshold > 0 else 0
                    failed_attempts['failed'] += 1 if threshold == 0 else 0
                    failed_attempts['total'] += 1
                    if threshold < best_threshold:
                        final_reward = best_reward
                        threshold = best_threshold
                        efficiency = best_efficiency

                if threshold >= best_threshold:
                    best_threshold = threshold
                    best_reward = final_reward
                    best_efficiency = efficiency
                    self.results[alg_name] = alg_result

                self.results[alg_name].update({'failed_attempts':failed_attempts})
                if failed_attempts['under_threshold'] >= 3: break

            self.results[alg_name]['efficiency'] = efficiency
            self.results[alg_name]['gap'] = gap
            if final_reward > best_reward:
                best_reward = final_reward
                self.winner = alg_name
            
            total = failed_attempts.get('total', 0)
            failed = failed_attempts.get('failed', 0)
            threshold = failed_attempts.get('threshold', 0)
            under_thr= failed_attempts.get('under_threshold', 0)
            print(f"\tEXP {self.id} {alg_name.upper():<20}: Reward={final_reward:07.2f}, Efficiency={efficiency:05.1f}% [Retries={total}, Failed={failed}, < Threshold={under_thr}, Threshold={threshold}]")

        self.display_experiment_conditions()
        print(f"\t-->🏆 EXP{self.id} Winner:{self.winner:<20}(Gap:{self.results.get(self.winner, {}).get('gap', 100):05.1f}%) [Env:{str(self.environment)}, Attack:{str(self.environment.attack)} X Rate:{self.environment.attack_rate}, Frames:{self.environment.frame_length}, SCapacity={self.capacity}, Alloc={str(self.configs.allocator)}]")
        return {'results': self.results, 'winner': self.winner}


    def get_oracle_reward(self, base_model, oracle_reward=0.0, reset=False):
        print(f"\t{'Getting' if not reset else 'Resetting'} Oracle Rewards ...")
        while oracle_reward <= 0:
            self.results[base_model] = self.run_algorithm(base_model)
            oracle_reward = self.results[base_model].get('final_reward', 0.0)
        return oracle_reward

    def run_experiment_parallel(self, frames_count=None, models=None, base_model='Oracle', attack_type=None, qubit_cap=None, max_workers=None):
        """Enhanced parallel execution of multiple models simultaneously"""
        if attack_type is not None: self.configs.attack_type = attack_type
        if models is None: models = list(self.algorithm_configs.keys())
        if frames_count: self.frames_count =frames_count
        if max_workers is None: max_workers = min(len(models), mp.cpu_count())

        if qubit_cap is None:
            # Strongly prefer caller to pass allocator-derived qubit_cap
            if self.configs.allocator is not None and not self.configs.allocator.has_allocated():
                qubit_cap = tuple(self.configs.allocator.allocate(timestep=0, route_stats={}, verbose=False))
            else: qubit_cap = (8, 10, 8, 9)  # legacy fallback to avoid breaking runs

        # Build the environment ONCE per experiment, then reuse across all models
        self._build_environment_once(frames_count=self.frames_count, qubit_cap=qubit_cap)


        self.results = {}
        best_reward = -1.0
        self.get_oracle_reward(base_model)
        # setting capacity at the experiment level
        self.capacity = self.capacity*self.configs.scale
        parallel_models = [m for m in models if m != base_model]
        
        # Enhanced parallel execution with live progress
        def run_single_model(alg_name, base_model="Oracle"):
            """Run a single model with retry logic"""
            if alg_name == base_model: return {base_model:{}}
            print(f"\n\t🔄 {str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Starting {alg_name:<20} in parallel...")
            
            threshold = -1
            efficiency = -1
            final_reward = -1
            best_threshold= threshold
            best_reward = final_reward
            best_efficiency = efficiency
            failed_attempts = {'total':0, 'failed':0, 'under_threshold':0, 'threshold':0}
            oracle_reward = self.results[base_model].get('final_reward', 0.0)
            failed_attempts['threshold'] = self._get_min_efficiency(alg_name)

            while (threshold-failed_attempts['threshold'] <= 0)  or efficiency <= 0:
                alg_result = self.run_algorithm(alg_name)
                final_reward = alg_result.get('final_reward', 0.0)
                failed_attempts['failed'] += alg_result['retries']
                failed_attempts['total'] += alg_result['retries']
                threshold = final_reward/oracle_reward 
                efficiency = (threshold * 100) if oracle_reward > 0 else self.get_oracle_reward(reset=True)
                gap = 100 - efficiency

                if threshold < failed_attempts['threshold']: 
                    # print(f"\t\tEXP {self.id} {alg_name.upper()} Threshold: {threshold} \t", f"Expected Threshold: {failed_attempts['threshold']}", f"Efficiency: {efficiency}")
                    failed_attempts['under_threshold'] += 1 if threshold > 0 else 0
                    failed_attempts['failed'] += 1 if threshold == 0 else 0
                    failed_attempts['total'] += 1
                    if threshold < best_threshold:
                        final_reward = best_reward
                        threshold = best_threshold
                        efficiency = best_efficiency

                if threshold >= best_threshold:
                    best_threshold = threshold
                    best_reward = final_reward
                    best_efficiency = efficiency
                    self.results[alg_name] = alg_result

                self.results[alg_name].update({'failed_attempts':failed_attempts})
                if failed_attempts['under_threshold'] >= 3: break

            self.results[alg_name]['efficiency'] = efficiency
            self.results[alg_name]['gap'] = gap
            return alg_name

        # Execute models in parallel with controlled concurrency
        print(f"\n\t🚀{str(self.environment).upper()} ({str(self.environment.attack).upper()}) EXP {self.id}: Running {len(parallel_models)} models in parallel (max_workers={max_workers})")
        print("\t", "="*100)
        
        best_reward = -1
        self.winner = None
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all model tasks
            future_to_model = {
                executor.submit(run_single_model, model_name): model_name 
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
                    if final_reward > best_reward:
                        best_reward = final_reward
                        self.winner = alg_name
                    
                    total = failed_attempts.get('total', 0)
                    failed = failed_attempts.get('failed', 0)
                    threshold = failed_attempts.get('threshold', 0)
                    under_thr= failed_attempts.get('under_threshold', 0)
                    print(f"\tEXP {self.id} {alg_name.upper():<20}: Reward={final_reward:07.2f}, Efficiency={efficiency:05.1f}% [Retries={total}, Failed={failed}, < Threshold={under_thr}, SCapacity={self.capacity}, Threshold={threshold}]")
                        
                except Exception as e:
                    print(f"❌ Parallel execution failed for {alg_name}: {e}")
                    self.results[alg_name] = {'final_reward': 0.0, 'error': str(e)}

        self.display_experiment_conditions()
        print(f"\t-->🏆 EXP{self.id} Winner:{self.winner:<20}(Gap:{self.results.get(self.winner, {}).get('gap', 100):05.1f}%) [Env:{str(self.environment)}, Attack:{str(self.environment.attack)} X Rate:{self.environment.attack_rate}, Frames:{self.environment.frame_length}, SCapacity={self.capacity}, Alloc={str(self.configs.allocator)}]")
        return {'results': self.results, 'winner': self.winner}



    def get_or_create_model(self, algorithm_name, env_info, algorithm_seed):
        """Thread-safe model creation with caching"""
        cache_key = f"{algorithm_name}_{algorithm_seed}_{self.frames_count}"
        
        with self._model_lock:
            if cache_key in self._model_cache:
                model = self._model_cache[cache_key]
                if hasattr(model, 'reset'):
                    model.reset()  # Reset state but reuse instance
                return model
            
            # Create new model
            config = self.algorithm_configs[algorithm_name]
            model_class = config['model_class']
            model_kwargs = config['kwargs'].copy()
            
            if algorithm_name == 'Oracle':
                model = model_class(
                    X_n=env_info['contexts'],
                    reward_list=env_info['reward_functions'],
                    attack_list=env_info['attack_pattern']
                )
            else:
                model = model_class(
                    X_n=env_info['contexts'],
                    reward_list=env_info['reward_functions'],
                    frame_number=self.frames_count,
                    **model_kwargs,
                )
                model.set_capacity(self.capacity)
            
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
        
        if models is None:
            models = list(self.algorithm_configs.keys())
        
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
