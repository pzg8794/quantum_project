import numpy as np
import copy
import math
import time
import random
import torch
import pandas as pd
import random as rd
import matplotlib.pyplot as plt
from quantum_models import NeuralUCB
# -*- coding: utf-8 -*-
"""
EXPNeuralUCB Test: Complete Adversarial Group Neural Bandits Implementation
PhD-Quality Publication-Ready Version with Enhanced Visualizations
Based on Huang, Y., Wang, L., & Xu, J. (2024). arXiv:2411.00316v1
"""

class IRIS():
    def __init__(self):
        self.arm = 3
        self.dim = 12
        self.data = pd.read_csv('Iris.csv')

    def step(self):
        r = rd.randint( 0, 149)
        if  0 <= r <= 49:
            target = 0
        elif 50 <= r <= 99:
            target = 1
        else:
            target = 2
        random = self.data.loc[r]
        x = np.zeros(4)
        for i in range(1,5):
            x[i-1] = random[i]
        X_n = []
        for i in range(3):
            front = np.zeros((4 * i))
            back = np.zeros((4 * (2 - i)))
            new_d = np.concatenate((front, x, back), axis=0)
            X_n.append(new_d)
        X_n = np.array(X_n)
        reward = np.zeros(self.arm)
        # print(target)
        reward[target] = 1
        return X_n, reward


# Set publication-quality style
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': 'Times New Roman',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'axes.linewidth': 1.2,
    'grid.linewidth': 0.8,
    'lines.linewidth': 2.0
})

# Set random seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)
random.seed(42)


# Calculate reward functions for all paths
def calculate_all_rewards(X_n):
    reward_list = []
    reward_list.append(get_reward_path_1(X_n))
    reward_list.append(get_reward_path_2(X_n))
    reward_list.append(get_reward_path_3(X_n))
    reward_list.append(get_reward_path_4(X_n))
    return reward_list

def get_context_list(qubit_list):
    """
    Generate context lists for different quantum paths with varying qubit allocations.

    Parameters:
    qubit_list: List of total qubits available for each path [path1_qubits, path2_qubits, path3_qubits, path4_qubits]

    Returns:
    X_n: List of context arrays for each path representing all possible qubit allocations
    """
    X_n = []

    # Path 1: 2-hop path (2 edges)
    context_group1 = []
    qubit = qubit_list[0]
    for i in range(qubit + 1):
        new_d = np.array([i, qubit - i])
        context_group1.append(new_d)
    context_group1 = np.array(context_group1)
    X_n.append(context_group1)

    # Path 2: 2-hop path (2 edges)
    context_group2 = []
    qubit = qubit_list[1]
    for i in range(qubit + 1):
        new_d = np.array([i, qubit - i])
        context_group2.append(new_d)
    context_group2 = np.array(context_group2)
    X_n.append(context_group2)

    # Path 3: 3-hop path (3 edges)
    context_group3 = []
    qubit = qubit_list[2]
    for i in range(qubit + 1):
        for j in range(qubit + 1 - i):
            new_d = np.array([i, j, qubit - i - j])
            context_group3.append(new_d)
    context_group3 = np.array(context_group3)
    X_n.append(context_group3)

    # Path 4: 3-hop path (3 edges)
    context_group4 = []
    qubit = qubit_list[3]
    for i in range(qubit + 1):
        for j in range(qubit + 1 - i):
            new_d = np.array([i, j, qubit - i - j])
            context_group4.append(new_d)
    context_group4 = np.array(context_group4)
    X_n.append(context_group4)

    return X_n

def get_reward_path_1(X_n, A=4000):
    """
    Calculate success rates for Path 1 (2-hop path with higher success rate)
    """
    reward = []
    pe_1 = 1.5e-4  # Single-hop single-qubit single-attempt success rate
    pe_2 = 1.5e-4

    p_1 = 1 - (1 - pe_1)**A  # Single-hop single-qubit success rate after A attempts
    p_2 = 1 - (1 - pe_2)**A

    for j in range(len(X_n[0])):
        P_1 = 1 - (1 - p_1)**X_n[0][j][0]  # Success with allocated qubits
        P_2 = 1 - (1 - p_2)**X_n[0][j][1]
        P_path = P_1 * P_2  # Overall path success rate
        reward.append(P_path)

    return reward

