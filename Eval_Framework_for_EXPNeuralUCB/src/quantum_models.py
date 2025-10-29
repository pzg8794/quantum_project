import os
import math
import time
import copy
import psutil
import random
import warnings
import numpy as np
import pandas as pd
from tqdm import tqdm
import seaborn as sns
from random import choice
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from scipy.stats import beta, multivariate_normal, norm

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

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



class Oracle:
    """
    Oracle algorithm with perfect knowledge of reward functions and attack patterns.
    Always selects the optimal path and allocation given current attack state.
    """

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
                    # Find best action for this path
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



# Base Random Algorithm Class
class RandomAlg:
    def __init__(self, K):
        self.K = K

    def take_action(self):
        return np.random.choice(self.K)

# Upper Confidence Bound (UCB) Algorithm
class UCB(RandomAlg):
    def __init__(self, K, c=1):
        self.K = K
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
        self.sigma_inv = lamb * np.eye(d)
        self.K = K
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
        self.K =K
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
        self.sigma_inv = lamb * np.eye(d)
        self.K = K
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
        self.buffer = {'context':np.zeros((capacity, d)), 'reward': np.zeros((capacity,1))}
        self.capacity = capacity
        self.size = 0
        self.pointer = 0


    def add(self, context, reward):
        self.buffer['context'][self.pointer] = context
        self.buffer['reward'][self.pointer] = reward
        self.size = min(self.size+1, self.capacity)
        self.pointer = (self.pointer+1)%self.capacity

    def sample(self, n):
        idx = np.random.randint(0,self.size,size=n)
        return self.buffer['context'][idx], self.buffer['reward'][idx]

class NeuralTS(RandomAlg):

    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=3e-4, reg=0.000625):
        self.K = K
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

        self.theta0 = torch.cat(
            [w.flatten() for w in self.net.parameters() if w.requires_grad]
        )
        self.replay_buffer = ReplayBuffer(d, 10000)

    def take_action(self, context):
        context = torch.tensor(context, dtype=torch.float32)
        context = context.to(self.device)
        g = np.zeros((self.K, self.numel), dtype=np.float32)

        for k in range(self.K):
            g[k] = self.grad(context[k]).cpu().numpy()

        with torch.no_grad():
            p = norm.rvs(loc=self.net(context).cpu().numpy(), scale=self.beta * np.sqrt(
                np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :]))

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
        context = torch.tensor(context, dtype=torch.float32)
        context = context.to(self.device)
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
                loss += self.reg * torch.norm(torch.cat(
                    [w.flatten() for w in self.net.parameters() if w.requires_grad]
                ) - self.theta0) ** 2
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()



class NeuralUCB(RandomAlg):

    def __init__(self, d, K, beta=1, lamb=1, hidden_size=128, lr=1e-4, reg=0.000625):
        self.K = K
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

        self.theta0 = torch.cat(
                [w.flatten() for w in self.net.parameters() if w.requires_grad]
            )
        self.replay_buffer = ReplayBuffer(d, 10000)

    def take_action(self, context):
        context = torch.tensor(context, dtype=torch.float32)
        context = context.to(self.device)
        g = np.zeros((self.K, self.numel), dtype=np.float32)

        for k in range(self.K):
            g[k] = self.grad(context[k]).cpu().numpy()

        with torch.no_grad():
            p = self.net(context).cpu().numpy() + self.beta * np.sqrt(np.matmul(np.matmul(g[:, None, :], self.sigma_inv), g[:, :, None])[:, 0, :])

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
        context = torch.tensor(context, dtype=torch.float32)
        context = context.to(self.device)
        self.sherman_morrison_update(self.grad(context[action, None]).cpu().numpy()[:, None])
        self.replay_buffer.add(context[action].cpu().numpy(), reward)
        self.T += 1
        self.train()

    def sherman_morrison_update(self, v):
        self.sigma_inv -= (self.sigma_inv @ v @ v.T @ self.sigma_inv) / (1+v.T @ self.sigma_inv @ v)

    def train(self):
        if self.T > self.K and self.T % 1 == 0:
            for _ in range(2):
                x, y = self.replay_buffer.sample(64)
                x = torch.tensor(x, dtype=torch.float32).to(self.device)
                y = torch.tensor(y, dtype=torch.float32).to(self.device).view(-1,1)
                y_hat = self.net(x)
                loss = F.mse_loss(y_hat, y)
                loss += self.reg * torch.norm(torch.cat(
                [w.flatten() for w in self.net.parameters() if w.requires_grad]
            ) - self.theta0)**2
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()



