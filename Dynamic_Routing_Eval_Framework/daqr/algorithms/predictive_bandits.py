import os
import math
import time
import copy
import psutil
import random
import warnings
import gc
import numpy as np
from tqdm import tqdm
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from scipy.stats import beta, multivariate_normal, norm

from daqr.algorithms.CMAB import CMAB, iCMAB
from daqr.algorithms.neural_bandits import *

warnings.filterwarnings('ignore')


# Core Scientific Computing Libraries
warnings.filterwarnings('ignore')

# Set Style for PhD-Quality Plots
sns.set_palette("husl")
plt.style.use('seaborn-v0_8')
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['legend.fontsize'] = 12
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['figure.figsize'] = (12, 8)

# Set Random Seeds for Reproducibility
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)

# Device Configuration
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"PyTorch version: {torch.__version__}")
print(f"NumPy version: {np.__version__}")
print(f"Using device: {device}")

# =============================================================================
# Enhanced Common Interface for All Models
# =============================================================================


class CPursuitNeuralUCB(EXPNeuralUCB):
    """
    EXPNeuralUCB with CMAB(Pursuit) replacing EXP3 for group selection
    """
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, 
                mode='cmab', beta=0.2, gamma_factor=0.1, eta_factor=0.005, learning_rate=0.1, verbose=False):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, 
                        'neural', beta, gamma_factor, eta_factor, verbose=verbose)   
        # Override mode and add CMAB components
        self.mode = mode
        self.verbose = verbose
        self.learning_rate = learning_rate
        self.n_features = len(X_n[0]) if X_n else 2
        
        if mode == 'cmab':
            self._initialize_pursuit_components()

    def _initialize_pursuit_components(self):
        """Initialize CMAB(Pursuit) instead of EXP3"""
        try:
            self.cmab = CMAB(
                bandit="pursuit",
                n_arms=self.num_groups,
                n_experts=4,
                n_features=self.n_features,
                learning_rate=self.learning_rate
            )
            if self.verbose:
                print(f"✓ CMAB(Pursuit) initialized with learning_rate={self.learning_rate}")
        except Exception as e:
            print(f"✗ Failed to initialize CMAB(Pursuit): {e}")
            self.cmab = None

    def select_group(self, frame):
        """Override: Use CMAB instead of parent's group selection"""
        if self.mode == 'cmab' and self.cmab is not None:
            return self._select_group_cmab(frame)
        else:
            return super()._select_group_simple(frame)
    
    def _select_group_cmab(self, frame):
        """CMAB(Pursuit) group selection"""
        selected_group = self.cmab.pickArm()
        return selected_group, None
    
    def select_action(self, selected_group):
        """Override: Always use Neural UCB for action selection"""
        return self.neuralucb_list[selected_group].take_action(self.X_n[selected_group])
    
    def update_algorithms(self, selected_path, selected_action, base_reward, attack_list, frame):
        """Override: Only update Neural UCB, avoid linear_ucb_list"""
        if attack_list[frame][selected_path] > 0:
            self.neuralucb_list[selected_path].update(
                self.X_n[selected_path], selected_action, base_reward
            )
    
    def update_group_selection(self, selected_path, observed_reward, advice=None):
        """Override: Update CMAB(Pursuit) and simple tracking"""
        if self.mode == 'cmab' and self.cmab is not None:
            self.cmab.update(observed_reward)
        
        self.group_rewards[selected_path] += observed_reward
        self.group_counts[selected_path] += 1