def get_reward_path_2(X_n, A=4000):
    """
    Calculate success rates for Path 2 (2-hop path with lower success rate)
    """
    reward = []
    pe_1 = 1e-4  # Lower success rates for Path 2
    pe_2 = 1e-4

    p_1 = 1 - (1 - pe_1)**A
    p_2 = 1 - (1 - pe_2)**A

    for j in range(len(X_n[1])):
        P_1 = 1 - (1 - p_1)**X_n[1][j][0]
        P_2 = 1 - (1 - p_2)**X_n[1][j][1]
        P_path = P_1 * P_2
        reward.append(P_path)

    return reward

def get_reward_path_3(X_n, A=4000):
    """
    Calculate success rates for Path 3 (3-hop path with higher success rate)
    """
    reward = []
    pe_1 = 2e-4  # Higher per-hop success rates for Path 3
    pe_2 = 2e-4
    pe_3 = 2e-4

    p_1 = 1 - (1 - pe_1)**A
    p_2 = 1 - (1 - pe_2)**A
    p_3 = 1 - (1 - pe_3)**A

    for j in range(len(X_n[2])):
        P_1 = 1 - (1 - p_1)**X_n[2][j][0]
        P_2 = 1 - (1 - p_2)**X_n[2][j][1]
        P_3 = 1 - (1 - p_3)**X_n[2][j][2]
        P_path = P_1 * P_2 * P_3
        reward.append(P_path)

    return reward

def get_reward_path_4(X_n, A=4000):
    """
    Calculate success rates for Path 4 (3-hop path with lower success rate)
    """
    reward = []
    pe_1 = 1.5e-4
    pe_2 = 1.5e-4
    pe_3 = 1.5e-4

    p_1 = 1 - (1 - pe_1)**A
    p_2 = 1 - (1 - pe_2)**A
    p_3 = 1 - (1 - pe_3)**A

    for j in range(len(X_n[3])):
        P_1 = 1 - (1 - p_1)**X_n[3][j][0]
        P_2 = 1 - (1 - p_2)**X_n[3][j][1]
        P_3 = 1 - (1 - p_3)**X_n[3][j][2]
        P_path = P_1 * P_2 * P_3
        reward.append(P_path)

    return reward

def load_attack_pattern(filename):
    """Load attack pattern from file or generate if not found"""
    try:
        attack_list = np.loadtxt(filename)
        print(f"Loaded attack pattern from {filename}")
        return attack_list
    except FileNotFoundError:
        print(f"File {filename} not found, generating synthetic attack pattern")
        # Generate synthetic Markov attack pattern
        # frame_num = 4000
        # attack_list = np.ones((frame_num, 4))
        # transition_matrix = [[0.35,0.15,0.35,0.15],[0.3,0.2,0.3,0.2],[0.35,0.15,0.35,0.15],[0.3,0.2,0.3,0.2]]
        
        # p_q = [0.25,0.25,0.25,0.25]
        # for frame in range(frame_num):
        #     if frame == 0:
        #         p0 = np.array(p_q)
        #     else:
        #         p0 = np.array(transition_matrix[index])
        #     index = np.random.choice([0,1,2,3], p=p0.ravel())
        #     attack_list[frame][index] = 0
        return generate_markov_attack_pattern()

def analyze_attack_pattern(attack_list):
    """Analyze the generated attack pattern for statistical properties"""
    attack_counts = [0, 0, 0, 0]
    total_frames = len(attack_list)

    for i in range(total_frames):
        for path in range(4):
            if attack_list[i][path] == 0:
                attack_counts[path] += 1

    print(f"Attack Pattern Analysis (Total frames: {total_frames})")
    for path in range(4):
        attack_rate = attack_counts[path] / total_frames
        print(f"- Path {path + 1}: {attack_counts[path]} attacks ({attack_rate:.3f} rate)")

    return attack_counts

