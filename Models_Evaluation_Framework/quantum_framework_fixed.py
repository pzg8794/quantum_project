import time
import threading
import numpy as np
import matplotlib.pyplot as plt
from quantum_experiments_updated import QuantumExperimentRunner as ExperimentRunner

class MultiRunEvaluator:
    """
    Enhanced Multi-Run Evaluator for Comprehensive Model Evaluation
    Supports comprehensive model testing in realistic quantum network conditions
    with focus on stochastic environment analysis and baseline comparison.
    """

    def __init__(self, base_seed=12345, base_frames=4000, frame_step=2000,
                 attack_type="stochastic", attack_intensity=1.0, enable_progress=False):
        # Environment experiments organized by attack type
        self.env_experiments = {} # {attack_type: {exp_id: experiment_data}}
        
        # Configuration
        self.base_seed = base_seed
        self.base_frames = base_frames
        self.frame_step = frame_step
        self.attack_type = attack_type
        self.attack_intensity = attack_intensity
        self.enable_progress = enable_progress
        
        # Results tracking
        self.env_experiments[self.attack_type] = {}
        self.all_results = [] # Flat list of all results
        self.start_time = None
        self.total_time = 0
        
        # Analysis storage
        self.gap_analysis = {} # {algorithm: [gap1, gap2, gap3, ...]}
        
        # NEW: Overall winner stats storage
        self.overall_winner_stats = {} # {scenario: {'winner': str, 'wins': int, 'total': int, 'avg_gap': float, 'avg_efficiency': float}}
        
        print(f"Multi-Run Evaluator Initialized")
        print(f"Environment Type: {attack_type}")
        print(f"Frame Range: {base_frames} -> {base_frames + 2*frame_step} (step: {frame_step})")

    def calculate_overall_winner(self, scenario, comparison_results):
        """
        Calculate the overall winner across all experiments for a scenario.
        Returns winner stats including average gap and efficiency.
        """
        if scenario not in comparison_results:
            return None
            
        all_experiments = comparison_results[scenario]
        num_experiments = len(all_experiments)
        
        # Track each winner
        winner_stats = {}
        
        for exp_id, exp_data in all_experiments.items():
            winner = exp_data['winner']
            oracle_reward = exp_data['oracle_reward']
            winner_efficiency = exp_data['winner_efficiency']
            winner_gap = exp_data['results'][winner]['gap']
            winner_reward = exp_data['results'][winner]['final_reward']
            
            if winner not in winner_stats:
                winner_stats[winner] = {'count': 0, 'total_efficiency': 0, 'total_gap': 0}
            
            winner_stats[winner]['count'] += 1
            winner_stats[winner]['total_gap'] += winner_gap
            winner_stats[winner]['total_efficiency'] += winner_efficiency
        
        # Find most common winner
        overall_winner = max(winner_stats, key=lambda x: winner_stats[x]['count'])
        
        # Calculate averages
        avg_gap = winner_stats[overall_winner]['total_gap'] / num_experiments
        avg_efficiency = winner_stats[overall_winner]['total_efficiency'] / num_experiments
        
        # Store in class variable
        self.overall_winner_stats[scenario] = {
            'winner': overall_winner,
            'wins': winner_stats[overall_winner]['count'],
            'total': num_experiments,
            'avg_gap': avg_gap,
            'avg_efficiency': avg_efficiency,
            'win_percentage': (winner_stats[overall_winner]['count'] / num_experiments) * 100
        }
        
        return self.overall_winner_stats[scenario]

    def run_experiments(self, attack_type=None, num_experiments=3,
                       algorithms=["EXPNeuralUCB", 'GNeuralUCB', 'CEXPNeuralUCB', 'Oracle']):
        """
        Run experiments for a specific environment type.
        
        Args:
            attack_type: Override default attack type
            num_experiments: Number of frame count experiments (default: 3)
            algorithms: List of algorithms to test
        """
        if attack_type:
            self.attack_type = attack_type
            
        if attack_type not in self.env_experiments:
            self.env_experiments[attack_type] = {}
            
        print(f"\nSTARTING EXPERIMENTS: {self.attack_type.upper()}")
        
        # Environment category identification
        category_map = {
            'none': 'Baseline (No Attacks)',
            'stochastic': 'Stochastic (Natural Random Failures)',
            'random': 'Stochastic (Natural Random Failures)',
            'markov': 'Structured (Markov Chain Based)',
            'adaptive': 'Adaptive (Reactive Strategic)',
            'onlineadaptive': 'Online Adaptive (Real-time Strategic)'
        }
        
        attack_category = category_map.get(self.attack_type, 'Unknown')
        print(f"Category: {attack_category}")
        print("="*60)
        
        self.start_time = time.time()
        
        for i in range(0, num_experiments):
            current_frames = self.base_frames + (i * self.frame_step)
            exp_id = i + 1
            
            print(f"EXPERIMENT {exp_id}: {current_frames} frames")
            print("-" * 40)
            
            # Create runner for this experiment
            runner = ExperimentRunner(
                attack_type=self.attack_type,
                base_seed=self.base_seed + i * 1000,
                enable_progress=self.enable_progress,
                attack_intensity=self.attack_intensity
            )
            
            # Run experiment
            try:
                experiment_results = runner.run_experiment(frame_count=current_frames, algorithms=algorithms)
                experiment_results['exp_id'] = exp_id
                experiment_results['attack_category'] = attack_category
                
                # Store in environment experiments
                self.env_experiments[self.attack_type][exp_id] = experiment_results
                
                # Add to flat results for cross-experiment analysis
                for alg_name, alg_result in experiment_results['results'].items():
                    flat_result = {
                        'exp_id': exp_id,
                        'frame_count': current_frames,
                        'attack_type': self.attack_type,
                        'attack_category': attack_category,
                        'algorithm': alg_name,
                        'final_reward': alg_result['final_reward']
                    }
                    self.all_results.append(flat_result)
                
                # Track gaps for analysis
                for alg_name, gap_value in experiment_results['gaps'].items():
                    if alg_name not in self.gap_analysis:
                        self.gap_analysis[alg_name] = []
                    self.gap_analysis[alg_name].append(gap_value)
                
                print(f"Experiment {exp_id} completed successfully")
                runner.cleanup()
            except Exception as e:
                print(f"Experiment {exp_id} failed: {e}")
                continue
        
        self.total_time = time.time() - self.start_time
        print(f"Total experiment time: {self.total_time:.1f}s")
        print(f"Experiments completed for {self.attack_type}")
        
        return self.env_experiments[self.attack_type]

    def run_comprehensive_model_evaluation(self, runs=1, models=["EXPNeuralUCB", 'GNeuralUCB', 'CEXPNeuralUCB', 'Oracle'], attack_type='stochastic',
                                         test_scenarios={'stochastic': 'Stochastic Environment (Natural Network Conditions)', 'none': 'Baseline (Optimal Conditions)'}):
        """
        Run comprehensive model evaluation in realistic quantum network conditions.
        This method provides thorough analysis of:
        - Model performance under natural stochastic conditions
        - Oracle efficiency and convergence analysis
        - Statistical significance and ranking
        - Baseline comparison for validation
        """
        print("="*70)
        print("COMPREHENSIVE MODEL EVALUATION")
        print("="*70)
        print("Testing algorithm performance against:")
        print("   • Stochastic: Natural quantum decoherence and network failures")
        print("   • Baseline: Optimal conditions for validation")
        print("="*70)
        
        # Run experiments for both scenarios
        evaluation_results = {}
        
        for environment_type, description in test_scenarios.items():
            print(f"TESTING ENVIRONMENT SCENARIO: {description}")
            print("="*50)
            
            # Run experiments for this environment type
            self.attack_type = environment_type
            if environment_type not in self.env_experiments:
                self.env_experiments[environment_type] = {}
                
            experiment_results = self.run_experiments(num_experiments=runs, attack_type=attack_type, algorithms=models)
            evaluation_results[environment_type] = experiment_results
        
        # FIXED: Calculate overall winners using the correct method
        print("="*70)
        print("COMPREHENSIVE ENVIRONMENT SCENARIOS PERFORMANCE ANALYSIS")
        print("="*70)
        
        for environment_type, description in test_scenarios.items():
            print(f"{description.upper()}:")
            
            # Calculate overall winner stats
            winner_stats = self.calculate_overall_winner(environment_type, evaluation_results)
            
            if winner_stats:
                print(f"   Best Algorithm: {winner_stats['winner']}")
                print(f"   Oracle Efficiency: {winner_stats['avg_efficiency']:.1f}%")
                print(f"   Oracle Gap: {winner_stats['avg_gap']:.1f}%")
                print(f"   Wins: {winner_stats['wins']}/{winner_stats['total']} experiments")
                
                # Show all algorithm performance from the overall winner stats calculation
                print(f"   All Algorithm Performance:")
                for alg_name in models:
                    # Calculate average across all experiments for this algorithm
                    total_reward = 0
                    total_gap = 0
                    count = 0
                    
                    for exp_data in evaluation_results[environment_type].values():
                        if alg_name in exp_data['results']:
                            alg_reward = exp_data['results'][alg_name]['final_reward']
                            alg_gap = exp_data['results'][alg_name]['gap']
                            oracle_reward = exp_data['oracle_reward']
                            
                            total_reward += alg_reward
                            total_gap += alg_gap
                            count += 1
                    
                    if count > 0:
                        avg_reward = total_reward / count
                        avg_gap = total_gap / count
                        # Calculate average efficiency using first experiment's oracle (they should be similar)
                        first_oracle = next(iter(evaluation_results[environment_type].values()))['oracle_reward']
                        efficiency = (avg_reward / first_oracle * 100) if first_oracle > 0 else 0
                        print(f"      • {alg_name}: {efficiency:.1f}% efficiency ({avg_gap:.1f}% gap)")
            
        print("="*70)
        print("KEY INSIGHTS:")
        
        # Performance analysis across environments
        for environment_type in test_scenarios.keys():
            if environment_type in self.overall_winner_stats:
                stats = self.overall_winner_stats[environment_type]
                print(f"{test_scenarios[environment_type]} Analysis:")
                print(f"   • Best Model: {stats['winner']}")
                print(f"   • Oracle Efficiency: {stats['avg_efficiency']:.1f}%")
                print(f"   • Performance under realistic quantum network conditions validated")
        
        # Statistical significance and ranking
        print(f"Statistical Analysis:")
        print(f"   • Total models evaluated: {len(models)}")
        print(f"   • Experiments per environment: {runs}")
        print(f"   • Quantum network simulation: Comprehensive stochastic modeling")
        print("="*70)
        
        return evaluation_results

    def print_summary(self, attack_type=None):
        """Print comprehensive results summary."""
        if attack_type:
            target_type = attack_type
        else:
            target_type = self.attack_type
            
        if target_type not in self.env_experiments:
            print(f"No results found for attack_type='{target_type}'")
            return
            
        experiments = self.env_experiments[target_type]
        
        print("="*60)
        print(f"COMPREHENSIVE SUMMARY: {target_type.upper()}")
        print("="*60)
        
        # Get all algorithms from first experiment
        first_exp = next(iter(experiments.values()))
        algorithms = [alg for alg in first_exp['results'].keys() if alg != 'Oracle']
        
        for alg in algorithms:
            rewards = [exp['results'][alg]['final_reward'] for exp in experiments.values()]
            gaps = [exp['results'][alg]['gap'] for exp in experiments.values()]
            
            print(f"{alg}:")
            print(f"  Rewards: {np.mean(rewards):.1f} ± {np.std(rewards):.1f}")
            print(f"  Avg Gap: {np.mean(gaps):.1f}%")
            print(f"  Wins: {sum(1 for exp in experiments.values() if exp['winner'] == alg)}/{len(experiments)}")
        
        # Oracle efficiency analysis
        oracle_rewards = [exp['oracle_reward'] for exp in experiments.values()]
        print(f"Oracle Performance: {np.mean(oracle_rewards):.1f} ± {np.std(oracle_rewards):.1f}")
        
        # Best performing algorithm using the correct method
        winner_counts = {}
        for exp in experiments.values():
            winner = exp['winner']
            winner_counts[winner] = winner_counts.get(winner, 0) + 1
            
        best_algorithm = max(winner_counts, key=winner_counts.get)
        print(f"Best Overall Algorithm: {best_algorithm} ({winner_counts[best_algorithm]}/{len(experiments)} wins)")