class iCPursuitNeuralUCB(CPursuitNeuralUCB):
    """
    Informative CPursuitNeuralUCB: Enhances CPursuitNeuralUCB with iCMAB's 
    predictive intelligence and anomaly detection for improved performance.
    
    Combines:
    - iCMAB(Pursuit) for informed group selection with ARIMA predictions
    - Neural UCB for action selection
    - Anomaly detection for reward filtering
    """        
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, 
                capacity, mode='icmab', beta=0.2, gamma_factor=0.1, eta_factor=0.005, 
                learning_rate=0.1, arima_update_interval=200, warmup_frames=50, obs=None, obs_noise=0.1, n_experts=4, verbose=False):
        """
        Initialize iCPursuitNeuralUCB
        
        Args:
            X_n: Context features for each path
            reward_list: Reward structure for paths
            frame_number: Total frames to run
            mode: 'icmab' for informative version
            gamma_factor, eta_factor, beta: Algorithm parameters
            learning_rate: Pursuit learning rate
            obs: Initial observation for iCMAB (optional)
        """
        # Initialize CPursuitNeuralUCB base (gets neural UCB components)
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, 
                        mode, beta, gamma_factor, eta_factor, learning_rate)
        
        self.basemode = mode
        self.n_features = len(X_n[0]) if X_n else 2
        
        # Store configurable parameters
        self.arima_update_interval = arima_update_interval
        self.warmup_frames = warmup_frames
        self.obs_noise = obs_noise
        self.n_experts = n_experts
        
        if mode == 'icmab': self._initialize_icmab_components(obs)
    
    def _initialize_icmab_components(self, obs):
        """Initialize iCMAB(Pursuit) with anomaly detection"""
        try:
            if obs is None:
                obs = np.zeros((self.n_features, self.num_groups))
            
            self.icmab = iCMAB(
                bandit="pursuit",
                n_arms=self.num_groups,
                n_experts=self.n_experts,
                n_features=self.n_features,
                learning_rate=self.learning_rate,
                obs=obs
            )
            
            self.arima_models = {}
            self.use_arima = False
            
            if self.verbose:
                print(f"✓ iCMAB(Pursuit) initialized with ARIMA prediction capability")
                print(f"  - Learning rate: {self.learning_rate}")
                print(f"  - Warmup frames: {self.warmup_frames} (configurable)")
                print(f"  - ARIMA update interval: {self.arima_update_interval} (configurable)")
            
        except Exception as e:
            print(f"✗ Failed to initialize iCMAB(Pursuit): {e}")
            self.icmab = None
            self.mode = 'cmab'
    
    def select_group(self, frame):
        """Override: Use iCMAB with predictive intelligence"""
        if self.mode == 'icmab' and self.icmab is not None:
            return self._select_group_icmab(frame)
        else:
            # Fallback to parent CPursuitNeuralUCB
            return super().select_group(frame)
    
    def _select_group_icmab(self, frame):
        """iCMAB(Pursuit) group selection with predictive priors"""
        # Enable ARIMA after warmup period
        if frame >= self.warmup_frames and not self.use_arima:
            self.use_arima = True
            if self.verbose: print(f"✓ ARIMA prediction enabled at frame {frame}")
        
        # Use iCMAB to select arm (path)
        selected_group = self.icmab.pickArm()
        
        return selected_group, None
    
    def update_group_selection(self, selected_path, observed_reward, advice=None, 
                              frame=0, obs=None, arm_rewards=None):
        """
        Override: Update iCMAB with anomaly detection
        
        Args:
            selected_path: Chosen path
            observed_reward: Received reward
            advice: Not used for Pursuit
            frame: Current frame number
            obs: New observation (optional)
            arm_rewards: Rewards for all arms (optional)
        """
        if self.mode == 'icmab' and self.icmab is not None:
            filtered_reward = observed_reward
            
            # Use configurable interval instead of hardcoded 200
            if self.use_arima and frame % self.arima_update_interval == 0:
                try:
                    arima_model = self.icmab.generateRewardARIMA(selected_path)
                    filtered_reward = self.icmab.detectRewardAnomaly(
                        observed_reward, 
                        arima_model
                    )
                    self.arima_models[selected_path] = arima_model
                except Exception as e:
                    filtered_reward = observed_reward
            
            if obs is None:
                obs = np.zeros((self.n_features, self.num_groups))
            
            if arm_rewards is None:
                arm_rewards = [0.0] * self.num_groups
                arm_rewards[selected_path] = filtered_reward
            
            self.icmab.update(
                reward=filtered_reward,
                obs=obs,
                action=selected_path,
                arm_rewards=arm_rewards
            )
            
            self.group_rewards[selected_path] += filtered_reward
            self.group_counts[selected_path] += 1
        else:
            super().update_group_selection(selected_path, observed_reward, advice)

    
    def run(self, attack_list, verbose=False):
        """Enhanced batch runner with progress suppression"""
        if verbose: self.verbose = verbose
                
        start_time = time.time()
        
        if self.verbose:
            print(f"\nEXECUTION STARTING:")
            print("=" * 50)
            print(f"| Mode:             | {self.mode.upper():<15} |")
            print(f"| Frames:           | {self.frame_number:,} |")
            print(f"| Paths:            | {self.num_groups} |")
            print(f"| ARIMA Warmup:     | {self.warmup_frames} frames |")
            print(f"| ARIMA Update:     | Every {self.arima_update_interval} frames |")
            print("=" * 50)
        
        for frame in tqdm(range(self.frame_number), desc=f"- {self.mode.upper()} Progress", disable=not self.verbose):  # Now respects verbose

            if self.transition_trigger and frame > 0 and frame % self.transition_interval == 0:
                new_contexts, new_rewards = self.transition_trigger()
                if new_contexts is not None:
                    self.Xn = new_contexts
                    self.reward_list = new_rewards

            selected_path, _ = self.select_group(frame)
            selected_action = self.select_action(selected_path)
            self.path_action_list.append([selected_path, selected_action])
            
            base_reward = self.reward_list[selected_path][selected_action]
            d_t = np.random.choice([0, 1], p=[1 - base_reward, base_reward])
            dt = d_t * attack_list[frame][selected_path]
            observed_reward = base_reward * attack_list[frame][selected_path]
            
            self.update_algorithms(selected_path, selected_action, base_reward, attack_list, frame)
            
            # Use configurable noise
            obs = np.random.randn(self.n_features, self.num_groups) * self.obs_noise
            obs[:, selected_path] += observed_reward
            
            arm_rewards = [0.0] * self.num_groups
            for i in range(self.num_groups):
                if i == selected_path:
                    arm_rewards[i] = observed_reward
                else:
                    if self.group_counts[i] > 0:
                        arm_rewards[i] = self.group_rewards[i] / self.group_counts[i]
            
            self.update_group_selection(
                selected_path, 
                observed_reward, 
                frame=frame,
                obs=obs,
                arm_rewards=arm_rewards
            )
            
            oracle_reward = (self.reward_list[self.oracle_path][self.oracle_action] * 
                           attack_list[frame][self.oracle_path])
            oracle_regret = oracle_reward - observed_reward
            if oracle_regret < 0: oracle_regret = 0
            
            self.regret += np.abs(oracle_regret)
            self.total_reward += observed_reward
            self.regret_list.append(self.regret)
            self.reward_list_total.append(self.total_reward)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        if self.verbose: self._print_experiment_results(elapsed_time)
    
    def get_results(self):
        """Return results with iCMAB metadata"""
        results = super().get_results()
        results['mode'] = self.mode
        results['arima_enabled'] = self.use_arima if hasattr(self, 'use_arima') else False
        results['arima_models_count'] = len(self.arima_models) if hasattr(self, 'arima_models') else 0
        return results