def calculate_oracle_solution(reward_list, attack_list):
    """Calculate oracle solution exactly as in expneural.ipynb"""
    frame_number = len(attack_list)
    oracle_path_action_list = []

    for graph_index in range(len(reward_list)):
        oracle_graph_list = []
        for partition_point in range(len(reward_list[graph_index])):
            oracle_frame_list = []
            for frame in range(frame_number):
                dt = reward_list[graph_index][partition_point]*attack_list[frame][graph_index]
                oracle_frame_list.append(dt)
            oracle_graph_list.append(oracle_frame_list)
        oracle_path_action_list.append(oracle_graph_list)

    max_graph_action = []
    oracle_graph_list = []
    for graph_index in range(len(reward_list)):
        x_list = []
        for partition_point in range(len(reward_list[graph_index])):
            x = sum(oracle_path_action_list[graph_index][partition_point])
            x_list.append(x)
        oracle_graph_list.append(max(x_list))
        max_graph_action.append(x_list.index(max(x_list)))

    oracle_path = oracle_graph_list.index(max(oracle_graph_list))
    oracle_action = max_graph_action[oracle_graph_list.index(max(oracle_graph_list))]
    
    print(f"Oracle solution: path = {oracle_path}, action = {oracle_action}")
    return oracle_path, oracle_action





def generate_markov_attack_pattern(graph_num=4, frame_num=4000):
    """
    Generate Markov-based attack patterns exactly as in the original research.
    Based on the attached markov_attack_list files.
    """
    attack_list = []
    transition_matrix_list = [
        [0.35, 0.15, 0.35, 0.15],
        [0.3, 0.2, 0.3, 0.2],
        [0.35, 0.15, 0.35, 0.15],
        [0.3, 0.2, 0.3, 0.2]
    ]

    for frame in range(frame_num):
        attack_list_frame = [1] * graph_num  # 1 means no attack
        attack_list.append(attack_list_frame)

    p_q = [0.25, 0.25, 0.25, 0.25]  # Initial uniform distribution

    for frame in range(frame_num):
        if frame == 0:
            p0 = np.array(p_q)
        else:
            p0 = np.array(transition_matrix_list[index])

        index = np.random.choice([0, 1, 2, 3], p=p0.ravel())
        attack_list_copy = copy.copy(attack_list)
        attack_list_copy[frame][index] = 0  # 0 means attack
        attack_list = attack_list_copy

    return np.array(attack_list)

def load_attack_pattern(frame_count, filename='dataset/markov_attack_list_0713_2022_1.txt'):
    """Load their pre-generated attack patterns"""
    try:
        attack_list = np.loadtxt(filename)
        print(f"Loaded attack pattern from {filename}")
        return attack_list
    except FileNotFoundError:
        print(f"Attack file {filename} not found, generating new pattern")
        return generate_markov_attack_pattern(frame_num=frame_count)

