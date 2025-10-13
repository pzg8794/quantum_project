import gc
import torch
import numpy as np
from quantum_tools import *
from quantum_models import *

class ExperimentRunner:
    """
    Simple scientific experiment with clean OOP and summary per run
    """
    
    def __init__(self, base_seed=12345):
        self.base_seed = base_seed
        self.qubit_list = [8, 10, 8, 9]
        self.X_n = get_context_list(self.qubit_list)
        self.reward_list = calculate_all_rewards(self.X_n)
        
        # Experimental data (encapsulated)
        self.attack_list = None
        self.experiment_seed = None
        
        # Algorithm instances (encapsulated)
        self.oracle_alg = None
        self.neural_alg = None
        self.exp3_alg = None
        self.hybrid_alg = None

    def generate_markov_attack_pattern(self, graph_num=4, frame_num=4000):
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

    def load_attack_pattern(self, frame_count=4000, filename='markov_attack_list_0713_2022_4.txt'):
        """Load attack pattern from file or generate if not found"""
        try:
            # print current directory
            curr_dir = os.getcwd()
            file_dir = f"{curr_dir}/dataset/{filename}"
            print(f"Current directory: {curr_dir}")
            attack_list = np.loadtxt(file_dir)
            print(f"Loaded attack pattern from {file_dir}")
            return attack_list
        except Exception as e:
            # print(f"Error loading {filename}: {e}")
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
            return self.generate_markov_attack_pattern(frame_num=frame_count)

    def run_single_experiment(self, frame_count, experiment_id):
        """Run complete experiment with simple summary"""
        print(f"\n🔬 EXPERIMENT {experiment_id}: {frame_count} frames")
        
        # Setup
        self.experiment_seed = self.base_seed + experiment_id
        self.attack_list = self.load_attack_pattern(frame_count=frame_count)

        # Run algorithms
        self._run_oracle(frame_count)
        # self._cleanup_between_algorithms()
        
        self._run_neural_baseline(frame_count)
        # self._cleanup_between_algorithms()
        
        self._run_exp3_baseline(frame_count)
        # self._cleanup_between_algorithms()
        
        self._run_hybrid_test(frame_count)
        # self._cleanup_between_algorithms()
        
        # Simple summary per run
        self.print_experiment_summary()
    
    def _run_oracle(self, frame_count):
        self.set_all_seeds(self.experiment_seed + 100)
        self.oracle_alg = Oracle(self.X_n, self.reward_list, self.attack_list)
        
        for frame in range(frame_count):
            path, action = self.oracle_alg.take_action()
            base_reward = self.reward_list[path][action]
            final_reward = base_reward * self.attack_list[frame][path]
            self.oracle_alg.update(path, action, final_reward)
    
    def _run_neural_baseline(self, frame_count):
        self.set_all_seeds(self.experiment_seed + 200)
        self.neural_alg = EXPNeuralUCB(
            X_n=self.X_n,
            reward_list=self.reward_list,
            frame_number=frame_count,
            mode='neural',
            beta=0.2
        )
        self.neural_alg.run_experiment(self.attack_list, verbose=False)
    
    def _run_exp3_baseline(self, frame_count):
        self.set_all_seeds(self.experiment_seed + 300)
        self.exp3_alg = EXPNeuralUCB(
            X_n=self.X_n,
            reward_list=self.reward_list,
            frame_number=frame_count,
            mode='exp3',
            gamma_factor=0.1,
            eta_factor=0.005,
            beta=0.2
        )
        self.exp3_alg.run_experiment(self.attack_list, verbose=False)
    
    def _run_hybrid_test(self, frame_count):
        self.set_all_seeds(self.experiment_seed + 400)
        self.hybrid_alg = EXPNeuralUCB(
            X_n=self.X_n,
            reward_list=self.reward_list,
            frame_number=frame_count,
            mode='hybrid',
            gamma_factor=0.01,
            eta_factor=0.05,
            beta=0.2
        )
        self.hybrid_alg.run_experiment(self.attack_list, verbose=False)
    
    def print_experiment_summary(self):
        """Simple OOP summary per run"""
        results = self.get_results()
        
        print("📊 RESULTS:")
        print(f"   Oracle:  {results['Oracle']['final_reward']:.2f}")
        print(f"   Neural:  {results['GNeuralUCB']['final_reward']:.2f}")
        print(f"   EXP3:    {results['EXPUCB']['final_reward']:.2f}")
        print(f"   Hybrid:  {results['EXPNeuralUCB']['final_reward']:.2f}")
        
        # Winner
        algorithms = ['GNeuralUCB', 'EXPUCB', 'EXPNeuralUCB']
        winner = max(algorithms, key=lambda x: results[x]['final_reward'])
        print(f"   🏆 Winner: {winner}")
    
    def _cleanup_between_algorithms(self):
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def get_results(self):
        return {
            'Oracle': self.oracle_alg.get_results(),
            'GNeuralUCB': self.neural_alg.get_results(),
            'EXPUCB': self.exp3_alg.get_results(),
            'EXPNeuralUCB': self.hybrid_alg.get_results()
        }
    
    def full_experiment_cleanup(self):
        self.oracle_alg = None
        self.neural_alg = None
        self.exp3_alg = None
        self.hybrid_alg = None
        self.attack_list = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()

    def set_all_seeds(self, seed_value):
        random.seed(seed_value)
        os.environ['PYTHONHASHSEED'] = str(seed_value)
        np.random.seed(seed_value)
        torch.manual_seed(seed_value)
        torch.cuda.manual_seed(seed_value)
        torch.cuda.manual_seed_all(seed_value)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def run_contamination_free_experiments(FRAME_NUMBERS = [6000, 4000, 8000]):
    """Run multiple experiments with different frame counts"""
    for experiment_id, frame_count in enumerate(FRAME_NUMBERS, 1):
        runner = ExperimentRunner(base_seed=12345)
        runner.run_single_experiment(frame_count, experiment_id)
        runner.full_experiment_cleanup()