class CEXPNeuralUCB(EXPNeuralUCB):
    """
    EXPNeuralUCB with CMAB(EXP4) replacing EXP3 for group selection
    """
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, 
                mode='cmab', gamma_factor=0.1, eta_factor=0.005, beta=0.2, n_experts=4, verbose=False):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, 
                        mode, gamma_factor, eta_factor, beta, n_experts)
        
        # Override mode and add CMAB components
        self.mode = mode
        self.n_experts = n_experts
        self.n_features = len(X_n[0]) if X_n else 2
        
        if mode == 'cmab':
            self._initialize_cmab_components()

    def _initialize_cmab_components(self):
        """Initialize CMAB(EXP4) instead of EXP3"""
        try:
            self.cmab = CMAB(
                bandit="exp4",
                gamma=self.gamma,
                n_arms=self.num_groups,
                n_experts=self.n_experts,
                n_features=self.n_features
            )
            self.expert_advice_history = []        
            if self.verbose:
                print(f"\t✓ CMAB(EXP4) initialized with {self.n_experts} experts")
        except Exception as e:
            print(f"✗ Failed to initialize CMAB: {e}")
            self.cmab = None

    def select_group(self, frame):
        """Override: Use CMAB instead of parent's group selection"""
        if self.mode == 'cmab' and self.cmab is not None:
            return self._select_group_cmab(frame)
        else:
            # Fallback to parent's simple selection (mode='neural')
            return super()._select_group_simple(frame)
    
    def _select_group_cmab(self, frame):
        """CMAB(EXP4) group selection"""
        expert_advice = self._generate_expert_advice(frame)
        selected_group = self.cmab.pickArm(advice=expert_advice)
        self.expert_advice_history.append(expert_advice)
        return selected_group, expert_advice
    
    def select_action(self, selected_group):
        """Override: Always use Neural UCB for action selection"""
        # Force neural UCB action selection regardless of mode
        return self.neuralucb_list[selected_group].take_action(self.X_n[selected_group])
    
    def update_algorithms(self, selected_path, selected_action, base_reward, attack_list, frame):
        """Override: Only update Neural UCB, avoid linear_ucb_list"""
        if attack_list[frame][selected_path] > 0:
            # Always use neural UCB update (safe for cmab mode)
            self.neuralucb_list[selected_path].update(
                self.X_n[selected_path], selected_action, base_reward
            )
    
    def update_group_selection(self, selected_path, observed_reward, advice=None):
        """Override: Update CMAB and simple tracking"""
        if self.mode == 'cmab' and self.cmab is not None:
            self.cmab.update(observed_reward)
        
        # Always update simple group tracking (inherited from neural mode)
        self.group_rewards[selected_path] += observed_reward
        self.group_counts[selected_path] += 1

    def _generate_expert_advice(self, frame):
        """Generate simple, robust expert advice for EXP4."""
        advice = np.zeros((self.n_experts, self.num_groups))

        # Expert 1: Uniform (pure exploration)
        advice[0, :] = 1.0 / self.num_groups

        # Expert 2: Static preference for Path 0
        advice[1, 0] = 1.0
        
        # Expert 3: Greedy based on historical reward
        if hasattr(self, 'group_rewards') and sum(self.group_rewards) > 0:
            best_group = np.argmax(self.group_rewards)
            advice[2, best_group] = 1.0
        else:
            # Fallback to uniform if no rewards yet
            advice[2, :] = 1.0 / self.num_groups

        # Expert 4: Round-robin (cyclical preference)
        expert_choice = frame % self.num_groups
        advice[3, expert_choice] = 1.0
        
        # Final validation to prevent any normalization errors
        for i in range(self.n_experts):
            if not np.isclose(advice[i, :].sum(), 1.0):
                advice[i, :] = np.ones(self.num_groups) / self.num_groups

        return advice