def run_expneural_ucb_experiment():
    """Main EXPNeuralUCB experiment exactly as in their expneural.py"""
    
    # Setup - exactly as their code
    qubit_list = [8,10,8,9]
    X_n = get_context_list(qubit_list)
    
    # Get rewards for each path
    reward_list = []
    reward_list.append(get_reward_path_1(X_n))
    reward_list.append(get_reward_path_2(X_n))
    reward_list.append(get_reward_path_3(X_n))
    reward_list.append(get_reward_path_4(X_n))

    # Display max rewards
    for i in range(len(reward_list)):
        print(f"Path {i+1} max reward: {max(reward_list[i])}")
    
    # Load attack patterns
    attack_list = load_attack_pattern()
    frame_number = len(attack_list)
    
    # Calculate oracle solution
    oracle_path_action_list = []
    for graph_index in range(len(reward_list)):
        oracle_graph_list = []
        for partition_point in range(len(reward_list[graph_index])):
            oracle_frame_list = []
            for frame in range(frame_number):
                dt = reward_list[graph_index][partition_point]*attack_list[frame][graph_index]
                oracle_frame_list.append(dt)
            oracle_graph_list.append(oracle_frame_list)
        oracle_path_action_list.append(oracle_graph_list)
    
    # Find oracle path and action
    max_graph_action = []
    oracle_graph_list = []
    for graph_index in range(len(reward_list)):
        x_list = []
        for partition_point in range(len(reward_list[graph_index])):
            x = sum(oracle_path_action_list[graph_index][partition_point])
            x_list.append(x)
        oracle_graph_list.append(max(x_list))
        max_graph_action.append(x_list.index(max(x_list)))
    
    oracle_path = oracle_graph_list.index(max(oracle_graph_list))
    oracle_action = max_graph_action[oracle_graph_list.index(max(oracle_graph_list))]
    
    print(f'Oracle path: {oracle_path}, Oracle action: {oracle_action}')
    
    # EXPNeuralUCB Algorithm - exactly as their implementation
    regret_list_neuralucbexp = []
    regret = 0
    r_list_neuralucbexp = []
    r_total = 0
    prob_list = []
    estimate_group_reward = []
    estimate_path_action_list = []
    allocation_array = []
    
    # Algorithm parameters - exactly as in their code
    gamma = 1*math.pow(frame_number,-1/4)*math.sqrt(math.log(frame_number))
    eta = 1*math.sqrt(1/frame_number)
    
    for i in range(len(reward_list)):
        estimate_group_reward.append([0])
        allocation_array.append(i)
    
    # Initialize NeuralUCB instances - exactly as their code
    neuralucb_list = []
    beta = 0.2
    neuralucb_list.append(NeuralUCB(2, len(X_n[0]), beta, lamb=1))
    neuralucb_list.append(NeuralUCB(2, len(X_n[1]), beta, lamb=1))
    neuralucb_list.append(NeuralUCB(3, len(X_n[2]), beta, lamb=1))
    neuralucb_list.append(NeuralUCB(3, len(X_n[3]), beta, lamb=1))
    
    start_time = time.time()
    
    print("Starting EXPNeuralUCB experiment...")
    
    # Main algorithm loop - exactly as their implementation
    for frame in range(min(frame_number, 1000)):  # Limit to 1000 for demo
        if frame % 100 == 0:
            print(f"Frame: {frame}")
        
        estimate_path_action = []
        collect_path_action = []
        prob_array = []
        sum_group = 0
        
        # Step 1: Get optimal actions from each group
        for graph_index in range(len(reward_list)):
            arm = neuralucb_list[graph_index].take_action(X_n[graph_index])
            collect_path_action.append([graph_index,arm])
        
        # Step 2: Calculate group probabilities
        for group_index in range(len(estimate_group_reward)):
            sum_group = sum_group + math.exp(eta*sum(estimate_group_reward[group_index]))
        
        for group_index in range(len(estimate_group_reward)):
            p = gamma/len(reward_list) + (1-gamma)*math.exp(eta*sum(estimate_group_reward[group_index]))/sum_group
            prob_array.append(p)
        
        prob_list.append(prob_array)
        
        # Step 3: Sample path based on probabilities
        estimate_path = np.random.choice(allocation_array, p=prob_array)
        estimate_action = collect_path_action[estimate_path][1]
        
        estimate_path_action.append(estimate_path)
        estimate_path_action.append(estimate_action)
        estimate_path_action_list.append(estimate_path_action)
        
        # Step 4: Calculate rewards and update
        X_t = reward_list[estimate_path][estimate_action]
        d_t = np.random.choice([0,1], p=[1-X_t, X_t])
        dt = d_t*attack_list[frame][estimate_path]
        Xt = X_t*attack_list[frame][estimate_path]
        
        # Update NeuralUCB if path not attacked
        if attack_list[frame][estimate_path] > 0:
            neuralucb_list[estimate_path].update(X_n[estimate_path], estimate_action, X_t)
        
        r_total = r_total + Xt
        r_list_neuralucbexp.append(r_total)
        
        # Update group reward estimates
        for group_index in range(len(reward_list)):
            if group_index == estimate_path:
                estimate_group_reward[group_index].append(dt/prob_array[estimate_path])
            else:
                estimate_group_reward[group_index].append(0)
        
        # Calculate regret
        oracle_r = reward_list[oracle_path][oracle_action]*attack_list[frame][oracle_path] - Xt
        if oracle_r < 0:
            oracle_r = 0
        regret = regret + abs(oracle_r)
        regret_list_neuralucbexp.append(regret)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"Experiment completed in {elapsed_time:.2f} seconds")
    print(f"Final regret: {regret}")
    print(f"Final reward: {r_total}")
    
    # Plot results - exactly as their code
    t_range = len(regret_list_neuralucbexp)
    t = np.arange(0, t_range, 1)
    
    # Plot group probabilities
    plt.figure(figsize=(12, 4))
    
    plt.subplot(1, 2, 1)
    group1 = [prob_list[i][0] for i in range(len(prob_list))]
    group2 = [prob_list[i][1] for i in range(len(prob_list))]
    group3 = [prob_list[i][2] for i in range(len(prob_list))]
    group4 = [prob_list[i][3] for i in range(len(prob_list))]
    
    t_prob = np.arange(0, len(prob_list), 1)
    plt.plot(t_prob, group1, color='green', label='Path 1', linestyle="--", linewidth=2)
    plt.plot(t_prob, group2, color='red', label='Path 2', linestyle="--", linewidth=2)
    plt.plot(t_prob, group3, color='blue', label='Path 3', linestyle="--", linewidth=2)
    plt.plot(t_prob, group4, color='purple', label='Path 4', linestyle="--", linewidth=2)
    plt.legend()
    plt.grid()
    plt.xlabel('Frame Number')
    plt.ylabel('Sampling Probability')
    plt.title('Group Sampling Probabilities')
    
    # Plot cumulative regret
    plt.subplot(1, 2, 2)
    plt.plot(t, regret_list_neuralucbexp, color='red', linewidth=2)
    plt.xlabel('Frame Number')
    plt.ylabel('Cumulative Regret')
    plt.title('EXPNeuralUCB Cumulative Regret')
    plt.grid()
    
    plt.tight_layout()
    plt.show()
    
    return {
        'regret_list': regret_list_neuralucbexp,
        'reward_list': r_list_neuralucbexp,
        'prob_list': prob_list,
        'final_regret': regret,
        'final_reward': r_total,
        'execution_time': elapsed_time
    }