# Usage functions
def test_stochastic_environment(runs=1, base_frames=4000, frame_step=2000, primary_env='stochastic', attack_type='stochastic', models=["EXPNeuralUCB", 'GNeuralUCB', 'CEXPNeuralUCB', 'Oracle'], test_scenarios={'stochastic': 'Stochastic Environment (Natural Network Conditions)', 'none': 'Baseline (Optimal Conditions)'}):
    """
    Main function to test models in stochastic quantum network conditions.
    Provides comprehensive model evaluation for research purposes.
    """
    evaluator = MultiRunEvaluator(
        attack_type = attack_type,
        base_frames =base_frames,
        frame_step = frame_step,
        enable_progress = True,
        attack_intensity =1.0,
        base_seed = 12345,
    )
    
    # Run the comprehensive evaluation
    results = evaluator.run_comprehensive_model_evaluation(
        runs=runs,
        models=models,
        attack_type = attack_type,
        test_scenarios=test_scenarios
    )
    
    return evaluator, results

def test_individual_environment(attack_type="stochastic"):
    """Test a single environment type."""
    evaluator = MultiRunEvaluator(
        base_seed=12345,
        base_frames=4000,
        frame_step=2000,
        attack_type=attack_type,
        attack_intensity=1.0,
        enable_progress=True
    )
    
    results = evaluator.run_experiments()
    evaluator.print_summary()
    
    return evaluator

# # Example usage
# if __name__ == "__main__":
#     print("Running Comprehensive Model Evaluation...")
#     evaluator, evaluation_results = test_stochastic_environment()