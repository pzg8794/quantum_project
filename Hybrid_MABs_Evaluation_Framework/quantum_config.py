"""
Pure configuration class - NO imports from algorithms
"""
from quantum_configuration import QuantumExperimentConfigRegistry


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
    


class QuantumExperimentConfig:
    """
    Configuration holder for quantum experiments.
    """
    def __init__(self, seed_offset=100, attack_type="markov", attack_intensity=1.0, models=None, scenarios=None):
        

        # =============================================================================
        # MODEL NAME COLLECTIONS FOR TESTING
        # =============================================================================
        self.registry = QuantumExperimentConfigRegistry()
        
        self.attack_mapping = {}
        self.environ_mapping = {}
        self.attack_type = attack_type.lower()
        self.attack_intensity = attack_intensity
        self.category_map = self.registry.category_map

        self.models = self.registry.models
        self.test_scenarios = self.registry.test_scenarios

        # Custom/Hybrid Models (Research Extensions)
        self.CUSTOM_MODELS = self.registry.CUSTOM_MODELS

        # Core Quantum Models (Original Research Models)
        self.NEURAL_MODELS = self.registry.NEURAL_MODELS

        # Contextual Multi-Armed Bandit Models (CMAB)
        self.CONTEXTUAL_MODELS = self.registry.CONTEXTUAL_MODELS

        # Informed Contextual Multi-Armed Bandit Models (iCMAB with ARIMA)
        self.INFORMED_CONTEXTUAL_MODELS = self.registry.INFORMED_CONTEXTUAL_MODELS


        # =============================================================================
        # COMPREHENSIVE MODEL GROUPS
        # =============================================================================

        # Batch models (for batch runner)
        self.BATCH_MODELS = self.registry.BATCH_MODELS

        # Models with prediction capabilities
        self.PREDICTIVE_MODELS = self.registry.PREDICTIVE_MODELS

        # =============================================================================
        # TESTING PRESETS
        # =============================================================================

        # Research models for paper/publication
        self.RESEARCH_MODELS = self.registry.RESEARCH_MODELS
        # Quick test subset (representative models)
        self.QUICK_TEST_MODELS = self.registry.QUICK_TEST_MODELS
        # Performance comparison set
        self.PERFORMANCE_COMPARISON_MODELS = self.registry.PERFORMANCE_COMPARISON_MODELS

        self.algorithm_configs = self.registry.algorithm_configs

    def get_cleanup_wait_time(self, frame_count=1000):
        """
        Calculate frame-scaled cleanup wait time.
        
        Args:
            frame_count: Number of frames (if None, uses self.frame_count)
        
        Returns:
            float: Wait time in seconds
        """
        if frame_count is None:
            frame_count = self.frame_count
        
        # Handle None case (model doesn't have frame info)
        if frame_count is None:
            return 6.0  # Default fallback
        
        # Frame-scaled timing formula
        scale = (frame_count / 1000.0) * self.cooldown_scale_factor
        wait_time = self.cooldown_base + scale
        
        return min(wait_time, self.cooldown_max)
    
    def get_models(self):
        """Return the list of model names to be used in experiments"""
        return self.models
    
    def set_environment(self, environment_type='adversarial', qubit_cap= (8, 10, 8, 9), frames_no=2000, strategy='markov', seed=42):
        """Set environment configuration based on type"""
        if environment_type.lower() == 'adversarial':
            self.environ_mapping[environment_type.lower()] = AdversarialQuantumEnvironment(qubit_capacities= qubit_cap, seed= seed,frame_length = frames_no, attack=strategy)
        else: raise ValueError(f"Unknown environment_type='{environment_type}'")
        
        return self.environ_mapping[environment_type.lower()]
    
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



    def set_attack(self, attack_rate=0.25, memory_window=50, sticky_p=0.7, decay=0.97, temperature=0.5):
        """Only addition: create attack strategy based on attack_type"""
        self.attack_mapping = {
            'none': NoAttack(),
            'random': RandomAttack(attack_rate=attack_rate * self.attack_intensity),
            'stochastic': RandomAttack(attack_rate=attack_rate * self.attack_intensity),
            'markov': MarkovAttack(
                attack_rate=self.attack_intensity,
                k_attacks=max(1, min(2, int(round(2 * self.attack_intensity))))
            ),

            'adaptive': AdaptiveAttack(
                sticky_p=sticky_p,
                memory_window=memory_window,
                attack_rate=self.attack_intensity
            ),

            'onlineadaptive': OnlineAdaptiveAttack(
                decay=decay,
                temperature=temperature,
                memory_window=memory_window,
                attack_rate=self.attack_intensity,
                k=max(1, min(2, int(round(2 * self.attack_intensity))))
            )
        }

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