# def analyze_attack_pattern(attack_list):
#     """Analyze attack patterns exactly as in their code"""
#     a0 = a1 = a2 = a3 = 0
#     for i in range(len(attack_list)):
#         if attack_list[i][0] == 0:
#             a0 = a0 + 1
#         if attack_list[i][1] == 0:
#             a1 = a1 + 1
#         if attack_list[i][2] == 0:
#             a2 = a2 + 1
#         if attack_list[i][3] == 0:
#             a3 = a3 + 1
    
    print(f"Attack pattern analysis:")
    print(f"Path 0 attacks: {a0}")
    print(f"Path 1 attacks: {a1}")
    print(f"Path 2 attacks: {a2}")
    print(f"Path 3 attacks: {a3}")

if __name__ == "__main__":
    # Load and analyze attack pattern
    attack_list = load_attack_pattern()
    analyze_attack_pattern(attack_list)
    
    # Run the main experiment
    results = run_expneural_ucb_experiment()
    
    print("\nExperiment Results:")
    print(f"Final Regret: {results['final_regret']}")
    print(f"Final Reward: {results['final_reward']}")
    print(f"Execution Time: {results['execution_time']:.2f} seconds")



# ========================= NEURAL NETWORK COMPONENTS =========================

class SimpleNeuralNetwork:
    """Lightweight Neural Network for Quantum Reward Function Approximation"""
    
    def __init__(self, input_dim, hidden_dim=64, lr=0.001):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.lr = lr
        
        # Xavier initialization
        self.W1 = np.random.normal(0, np.sqrt(2.0/input_dim), (input_dim, hidden_dim))
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.normal(0, np.sqrt(2.0/hidden_dim), (hidden_dim, 1))
        self.b2 = np.zeros(1)
        
        # For gradient tracking
        self.last_gradients = None
        
    def forward(self, x):
        """Forward pass with ReLU activation"""
        x = np.array(x).reshape(-1)
        z1 = np.dot(x, self.W1) + self.b1
        a1 = np.maximum(0, z1)  # ReLU
        z2 = np.dot(a1, self.W2) + self.b2
        return z2[0], a1, z1
    
    def compute_gradients(self, x):
        """Compute gradients for UCB confidence bounds"""
        pred, a1, z1 = self.forward(x)
        
        # Gradient w.r.t. output
        grad_output = np.array([1.0])
        
        # Backprop through second layer
        grad_W2 = np.outer(a1, grad_output)
        grad_b2 = grad_output
        
        # Backprop through ReLU
        grad_a1 = np.dot(grad_output, self.W2.T)
        grad_z1 = grad_a1 * (z1 > 0).astype(float)
        
        # Backprop through first layer
        x = np.array(x).reshape(-1)
        grad_W1 = np.outer(x, grad_z1)
        grad_b1 = grad_z1
        
        # Flatten all gradients
        gradients = np.concatenate([
            grad_W1.flatten(),
            grad_b1,
            grad_W2.flatten(),
            grad_b2
        ])
        
        self.last_gradients = gradients
        return gradients
    
    def update_weights(self, x, target):
        """Update weights using gradient descent"""
        pred, a1, z1 = self.forward(x)
        error = pred - target
        
        # Compute gradients
        x_reshaped = np.array(x).reshape(-1)
        
        # Update W2 and b2
        grad_W2 = error * a1.reshape(-1, 1)
        grad_b2 = error
        
        # Update W1 and b1
        grad_a1 = error * self.W2.flatten()
        grad_z1 = grad_a1 * (z1 > 0).astype(float)
        grad_W1 = np.outer(x_reshaped, grad_z1)
        grad_b1 = grad_z1
        
        # Apply updates
        self.W2 -= self.lr * grad_W2
        self.b2 -= self.lr * grad_b2
        self.W1 -= self.lr * grad_W1
        self.b1 -= self.lr * grad_b1



