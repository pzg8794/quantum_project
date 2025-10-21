import os
import math
import time
import copy
import psutil
import random
import random as rd
import warnings
import numpy as np
import pandas as pd
from tqdm import tqdm
import seaborn as sns
from random import choice
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from scipy.stats import beta, multivariate_normal, norm

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

class QuantumModel(ABC):
    """
    Enhanced minimal interface that every model (policy/algorithm) in the quantum environment obeys.
    Keep methods generic so both 'step-wise' (Oracle) and 'batch' (EXPNeuralUCB) fit.
    """
    
    @property
    def model_type(self):
        """Return 'step-wise' or 'batch' to indicate usage pattern"""
        return 'step-wise'  # Default for most models
    
    @property
    def supports_batch_execution(self):
        # True iff subclass overrides QuantumModel.run_experiment
        return self.__class__.run_experiment is not QuantumModel.run_experiment
    
    def reset(self, *args, **kwargs):
        """Optional: clear internal state between runs."""
        pass
    
    @abstractmethod
    def take_action(self, *args, **kwargs):
        """Select an action (signature may vary by model)."""
        raise NotImplementedError
    
    def update(self, *args, **kwargs):
        """Optional: incorporate feedback after an action."""
        pass
    
    def run_experiment(self, *args, **kwargs):
        """
        Optional: batch/episode runner (e.g., EXPNeuralUCB).
        Step-wise models provide helpful error message.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is a {self.model_type} model. "
            f"Use take_action() and update() in a loop instead of run_experiment()."
        )
    
    def get_results(self) -> dict:
        """
        Optional: standardized results payload.
        Top-level models override this; low-level policies can return {}.
        """
        return {}
    
    def get_model_info(self) -> dict:
        """Return comprehensive model metadata"""
        return {
            'name': self.__class__.__name__,
            'model_type': self.model_type,
            'supports_batch_execution': self.supports_batch_execution,
            'has_update': hasattr(self, 'update') and callable(self.update),
            'has_get_results': hasattr(self, 'get_results') and callable(self.get_results),
            'module': self.__class__.__module__
        }

# =============================================================================
# Models & Policies with Enhanced Metadata
# =============================================================================

class Oracle(QuantumModel):
    """
    Oracle algorithm with perfect knowledge of reward functions and attack patterns.
    Always selects the optimal path and allocation given current attack state.
    """
    
    @property
    def model_type(self):
        return 'step-wise'
    
    def __init__(self, X_n, reward_list, attack_list):
        self.X_n = X_n
        self.reward_list = reward_list
        self.attack_list = attack_list
        self.frame_number = len(attack_list)
        # Pre-compute optimal actions for each time step
        self.optimal_actions = self._compute_optimal_actions()
        # Tracking variables
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.total_reward = 0
        self.current_frame = 0

    def _compute_optimal_actions(self):
        """Pre-compute optimal path and action for each time step"""
        optimal_actions = []
        for frame in range(self.frame_number):
            best_reward = -1
            best_path = 0
            best_action = 0
            # Check all paths
            for path in range(len(self.reward_list)):
                if self.attack_list[frame][path] > 0:  # Path not attacked
                    path_rewards = self.reward_list[path]
                    best_path_action = np.argmax(path_rewards)
                    path_reward = path_rewards[best_path_action] * self.attack_list[frame][path]
                    if path_reward > best_reward:
                        best_reward = path_reward
                        best_path = path
                        best_action = best_path_action
            optimal_actions.append((best_path, best_action, best_reward))
        return optimal_actions

    def take_action(self):
        """Return optimal action for current frame"""
        if self.current_frame < len(self.optimal_actions):
            path, action, _ = self.optimal_actions[self.current_frame]
            return path, action
        return 0, 0

    def update(self, path, action, reward):
        """Update Oracle (just tracking)"""
        self.total_reward += reward
        self.reward_list_total.append(self.total_reward)
        self.path_action_list.append([path, action])
        self.regret_list.append(0)  # Oracle has zero regret by definition
        self.current_frame += 1

    def get_results(self):
        return {
            'regret_list': self.regret_list,
            'reward_list': self.reward_list_total,
            'path_action_list': self.path_action_list,
            'final_regret': 0,
            'final_reward': self.total_reward
        }



# --- Define the IRIS Bandit Environment ---
# This is a corrected and more robust implementation.
class IRIS():
    """
    A bandit environment for the Iris dataset.
    Loads data remotely and preprocesses it for simulation.
    """
    def __init__(self, use_remote=True, random_state=None):
        self.arm = 3
        self.dim = 12
        self.random_state = random_state
        
        if use_remote:
            # Use a reliable remote URL for the dataset
            url = 'https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv'
            self.data = pd.read_csv(url)
        else:
            # Fallback to local file
            self.data = pd.read_csv('Iris.csv')
            
        self._prepare_data()
        self.reset()

    def _prepare_data(self):
        """Internal method to preprocess the data."""
        # Feature engineering to create 12 dimensions
        features = ['sepal_length', 'sepal_width', 'petal_length', 'petal_width']
        X = self.data[features].values
        
        X_poly = np.column_stack([
            X,                     # Original 4 features
            X**2,                  # Squared features (adds 4)
            X[:, 0] * X[:, 1],     # Interaction term 1
            X[:, 2] * X[:, 3],     # Interaction term 2
            X[:, 0] * X[:, 2],     # Interaction term 3
            X[:, 1] * X[:, 3]      # Interaction term 4
        ])
        
        # Normalize features
        self.features = (X_poly - X_poly.mean(axis=0)) / (X_poly.std(axis=0) + 1e-8)
        
        # Map species names to integer arms (0, 1, 2)
        species_map = {species: i for i, species in enumerate(self.data['species'].unique())}
        self.labels = self.data['species'].map(species_map).values

    def reset(self):
        """Resets the environment by shuffling the data for a new epoch."""
        self.current_step = 0
        # Shuffle indices for this run
        self.shuffled_indices = np.random.RandomState(self.random_state).permutation(len(self.data))

    def step(self):
        """Returns a context and reward for one time step."""
        if self.current_step >= len(self.data):
            self.reset() # Reshuffle and start over if we've seen all data
        
        idx = self.shuffled_indices[self.current_step]
        
        # Get the feature vector for the current step
        base_context = self.features[idx]
        
        # Create the padded context for each arm
        contexts = []
        for i in range(self.arm):
            pre_pad = np.zeros(4 * i)
            post_pad = np.zeros(4 * (self.arm - 1 - i))
            context_vector = np.concatenate([pre_pad, base_context[:4], post_pad])
            contexts.append(context_vector)
        
        # Get the correct arm and create the reward vector
        correct_arm = self.labels[idx]
        reward_vector = np.zeros(self.arm)
        reward_vector[correct_arm] = 1
        
        self.current_step += 1
        return np.array(contexts), reward_vector


# Base Random Algorithm Class
class RandomAlg(QuantumModel):
    @property
    def model_type(self):
        return 'step-wise'
    
    def __init__(self, K):
        self.K = K

    def take_action(self):
        return np.random.choice(self.K)

# Upper Confidence Bound (UCB) Algorithm
class UCB(RandomAlg):
    def __init__(self, K, c=1):
        super().__init__(K)
        self.c = c
        self.T = 0
        self.q = np.zeros(K)
        self.N = np.zeros(K)

    def take_action(self):
        if self.T < self.K:
            action = self.T
        else:
            action = np.argmax(self.q + self.c * np.sqrt(2 * np.log(self.T) / self.N))
        self.T += 1
        return action

    def update(self, context, action, reward):
        self.q[action] = (self.q[action] * self.N[action] + reward) / (self.N[action] + 1)
        self.N[action] += 1

# Linear Upper Confidence Bound (LinUCB) Algorithm
class LinUCB(RandomAlg):
    def __init__(self, d, K, beta=1, lamb=1):
        super().__init__(K)
        self.sigma_inv = lamb * np.eye(d)
        self.b = np.zeros((d, 1))
        self.beta = beta

    def take_action(self, context):
        theta = self.sigma_inv @ self.b
        p = np.matmul(context[:, None, :], theta) + self.beta * np.sqrt(
            np.matmul(np.matmul(context[:, None, :], self.sigma_inv), context[:, :, None]))
        action = np.argmax(p)
        return action

    def update(self, context, action, reward):
        self.sherman_morrison_update(context[action, :, None])
        self.b += context[action, :, None] * reward

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

class TS(RandomAlg):
    def __init__(self, K):
        super().__init__(K)
        self.alpha = np.ones(K)
        self.beta = np.ones(K)

    def take_action(self):
        p = np.zeros(self.K)
        for k in range(self.K):
            p[k] = beta.rvs(a=self.alpha[k], b=self.beta[k])
        return np.argmax(p)

    def update(self, context, action, reward):
        if reward == 0:
            self.alpha[action] += 1
        else:
            self.beta[action] += 1

class LinTS(RandomAlg):
    def __init__(self, d, K, beta=1, lamb=1):
        super().__init__(K)
        self.sigma_inv = lamb * np.eye(d)
        self.b = np.zeros((d, 1))
        self.beta = beta

    def take_action(self, context):
        theta = multivariate_normal.rvs(mean=(self.sigma_inv @ self.b).flatten(), cov=self.beta*self.sigma_inv)
        r_hat = np.matmul(theta[None], context[:, :, None])
        return np.argmax(r_hat)

    def update(self, context, action, reward):
        self.sherman_morrison_update(context[action, :, None])
        self.b += context[action, :, None] * reward

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

# NN pieces (not themselves "environment models"; keep as-is)
class NeuralBanditModel(nn.Module):
    def __init__(self, input_size, hidden_size, out_size):
        super().__init__()
        self.affine1 = nn.Linear(input_size, hidden_size)
        self.affine2 = nn.Linear(hidden_size, out_size)

    def forward(self, x):
        x = F.relu(self.affine1(x))
        return self.affine2(x)

class ReplayBuffer:
    def __init__(self, d, capacity):
        self.buffer = {'context': np.zeros((capacity, d)), 'reward': np.zeros((capacity, 1))}
        self.capacity = capacity
        self.size = 0
        self.pointer = 0

    def add(self, context, reward):
        self.buffer['context'][self.pointer] = context
        self.buffer['reward'][self.pointer] = reward
        self.size = min(self.size + 1, self.capacity)
        self.pointer = (self.pointer + 1) % self.capacity

    def sample(self, n):
        idx = np.random.randint(0, self.size, size=n)
        return self.buffer['context'][idx], self.buffer['reward'][idx]

class NeuralTS(RandomAlg):
    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=3e-4, reg=0.000625):
        super().__init__(K)
        self.T = 0
        self.reg = reg
        self.beta = beta
        self.net = NeuralBanditModel(d, hidden_size, 1)
        self.hidden_size = hidden_size
        self.net.to(device)
        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        self.numel = sum(w.numel() for w in self.net.parameters() if w.requires_grad)
        self.sigma_inv = lamb * np.eye(self.numel, dtype=np.float32)
        self.device = device
        self.theta0 = torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad])
        self.replay_buffer = ReplayBuffer(d, 10000)

    def take_action(self, context):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        g = np.zeros((self.K, self.numel), dtype=np.float32)
        for k in range(self.K):
            g[k] = self.grad(context[k]).cpu().numpy()
        with torch.no_grad():
            p = norm.rvs(
                loc=self.net(context).cpu().numpy(),
                scale=self.beta * np.sqrt(
                    np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :]
                ),
            )
        action = np.argmax(p)
        return action

    def grad(self, x):
        y = self.net(x)
        self.optimizer.zero_grad()
        y.backward()
        return torch.cat(
            [w.grad.detach().flatten() / np.sqrt(self.hidden_size) for w in self.net.parameters() if w.requires_grad]
        ).to(self.device)

    def update(self, context, action, reward):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        self.sherman_morrison_update(self.grad(context[action, None]).cpu().numpy()[:, None])
        self.replay_buffer.add(context[action].cpu().numpy(), reward)
        self.T += 1
        self.train()

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

    def train(self):
        if self.T > self.K and self.T % 1 == 0:
            for _ in range(2):
                x, y = self.replay_buffer.sample(64)
                x = torch.tensor(x, dtype=torch.float32).to(self.device)
                y = torch.tensor(y, dtype=torch.float32).to(self.device).view(-1, 1)
                y_hat = self.net(x)
                loss = F.mse_loss(y_hat, y)
                loss += self.reg * torch.norm(
                    torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad]) - self.theta0
                ) ** 2
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

class NeuralUCB(RandomAlg):
    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=1e-4, reg=0.000625):
        super().__init__(K)
        self.T = 0
        self.reg = reg
        self.beta = beta
        self.net = NeuralBanditModel(d, hidden_size, 1)
        self.hidden_size = hidden_size
        self.net.to(device)
        self.optimizer = optim.Adam(self.net.parameters(), lr=lr)
        self.numel = sum(w.numel() for w in self.net.parameters() if w.requires_grad)
        self.sigma_inv = lamb * np.eye(self.numel, dtype=np.float32)
        self.device = device
        self.theta0 = torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad])
        self.replay_buffer = ReplayBuffer(d, 10000)

    def take_action(self, context):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        g = np.zeros((self.K, self.numel), dtype=np.float32)
        for k in range(self.K):
            g[k] = self.grad(context[k]).cpu().numpy()
        with torch.no_grad():
            p = self.net(context).cpu().numpy() + self.beta * np.sqrt(
                np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :]
            )
        action = np.argmax(p)
        return action

    def grad(self, x):
        y = self.net(x)
        self.optimizer.zero_grad()
        y.backward()
        return torch.cat(
            [w.grad.detach().flatten() / np.sqrt(self.hidden_size) for w in self.net.parameters() if w.requires_grad]
        ).to(self.device)

    def update(self, context, action, reward):
        context = torch.tensor(context, dtype=torch.float32).to(self.device)
        self.sherman_morrison_update(self.grad(context[action, None]).cpu().numpy()[:, None])
        self.replay_buffer.add(context[action].cpu().numpy(), reward)
        self.T += 1
        self.train()

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1 + v.T @ self.sigma_inv @ v)

    def train(self):
        if self.T > self.K and self.T % 1 == 0:
            for _ in range(2):
                x, y = self.replay_buffer.sample(64)
                x = torch.tensor(x, dtype=torch.float32).to(self.device)
                y = torch.tensor(y, dtype=torch.float32).to(self.device).view(-1, 1)
                y_hat = self.net(x)
                loss = F.mse_loss(y_hat, y)
                loss += self.reg * torch.norm(
                    torch.cat([w.flatten() for w in self.net.parameters() if w.requires_grad]) - self.theta0
                ) ** 2
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()

class EXPNeuralUCB(QuantumModel):
    """
    Enhanced Unified Quantum Routing Algorithm Framework
    
    Modes:
    - 'hybrid': EXP3 + Neural UCB (Main algorithm - EXPNeuralUCB)
    - 'neural': Neural UCB + Simple group selection (GNeuralUCB equivalent)  
    - 'exp3': EXP3 + Linear UCB (EXPUCB equivalent)
    """
    
    @property
    def model_type(self):
        return 'batch'
    
    @property
    def supports_batch_execution(self):
        return True  # Override detection since we implement run_experiment
    
    def __init__(self, X_n, reward_list, frame_number, mode='hybrid', 
                 gamma_factor=0.1, eta_factor=0.005, beta=0.2):
        # Core parameters (shared across all modes)
        self.X_n = X_n
        self.reward_list = reward_list
        self.frame_number = frame_number
        self.num_groups = len(reward_list)
        self.mode = mode
        self.beta = beta
        
        # EXP3 parameters (used in 'hybrid' and 'exp3' modes)
        self.gamma = gamma_factor
        self.eta = eta_factor
        
        # Shared tracking variables
        self.regret_list = []
        self.reward_list_total = []
        self.path_action_list = []
        self.regret = 0
        self.total_reward = 0
        
        # Calculate oracle (shared across all modes)
        self.oracle_path, self.oracle_action = self._calculate_oracle()
        
        # Mode-specific initialization
        self._initialize_mode_specific_components()
        
        print(f"\nEXPNeuralUCB initialized in '{mode}' mode")
        self._print_mode_description()

    def take_action(self, *args, **kwargs):
        raise NotImplementedError(
            f"EXPNeuralUCB is a {self.model_type} model that manages actions internally. "
            f"Use run_experiment(attack_list) to execute a full experiment, not take_action()."
        )

    def _initialize_mode_specific_components(self):
        """Initialize components based on selected mode"""
        # Neural UCB components (hybrid + neural modes)
        if self.mode in ['hybrid', 'neural']:
            self.neuralucb_list = []
            self.neuralucb_list.append(NeuralUCB(2, len(self.X_n[0]), self.beta, lamb=1))  # Path 1: 2D
            self.neuralucb_list.append(NeuralUCB(2, len(self.X_n[1]), self.beta, lamb=1))  # Path 2: 2D
            self.neuralucb_list.append(NeuralUCB(3, len(self.X_n[2]), self.beta, lamb=1))  # Path 3: 3D
            self.neuralucb_list.append(NeuralUCB(3, len(self.X_n[3]), self.beta, lamb=1))  # Path 4: 3D
        
        # EXP3 components (hybrid + exp3 modes)
        if self.mode in ['hybrid', 'exp3']:
            self.estimate_group_reward = []
            for _ in range(self.num_groups):
                self.estimate_group_reward.append([0])
            self.prob_list = []
        
        # Simple group selection components (neural mode)
        if self.mode == 'neural':
            self.group_rewards = [0.0] * self.num_groups
            self.group_counts = [1] * self.num_groups  # Avoid division by zero
        
        # Linear UCB components (exp3 mode)
        if self.mode == 'exp3':
            self.linear_ucb_list = []
            for i in range(self.num_groups):
                self.linear_ucb_list.append({
                    'counts': [1] * len(self.reward_list[i]),
                    'rewards': [0.0] * len(self.reward_list[i])
                })

    def _print_mode_description(self):
        """Clean tabular mode description"""
        print("\n" + "=" * 60)
        print("ALGORITHM CONFIGURATION")
        print("=" * 60)
        
        if self.mode == 'hybrid':
            print("| Component          | Method                    | Properties       |")
            print("|--------------------|-----------------------------|------------------|")
            print("| Group Selection    | EXP3                       | Adversarially    |")
            print("|                    |                            | Robust           |")
            print("| Action Selection   | Neural UCB                 | Nonlinear        |") 
            print("|                    |                            | Learning         |")
            print("| Parameters         | gamma={:.3f}, eta={:.3f}   | EXP3 Config      |".format(self.gamma, self.eta))
            print("|                    | beta={:.1f}                | Neural UCB       |".format(self.beta))
            
        elif self.mode == 'neural':
            print("| Component          | Method                    | Properties       |")
            print("|--------------------|-----------------------------|------------------|")
            print("| Group Selection    | Simple UCB                 | NOT Adversarial  |")
            print("|                    |                            | Robust           |")
            print("| Action Selection   | Neural UCB                 | Nonlinear        |")
            print("|                    |                            | Learning         |")
            print("| Parameters         | beta={:.1f}                | UCB Confidence   |".format(self.beta))
            
        elif self.mode == 'exp3':
            print("| Component          | Method                    | Properties       |")
            print("|--------------------|-----------------------------|------------------|")
            print("| Group Selection    | EXP3                       | Adversarially    |")
            print("|                    |                            | Robust           |")
            print("| Action Selection   | Linear UCB                 | Linear           |")
            print("|                    |                            | Learning         |")
            print("| Parameters         | gamma={:.3f}, eta={:.3f}   | EXP3 Config      |".format(self.gamma, self.eta))
            print("|                    | beta={:.1f}                | Linear UCB       |".format(self.beta))
            
        print("=" * 60)

    def _calculate_oracle(self):
        """Calculate oracle with clean output"""
        max_graph_action = []
        oracle_graph_list = []
        for graph_index in range(self.num_groups):
            max_reward = max(self.reward_list[graph_index])
            oracle_graph_list.append(max_reward)
            max_graph_action.append(self.reward_list[graph_index].index(max_reward))
        oracle_path = oracle_graph_list.index(max(oracle_graph_list))
        oracle_action = max_graph_action[oracle_path]
        
        print("\nORACLE ANALYSIS:")
        print("=" * 40)
        print(f"| Optimal Path:      | {oracle_path}              |")
        print(f"| Optimal Action:    | {oracle_action}            |")
        print(f"| Path Performance:  | {oracle_graph_list}        |")
        print("=" * 40)
        
        return oracle_path, oracle_action

    def select_group(self, frame):
        if self.mode in ['hybrid', 'exp3']:
            return self._select_group_exp3(frame)
        else:
            return self._select_group_simple(frame)

    def _select_group_exp3(self, frame):
        prob_array = self._calculate_group_probabilities()
        self.prob_list.append(prob_array.copy())
        allocation_array = list(range(self.num_groups))
        selected_path = np.random.choice(allocation_array, p=prob_array)
        return selected_path, prob_array

    def _select_group_simple(self, frame):
        group_values = []
        for i in range(self.num_groups):
            avg_reward = self.group_rewards[i] / self.group_counts[i]
            confidence = np.sqrt(2 * np.log(frame + 1) / self.group_counts[i])
            group_values.append(avg_reward + self.beta * confidence)
        return np.argmax(group_values), None

    def _calculate_group_probabilities(self):
        prob_array = []
        sum_group = 0
        for group_index in range(self.num_groups):
            sum_group += math.exp(self.eta * sum(self.estimate_group_reward[group_index]))
        for group_index in range(self.num_groups):
            p = (self.gamma / self.num_groups +
                 (1 - self.gamma) * math.exp(self.eta * sum(self.estimate_group_reward[group_index])) / sum_group)
            prob_array.append(p)
        return np.array(prob_array)

    def select_action(self, selected_group):
        if self.mode in ['hybrid', 'neural']:
            return self.neuralucb_list[selected_group].take_action(self.X_n[selected_group])
        else:
            return self._select_action_linear(selected_group)

    def _select_action_linear(self, selected_group):
        action_values = []
        total_group_count = sum(self.linear_ucb_list[selected_group]['counts'])
        for action in range(len(self.reward_list[selected_group])):
            count = self.linear_ucb_list[selected_group]['counts'][action]
            avg_reward = self.linear_ucb_list[selected_group]['rewards'][action] / count
            confidence = np.sqrt(2 * np.log(total_group_count) / count)
            action_values.append(avg_reward + self.beta * confidence)
        return np.argmax(action_values)

    def update_algorithms(self, selected_path, selected_action, base_reward, attack_list, frame):
        if attack_list[frame][selected_path] > 0:
            if self.mode in ['hybrid', 'neural']:
                self.neuralucb_list[selected_path].update(
                    self.X_n[selected_path], selected_action, base_reward
                )
            elif self.mode == 'exp3':
                self.linear_ucb_list[selected_path]['counts'][selected_action] += 1
                self.linear_ucb_list[selected_path]['rewards'][selected_action] += base_reward

    def update_group_selection(self, selected_path, observed_reward, prob_array=None):
        if self.mode in ['hybrid', 'exp3']:
            for group_index in range(self.num_groups):
                if group_index == selected_path:
                    safe_p = max(float(prob_array[selected_path]), 1e-12)
                    self.estimate_group_reward[group_index].append(observed_reward / safe_p)
                else:
                    self.estimate_group_reward[group_index].append(0)
        elif self.mode == 'neural':
            self.group_rewards[selected_path] += observed_reward
            self.group_counts[selected_path] += 1

    def run_experiment(self, attack_list, verbose=True):
        """Enhanced batch/episode runner with clean progress output"""
        start_time = time.time()
        
        if verbose:
            print(f"\nEXECUTION STARTING:")
            print("=" * 50)
            print(f"| Mode:             | {self.mode.upper():<15} |")
            print(f"| Frames:           | {self.frame_number:,}           |")
            print(f"| Paths:            | {self.num_groups}               |")
            print("=" * 50)
        
        for frame in tqdm(range(self.frame_number), desc=f"- {self.mode.upper()} Progress"):
            selected_path, prob_array = self.select_group(frame)
            selected_action = self.select_action(selected_path)
            self.path_action_list.append([selected_path, selected_action])
            
            base_reward = self.reward_list[selected_path][selected_action]
            d_t = np.random.choice([0, 1], p=[1 - base_reward, base_reward])
            dt = d_t * attack_list[frame][selected_path]
            observed_reward = base_reward * attack_list[frame][selected_path]
            
            self.update_algorithms(selected_path, selected_action, base_reward, attack_list, frame)
            self.update_group_selection(selected_path, dt, prob_array)
            
            oracle_reward = (self.reward_list[self.oracle_path][self.oracle_action] *
                             attack_list[frame][self.oracle_path])
            oracle_regret = oracle_reward - observed_reward
            if oracle_regret < 0:
                oracle_regret = 0
            
            self.regret += np.abs(oracle_regret)
            self.total_reward += observed_reward
            
            self.regret_list.append(self.regret)
            self.reward_list_total.append(self.total_reward)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        if verbose:
            self._print_experiment_results(elapsed_time)

    def _print_experiment_results(self, elapsed_time):
        """Clean tabular results output"""
        print(f"\nEXECUTION COMPLETED:")
        print("=" * 50)
        print(f"| Execution Time:   | {elapsed_time:.2f} seconds    |")
        print(f"| Final Regret:     | {self.regret:.2f}          |") 
        print(f"| Final Reward:     | {self.total_reward:.2f}       |")
        
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 ** 2
        print(f"| Memory Usage:     | {memory_mb:.2f} MB        |")
        print("=" * 50)

    def get_results(self):
        results = {
            'regret_list': self.regret_list,
            'reward_list': self.reward_list_total,
            'path_action_list': self.path_action_list,
            'final_regret': self.regret,
            'final_reward': self.total_reward,
            'oracle_path': self.oracle_path,
            'oracle_action': self.oracle_action,
            'mode': self.mode
        }
        if self.mode in ['hybrid', 'exp3']:
            results['prob_list'] = self.prob_list
        return results

# =============================================================================
# Enhanced Utility Functions for Model Management
# =============================================================================

def validate_quantum_model(model) -> bool:
    """Enhanced validation that an object implements QuantumModel interface"""
    if not isinstance(model, QuantumModel):
        return False
    
    # Check that take_action is implemented
    if not hasattr(model, 'take_action') or not callable(getattr(model, 'take_action')):
        return False
    
    return True

def get_model_capabilities(model) -> dict:
    """Get comprehensive model capabilities and metadata"""
    if not isinstance(model, QuantumModel):
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
        'run_experiment': model.supports_batch_execution,
        'reset': hasattr(model, 'reset') and callable(getattr(model, 'reset')),
        'get_results': hasattr(model, 'get_results') and callable(getattr(model, 'get_results')),
    }
    
    return info

def create_model_registry():
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

def print_model_summary(models):
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
        elif isinstance(model, QuantumModel):
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


# # =============================================================================
# # Usage Demonstration
# # =============================================================================

# if __name__ == "__main__":
#     print("🔬 ENHANCED QUANTUM MODEL INTERFACE DEMONSTRATION")
#     print("="*60)
    
#     # Create model registry
#     registry = create_model_registry()
#     print_model_summary(registry)
    
#     print(f"\n🔧 Testing Enhanced Interface Features:")
    
#     # Test step-wise model
#     ucb_model = UCB(K=4)
#     ucb_info = get_model_capabilities(ucb_model)
#     print(f"✅ UCB Model Info: {ucb_info['model_type']} model, supports batch: {ucb_info['supports_batch_execution']}")
    
#     # Test enhanced error messages
#     try:
#         ucb_model.run_experiment()
#     except NotImplementedError as e:
#         print(f"✅ Enhanced Error Message: {e}")
    
#     print(f"\n🎯 Interface validation complete!")