class EXPNeuralUCB:
    """
    Unified Quantum Routing Algorithm Framework
    
    Modes:
    - 'hybrid': EXP3 + Neural UCB (Main algorithm - EXPNeuralUCB)
    - 'neural': Neural UCB + Simple group selection (GNeuralUCB equivalent)  
    - 'exp3': EXP3 + Linear UCB (EXPUCB equivalent)
    
    This unified design eliminates code duplication and ensures fair comparisons
    by using the same underlying framework for all variants.
    """
    
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
        
        print(f"🔬 EXPNeuralUCB initialized in '{mode}' mode")
        self._print_mode_description()
    
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
            for i in range(self.num_groups):
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
                # Simple linear UCB for each group
                self.linear_ucb_list.append({
                    'counts': [1] * len(self.reward_list[i]),  # Action counts
                    'rewards': [0.0] * len(self.reward_list[i])  # Cumulative rewards
                })
    
    def _print_mode_description(self):
        """Print mode-specific description"""
        descriptions = {
            'hybrid': "   • Group Selection: EXP3 (adversarially robust)\n   • Action Selection: Neural UCB (nonlinear learning)",
            'neural': "   • Group Selection: Simple UCB (not adversarially robust)\n   • Action Selection: Neural UCB (nonlinear learning)", 
            'exp3': "   • Group Selection: EXP3 (adversarially robust)\n   • Action Selection: Linear UCB (linear learning)"
        }
        print(descriptions[self.mode])
    
    def _calculate_oracle(self):
        """Calculate oracle (shared across all modes)"""
        max_graph_action = []
        oracle_graph_list = []
        
        for graph_index in range(self.num_groups):
            max_reward = max(self.reward_list[graph_index])
            oracle_graph_list.append(max_reward)
            max_graph_action.append(self.reward_list[graph_index].index(max_reward))
        
        oracle_path = oracle_graph_list.index(max(oracle_graph_list))
        oracle_action = max_graph_action[oracle_path]
        
        print(f"- Oracle path: {oracle_path}, Oracle action: {oracle_action}")
        print(f"- Oracle performance: {oracle_graph_list}")
        
        return oracle_path, oracle_action
    
    def select_group(self, frame):
        """Mode-specific group selection"""
        if self.mode in ['hybrid', 'exp3']:
            return self._select_group_exp3(frame)
        else:  # neural mode
            return self._select_group_simple(frame)
    
    def _select_group_exp3(self, frame):
        """EXP3-style adversarially robust group selection"""
        prob_array = self._calculate_group_probabilities()
        self.prob_list.append(prob_array.copy())
        
        allocation_array = list(range(self.num_groups))
        selected_path = np.random.choice(allocation_array, p=prob_array)
        
        return selected_path, prob_array
    
    def _select_group_simple(self, frame):
        """Simple UCB-style group selection (not adversarially robust)"""
        group_values = []
        for i in range(self.num_groups):
            avg_reward = self.group_rewards[i] / self.group_counts[i]
            confidence = np.sqrt(2 * np.log(frame + 1) / self.group_counts[i])
            group_values.append(avg_reward + self.beta * confidence)
        
        return np.argmax(group_values), None  # Return tuple for consistency
    
    def _calculate_group_probabilities(self):
        """Calculate EXP3 group selection probabilities"""
        prob_array = []
        sum_group = 0
        
        # Calculate exponential weights
        for group_index in range(self.num_groups):
            sum_group += math.exp(self.eta * sum(self.estimate_group_reward[group_index]))
        
        # Calculate probabilities with exploration term
        for group_index in range(self.num_groups):
            p = (self.gamma / self.num_groups +
                 (1 - self.gamma) * math.exp(self.eta * sum(self.estimate_group_reward[group_index])) / sum_group)
            prob_array.append(p)
        
        return np.array(prob_array)
    
    def select_action(self, selected_group):
        """Mode-specific action selection within group"""
        if self.mode in ['hybrid', 'neural']:
            return self.neuralucb_list[selected_group].take_action(self.X_n[selected_group])
        else:  # exp3 mode
            return self._select_action_linear(selected_group)
    
    def _select_action_linear(self, selected_group):
        """Linear UCB action selection for exp3 mode"""
        action_values = []
        total_group_count = sum(self.linear_ucb_list[selected_group]['counts'])
        
        for action in range(len(self.reward_list[selected_group])):
            count = self.linear_ucb_list[selected_group]['counts'][action]
            avg_reward = self.linear_ucb_list[selected_group]['rewards'][action] / count
            confidence = np.sqrt(2 * np.log(total_group_count) / count)
            action_values.append(avg_reward + self.beta * confidence)
        
        return np.argmax(action_values)
    
    def update_algorithms(self, selected_path, selected_action, base_reward, attack_list, frame):
        """Mode-specific algorithm updates"""
        # Only update if path is not attacked
        if attack_list[frame][selected_path] > 0:
            if self.mode in ['hybrid', 'neural']:
                self.neuralucb_list[selected_path].update(
                    self.X_n[selected_path], selected_action, base_reward
                )
            elif self.mode == 'exp3':
                # Update linear UCB statistics
                self.linear_ucb_list[selected_path]['counts'][selected_action] += 1
                self.linear_ucb_list[selected_path]['rewards'][selected_action] += base_reward
    
    def update_group_selection(self, selected_path, observed_reward, prob_array=None):
        """Mode-specific group selection updates"""
        if self.mode in ['hybrid', 'exp3']:
            # EXP3 update with importance weighting
            for group_index in range(self.num_groups):
                if group_index == selected_path:
                    # prob_array may be very small; avoid div-by-zero/NaN
                    safe_p = max(float(prob_array[selected_path]), 1e-12)
                    self.estimate_group_reward[group_index].append(
                        observed_reward / safe_p
                    )
                else:
                    self.estimate_group_reward[group_index].append(0)

            # for group_index in range(self.num_groups):
            #     if group_index == selected_path:
            #         self.estimate_group_reward[group_index].append(
            #             observed_reward / prob_array[selected_path]
            #         )
            #     else:
            #         self.estimate_group_reward[group_index].append(0)
        
        elif self.mode == 'neural':
            # Simple group selection update
            self.group_rewards[selected_path] += observed_reward
            self.group_counts[selected_path] += 1
    
    def run_experiment(self, attack_list, verbose=True):
        """Run experiment with unified framework"""
        start_time = time.time()
        
        if verbose:
            print(f"\nStarting EXPNeuralUCB in '{self.mode}' mode with {self.frame_number} frames...")
            if self.mode in ['hybrid', 'exp3']:
                print(f"- EXP3 parameters: gamma={self.gamma:.6f}, eta={self.eta:.6f}")
        
        for frame in tqdm(range(self.frame_number), desc=f"- {self.mode.upper()} Progress"):
            # Step 1: Group selection - ALL modes now return tuple
            selected_path, prob_array = self.select_group(frame)
            
            # Step 2: Action selection within selected group
            selected_action = self.select_action(selected_path)
            
            self.path_action_list.append([selected_path, selected_action])
            
            # Step 3: Reward calculation (shared)
            base_reward = self.reward_list[selected_path][selected_action]
            d_t = np.random.choice([0, 1], p=[1-base_reward, base_reward])
            dt = d_t * attack_list[frame][selected_path]
            observed_reward = base_reward * attack_list[frame][selected_path]
            
            # Step 4: Update algorithms (mode-specific)
            self.update_algorithms(selected_path, selected_action, base_reward, attack_list, frame)
            
            # Step 5: Update group selection (mode-specific)
            self.update_group_selection(selected_path, dt, prob_array)
            
            # Step 6: Calculate regret and update metrics (shared)
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
            print(f"\n{self.mode.upper()} completed in {elapsed_time:.2f} seconds")
            print(f"- Final regret: {self.regret:.2f}")
            print(f"- Final total reward: {self.total_reward:.2f}")
            
            # Memory usage reporting
            process = psutil.Process(os.getpid())
            print(f"- Memory usage: {process.memory_info().rss / 1024 ** 2:.2f} MB")
    
    def get_results(self):
        """Return results (shared format)"""
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
        
        # Add mode-specific results
        if self.mode in ['hybrid', 'exp3']:
            results['prob_list'] = self.prob_list
        
        return results