# ========================= QUANTUM ENVIRONMENT =========================

# class QuantumNetworkEnvironment:
#     """Quantum Data Network Environment with Multiple Paths and Attack Models"""
    
#     def __init__(self, qubit_capacities=[8, 10, 8, 9], attack_pattern='markov'):
#         self.qubit_capacities = qubit_capacities
#         self.num_paths = len(qubit_capacities)
#         self.attack_pattern = attack_pattern
        
#         # Generate quantum contexts (qubit allocation strategies)
#         self.contexts = self._generate_contexts()
        
#         # Generate quantum success rates
#         self.reward_functions = self._generate_reward_functions()
        
#         # Calculate true rewards for each path
#         self.true_rewards = []
#         for i, reward_func in enumerate(self.reward_functions):
#             rewards = reward_func(self.contexts)
#             self.true_rewards.append(rewards)
        
#         # Generate attack patterns
#         self.attack_sequences = self._generate_attack_patterns()
    
#     def _generate_contexts(self):
#         """Generate qubit allocation contexts for each quantum path"""
#         contexts = []
        
#         for path_idx, qubit_capacity in enumerate(self.qubit_capacities):
#             if path_idx < 2:  # 2-hop paths
#                 path_contexts = []
#                 for i in range(qubit_capacity + 1):
#                     context = np.array([i, qubit_capacity - i])
#                     path_contexts.append(context)
#                 contexts.append(np.array(path_contexts))
#             else:  # 3-hop paths
#                 path_contexts = []
#                 for i in range(qubit_capacity + 1):
#                     for j in range(qubit_capacity + 1 - i):
#                         context = np.array([i, j, qubit_capacity - i - j])
#                         path_contexts.append(context)
#                 contexts.append(np.array(path_contexts))
        
#         return contexts
    
#     def _generate_reward_functions(self):
#         """Generate quantum entanglement success rate functions"""

#         def path_1_rewards(contexts):
#             return get_reward_path_1(contexts)

#         def path_2_rewards(contexts):
#             return get_reward_path_2(contexts)

#         def path_3_rewards(contexts):
#             return get_reward_path_3(contexts)