# =============================================================================
# FIXED CMAB QUANTUM MODELS
# =============================================================================

class CMABModelBase(QuantumModel):
    """Base class for CMAB-based quantum models"""
    
    @property
    def model_type(self):
        return 'step-wise'
    
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)

        self.X_n = X_n
        self.reward_list = reward_list
        self.frame_number = frame_number
        self.num_paths = len(reward_list)

        self.eta=kwargs.get('eta', 1.0),
        self.gamma=kwargs.get('gamma', 0.1)
        self.epsilon = kwargs.get('epsilon', 0.1)
        self.n_experts=kwargs.get('n_experts', 4)
        self.learning_rate=kwargs.get('learning_rate', 0.1)
        
        # Quantum tracking
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.total_reward = 0
        
        # Store parameters for child classes
        self.n_experts = kwargs.get('n_experts', 1)
        self.bandit_params = kwargs

    def take_action(self, **kwargs):
        """Must be implemented by child classes"""
        raise NotImplementedError
        
    def update(self, path, action, reward):
        """Standard quantum model update interface"""
        self.total_reward += reward
        self.path_action_list.append((path, action))
        self.reward_list_total.append(self.total_reward)
        
    def get_results(self):
        return {
            'regret_list': copy.deepcopy(self.regret_list),
            'reward_list': copy.deepcopy(self.reward_list_total),
            'path_action_list': copy.deepcopy(self.path_action_list),
            'final_regret': copy.deepcopy(sum(self.regret_list)),
            'final_reward': copy.deepcopy(self.total_reward),
            'state':self.state
        }


# =============================================================================
# FIXED INDIVIDUAL CMAB MODELS  
# =============================================================================

class CEpsilonGreedy(CMABModelBase):
    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        
        # Create CMAB for each path
        self.path_bandits = []
        for path_idx in range(self.num_paths):
            cmab = CMAB(
                epsilon=self.epsilon,
                bandit='epsilongreedy',
                n_experts=self.n_experts,
                learning_rate=self.learning_rate,
                n_arms=len(reward_list[path_idx]),
                n_features=len(X_n[path_idx]) if X_n else 2
            )
            self.path_bandits.append(cmab)
        
        # Path selection tracking  
        self.path_rewards = [0.0] * self.num_paths
        self.path_counts = [1] * self.num_paths
        
    def take_action(self, **kwargs):
        # Select path using epsilon-greedy on path rewards
        if np.random.random() < self.bandit_params.get('epsilon', 0.1):
            selected_path = np.random.randint(0, self.num_paths)
        else:
            path_values = [r/c for r, c in zip(self.path_rewards, self.path_counts)]
            selected_path = np.argmax(path_values)
            
        # Select action using path-specific CMAB
        selected_action = self.path_bandits[selected_path].pickArm()
        
        return selected_path, selected_action
    
    def update(self, path, action, reward):
        super().update(path, action, reward)
        
        # Update path rewards
        self.path_rewards[path] += reward
        self.path_counts[path] += 1
        
        # Update path-specific bandit
        self.path_bandits[path].update(reward)

class CPursuit(CMABModelBase):
    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        
        # Create Pursuit bandits for each path
        self.path_bandits = []
        for path_idx in range(self.num_paths):
            cmab = CMAB(
                # n_experts=1,
                bandit='pursuit',
                epsilon=self.epsilon,
                n_experts=self.n_experts,
                learning_rate=self.learning_rate,
                n_arms=len(reward_list[path_idx]),
                n_features=len(X_n[path_idx]) if X_n else 2,
            )
            self.path_bandits.append(cmab)
            
        # Path selection using UCB
        self.path_rewards = [0.0] * self.num_paths
        self.path_counts = [1] * self.num_paths
        
    def take_action(self, **kwargs):
        # UCB path selection
        t = sum(self.path_counts)
        ucb_values = []
        for i in range(self.num_paths):
            avg_reward = self.path_rewards[i] / self.path_counts[i]
            confidence = np.sqrt(2 * np.log(t) / self.path_counts[i])
            ucb_values.append(avg_reward + confidence)
            
        selected_path = np.argmax(ucb_values)
        selected_action = self.path_bandits[selected_path].pickArm()
        
        return selected_path, selected_action
        
    def update(self, path, action, reward):
        super().update(path, action, reward)
        self.path_rewards[path] += reward
        self.path_counts[path] += 1
        self.path_bandits[path].update(reward)


