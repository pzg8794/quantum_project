import gc, os, random, time, json, copy
import numpy as np
import torch
import inspect
from tqdm import tqdm

from quantum_environment import AdversarialQuantumEnvironment, NoAttack, RandomAttack, MarkovAttack, AdaptiveAttack, OnlineAdaptiveAttack
from quantum_algorithms import Oracle, EXPNeuralUCB, PNeuralUCB, CEXPNeuralUCB, validate_quantum_model


class QuantumExperimentRunner:
    """
    SIMPLE FIX: Your original working framework + minimal stochastic vs adversarial addition
    """

    def __init__(self, base_seed=12345, attack_type="markov", attack_intensity=1.0, enable_progress=True):
        self.base_seed = base_seed
        self.attack_type = attack_type  # Only change: added attack_type parameter
        self.attack_intensity = attack_intensity
        self.enable_progress = enable_progress
        self.environment = None
        self.experiment_seed = None

        # YOUR ORIGINAL algorithm configurations
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
                'runner_type': 'batch'  # YOUR ORIGINAL SETTING
            },
            'EXPUCB': {
                'model_class': EXPNeuralUCB, 
                'seed_offset': 300, 
                'kwargs': {'mode': 'exp3', 'gamma_factor': 0.1, 'eta_factor': 0.005, 'beta': 0.2},
                'runner_type': 'batch'  # YOUR ORIGINAL SETTING
            },
            'EXPNeuralUCB': {
                'model_class': EXPNeuralUCB, 
                'seed_offset': 400, 
                'kwargs': {'mode':'hybrid', 'gamma_factor':0.01, 'eta_factor':0.05, 'beta':0.2},
                'runner_type': 'batch'  # YOUR ORIGINAL SETTING
            },
            # 'PNeuralUCB': {
            #     'model_class': PNeuralUCB,
            #     'seed_offset': 500,
            #     'kwargs': {
            #                 # 'prediction_window': 5,
            #                 # 'confidence_threshold': 0.6,
            #                 'beta': 0.2
            #             },
            #     'runner_type': 'batch'
            # }
            'CEXPNeuralUCB': {
                'model_class': CEXPNeuralUCB,  # Our new minimal inheritance class
                'seed_offset': 500,
                'kwargs': {
                    'mode': 'cmab',
                    'beta': 0.2,
                    'n_experts': 4
                },
                'runner_type': 'batch'
            }
        }

    def remove_model(self, model_name):
        if model_name in self.algorithm_configs.keys():
            # remove model_name from 
            del self.algorithm_configs[model_name]

    def make_attack(self):
        """Only addition: create attack strategy based on attack_type"""
        attack_mapping = {
            'none': NoAttack(),
            'stochastic': RandomAttack(attack_rate=0.25 * self.attack_intensity),
            'random': RandomAttack(attack_rate=0.25 * self.attack_intensity),
            'markov': MarkovAttack(
                attack_rate=self.attack_intensity,
                k_attacks=max(1, min(2, int(round(2 * self.attack_intensity))))
            ),

            'adaptive': AdaptiveAttack(
                memory_window=50,
                attack_rate=self.attack_intensity,
                sticky_p=0.7
            ),
            'onlineadaptive': OnlineAdaptiveAttack(
                memory_window=50,
                attack_rate=self.attack_intensity,
                k=max(1, min(2, int(round(2 * self.attack_intensity)))),
                decay=0.97,
                temperature=0.5
            )
        }

        if self.attack_type not in attack_mapping:
            print(f"⚠️  WARNING: Unknown attack_type='{self.attack_type}', defaulting to 'markov'")
            return MarkovAttack(attack_rate=self.attack_intensity)

        return attack_mapping[self.attack_type]

    def setup_environment(self, frame_count=4000):
        """MINIMAL FIX: Only fix frame_length parameter"""
        self.experiment_seed = self.base_seed + hash(f"{self.attack_type}_{frame_count}") % 10000

        attack_strategy = self.make_attack()

        # ONLY CHANGE: Use your attack_strategy instead of hardcoded MarkovAttack
        self.environment = AdversarialQuantumEnvironment(
            qubit_capacities=(8, 10, 8, 9), 
            frame_length=frame_count,  # CRITICAL FIX: was missing
            attack=attack_strategy,    # Use dynamic attack strategy
            seed=self.experiment_seed
        )

        print(f"🔬 Environment: {frame_count} frames, seed={self.experiment_seed}")
        return self.environment

    def run_algorithm(self, algorithm_name, frame_count=4000):
        """YOUR ORIGINAL METHOD - minimal changes"""
        if not self.environment:
            self.setup_environment(frame_count)

        # ONLY CHANGE: Always recreate environment with correct frame_count
        self.setup_environment(frame_count)

        if algorithm_name not in self.algorithm_configs:
            raise ValueError(f"Unknown algorithm: {algorithm_name}. Available: {list(self.algorithm_configs.keys())}")

        config = self.algorithm_configs[algorithm_name]
        model_class = config['model_class']
        seed_offset = config['seed_offset']
        model_kwargs = config['kwargs']
        runner_type = config['runner_type']

        # Create model instance
        algorithm_seed = self.experiment_seed + seed_offset
        torch.manual_seed(algorithm_seed)
        np.random.seed(algorithm_seed)

        try:
            # Get environment data required by all algorithms
            env_info = self.environment.get_environment_info()
            
            if algorithm_name == 'Oracle':
                model = Oracle(
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

            validate_quantum_model(model)

        except Exception as e:
            print(f"❌ Failed to create {algorithm_name}: {e}")
            return {'final_reward': 0.0, 'error': str(e)}

        # YOUR ORIGINAL execution logic
        total_reward = 0.0

        try:
            if runner_type == 'step-wise':
                # YOUR ORIGINAL Oracle step-wise execution
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
                
            else:
                # YOUR ORIGINAL batch execution for EXPNeuralUCB
                result = model.run_experiment(
                    attack_list=env_info['attack_pattern'],
                    verbose=self.enable_progress
                )
                
                if result is not None:
                    total_reward = float(result)
                else:
                    if hasattr(model, 'get_results'):
                        model_results = model.get_results()
                        if model_results and 'final_reward' in model_results:
                            total_reward = float(model_results['final_reward'])
                        else:
                            total_reward = 0.0
                    else:
                        total_reward = 0.0
                
            results = {
                'final_reward': float(total_reward),
                'avg_reward': float(total_reward / frame_count) if frame_count > 0 else 0.0,
                'algorithm': algorithm_name,
                'frame_count': frame_count,
                'attack_type': self.attack_type,
                'seed': algorithm_seed
            }

        except Exception as e:
            print(f"❌ Runtime error in {algorithm_name}: {e}")
            results = {
                'final_reward': 0.0,
                'error': str(e),
                'algorithm': algorithm_name,
                'frame_count': frame_count
            }

        # Cleanup
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

        return results

    def run_experiment(self, frame_count=4000, algorithms=["EXPNeuralUCB", 'GNeuralUCB', 'EXPUCB', 'Oracle']):
        """YOUR ORIGINAL METHOD with minimal attack category addition"""
        if algorithms is None:
            algorithms = list(self.algorithm_configs.keys())

        print(f"\n🔬 EXPERIMENT: {frame_count} frames")
        print(f"📊 Attack Type: {self.attack_type}")

        # ONLY ADDITION: Attack category identification
        category_map = {
            'none': 'Baseline',
            'stochastic': 'Stochastic', 
            'random': 'Stochastic',
            'markov': 'Adversarial',
            'adaptive': 'Adversarial',
            'onlineadaptive': 'Adversarial'
        }
        attack_category = category_map.get(self.attack_type, 'Unknown')
        print(f"🏷️  Category: {attack_category}")
        print("="*50)

        results = {}
        oracle_reward = None

        # YOUR ORIGINAL algorithm execution loop
        for algorithm_name in algorithms:
            print(f"\n🤖 Running {algorithm_name}...")

            result = self.run_algorithm(algorithm_name, frame_count)
            results[algorithm_name] = result

            if algorithm_name == 'Oracle':
                oracle_reward = result['final_reward']

            print(f"✅ {algorithm_name}: {result['final_reward']:.2f} reward")

        # YOUR ORIGINAL results processing
        gaps = {}
        winner = None
        best_reward = -float('inf')

        for alg_name, result in results.items():
            if alg_name == 'Oracle':
                continue

            if oracle_reward and oracle_reward > 0:
                gap = ((oracle_reward - result['final_reward']) / oracle_reward) * 100
                gaps[alg_name] = max(0.0, gap)
            else:
                gaps[alg_name] = float('inf')

            if result['final_reward'] > best_reward:
                best_reward = result['final_reward']
                winner = alg_name

        # YOUR ORIGINAL return format with minimal addition
        experiment_results = {
            'id': int(time.time() * 1000) % 100000,
            'frame_count': frame_count,
            'attack_type': self.attack_type,
            'attack_category': attack_category,  # ONLY ADDITION
            'results': results,
            'gaps': gaps,
            'winner': winner,
            'oracle_reward': oracle_reward,
            'timestamp': time.time()
        }

        print(f"\n🏆 Winner: {winner} (Gap: {gaps.get(winner, 0):.1f}%)")
        print(f"📈 Oracle Efficiency: {(best_reward/oracle_reward*100):.1f}%" if oracle_reward else "N/A")

        return experiment_results

    def cleanup(self):
        """YOUR ORIGINAL cleanup method"""
        if hasattr(self, 'environment') and self.environment:
            del self.environment
            self.environment = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    def __del__(self):
        """YOUR ORIGINAL destructor"""
        self.cleanup()

    # ONLY ADDITION: Simple stochastic vs adversarial comparison
    def compare_stochastic_vs_adversarial(self, frame_count=4000):
        """Compare performance in stochastic vs adversarial settings"""
        print("=" * 70)
        print("STOCHASTIC vs ADVERSARIAL COMPARISON")
        print("=" * 70)
        
        original_attack_type = self.attack_type
        
        try:
            print("\n🔬 TESTING: Stochastic (Natural Random Failures)")
            self.attack_type = 'stochastic'
            stochastic_results = self.run_experiment(frame_count)
            
            print("\n🔬 TESTING: Adversarial (Strategic Attacks)")  
            self.attack_type = 'adaptive'
            adversarial_results = self.run_experiment(frame_count)
            
            print("\n📊 COMPARISON SUMMARY:")
            print("=" * 50)
            
            for alg in ['GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']:
                if alg in stochastic_results['results'] and alg in adversarial_results['results']:
                    stoch_reward = stochastic_results['results'][alg]['final_reward']
                    adv_reward = adversarial_results['results'][alg]['final_reward']
                    performance_loss = ((stoch_reward - adv_reward) / stoch_reward * 100) if stoch_reward > 0 else 0
                    
                    print(f"{alg:12} | Stoch: {stoch_reward:7.2f} | Adv: {adv_reward:7.2f} | Loss: {performance_loss:5.1f}%")
            
            return {
                'stochastic': stochastic_results,
                'adversarial': adversarial_results
            }
        
        finally:
            self.attack_type = original_attack_type


# YOUR ORIGINAL utility functions
def create_runner(**kwargs):
    """Factory function to create experiment runner."""
    return QuantumExperimentRunner(**kwargs)

def run_single_experiment(attack_type="markov", frame_count=4000, **kwargs):
    """Quick single experiment runner."""
    runner = QuantumExperimentRunner(attack_type=attack_type, **kwargs)
    results = runner.run_experiment(frame_count=frame_count)
    runner.cleanup()
    return results

def validate_attack_type(attack_type):
    """Validate if attack type is supported."""
    valid_types = ['none', 'stochastic', 'random', 'markov', 'adaptive', 'onlineadaptive']
    return attack_type in valid_types