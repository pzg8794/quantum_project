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
        self.env_experiments = {}  # {attack_type: {exp_id: experiment_data}}

        # Configuration
        self.base_seed = base_seed
        self.base_frames = base_frames
        self.frame_step = frame_step
        self.attack_type = attack_type
        self.attack_intensity = attack_intensity
        self.enable_progress = enable_progress

        # Results tracking
        self.env_experiments[self.attack_type] = {}
        self.all_results = []  # Flat list of all results
        self.start_time = None
        self.total_time = 0

        # Analysis storage
        self.gap_analysis = {}  # {algorithm: [gap1, gap2, gap3, ...]}

        print(f"Multi-Run Evaluator Initialized")
        print(f"Environment Type: {attack_type}")
        print(f"Frame Range: {base_frames} -> {base_frames + 2*frame_step} (step: {frame_step})")

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


    def calculate_scenario_winner(self, comparison_results, scenario):
        """
        Correctly calculates comprehensive stats for a single scenario.
        This version returns clean data with no side effects (no printing).
        """
        if scenario not in comparison_results:
            return {}

        all_experiments = comparison_results[scenario]
        num_experiments = len(all_experiments)
        if num_experiments == 0:
            return {}

        # --- Step 1: Aggregate stats for ALL models and count wins ---
        model_totals = {}
        win_counts = {}
        total_oracle_reward = 0

        for exp_data in all_experiments.values():
            total_oracle_reward += exp_data['oracle_reward']
            
            # Count wins for each model
            winner = exp_data.get('winner')
            if winner:
                win_counts[winner] = win_counts.get(winner, 0) + 1

            # Aggregate performance stats for every model
            for model_name, model_result in exp_data['results'].items():
                if model_name not in model_totals:
                    model_totals[model_name] = {'avg_reward': 0, 'avg_gap': 0}
                
                model_totals[model_name]['avg_reward'] += model_result['final_reward']
                model_totals[model_name]['avg_gap'] += model_result.get('gap', 0)

        # --- Step 2: Calculate final averages for each model ---
        all_model_averages = {}
        avg_oracle_reward = total_oracle_reward / num_experiments

        for model_name, totals in model_totals.items():
            avg_reward = totals['avg_reward'] / num_experiments
            avg_gap = totals['avg_gap'] / num_experiments
            avg_efficiency = (avg_reward / avg_oracle_reward * 100) if avg_oracle_reward > 0 else 0
            all_model_averages[model_name] = {
                'avg_gap': avg_gap,
                'avg_reward': avg_reward,
                'avg_efficiency': avg_efficiency
            }

        # --- Step 3: Determine the overall winner (most wins) ---
        overall_winner = max(win_counts, key=win_counts.get) if win_counts else "N/A"
        
        # --- Step 4: Return a structured dictionary with all data ---
        return {
            'oracle_avg_reward': avg_oracle_reward,
            'total_experiments': num_experiments,
            'overall_winner': overall_winner,
            'win_counts': win_counts,
            'all_model_metrics': all_model_averages,
            # Include metrics for the winning model for easy access
            'avg_gap': all_model_averages[overall_winner]['avg_gap'],
            'avg_reward': all_model_averages[overall_winner]['avg_reward'],
            'winner_avg_metrics': all_model_averages.get(overall_winner, {}),
            'avg_efficiency': all_model_averages[overall_winner]['avg_efficiency']
        }

    def calculate_scenarios_winner(self, comparison_results, test_scenarios):
        """
        Wrapper to calculate winner stats for all specified scenarios.
        """
        scenario_stats = {}
        for scenario in test_scenarios.keys():
            if scenario in comparison_results:
                scenario_stats[scenario] = self.calculate_scenario_winner(comparison_results, scenario)
        
        return scenario_stats


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

        # Run experiments for all specified scenarios
        evaluation_results = {}
        for environment_type, description in test_scenarios.items():
            print(f"TESTING ENVIRONMENT SCENARIO: {description}")
            print("="*50)
            self.attack_type = environment_type
            if environment_type not in self.env_experiments:
                self.env_experiments[environment_type] = {}
            
            # We assume attack_type is handled correctly inside run_experiments
            experiment_results = self.run_experiments(num_experiments=runs, attack_type=environment_type, algorithms=models)
            evaluation_results[environment_type] = experiment_results

        # --- Step 1: Calculate all stats using the corrected, robust function ---
        scenarios_stats = self.calculate_scenarios_winner(evaluation_results, test_scenarios)

        # --- Step 2: Print the summary using the NEW data structure ---
        print("\n" + "="*70)
        print("COMPREHENSIVE SCENARIO PERFORMANCE ANALYSIS")
        print("="*70)

        for scenario, stats in scenarios_stats.items():
            if stats:
                description = test_scenarios.get(scenario, scenario.title())
                print(f"SCENARIO: {description.upper()}")
                print("-" * 40)
                
                winner = stats.get('overall_winner', 'N/A')
                win_count = stats.get('win_counts', {}).get(winner, 0)
                total_exps = stats.get('total_experiments', 0)
                
                print(f"  Recommended Model: {winner} (Won {win_count}/{total_exps} experiments)")
                
                # Access the nested dictionary for the winner's metrics
                winner_metrics = stats.get('winner_avg_metrics', {})
                if winner_metrics:
                    print(f"  Winner Avg Efficiency: {winner_metrics.get('avg_efficiency', 0):.1f}%")
                    print(f"  Winner Avg Gap: {winner_metrics.get('avg_gap', 0):.1f}%")

                print("\n  Overall Model Performance:")
                
                # Access the nested dictionary for all models' metrics
                all_metrics = stats.get('all_model_metrics', {})
                
                # Sort models by their true average efficiency for a ranked view
                sorted_models = sorted(
                    all_metrics.items(), 
                    key=lambda item: item[1].get('avg_efficiency', 0), 
                    reverse=True
                )

                for model_name, metrics in sorted_models:
                    if model_name != 'Oracle':
                        print(f"    • {model_name:<15}: {metrics.get('avg_efficiency', 0):.1f}% Efficiency")
                print("="*70)

        evaluation_results.update({'scenarios_results':scenarios_stats})

        # --- Your KEY INSIGHTS section remains the same and should now work correctly ---
        print("KEY INSIGHTS:")

        # Performance retention analysis if both stochastic and baseline exist
        if 'stochastic' in scenarios_stats and scenarios_stats['stochastic'] and 'none' in scenarios_stats and scenarios_stats['none']:
            stoch_stats = scenarios_stats['stochastic']
            baseline_stats = scenarios_stats['none']
            
            best_model = stoch_stats['overall_winner']
            stoch_performance = stoch_stats['avg_reward']
            baseline_performance = baseline_stats['avg_reward']
            
            # Calculate realistic performance retention
            performance_retention = (stoch_performance / baseline_performance * 100) if baseline_performance > 0 else 100
            
            print(f"Best Performing Model Analysis ({best_model}):")
            print(f"   • Stochastic Performance: {stoch_performance:.3f}")
            print(f"   • Baseline Performance: {baseline_performance:.3f}")
            print(f"   • Performance Retention: {performance_retention:.1f}%")
            
            if performance_retention > 95:
                print(f"   EXCELLENT: Minimal performance loss under realistic conditions")
            elif performance_retention > 85:
                print(f"   GOOD: Acceptable performance under stochastic conditions")
            elif performance_retention > 75:
                print(f"   MODERATE: Some degradation under realistic network conditions")
            else:
                print(f"   NEEDS IMPROVEMENT: Significant performance loss in stochastic environment")

        elif 'stochastic' in scenarios_stats and scenarios_stats['stochastic']:
            # Stochastic-only analysis
            stoch_stats = scenarios_stats['stochastic']
            print(f"Stochastic Environment Analysis:")
            print(f"   • Best Model: {stoch_stats['overall_winner']}")
            print(f"   • Oracle Efficiency: {stoch_stats['avg_efficiency']:.1f}%")
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
            gaps = [exp['results'][alg]['gap']  for exp in experiments.values()]

            print(f"{alg}:")
            print(f"   Rewards: {np.mean(rewards):.1f} ± {np.std(rewards):.1f}")
            print(f"   Avg Gap: {np.mean(gaps):.1f}%")
            print(f"   Wins: {sum(1 for exp in experiments.values() if exp['winner'] == alg)}/{len(experiments)}")

        # Oracle efficiency analysis
        oracle_rewards = [exp['oracle_reward'] for exp in experiments.values()]
        print(f"Oracle Performance: {np.mean(oracle_rewards):.1f} ± {np.std(oracle_rewards):.1f}")

        # Best performing algorithm
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