#         def path_4_rewards(contexts):
#             return get_reward_path_4(contexts)

#         return [path_1_rewards, path_2_rewards, path_3_rewards, path_4_rewards]

#     def _generate_attack_patterns(self, length=4000):
#         """Generate sophisticated attack patterns"""
#         patterns = {}
        
#         # Markov Chain Attack Pattern
#         transition_matrix = np.array([
#             [0.35, 0.15, 0.35, 0.15],
#             [0.3, 0.2, 0.3, 0.2],
#             [0.35, 0.15, 0.35, 0.15],
#             [0.3, 0.2, 0.3, 0.2]
#         ])
        
#         markov_pattern = np.ones((length, 4))
#         current_state = np.random.choice(4)
        
#         for t in range(length):
#             markov_pattern[t, current_state] = 0
#             current_state = np.random.choice(4, p=transition_matrix[current_state])
        
#         patterns['markov'] = markov_pattern
        
#         # Adaptive Attack Pattern
#         adaptive_pattern = np.ones((length, 4))
#         for t in range(1, length):
#             # Attack the path that was selected most in recent history
#             recent_window = min(t, 50)
#             if t > recent_window:
#                 # Simple heuristic: attack path 1 more often initially
#                 target = (t // 100) % 4
#             else:
#                 target = np.random.choice(4)
#             adaptive_pattern[t, target] = 0
        
#         patterns['adaptive'] = adaptive_pattern
        
#         # Periodic Attack Pattern
#         periodic_pattern = np.ones((length, 4))
#         for t in range(length):
#             target = (t // 200) % 4  # Switch target every 200 steps
#             periodic_pattern[t, target] = 0
        
#         patterns['periodic'] = periodic_pattern
        
#         return patterns
    
#     def get_oracle_solution(self, attack_pattern='markov'):
#         """Compute oracle (optimal) solution given attack pattern"""
#         attack_sequence = self.attack_sequences[attack_pattern]
        
#         # Calculate expected reward for each path-action combination
#         path_action_rewards = []
#         for path_idx in range(self.num_paths):
#             action_rewards = []
#             for action_idx in range(len(self.true_rewards[path_idx])):
#                 total_reward = 0
#                 for t in range(len(attack_sequence)):
#                     reward = (self.true_rewards[path_idx][action_idx] * 
#                              attack_sequence[t, path_idx])
#                     total_reward += reward
#                 action_rewards.append(total_reward)
#             path_action_rewards.append(action_rewards)
        
#         # Find best path and action
#         best_reward = -1
#         best_path, best_action = 0, 0
        
#         for path_idx in range(self.num_paths):
#             max_reward_idx = np.argmax(path_action_rewards[path_idx])
#             if path_action_rewards[path_idx][max_reward_idx] > best_reward:
#                 best_reward = path_action_rewards[path_idx][max_reward_idx]
#                 best_path = path_idx
#                 best_action = max_reward_idx
        
#         return {
#             'oracle_path': best_path,
#             'oracle_action': best_action,
#             'oracle_reward': best_reward,
#             'path_action_rewards': path_action_rewards
#         }


# ========================= QUANTUM ENVIRONMENT =========================