class CEpochGreedy(CMABModelBase):
    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        
        # Create EpochGreedy bandits for each path  
        self.path_bandits = []
        for path_idx in range(self.num_paths):
            cmab = CMAB(
                # n_experts=1,
                bandit='epochgreedy',
                epsilon=self.epsilon,
                n_experts=self.n_experts,
                learning_rate=self.learning_rate,
                n_arms=len(reward_list[path_idx]),
                n_features=len(X_n[path_idx]) if X_n else 2
            )
            self.path_bandits.append(cmab)
            
        # Simple round-robin path selection
        self.current_path = 0
        
    def take_action(self, **kwargs):
        selected_path = self.current_path % self.num_paths
        self.current_path += 1
        
        # Generate dummy hypothesis and context for EpochGreedy
        hypothesis = np.random.rand(len(self.reward_list[selected_path]))
        context = self.X_n[selected_path] if self.X_n else np.random.rand(2)
        
        selected_action = self.path_bandits[selected_path].pickArm(
            hypothesis=hypothesis, 
            context=context
        )
        
        return selected_path, selected_action
        
    def update(self, path, action, reward):
        super().update(path, action, reward)
        self.path_bandits[path].update(reward)


class CThompsonSampling(CMABModelBase):
    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        
        # Create ThompsonSampling bandits for each path
        self.path_bandits = []
        for path_idx in range(self.num_paths):
            cmab = CMAB(
                # n_experts=1,
                epsilon=self.epsilon,
                n_experts=self.n_experts,
                bandit='thompsonsampling',
                learning_rate=self.learning_rate,
                n_arms=len(reward_list[path_idx]),
                n_features=len(X_n[path_idx]) if X_n else 2
            )
            self.path_bandits.append(cmab)
            
        # Random path selection
        self.step_count = 0
        
    def take_action(self, **kwargs):
        # Rotate through paths or use Thompson sampling for path selection
        selected_path = self.step_count % self.num_paths
        self.step_count += 1
        
        # Use dummy context for ThompsonSampling
        context = self.X_n[selected_path] if self.X_n else np.random.rand(2)
        selected_action = self.path_bandits[selected_path].pickArm(context=context)
        
        return selected_path, selected_action
        
    def update(self, path, action, reward):
        super().update(path, action, reward)
        self.path_bandits[path].update(reward)

# =============================================================================
# FINAL FIXES FOR REMAINING CMAB ERRORS
# =============================================================================

class CEXP4(CMABModelBase):
    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        
        # Create EXP4 for path selection
        self.path_selector = CMAB(
            bandit='exp4',
            gamma=self.gamma,
            epsilon=self.epsilon,
            n_arms=self.num_paths,
            n_experts=self.n_experts,
            learning_rate=self.learning_rate,
            n_features=len(X_n[0]) if X_n else 2
        )
        
        # Create individual bandits for each path
        self.path_bandits = []
        for path_idx in range(self.num_paths):
            cmab = CMAB(
                epsilon=self.epsilon,
                bandit='epsilongreedy',
                n_experts=self.n_experts,
                learning_rate=self.learning_rate,
                n_arms=len(reward_list[path_idx]),
                n_features=len(X_n[path_idx]) if X_n else 2,
            )
            self.path_bandits.append(cmab)
            
    def take_action(self, **kwargs):
        # Generate PROPERLY NORMALIZED advice for EXP4
        n_experts = self.bandit_params.get('n_experts', 4)
        advice = np.random.rand(n_experts, self.num_paths)
        
        # FIX: Ensure each expert's advice sums to 1
        for expert in range(n_experts):
            advice_sum = np.sum(advice[expert, :])
            if advice_sum > 0:
                advice[expert, :] = advice[expert, :] / advice_sum
            else:
                # If all zeros, make uniform
                advice[expert, :] = np.ones(self.num_paths) / self.num_paths
        
        # Select path using EXP4
        selected_path = self.path_selector.pickArm(advice=advice)
        
        # Select action using path-specific bandit
        selected_action = self.path_bandits[selected_path].pickArm()
        
        return selected_path, selected_action
        
    def update(self, path, action, reward):
        super().update(path, action, reward)
        
        # Update path selector
        self.path_selector.update(reward)
        
        # Update path-specific bandit
        self.path_bandits[path].update(reward)


