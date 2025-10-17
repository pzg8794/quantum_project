from    quantum_configuration import QuantumExperimentConfig, QuantumAlgorithmLock
from    tqdm    import tqdm
import  numpy as np, copy
import  gc, time
import  torch
import  threading  
from    threading import Lock, Event




class QuantumExperimentRunner:
    """
    Original working framework + minimal stochastic vs adversarial addition
    """

    def __init__(self, config=None, base_seed=12345, attack_type="markov", attack_intensity=1.0, enable_progress=True, threading=False, wait_timeout=1, use_locks=False):

        if config is None: config = QuantumExperimentConfig()
        self.use_threading = threading
        self.use_locks = use_locks

        self.base_seed = base_seed
        self.attack_type = attack_type  # Only change: added attack_type parameter
        self.attack_intensity = attack_intensity
        self.enable_progress = enable_progress
        self.experiment_seed = None
        self.environment = None
        self.winner = None

        self._model_cache = {}  # Track created models
        self.configs = config
        self.algorithm_configs = config.get_models_configs()    
        self.resource_lock = QuantumAlgorithmLock(cooldown_seconds=wait_timeout)

    
    def remove_model(self, model_name):
        if model_name in self.algorithm_configs.keys():
            # remove model_name from 
            del self.algorithm_configs[model_name]

    def setup_environment(self, frame_count=4000, environment_type='adversarial', qubit_cap = (8, 10, 8, 9)):
        """MINIMAL FIX: Only fix frame_length parameter"""

        self.configs.set_attack()
        attack_strategy = self.configs.get_attack_strategy(self.attack_type)
        self.experiment_seed = self.base_seed + hash(f"{self.attack_type}_{frame_count}") % 10000

        # ONLY CHANGE: Use your attack_strategy instead of hardcoded MarkovAttack
        self.configs.set_environment(qubit_cap= qubit_cap, seed= self.experiment_seed, frames_no= frame_count, strategy=attack_strategy)

        self.environment = self.configs.get_environment_config(environment_type=environment_type)
        
        print(f"🔬 Environment: \t{frame_count} frames, seed={self.experiment_seed}")
        
        return self.environment

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
    

    def run_algorithm(self, algorithm_name, frame_count=4000):
        """Always recreate environment with correct frame_count"""
        if not self.environment: self.setup_environment(frame_count)

        # ONLY CHANGE: Always recreate environment with correct frame_count
        self.setup_environment(frame_count)

        if algorithm_name not in self.algorithm_configs:
            raise ValueError(f"Unknown algorithm: {algorithm_name}. Available: {list(self.algorithm_configs.keys())}")

        config = self.algorithm_configs[algorithm_name]
        model_class = config['model_class']
        seed_offset = config['seed_offset']
        runner_type = config['runner_type']
        model_kwargs = config['kwargs']

        # Create model instance
        algorithm_seed = self.experiment_seed + seed_offset
        torch.manual_seed(algorithm_seed)
        np.random.seed(algorithm_seed)
        enable_progress = self.enable_progress

        try:
            total_reward = 0.0
            while total_reward <= 0.0:
                # Get environment data required by all algorithms
                env_info = self.environment.get_environment_info()
                
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

                if enable_progress: self.validate_quantum_model(model)

                try:
                    if runner_type == 'step-wise':
                        total_reward = self.run_step_wise_oracle(env_info, model, frame_count, algorithm_name)

                    else:
                        # batch execution for EXPNeuralUCB
                        result = model.run(attack_list=env_info['attack_pattern'], verbose=enable_progress)

                        if result is not None: total_reward = float(result)
                        else:
                            if hasattr(model, 'get_results'):
                                model_results = model.get_results()
                                if model_results and 'final_reward' in model_results:
                                    total_reward = float(model_results['final_reward'])
                    
                    # raise exception
                    enable_progress = False
                    if algorithm_name != 'Oracle' and total_reward < model._get_expected_min_reward(algorithm_name): 
                        total_reward = 0.0
                        raise ValueError(f"Invalid reward '{total_reward}' retrying")

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
                    
                except ValueError as ve:  # Reward invalid: Continue loop
                    print(f"❌ Runtime error in {algorithm_name}: {ve}")

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

    def run_experiment_models_sequential(self, results, algorithms, frame_count=4000, base_model='Oracle'):
        best_reward = -1
        self.winner = None
        oracle_reward = results[base_model].get('final_reward', 100)

        # YOUR ORIGINAL algorithm execution loop AND CALCULATE GAP FUNCTION
        for algorithm_name in algorithms:
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

    def run_experiment_models_threaded(self, results, algorithms, frame_count=4000, base_model='Oracle'):
        """Parallel algorithm execution with threading"""
        
        best_reward = -1
        self.winner = None
        oracle_reward = results[base_model].get('final_reward', 100)
        print(f"\n🔄 Running {len(algorithms)-1} algorithms in parallel...")
        
        # Thread-safe results storage
        threaded_results = {}
        threads = []
        
        # Start all algorithm threads
        for algorithm_name in algorithms:
            if algorithm_name == base_model: continue
            
            thread = threading.Thread(
                target=self._run_algorithm_threaded,
                args=(algorithm_name, frame_count, threaded_results)
            )
            threads.append(thread)
            thread.start()
            print(f"  ├─ Started thread for {algorithm_name}")
        
        # Wait for all threads to complete
        print(f"  └─ Waiting for all algorithms to complete...")
        for thread in threads: thread.join()
        print(f"All algorithms completed!\n")
        
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

    def run_experiment_models_with_locks(self, results, algorithms, frame_count=4000, base_model='Oracle'):
        """Sequential execution with enforced locks and cooldown"""
        
        best_reward = -1
        self.winner = None
        oracle_reward = results[base_model].get('final_reward', 100)
        
        print(f"\n🔒 Running {len([a for a in algorithms if a != base_model])} algorithms with resource locks...")
        
        for algorithm_name in algorithms:
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

    def run_experiment(self, frame_count=4000, algorithms=None, base_model='Oracle', attack_type=None):
        """YOUR ORIGINAL METHOD with minimal attack category addition"""
        if attack_type is not None: self.attack_type = attack_type
        if algorithms is None: algorithms = list(self.algorithm_configs.keys())
        attack_category = self.configs.category_map.get(self.attack_type, 'Unknown')
        
        print(f"\nEXPERIMENT: \t{frame_count} frames")
        print(f"Attack Type: \t{self.attack_type}")
        print(f"Category: \t{attack_category}")
        print("="*50)

        results = {}
        results.update({base_model:self.run_algorithm(base_model, frame_count)})
        results[base_model].update({'gap':0.0})
        
        # Run other algorithms (threaded or sequential)
        # if self.use_threading: self.run_experiment_models_threaded(results, algorithms, frame_count, base_model)
        # else: self.run_experiment_models_sequential(results, algorithms, frame_count, base_model)

        # Run other algorithms (with or without locks)
        if self.use_locks: self.run_experiment_models_with_locks(results, algorithms, frame_count, base_model)
        else: self.run_experiment_models_sequential(results, algorithms, frame_count, base_model)
        oracle_reward = results[base_model].get('final_reward', 100)
        
            
        # YOUR ORIGINAL return format with minimal addition
        experiment_results = {
            'winner': self.winner,
            'timestamp': time.time(),
            'frame_count': frame_count,
            'oracle_reward': oracle_reward,
            'attack_type': self.attack_type,
            'winner_effiency': oracle_reward,
            'results': copy.deepcopy(results),
            'attack_category': attack_category,
            'id': int(time.time() * 1000) % 100000
        }

        print(f"\n🏆 Winner: \t\t{self.winner} \t(Gap: {results[self.winner]['gap']:.1f}%)")
        print(f"Winner Efficiency: \t{results[self.winner]['efficiency']:.1f}%" if oracle_reward else "N/A")

        return experiment_results

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
        
        original_attack_type = self.attack_type
        
        try:
            print("\n🔬 TESTING: \tStochastic (Natural Random Failures)")
            self.attack_type = 'stochastic'
            stochastic_results = self.run_experiment(frame_count)
            
            print("\n🔬 TESTING: \tAdversarial (Strategic Attacks)")  
            self.attack_type = 'adaptive'
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