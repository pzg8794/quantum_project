import gc, os, random, time, json, copy
import numpy as np
import torch
import inspect

from quantum_environment    import NoAttack, RandomAttack, MarkovAttack, AdaptiveAttack, OnlineAdaptiveAttack
from quantum_algorithms     import iCEXP4, iCEpochGreedy, iCEpsilonGreedy, iCKernelUCB, iCThompsonSampling
from quantum_algorithms     import CEXP4, CEpochGreedy, CEpsilonGreedy, CKernelUCB, CThompsonSampling
from quantum_algorithms     import Oracle, GNeuralUCB, EXPUCB, EXPNeuralUCB, LinUCB, CEXPNeuralUCB, CPursuit, iCPursuit
from quantum_environment    import AdversarialQuantumEnvironment
from quantum_algorithms     import validate_quantum_model
from tqdm                   import tqdm




# =============================================================================
# MODEL NAME COLLECTIONS FOR TESTING
# =============================================================================

# Core Quantum Models (Original Research Models)
NEURAL_MODELS = [
    'Oracle',
    'GNeuralUCB', 
    'EXPUCB',
    'EXPNeuralUCB',
    # 'LinUCB',
    # 'CEXPNeuralUCB'
]

# Contextual Multi-Armed Bandit Models (CMAB)
CONTEXTUAL_MODELS = [
    'CEpsilonGreedy',
    'CEXP4',
    'CPursuit', 
    'CEpochGreedy',
    'CThompsonSampling',
    'CKernelUCB'
]

# Informed Contextual Multi-Armed Bandit Models (iCMAB with ARIMA)
INFORMED_CONTEXTUAL_MODELS = [
    'iCEpsilonGreedy',
    'iCEXP4', 
    'iCPursuit',
    'iCEpochGreedy',
    'iCThompsonSampling',
    # 'iCKernelUCB'
]

# Custom/Hybrid Models (Research Extensions)
CUSTOM_MODELS = [
    'CEXPNeuralUCB',  # Hybrid of CMAB + Neural UCB approach
    'LinUCB'
]

# =============================================================================
# COMPREHENSIVE MODEL GROUPS
# =============================================================================

# All CMAB-based models (Standard + Informed)
ALL_CMAB_MODELS = CONTEXTUAL_MODELS + INFORMED_CONTEXTUAL_MODELS

# All models for comprehensive testing
ALL_QUANTUM_MODELS = NEURAL_MODELS + CONTEXTUAL_MODELS + INFORMED_CONTEXTUAL_MODELS + CUSTOM_MODELS

# Step-wise models (for step-wise runner)
STEP_WISE_MODELS = CONTEXTUAL_MODELS + INFORMED_CONTEXTUAL_MODELS + ['LinUCB']

# Batch models (for batch runner)
BATCH_MODELS = ['Oracle', 'GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB', 'CEXPNeuralUCB']

# Models with prediction capabilities
PREDICTIVE_MODELS = INFORMED_CONTEXTUAL_MODELS + ['EXPNeuralUCB', 'CEXPNeuralUCB']

# =============================================================================
# TESTING PRESETS
# =============================================================================

# Quick test subset (representative models)
QUICK_TEST_MODELS = [
    'Oracle', 
    'EXPNeuralUCB',
    'CEpsilonGreedy', 
    'iCEpsilonGreedy'
]