class CKernelUCB(CMABModelBase):
    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)

        self.path_bandits = []
        self.path_n_arms = []
        self.path_n_features = []
        self.path_rewards = [0.0] * self.num_paths
        self.path_counts = [1] * self.num_paths
        self.round_count = 0

        for path_idx in range(self.num_paths):
            n_arms = len(reward_list[path_idx])
            self.path_n_arms.append(n_arms)

            # Infer n_features from X_n[path_idx]
            n_features = 1
            if X_n and path_idx < len(X_n):
                xi = np.asarray(X_n[path_idx]).astype(float).ravel()
                if xi.size == n_arms:
                    n_features = 1
                elif xi.size % n_arms == 0:
                    n_features = int(xi.size // n_arms)
                else:
                    n_features = 1  # fallback; we will pad in take_action
            self.path_n_features.append(n_features)

            try:
                cmab = CMAB(
                    eta=self.eta,
                    n_arms=n_arms,
                    # n_experts=1,
                    gamma=self.gamma,
                    bandit='kernelucb',
                    epsilon=self.epsilon,
                    n_features=n_features,
                    n_experts=self.n_experts,
                    learning_rate=self.learning_rate
                )
            except Exception as e:
                # Fall back to epsilon-greedy if KernelUCB cannot be constructed
                cmab = CMAB(
                    # n_experts=1,
                    n_arms=n_arms,
                    epsilon=self.epsilon,
                    n_features=n_features,
                    bandit='epsilongreedy',
                    n_experts=self.n_experts,
                    learning_rate=self.learning_rate
                )
            self.path_bandits.append(cmab)

    def _build_context_vector(self, path_idx):
        """
        Build a flat vector of length n_arms * n_features as required by KernelUCB.run,
        reshaped internally to (n_arms, n_features).
        """
        n_arms = self.path_n_arms[path_idx]
        n_feat = self.path_n_features[path_idx]

        # Start with zeros
        ctx = np.zeros(n_arms * n_feat, dtype=float)

        if self.X_n and path_idx < len(self.X_n):
            raw = np.asarray(self.X_n[path_idx]).astype(float).ravel()
            if raw.size == n_arms * n_feat:
                ctx = raw
            elif raw.size == n_arms and n_feat == 1:
                # Per-arm single feature
                ctx = raw
            elif raw.size % n_arms == 0:
                # Collapse/expand to n_feat computed earlier
                tmp_feat = int(raw.size // n_arms)
                mat = raw.reshape(n_arms, tmp_feat)
                if tmp_feat >= n_feat:
                    ctx = mat[:, :n_feat].ravel()
                else:
                    pad = np.zeros((n_arms, n_feat - tmp_feat), dtype=float)
                    ctx = np.hstack([mat, pad]).ravel()
            else:
                # Incompatible length; put raw into first positions and pad
                take = min(raw.size, n_arms * n_feat)
                ctx[:take] = raw[:take]
        return ctx

    def take_action(self, **kwargs):
        self.round_count += 1

        # Simple UCB for path selection
        if self.round_count <= self.num_paths:
            selected_path = (self.round_count - 1) % self.num_paths
        else:
            ucb_vals = [
                (r / c) + np.sqrt(2.0 * np.log(self.round_count) / c)
                for r, c in zip(self.path_rewards, self.path_counts)
            ]
            selected_path = int(np.argmax(ucb_vals))

        # Build context matching KernelUCB.run needs: flat vector of length n_arms * n_features
        context_vec = self._build_context_vector(selected_path)

        try:
            # CMAB KernelUCB expects flat context; inside it reshapes to (n_arms, n_features)
            selected_action = self.path_bandits[selected_path].pickArm(
                context=context_vec,
                tround=self.round_count
            )
        except Exception as e:
            # Graceful fallback: random arm for this path
            selected_action = np.random.randint(0, self.path_n_arms[selected_path])

        return selected_path, selected_action

    def update(self, path, action, reward):
        # Book-keeping for path-level UCB
        self.path_rewards[path] += reward
        self.path_counts[path] += 1

        # Delegate to CMAB bandit; CMAB tracks last choice internally
        try:
            self.path_bandits[path].update(reward)
        except Exception as e:
            # Skip silently; bandit state may be in fallback
            pass


# =============================================================================
# iCMAB MODELS (with ARIMA prediction)
# =============================================================================

class iCMABModelBase(CMABModelBase):
    """Base for iCMAB models with ARIMA prediction"""
    
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)

        self.path_icmabs = []
        for path_idx in range(self.num_paths):
            obs_vec = np.asarray(X_n[path_idx], dtype=np.float64).ravel() if X_n else np.zeros(2, dtype=np.float64)
            n_features = max(1, int(obs_vec.shape[0]))  # never 0

            icmab = iCMAB(
                bandit=self.bandit_type,          # "kernelucb"
                n_arms=len(reward_list[path_idx]),
                # n_experts=kwargs.get('n_experts', 4),
                n_features=n_features,            # binds KernelUCB.n_features
                obs=obs_vec,
                **kwargs
            )
            self.path_icmabs.append(icmab)
            
    def update(self, path, action, reward, **kwargs):
        """iCMAB-specific update"""
        super().update(path, action, reward)
        obs = kwargs.get('obs')
        if obs is None:
            obs = np.asarray(self.X_n[path], dtype=np.float64).ravel()
        if obs.size == 0:
            # match bandit’s n_features exactly
            nf = self.path_icmabs[path].bandit.n_features
            obs = np.zeros(nf, dtype=np.float64)

        arm_rewards = kwargs.get('arm_rewards', [reward] * len(self.reward_list[path]))
        self.path_icmabs[path].update(
            reward,
            obs=np.asarray(obs, dtype=np.float64).ravel(),
            action=action,
            arm_rewards=arm_rewards
        )


# =============================================================================
# iCMAB VERSIONS - UPDATED
# =============================================================================

class iCEXP4(iCMABModelBase):
    bandit_type = 'exp4'
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)
    
    def take_action(self, **kwargs):
        # Use simple path selection for iCMAB
        selected_path = np.random.randint(0, self.num_paths)
        
        # Generate PROPERLY NORMALIZED advice for EXP4
        n_experts = self.bandit_params.get('n_experts', 1)
        n_arms = len(self.reward_list[selected_path])
        advice = np.random.rand(n_experts, n_arms)
        
        # FIX: Ensure each expert's advice sums to 1
        for expert in range(n_experts):
            advice_sum = np.sum(advice[expert, :])
            if advice_sum > 0:
                advice[expert, :] = advice[expert, :] / advice_sum
            else:
                advice[expert, :] = np.ones(n_arms) / n_arms
        
        selected_action = self.path_icmabs[selected_path].pickArm(advice=advice)
        return selected_path, selected_action