class QuantumNetworkEnvironment:
    """Quantum Data Network Environment with Multiple Paths and Attack Models"""
    
    def __init__(self, qubit_capacities=[8, 10, 8, 9], attack_pattern='markov', frame_length=4000):
        self.qubit_capacities = qubit_capacities
        self.num_paths = len(qubit_capacities)
        self.attack_pattern = attack_pattern
        self.frame_length = frame_length

        # Generate quantum contexts (qubit allocation strategies)
        self.contexts = self._generate_contexts()
        
        # Generate quantum success rates
        self.reward_functions = self._generate_reward_functions(frame=self.frame_length)
        
        # Calculate true rewards for each path
        self.true_rewards = []
        for i, reward_func in enumerate(self.reward_functions):
            rewards = reward_func(self.contexts)
            self.true_rewards.append(rewards)
        
        # Generate attack patterns
        self.attack_sequences = self._generate_attack_patterns(length=self.frame_length)
    
    def _generate_contexts(self):
        """Generate qubit allocation contexts for each quantum path"""
        contexts = []
        
        for path_idx, qubit_capacity in enumerate(self.qubit_capacities):
            if path_idx < 2:  # 2-hop paths
                path_contexts = []
                for i in range(qubit_capacity + 1):
                    context = np.array([i, qubit_capacity - i])
                    path_contexts.append(context)
                contexts.append(np.array(path_contexts))
            else:  # 3-hop paths
                path_contexts = []
                for i in range(qubit_capacity + 1):
                    for j in range(qubit_capacity + 1 - i):
                        context = np.array([i, j, qubit_capacity - i - j])
                        path_contexts.append(context)
                contexts.append(np.array(path_contexts))
        
        return contexts
    
    def _generate_reward_functions(self, frame=4000):
        """Generate quantum entanglement success rate functions"""

        def path_1_rewards(contexts):
            return get_reward_path_1(contexts, A=frame)

        def path_2_rewards(contexts):
            return get_reward_path_2(contexts, A=frame)

        def path_3_rewards(contexts):
            return get_reward_path_3(contexts, A=frame)

        def path_4_rewards(contexts):
            return get_reward_path_4(contexts, A=frame)

        return [path_1_rewards(self.contexts), path_2_rewards(self.contexts), path_3_rewards(self.contexts), path_4_rewards(self.contexts)]

    def _generate_attack_patterns(self, length=4000):
        """Generate sophisticated attack patterns"""
        patterns = {}
        
        # Markov Chain Attack Pattern
        transition_matrix = np.array([
            [0.35, 0.15, 0.35, 0.15],
            [0.3, 0.2, 0.3, 0.2],
            [0.35, 0.15, 0.35, 0.15],
            [0.3, 0.2, 0.3, 0.2]
        ])
        
        markov_pattern = np.ones((length, 4))
        current_state = np.random.choice(4)
        
        for t in range(length):
            markov_pattern[t, current_state] = 0
            current_state = np.random.choice(4, p=transition_matrix[current_state])
        
        patterns['markov'] = markov_pattern
        
        # Adaptive Attack Pattern
        adaptive_pattern = np.ones((length, 4))
        for t in range(1, length):
            # Attack the path that was selected most in recent history
            recent_window = min(t, 50)
            if t > recent_window:
                # Simple heuristic: attack path 1 more often initially
                target = (t // 100) % 4
            else:
                target = np.random.choice(4)
            adaptive_pattern[t, target] = 0
        
        patterns['adaptive'] = adaptive_pattern
        
        # Periodic Attack Pattern
        periodic_pattern = np.ones((length, 4))
        for t in range(length):
            target = (t // 200) % 4  # Switch target every 200 steps
            periodic_pattern[t, target] = 0
        
        patterns['periodic'] = periodic_pattern
        
        return patterns
    
    def get_oracle_solution(self, attack_pattern='markov'):
        """Compute oracle (optimal) solution given attack pattern"""
        attack_sequence = self.attack_sequences[attack_pattern]
        
        # Calculate expected reward for each path-action combination
        path_action_rewards = []
        for path_idx in range(self.num_paths):
            action_rewards = []
            for action_idx in range(len(self.true_rewards[path_idx])):
                total_reward = 0
                for t in range(len(attack_sequence)):
                    reward = (self.true_rewards[path_idx][action_idx] * 
                             attack_sequence[t, path_idx])
                    total_reward += reward
                action_rewards.append(total_reward)
            path_action_rewards.append(action_rewards)
        
        # Find best path and action
        best_reward = -1
        best_path, best_action = 0, 0
        
        for path_idx in range(self.num_paths):
            max_reward_idx = np.argmax(path_action_rewards[path_idx])
            if path_action_rewards[path_idx][max_reward_idx] > best_reward:
                best_reward = path_action_rewards[path_idx][max_reward_idx]
                best_path = path_idx
                best_action = max_reward_idx
        
        return {
            'oracle_path': best_path,
            'oracle_action': best_action,
            'oracle_reward': best_reward,
            'path_action_rewards': path_action_rewards
        }