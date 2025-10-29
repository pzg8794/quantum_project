from quantum_environment        import NoAttack, RandomAttack, MarkovAttack, AdaptiveAttack, OnlineAdaptiveAttack
from quantum_environment        import AdversarialQuantumEnvironment, StochasticQuantumEnvironment, QuantumEnvironment

from quantum_algorithms    import iCEXP4, iCEpochGreedy, iCEpsilonGreedy, iCKernelUCB, iCThompsonSampling
from quantum_algorithms    import CEXP4, CEpochGreedy, CEpsilonGreedy, CKernelUCB, CThompsonSampling
from quantum_algorithms    import Oracle, GNeuralUCB, EXPUCB, EXPNeuralUCB, LinUCB, CEXPNeuralUCB 
from quantum_algorithms    import UCB, RandomAlg, TS, LinTS, LinUCB, iCPursuitNeuralUCB, NeuralTS
from quantum_algorithms    import CPursuitNeuralUCB, CPursuit, iCPursuit, QuantumModel, NeuralUCB

import  gc, time
import  threading  
from    threading import Lock, Event


class QuantumAlgorithmLock:
    """Resource lock for sequential execution with guaranteed cleanup"""
    
    def __init__(self, cooldown_seconds=3):
        self.cooldown_seconds = cooldown_seconds
        self.current_holder = None
    
    def acquire(self, alg_name: str):
        """Acquire exclusive access (sequential, no actual blocking)"""
        if self.current_holder is not None:
            raise RuntimeError(f"Lock violation: {alg_name} tried to acquire while {self.current_holder} holds it!")
        self.current_holder = alg_name
    
    def release(self, alg_name: str):
        """Release with mandatory cleanup and cooldown"""
        if self.current_holder != alg_name:
            raise RuntimeError(f"Lock violation: {alg_name} tried to release but doesn't hold the lock!")
        
        # Mandatory cleanup
        gc.collect()
        
        # Mandatory cooldown
        if self.cooldown_seconds > 0:
            time.sleep(self.cooldown_seconds)
        
        self.current_holder = None
        
# class QuantumAlgorithmLock:
#     """Thread-safe resource manager for algorithm execution"""
    
#     def __init__(self, cooldown_seconds=3):
#         self.algorithm_lock = Lock()
#         self.algorithm_ready = Event()
#         self.algorithm_ready.set()  # Initially ready
#         self.cooldown_seconds = cooldown_seconds
    
#     def acquire(self, alg_name: str):
#         """Acquire lock for algorithm execution"""
#         self.algorithm_ready.wait()  # Wait for previous algorithm cleanup
#         self.algorithm_lock.acquire()
    
#     def release(self, alg_name: str):
#         """Release algorithm lock with cooldown"""
#         self.algorithm_ready.clear()  # Block next algorithm
        
#         # Cleanup
#         gc.collect()
#         time.sleep(self.cooldown_seconds)
        
#         # Release
#         self.algorithm_lock.release()
#         self.algorithm_ready.set()