# PROBLEM ANALYSIS:
# ================
# Error 1: "cannot reshape array of size 0 into shape (1,165)" 
#          → context_vec is EMPTY but needs to be tiled for 165 arms
# Error 2: "cannot reshape array of size 165 into shape (2,165)"
#          → context_vec has 165 elements but should have n_features dimensions
#
# ROOT CAUSE: The context vector preprocessing is creating inconsistent sizes

class iCKernelUCB(iCMABModelBase):
    bandit_type = 'kernelucb'
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)

    def __init__(self, configs, X_n, reward_list, frame_number, **kwargs):
        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        # FIXED: Ensure consistent context preprocessing
        if X_n:
            processed_X_n = []
            # First pass: collect all valid arrays and find consistent feature size
            valid_arrays = []
            for path_data in X_n:
                if path_data is not None:
                    arr = np.asarray(path_data, dtype=np.float64)
                    if arr.size > 0:  # Only keep non-empty
                        valid_arrays.append(arr.flatten())

            # Determine consistent feature dimension
            if valid_arrays:
                # Use mode of sizes, fallback to 2 if inconsistent
                sizes = [arr.size for arr in valid_arrays]
                most_common_size = max(set(sizes), key=sizes.count) if sizes else 2
                target_features = max(2, min(most_common_size, 10))  # Reasonable bounds
            else:
                target_features = 2  # Default fallback

            # Second pass: normalize all to target_features size
            for path_data in X_n:
                if path_data is not None:
                    arr = np.asarray(path_data, dtype=np.float64).flatten()
                    if arr.size == 0:
                        # Empty array → create default feature vector
                        normalized = np.random.rand(target_features) * 0.1
                    elif arr.size == target_features:
                        # Perfect size → use as-is
                        normalized = arr
                    elif arr.size < target_features:
                        # Too small → pad with zeros
                        normalized = np.pad(arr, (0, target_features - arr.size), mode='constant')
                    else:
                        # Too large → truncate to target size
                        normalized = arr[:target_features]
                    processed_X_n.append(normalized)
                else:
                    # None data → create default feature vector
                    processed_X_n.append(np.random.rand(target_features) * 0.1)

            X_n = processed_X_n
            self.n_features = target_features
        else:
            # No context provided → create uniform default
            num_paths = len(reward_list)
            self.n_features = 2  # Default feature size
            X_n = [np.random.rand(self.n_features) * 0.1 for _ in range(num_paths)]

        super().__init__(configs,  X_n, reward_list, frame_number, **kwargs)
        self.round_count = 0

        if self.verbose:
            print(f"\t✓ iCKernelUCB initialized with {len(X_n)} paths, {self.n_features} features each")

    def take_action(self, **kwargs):
        try:
            tround = self.round_count  # KernelUCB starts at round 0
            selected_path = tround % self.num_paths

            # FIXED: Get context vector with robust error handling
            if self.X_n and selected_path < len(self.X_n):
                context_vec = np.asarray(self.X_n[selected_path], dtype=np.float64).flatten()

                # Validate context vector
                if context_vec.size == 0:
                    print(f"⚠ Empty context at path {selected_path}, using random fallback")
                    context_vec = np.random.rand(self.n_features) * 0.1
                elif context_vec.size != self.n_features:
                    print(f"⚠ Context size mismatch: got {context_vec.size}, expected {self.n_features}")
                    if context_vec.size < self.n_features:
                        # Pad if too small
                        context_vec = np.pad(context_vec, (0, self.n_features - context_vec.size), mode='constant')
                    else:
                        # Truncate if too large  
                        context_vec = context_vec[:self.n_features]
            else:
                # Fallback for invalid path
                context_vec = np.random.rand(self.n_features) * 0.1

            # FIXED: Build proper context matrix for KernelUCB
            n_arms = len(self.reward_list[selected_path])

            # Validate we have valid inputs before matrix construction
            if context_vec.size == 0:
                print(f"❌ Critical: context_vec is empty, cannot proceed")
                context_vec = np.random.rand(self.n_features) * 0.1

            if n_arms == 0:
                print(f"❌ Critical: no arms available for path {selected_path}")
                return selected_path, 0

            # Create (n_arms × n_features) matrix - same context for all arms
            context_matrix = np.tile(context_vec.reshape(1, -1), (n_arms, 1))

            # Validate final matrix shape
            expected_shape = (n_arms, self.n_features)
            if context_matrix.shape != expected_shape:
                print(f"⚠ Matrix shape mismatch: got {context_matrix.shape}, expected {expected_shape}")
                # Emergency reconstruction
                context_matrix = np.full(expected_shape, 0.1, dtype=np.float64)

            try:
                selected_action = self.path_icmabs[selected_path].pickArm(
                    context=context_matrix,
                    tround=tround
                )
                # print(f"✓ iCKernelUCB: path={selected_path}, action={selected_action}, context_shape={context_matrix.shape}")

            except Exception as e:
                print(f"⚠ iCMAB KernelUCB pickArm failed: {e}")
                selected_action = np.random.randint(0, n_arms)

            self.round_count += 1
            return selected_path, selected_action

        except Exception as e:
            print(f"❌ iCKernelUCB take_action failed: {e}")
            # Emergency fallback
            return np.random.randint(0, self.num_paths), np.random.randint(0, 4)

    