# Performance comparison set
PERFORMANCE_COMPARISON_MODELS = [
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
RESEARCH_MODELS = [
    'Oracle',
    'EXPNeuralUCB',
    'CEXPNeuralUCB', 
    'iCEpsilonGreedy',
    'iCEXP4',
    'iCKernelUCB'
]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_model_category(model_name):
    """Return the category of a given model"""
    if model_name in NEURAL_MODELS:
        return 'Neural'
    elif model_name in CONTEXTUAL_MODELS:
        return 'Contextual'
    elif model_name in INFORMED_CONTEXTUAL_MODELS:
        return 'Informed_Contextual'
    elif model_name in CUSTOM_MODELS:
        return 'Custom'
    else:
        return 'Unknown'

def get_models_by_category(category):
    """Get all models in a specific category"""
    category_map = {
        'neural': NEURAL_MODELS,
        'contextual': CONTEXTUAL_MODELS,
        'informed': INFORMED_CONTEXTUAL_MODELS,
        'custom': CUSTOM_MODELS,
        'all_cmab': ALL_CMAB_MODELS,
        'all': ALL_QUANTUM_MODELS,
        'quick': QUICK_TEST_MODELS,
        'performance': PERFORMANCE_COMPARISON_MODELS,
        'research': RESEARCH_MODELS,
        'stepwise': STEP_WISE_MODELS,
        'batch': BATCH_MODELS,
        'predictive': PREDICTIVE_MODELS
    }
    return category_map.get(category.lower(), [])

def print_model_summary():
    """Print summary of all available models"""
    print("=" * 60)
    print("QUANTUM MODEL SUMMARY")
    print("=" * 60)
    print(f"Neural Models ({len(NEURAL_MODELS)}): {', '.join(NEURAL_MODELS)}")
    print(f"Contextual Models ({len(CONTEXTUAL_MODELS)}): {', '.join(CONTEXTUAL_MODELS)}")
    print(f"Informed Contextual Models ({len(INFORMED_CONTEXTUAL_MODELS)}): {', '.join(INFORMED_CONTEXTUAL_MODELS)}")
    print(f"Custom Models ({len(CUSTOM_MODELS)}): {', '.join(CUSTOM_MODELS)}")
    print(f"Total Models: {len(ALL_QUANTUM_MODELS)}")
    print("=" * 60)

# Example usage for testing:
# runner.run_experiment(algorithms=QUICK_TEST_MODELS)
# runner.run_experiment(algorithms=get_models_by_category('contextual'))
# runner.run_experiment(algorithms=PERFORMANCE_COMPARISON_MODELS)





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
        self.winner = None

        # YOUR ORIGINAL algorithm configurations
        self.algorithm_configs = {
            'Oracle': {
                'model_class': Oracle, 
                'seed_offset': 100, 
                'kwargs': {},
                'runner_type': 'step-wise'
            },
            'GNeuralUCB': {
                'model_class': GNeuralUCB, 
                'seed_offset': 200, 
                'kwargs': {'mode': 'neural', 'beta': 0.2},
                'runner_type': 'batch'  # YOUR ORIGINAL SETTING
            },
            'EXPUCB': {
                'model_class': EXPUCB, 
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

            # Updated algorithm configurations with individual CMAB models

            # =============================================================================
            # CMAB MODELS (Standard Contextual Multi-Armed Bandits)
            # =============================================================================

            'CEpsilonGreedy': {
                'model_class': CEpsilonGreedy,
                'seed_offset': 600,
                'kwargs': {
                    'epsilon': 0.1,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'CEXP4': {
                'model_class': CEXP4,
                'seed_offset': 610, 
                'kwargs': {
                    'gamma': 0.1,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'CPursuit': {
                'model_class': CPursuit,
                'seed_offset': 620,
                'kwargs': {
                    'learning_rate': 0.1,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'CEpochGreedy': {
                'model_class': CEpochGreedy,
                'seed_offset': 630,
                'kwargs': {
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'CThompsonSampling': {
                'model_class': CThompsonSampling,
                'seed_offset': 640,
                'kwargs': {
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'CKernelUCB': {
                'model_class': CKernelUCB,
                'seed_offset': 650,
                'kwargs': {
                    'gamma': 0.1,
                    'eta': 1.0,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            # =============================================================================
            # iCMAB MODELS (Informed CMAB with ARIMA Prediction)
            # =============================================================================

            'iCEpsilonGreedy': {
                'model_class': iCEpsilonGreedy,
                'seed_offset': 700,
                'kwargs': {
                    'epsilon': 0.1,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'iCEXP4': {
                'model_class': iCEXP4,
                'seed_offset': 710,
                'kwargs': {
                    'gamma': 0.1,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'iCPursuit': {
                'model_class': iCPursuit,
                'seed_offset': 720,
                'kwargs': {
                    'learning_rate': 0.1,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'iCEpochGreedy': {
                'model_class': iCEpochGreedy,
                'seed_offset': 730,
                'kwargs': {
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'iCThompsonSampling': {
                'model_class': iCThompsonSampling,
                'seed_offset': 740,
                'kwargs': {
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
            },

            'iCKernelUCB': {
                'model_class': iCKernelUCB,
                'seed_offset': 750,
                'kwargs': {
                    'gamma': 0.1,
                    'eta': 1.0,
                    'n_experts': 4
                },
                'runner_type': 'step-wise'
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
            'LinUCB': {
                'model_class': LinUCB,
                'seed_offset': 500,
                'kwargs': {
                    # LinUCB-specific parameters
                    'alpha': 1.0,                    # Confidence parameter (not beta)
                    'lambda_reg': 1.0,               # Regularization parameter
                    
                    # ContextualModelBase parameters
                    'n_features': 6,                 # Context feature dimension
                    'quantum_state_dim': 6,          # Quantum state dimension
                    'entanglement_aware': True,      # Enable quantum features
                    
                    # Optional enhancements
                    'prediction_window': 10,         # For contextual intelligence
                    'anomaly_threshold': 0.2         # For robustness detection
                },
                'runner_type': 'step-wise'           # LinUCB is step-wise, not batch
            },
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
                'seed': algorithm_seed,
                'model_results': model.get_results()
            }

        except Exception as e:
            print(f"❌ Runtime error in {algorithm_name}: {e}")
            results = {
                'final_reward': 0.0,
                'error': str(e),
                'algorithm': algorithm_name,
                'frame_count': frame_count,
                'model_results': {}
            }

        # Cleanup
        del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

        return results

    def run_experiment(self, frame_count=4000, algorithms=["EXPNeuralUCB", 'GNeuralUCB', 'EXPUCB'], base_model='Oracle'):
        """YOUR ORIGINAL METHOD with minimal attack category addition"""
        if algorithms is None: algorithms = list(self.algorithm_configs.keys())

        print(f"\nEXPERIMENT: {frame_count} frames")
        print(f"Attack Type: {self.attack_type}")

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
        print(f"Category: {attack_category}")
        print("="*50)

        results = {}
        oracle_reward = None

        oracle_results = self.run_algorithm(base_model, frame_count)
        oracle_reward = oracle_results['final_reward']
        results.update({base_model:oracle_results})
        results[base_model].update({'gap':0.0})

        gaps = {}
        self.winner = None
        best_reward = -1
        winner_efficiency = 0

        # YOUR ORIGINAL algorithm execution loop AND CALCULATE GAP FUNCTION
        for algorithm_name in algorithms:
            print(f"\nRunning {algorithm_name}...")
            if algorithm_name == base_model: continue

            results.update({algorithm_name:self.run_algorithm(algorithm_name, frame_count)})
            print(f"{algorithm_name}: {results[algorithm_name]['final_reward']:.2f} reward")

            if oracle_reward and oracle_reward > 0:
                gap = ((oracle_reward - results[algorithm_name]['final_reward']) / oracle_reward) * 100
                gaps[algorithm_name] = max(0.0, gap)
            else:   gaps[algorithm_name] = float('inf')

            results[algorithm_name].update({'gap':gaps[algorithm_name]})
            if best_reward == -1: 
                best_reward = results[algorithm_name]['final_reward'] 
                self.winner = algorithm_name
            elif results[algorithm_name]['final_reward'] > best_reward:
                best_reward = results[algorithm_name]['final_reward']
                self.winner = algorithm_name

        winner_efficiency = best_reward/oracle_reward*100
            
        # YOUR ORIGINAL return format with minimal addition
        experiment_results = {
            'id': int(time.time() * 1000) % 100000,
            'frame_count': frame_count,
            'attack_type': self.attack_type,
            'attack_category': attack_category,  # ONLY ADDITION
            'results': results,
            'gaps': gaps,
            'winner': self.winner,
            'oracle_reward': oracle_reward,
            'winner_effiency': winner_efficiency,
            'timestamp': time.time()
        }

        print(f"\n🏆 Winner: {self.winner} (Gap: {gaps.get(self.winner, 0):.1f}%)")
        print(f"Winner Efficiency: {winner_efficiency:.1f}%" if oracle_reward else "N/A")

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