class QuantumExperimentConfig:
    """
    Configuration holder for quantum experiments.
    """
    def __init__(self, seed_offset=100, attack_type="markov", attack_intensity=1.0, models=None, scenarios=None):
        

        # =============================================================================
        # MODEL NAME COLLECTIONS FOR TESTING
        # =============================================================================
        self.attack_mapping = {}
        self.environ_mapping = {}
        self.attack_strategy = None  # Will be instantiated by set_attack_scenario
        self.attack_type = attack_type.lower()
        self.attack_intensity = attack_intensity

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
            'iC'
            'KernelUCB'
        ]

        self.algorithm_configs = {
            'Quantum': {'model_class': QuantumModel, 'seed_offset': seed_offset * 1, 'kwargs': {}, 'runner_type': 'step-wise'},
            'Oracle': {'model_class': Oracle, 'seed_offset': seed_offset * 2, 'kwargs': {}, 'runner_type': 'step-wise'},
            'GNeuralUCB': {'model_class': GNeuralUCB, 'seed_offset': seed_offset * 3, 'kwargs': {'mode': 'neural', 'beta': 0.2}, 'runner_type': 'batch'},
            'EXPUCB': {'model_class': EXPUCB, 'seed_offset': seed_offset * 4, 'kwargs': {'mode': 'exp3', 'gamma_factor': 0.1, 'eta_factor': 0.005, 'beta': 0.2}, 'runner_type': 'batch'},
            'EXPNeuralUCB': {'model_class': EXPNeuralUCB, 'seed_offset': seed_offset * 5, 'kwargs': {'mode': 'hybrid', 'gamma_factor': 0.01, 'eta_factor': 0.05, 'beta': 0.2}, 'runner_type': 'batch'},
            'CPursuitNeuralUCB': {'model_class': CPursuitNeuralUCB, 'seed_offset': seed_offset * 6, 'kwargs': {'mode': 'cmab', 'learning_rate': 0.1, 'beta': 0.2}, 'runner_type': 'batch'},
            'iCPursuitNeuralUCB': {'model_class': iCPursuitNeuralUCB, 'seed_offset': seed_offset * 7, 'kwargs': {'mode': 'icmab', 'learning_rate': 0.1, 'beta': 0.2, 'gamma_factor': 0.1, 'eta_factor': 0.005, 'obs': None}, 'runner_type': 'batch'},
            'CEpsilonGreedy': {'model_class': CEpsilonGreedy, 'seed_offset': seed_offset * 8, 'kwargs': {'epsilon': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CEXP4': {'model_class': CEXP4, 'seed_offset': seed_offset * 9, 'kwargs': {'gamma': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CPursuit': {'model_class': CPursuit, 'seed_offset': seed_offset * 10, 'kwargs': {'learning_rate': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'CEpochGreedy': {'model_class': CEpochGreedy, 'seed_offset': seed_offset * 11, 'kwargs': {'n_experts': 4}, 'runner_type': 'step-wise'},
            'CThompsonSampling': {'model_class': CThompsonSampling, 'seed_offset': seed_offset * 12, 'kwargs': {'n_experts': 4}, 'runner_type': 'step-wise'},
            'CKernelUCB': {'model_class': CKernelUCB, 'seed_offset': seed_offset * 13, 'kwargs': {'gamma': 0.1, 'eta': 1.0, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCEpsilonGreedy': {'model_class': iCEpsilonGreedy, 'seed_offset': seed_offset * 14, 'kwargs': {'epsilon': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCEXP4': {'model_class': iCEXP4, 'seed_offset': seed_offset * 15, 'kwargs': {'gamma': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCPursuit': {'model_class': iCPursuit, 'seed_offset': seed_offset * 16, 'kwargs': {'learning_rate': 0.1, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCEpochGreedy': {'model_class': iCEpochGreedy, 'seed_offset': seed_offset * 17, 'kwargs': {'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCThompsonSampling': {'model_class': iCThompsonSampling, 'seed_offset': seed_offset * 18, 'kwargs': {'n_experts': 4}, 'runner_type': 'step-wise'},
            'iCKernelUCB': {'model_class': iCKernelUCB, 'seed_offset': seed_offset * 19, 'kwargs': {'gamma': 0.1, 'eta': 1.0, 'n_experts': 4}, 'runner_type': 'step-wise'},
            'LinUCB': {'model_class': LinUCB, 'seed_offset': seed_offset * 20, 'kwargs': {'alpha': 1.0, 'lambda_reg': 1.0, 'n_features': 6, 'quantum_state_dim': 6, 'entanglement_aware': True, 'prediction_window': 10, 'anomaly_threshold': 0.2}, 'runner_type': 'step-wise'},
            'CEXPNeuralUCB': {'model_class': CEXPNeuralUCB, 'seed_offset': seed_offset * 21, 'kwargs': {'mode': 'cmab', 'beta': 0.2, 'n_experts': 4}, 'runner_type': 'batch'}
        }


    def get_cleanup_wait_time(self, frame_count=1000, cooldown_base=3, cooldown_scale_factor=1, cooldown_max=15):
        """
        Calculate frame-scaled cleanup wait time.
        
        Args:
            frame_count: Number of frames (if None, uses self.frame_count)
        
        Returns:
            float: Wait time in seconds
        """

        # Frame-scaled timing formula
        scale = (frame_count / 1000.0) * cooldown_scale_factor
        wait_time = cooldown_base + scale
        
        return min(wait_time, cooldown_max)
    
    def get_models(self):
        """Return the list of model names to be used in experiments"""
        return self.models

    def set_environment_params(self, qubit_cap, frames_no, seed):
        """
        Stores the core parameters needed to build any environment.
        """
        self._env_params = {
            'qubit_capacities': tuple(qubit_cap),
            'frame_length': int(frames_no),
            'seed': int(seed),
        }

    def set_environment(self, environment_type='adversarial', qubit_cap= (8, 10, 8, 9), frames_no=2000, strategy='markov', seed=42):
        """Set environment configuration based on type"""
        if environment_type.lower() == 'adversarial':
            self.environ_mapping[environment_type.lower()] = AdversarialQuantumEnvironment(qubit_capacities= qubit_cap, seed= seed,frame_length = frames_no, attack=strategy)
        else: raise ValueError(f"Unknown environment_type='{environment_type}'")
        
        return self.environ_mapping[environment_type.lower()]
    
    def get_environment(self):
        """
        Factory method: builds and returns the correct environment instance based
        on the currently configured attack strategy.
        """
        if not self._env_params:
            raise RuntimeError("Environment parameters not set. Call set_environment_params() first.")
        
        # Determine which environment to create based on the strategy object type
        if isinstance(self.attack_strategy, NoAttack):
            # Baseline scenario -> QuantumEnvironment
            return QuantumEnvironment(**self._env_params)
        
        elif isinstance(self.attack_strategy, RandomAttack):
            # Stochastic scenario -> StochasticQuantumEnvironment
            params = self._env_params.copy()
            params['attack_rate'] = self.attack_strategy.attack_rate
            return StochasticQuantumEnvironment(**params)
        
        else:
            # All other strategies (Markov, Adaptive, etc.) -> AdversarialQuantumEnvironment
            params = self._env_params.copy()
            params['attack'] = self.attack_strategy
            return AdversarialQuantumEnvironment(**params)



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



    def set_attack_scenario(self, attack_type: str, **kwargs):
        """
        Configures the attack strategy based on a scenario name. This method
        instantiates the correct AttackStrategy object.
        """
        self.attack_type = attack_type.lower()
        
        attack_mapping = {
            'none': NoAttack(),
            'random': RandomAttack(attack_rate=kwargs.get('attack_rate', 0.25) * self.attack_intensity),
            'stochastic': RandomAttack(attack_rate=kwargs.get('attack_rate', 0.25) * self.attack_intensity),
            'markov': MarkovAttack(attack_rate=self.attack_intensity),
            'adaptive': AdaptiveAttack(attack_rate=self.attack_intensity),
            'onlineadaptive': OnlineAdaptiveAttack(attack_rate=self.attack_intensity)
        }
        
        self.attack_strategy = attack_mapping.get(self.attack_type, NoAttack())


    def get_attack_strategy(self, attack_type=None):
        """Return the configured attack strategy or default to MarkovAttack"""
        if attack_type and attack_type not in self.attack_mapping:
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
                if name == 'Oracle':
                    continue  # Skip Oracle as it needs specific parameters
                elif name in ['UCB', 'TS', 'RandomAlg']:
                    dummy_model = model_class(K=2)
                elif name in ['LinUCB', 'LinTS']:
                    dummy_model = model_class(d=2, K=2)
                elif name in ['NeuralUCB', 'NeuralTS']:
                    dummy_model = model_class(d=2, K=2)
                elif name == 'EXPNeuralUCB':
                    continue  # Skip EXPNeuralUCB as it needs specific parameters
                else:
                    continue
                
                registry[name] = {
                    'class': model_class,
                    'metadata': dummy_model.get_model_info()
                }
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

        if attack_type  and self.attack_type not in self.attack_mapping:
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
        if model_name in self.NEURAL_MODELS:
            return 'Neural'
        elif model_name in self.CONTEXTUAL_MODELS:
            return 'Contextual'
        elif model_name in self.INFORMED_CONTEXTUAL_MODELS:
            return 'Informed_Contextual'
        elif model_name in self.CUSTOM_MODELS:
            return 'Custom'
        else:
            return 'Unknown'

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