# Individual iCMAB models
class iCEpsilonGreedy(iCMABModelBase):
    bandit_type = 'epsilongreedy'
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)
    
    def take_action(self, **kwargs):
        # Simple path selection with exploration
        if np.random.random() < 0.1:
            selected_path = np.random.randint(0, self.num_paths)
        else:
            # Use path with highest average reward
            path_values = []
            for icmab in self.path_icmabs:
                if len(icmab.rewardHistory[0]) > 0:
                    avg_reward = np.mean([np.mean(arm_rewards) for arm_rewards in icmab.rewardHistory])
                    path_values.append(avg_reward)
                else:
                    path_values.append(0.0)
            selected_path = np.argmax(path_values)
        
        selected_action = self.path_icmabs[selected_path].pickArm()
        return selected_path, selected_action


class iCPursuit(iCMABModelBase):
    bandit_type = 'pursuit'
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)

    
    def take_action(self, **kwargs):
        selected_path = np.random.randint(0, self.num_paths)
        selected_action = self.path_icmabs[selected_path].pickArm()
        return selected_path, selected_action


class iCEpochGreedy(iCMABModelBase):
    bandit_type = 'epochgreedy'
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)

    
    def take_action(self, **kwargs):
        selected_path = np.random.randint(0, self.num_paths)
        
        # Generate required parameters for EpochGreedy
        hypothesis = np.random.rand(len(self.reward_list[selected_path]))
        context = self.X_n[selected_path] if self.X_n else np.random.rand(2)
        
        selected_action = self.path_icmabs[selected_path].pickArm(
            hypothesis=hypothesis,
            context=context
        )
        return selected_path, selected_action


class iCThompsonSampling(iCMABModelBase):
    bandit_type = 'thompsonsampling'
    def __init__(self, configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs):
        super().__init__(configs, X_n, reward_list, frame_number, attack_list, capacity, **kwargs)

    
    def take_action(self, **kwargs):
        selected_path = np.random.randint(0, self.num_paths)
        context = self.X_n[selected_path] if self.X_n else np.random.rand(2)
        selected_action = self.path_icmabs[selected_path].pickArm(context=context)
        return selected_path, selected_action