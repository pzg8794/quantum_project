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
    def __init__(self, configs= None, env_type= "stochastic", base_seed=12345, attack_type="markov", attack_intensity=1.0, enable_progress=True, use_locks=False):
        
        self.use_locks = use_locks
        self.resource_lock = QuantumAlgorithmLock(cooldown_seconds=1)


        self.winner = None
        self.base_seed = base_seed
        self.experiment_seed = None
        self.enable_progress = enable_progress
        

        self.environment = None
        self.env_type = env_type
        self.attack_type = attack_type
        self.attack_intensity = attack_intensity
        if configs: self.configs = configs
        else: self.configs = ExperimentConfiguration()
        
        self.environment = self.configs.get_environment()
        # print(f"Environment loaded: {self.environment.__class__.__name__} | attack_rate={self.environment.attack_rate}")

        self.algorithm_configs = self.configs.get_models_configs()

        self.thresholds = {
                'EXPNeuralUCB': {'stochastic': 0.628, 'adversarial': 0.598},
                'CPursuitNeuralUCB': {'stochastic': 0.634, 'adversarial': 0.614},
                'GNeuralUCB': {'stochastic': 0.582, 'adversarial': 0.509},  # Added; higher stochastic for grouping
                'iCPursuitNeuralUCB': {'stochastic': 0.712, 'adversarial': 0.689}
            }


    
    def remove_model(self, model_name):
        if model_name in self.algorithm_configs.keys():
            # remove model_name from 
            del self.algorithm_configs[model_name]


    def set_experiment_seed(self, model_seed_offset: int, frame_count=None):
        """
        **CORRECTED FACTORY USAGE**: Configures and creates the appropriate
        environment using the decoupled configuration object.
        """
        # 1. Calculate the unique, deterministic seed for this specific run.
        frame_count = frame_count if frame_count else self.environment.frame_length
        self.experiment_seed = self.base_seed + hash(f"{self.attack_type}_{frame_count}_{model_seed_offset}") % 10000

        print(f"🔬 Environment: {self.environment.__class__.__name__} | Frames: {frame_count} | Experiment Seed: {self.experiment_seed}")


    def run_step_wise_oracle(self, env_info, model, frame_count=4000, algorithm_name='Oracle'):
        """Oracle execution for benchmarking"""
        # Oracle step-wise execution
        total_reward = 0.0
        for t in tqdm(range(frame_count), desc=f"{algorithm_name}", disable=not self.enable_progress):
            # Check bounds
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
    
    def run_algorithm(self, algorithm_name: str, frame_count: int, enable_progress=True):
        """
        Runs a single algorithm in a freshly configured environment.
        """
        if algorithm_name not in self.algorithm_configs:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")

        config = self.algorithm_configs[algorithm_name]
        env_info = self.environment.get_environment_info()
        
        model_class = config['model_class']
        seed_offset = config['seed_offset']
        runner_type = config['runner_type']
        model_kwargs = config['kwargs']
        model_kwargs['verbose'] = self.enable_progress

        # Create model instance
        self.set_experiment_seed(config['seed_offset'], frame_count)
        algorithm_seed = self.experiment_seed + seed_offset
        torch.manual_seed(algorithm_seed)
        np.random.seed(algorithm_seed)

        try:
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
                    **model_kwargs
                )

            if self.enable_progress: self.validate_quantum_model(model)

            try:
                if runner_type == 'step-wise':
                    total_reward = self.run_step_wise_oracle(env_info, model, frame_count, algorithm_name)

                else:
                    # batch execution for EXPNeuralUCB
                    result = model.run(attack_list=env_info['attack_pattern'], verbose=self.enable_progress)

                    if result is not None: total_reward = float(result)
                    else:
                        if hasattr(model, 'get_results'):
                            model_results = model.get_results()
                            if model_results and 'final_reward' in model_results:
                                total_reward = float(model_results['final_reward'])
                
                # raise exception
                self.enable_progress = False

                avg_reward = total_reward / frame_count if (frame_count > 0 and total_reward > 0) else 0.0    
                results = {
                    'final_reward': float(total_reward),
                    'avg_reward': float(avg_reward),
                    'algorithm': algorithm_name,
                    'seed': algorithm_seed,
                    'frame_count': frame_count,
                    'attack_type': self.attack_type,
                    'model_results': model.get_results()
                }

            except Exception as e:
                print(f"❌ Runtime error in {algorithm_name}: {e}")
                results = {
                    'final_reward': 0.0,
                    'error': str(e),
                    'model_results': {},
                    'frame_count': frame_count,
                    'algorithm': algorithm_name
                }

        except Exception as e:
            print(f"❌ Failed to create {algorithm_name}: {e}")
            results = {'final_reward': 0.0, 'error': str(e)}
            
        finally:
            # AUTOMATIC model cleanup
            if model is not None:
                # if hasattr(model, 'cleanup'):
                #     model.cleanup(verbose=False)
                del model
            gc.collect()
            
        return results

    def _run_algorithm_threaded(self, algorithm_name, frame_count, results_dict):
        """Thread-safe wrapper for algorithm execution"""
        
        # Acquire lock
        self.resource_lock.acquire(algorithm_name)
        
        try:
            # Run algorithm (your existing method)
            result = self.run_algorithm(algorithm_name, frame_count)
            
            # Store results (thread-safe dict update)
            results_dict[algorithm_name] = result
            
        except Exception as e:
            print(f"❌ {algorithm_name} crashed in thread: {e}")
            results_dict[algorithm_name] = {
                'final_reward': 0.0,
                'error': str(e),
                'frame_count': frame_count,
                'algorithm': algorithm_name
            }
        
        finally:
            # Always release lock (even if crash)
            self.resource_lock.release(algorithm_name)

    def run_experiment_models_sequential(self, results, models, frame_count=4000, base_model='Oracle'):
        best_reward = -1
        self.winner = None
        oracle_reward = results[base_model].get('final_reward', 100)

        # YOUR ORIGINAL algorithm execution loop AND CALCULATE GAP FUNCTION
        for algorithm_name in models:
            print(f"\nRunning {algorithm_name}...")
            if algorithm_name == base_model: continue
            
            results.update({algorithm_name:self.run_algorithm(algorithm_name, frame_count)})
            final_reward = results[algorithm_name].get('final_reward', 0.0)

            gap = ((oracle_reward - final_reward) / oracle_reward) * 100 if final_reward > 0 else 0.0
            results[algorithm_name].update({'efficiency': (final_reward/oracle_reward)*100})
            results[algorithm_name].update({'gap': gap})

            if best_reward == -1: 
                best_reward = results[algorithm_name]['final_reward'] 
                self.winner = algorithm_name
            elif results[algorithm_name]['final_reward'] > best_reward:
                best_reward = results[algorithm_name]['final_reward']
                self.winner = algorithm_name

            print(f"{algorithm_name.title()}:           \t{results[algorithm_name]['final_reward']:.2f} reward")
            print(f"{algorithm_name.title()} Gap:       \t{results[algorithm_name]['gap'] :.1f}%")
            print(f"{algorithm_name.title()} Efficiency:\t{results[algorithm_name]['efficiency'] :.1f}%")

    def run_experiment_models_threaded(self, results, models, frame_count=4000, base_model='Oracle'):
        """Parallel algorithm execution with threading"""
        
        best_reward = -1
        self.winner = None
        oracle_reward = results[base_model].get('final_reward', 100)
        print(f"\n🔄 Running {len(models)-1} models in parallel...")
        
        # Thread-safe results storage
        threaded_results = {}
        threads = []
        
        # Start all algorithm threads
        for algorithm_name in models:
            if algorithm_name == base_model: continue
            
            thread = threading.Thread(
                target=self._run_algorithm_threaded,
                args=(algorithm_name, frame_count, threaded_results)
            )
            threads.append(thread)
            thread.start()
            print(f"  ├─ Started thread for {algorithm_name}")
        
        # Wait for all threads to complete
        print(f"  └─ Waiting for all models to complete...")
        for thread in threads: thread.join()
        print(f"All models completed!\n")
        
        # Process results (same logic as sequential)
        for algorithm_name in threaded_results.keys():
            results[algorithm_name] = threaded_results[algorithm_name]
            final_reward = results[algorithm_name].get('final_reward', 0.0)

            gap = ((oracle_reward - final_reward) / oracle_reward) * 100 if final_reward > 0 else 0.0
            results[algorithm_name].update({'efficiency': final_reward/oracle_reward*100})
            results[algorithm_name].update({'gap': gap})

            if best_reward == -1:
                best_reward = results[algorithm_name]['final_reward']
                self.winner = algorithm_name
            elif results[algorithm_name]['final_reward'] > best_reward:
                best_reward = results[algorithm_name]['final_reward']
                self.winner = algorithm_name

            print(f"{algorithm_name.title()}:           \t{results[algorithm_name]['final_reward']:.2f} reward")
            print(f"{algorithm_name.title()} Gap:       \t{results[algorithm_name]['gap']:.1f}%")
            print(f"{algorithm_name.title()} Efficiency:\t{results[algorithm_name]['efficiency']:.1f}%")

    def run_experiment_models_with_locks(self, results, models, frame_count=4000, base_model='Oracle'):
        """Sequential execution with enforced locks and cooldown"""
        
        best_reward = -1
        self.winner = None
        oracle_reward = results[base_model].get('final_reward', 100)
        
        print(f"\n🔒 Running {len([a for a in models if a != base_model])} models with resource locks...")
        
        for algorithm_name in models:
            if algorithm_name == base_model:
                continue
            
            print(f"\n🔐 Acquiring lock for {algorithm_name}...")
            
            # Acquire lock (blocks if previous algorithm still cleaning up)
            self.resource_lock.acquire(algorithm_name)
            
            try:
                print(f"Lock acquired. Running {algorithm_name}...")
                
                # Run algorithm
                results[algorithm_name] = self.run_algorithm(algorithm_name, frame_count)
                final_reward = results[algorithm_name].get('final_reward', 0.0)

                # Calculate gap
                gap = ((oracle_reward - final_reward) / oracle_reward) * 100 if final_reward > 0 else 0.0
                results[algorithm_name].update({'efficiency': final_reward/oracle_reward*100})
                results[algorithm_name].update({'gap': gap})

                # Track best
                if best_reward == -1:
                    best_reward = results[algorithm_name]['final_reward']
                    self.winner = algorithm_name
                elif results[algorithm_name]['final_reward'] > best_reward:
                    best_reward = results[algorithm_name]['final_reward']
                    self.winner = algorithm_name

                # Print results
                print(f"{algorithm_name.title()}:           \t{results[algorithm_name]['final_reward']:.2f} reward")
                print(f"{algorithm_name.title()} Gap:       \t{results[algorithm_name]['gap']:.1f}%")
                print(f"{algorithm_name.title()} Efficiency:\t{results[algorithm_name]['efficiency']:.1f}%")
                
            except Exception as e:
                print(f"❌ {algorithm_name} crashed: {e}")
                results[algorithm_name] = {
                    'final_reward': 0.0,
                    'error': str(e),
                    'gap': 0.0,
                    'efficiency': 0.0
                }
            
            finally:
                # Always release lock with cooldown (even if crash)
                print(f"Cleaning up {algorithm_name} and enforcing cooldown...")
                self.resource_lock.release(algorithm_name)
                print(f"{algorithm_name} cleanup complete\n")


    def _get_min_efficiency(self, model_name, env_type='stochastic') -> float:
        """Return expected minimum reward thresholds for retry decisions"""
        if model_name not in self.thresholds:
            return 0.5

        # Always retry 0% (return 0.0 if not in dict or as fallback)
        return self.thresholds[model_name].get(env_type, 0.50)  # Fallback 50%
    

    def run_experiment(self, frame_count=4000, models=None, base_model='Oracle', attack_type=None, qubit_cap=None):
        """
        Main experiment execution loop.
        """
        if attack_type is not None: self.attack_type = attack_type
        if models is None: models = list(self.algorithm_configs.keys())
        
        print(f"\nEXPERIMENT: Frames={frame_count}, Attack='{self.attack_type}'")
        print("="*50)

        results = {}
        # Run Oracle first to establish a baseline
        results[base_model] = self.run_algorithm(base_model, frame_count) 
        oracle_reward = results[base_model].get('final_reward', 0.0)
        
        # Run other models
        best_reward = -1
        for alg_name in models:
            if alg_name == base_model: continue
            
            print(f"\nRunning {alg_name}...")

            threshold = -1
            self.enable_progress = True
            failed_attempts = {'total':0, 'failed':0, 'under_threshold':0, 'threshold':0}
            while threshold < failed_attempts['threshold']:
                alg_result = self.run_algorithm(alg_name, frame_count)
                final_reward = alg_result.get('final_reward', 0.0)
                results[alg_name] = alg_result

                # Calculate efficiency and gap
                threshold = final_reward/oracle_reward 
                failed_attempts['threshold'] = self._get_min_efficiency(alg_name)
                efficiency = (threshold * 100) if oracle_reward > 0 else 0
                gap = 100 - efficiency
                results[alg_name]['efficiency'] = efficiency
                results[alg_name]['gap'] = gap

                if final_reward > best_reward:
                    best_reward = final_reward
                    self.winner = alg_name

                if threshold < failed_attempts['threshold']: 
                    failed_attempts['total'] += 1
                    failed_attempts['failed'] += 1 if threshold <= 0 else 0
                    failed_attempts['under_threshold'] += 1 if threshold > 0 else 0

                self.enable_progress = False
                if failed_attempts['under_threshold'] >= 3: break
                # results[alg_name].update({'failed_attempts':failed_attempts})

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
        if verbose: print(f"✓ QuantumExperimentRunner cleaned: \t{', '.join(cleanup_items)}")


    def __del__(self):
        """YOUR ORIGINAL destructor"""
        try:
            self.cleanup()
        except Exception as e:
            print(f"❌ Error during QuantumQuantumExperimentRunner cleanup: {e}")

    # ONLY ADDITION: Simple stochastic vs adversarial comparison
    def compare_stochastic_vs_adversarial(self, frame_count=4000, qubit_cap=None):
        """Compare performance in stochastic vs adversarial settings"""
        print("=" * 70)
        print("STOCHASTIC vs ADVERSARIAL COMPARISON")
        print("=" * 70)
        
        original_attack_type = self.attack_type
        
        try:
            print("\n🔬 TESTING: \tStochastic (Natural Random Failures)")
            self.attack_type = 'stochastic'
            stochastic_results = self.run_experiment(frame_count, qubit_cap=qubit_cap)
            
            print("\n🔬 TESTING: \tAdversarial (Strategic Attacks)")  
            self.attack_type = 'adaptive'
            adversarial_results = self.run_experiment(frame_count, qubit_cap=qubit_cap)
            
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
            self.attack_type = original_attack_type


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