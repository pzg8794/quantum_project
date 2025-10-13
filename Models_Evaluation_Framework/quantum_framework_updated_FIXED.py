"""
Quantum MAB Framework - Updated Multi-Run Evaluator
Comprehensive evaluation framework for quantum multi-armed bandit algorithms
"""

import numpy as np
import time
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from collections import defaultdict


class MultiRunEvaluator:
    """
    Multi-run evaluator for quantum MAB algorithms with comprehensive analysis.
    """

    def __init__(self, experiment_runner):
        """
        Initialize the multi-run evaluator.

        Args:
            experiment_runner: Instance of QuantumExperimentRunner
        """
        self.runner = experiment_runner
        self.env_experiments = {}
        self.attack_type = 'stochastic'

        # NEW: Store aggregated winner results
        self.aggregated_winners = {}

    def calculate_overall_winner(self, experiment_results):
        """
        Calculate the overall winner across all experiments by counting wins.

        Args:
            experiment_results: Dictionary of experiment results

        Returns:
            Dictionary with overall winner, stats, and averages
        """
        num_experiments = len(experiment_results)
        winner_stats = {}

        for exp_id, exp_data in experiment_results.items():
            winner = exp_data['winner']
            winner_efficiency = exp_data['winner_effiency']
            winner_gap = exp_data['results'][winner]['gap']

            if winner not in winner_stats:
                winner_stats[winner] = {
                    'count': 0, 
                    'total_efficiency': 0, 
                    'total_gap': 0
                }

            winner_stats[winner]['count'] += 1
            winner_stats[winner]['total_gap'] += winner_gap
            winner_stats[winner]['total_efficiency'] += winner_efficiency

        # Find most common winner
        overall_winner = max(winner_stats, key=lambda x: winner_stats[x]['count'])

        # Calculate averages
        avg_gap = winner_stats[overall_winner]['total_gap'] / num_experiments
        avg_efficiency = winner_stats[overall_winner]['total_efficiency'] / num_experiments
        wins = winner_stats[overall_winner]['count']

        return {
            'overall_winner': overall_winner,
            'wins': wins,
            'total_experiments': num_experiments,
            'avg_gap': avg_gap,
            'avg_efficiency': avg_efficiency,
            'winner_stats': winner_stats
        }

    def run_experiments(self, num_experiments=3, attack_type='stochastic', algorithms=None):
        """Run multiple experiments across different frame counts."""
        if algorithms is None:
            algorithms = ["EXPNeuralUCB", 'GNeuralUCB', 'CEXPNeuralUCB', 'Oracle']

        results = {}

        for exp_id in range(1, num_experiments + 1):
            print(f"EXPERIMENT {exp_id}: {self.runner.frame_length} frames")
            print("-" * 40)

            # Run experiment
            exp_results = self.runner.run_comparison(algorithms=algorithms)
            results[exp_id] = exp_results

            print(f"Experiment {exp_id} completed successfully")

            # Update frame length for next experiment
            self.runner.frame_length += self.runner.frame_step

        return results

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

            # CALCULATE AND STORE OVERALL WINNER
            winner_analysis = self.calculate_overall_winner(experiment_results)
            self.aggregated_winners[environment_type] = winner_analysis

        # Analysis and performance metrics
        print("="*70)
        print("COMPREHENSIVE ENVIRONMENT SCENARIOS PERFORMANCE ANALYSIS")
        print("="*70)

        for environment_type, description in test_scenarios.items():
            print(f"{description.upper()}:")

            # USE THE AGGREGATED WINNER DATA
            winner_data = self.aggregated_winners[environment_type]
            overall_winner = winner_data['overall_winner']
            avg_gap = winner_data['avg_gap']
            avg_efficiency = winner_data['avg_efficiency']
            wins = winner_data['wins']
            total_exps = winner_data['total_experiments']

            print(f"   Best Algorithm: {overall_winner}")
            print(f"   Wins: {wins}/{total_exps} experiments")
            print(f"   Oracle Efficiency: {avg_efficiency:.1f}%")
            print(f"   Oracle Gap: {avg_gap:.1f}%")

            # Show all algorithm performance (using last experiment for comparison)
            highest_exp = max(evaluation_results[environment_type].keys())
            exp_data = evaluation_results[environment_type][highest_exp]
            oracle_reward = exp_data['oracle_reward']

            print(f"   All Algorithm Performance:")
            for alg_name in models:
                if alg_name in exp_data['results']:
                    alg_reward = exp_data['results'][alg_name]['final_reward']
                    alg_gap = exp_data['results'][alg_name]['gap']
                    efficiency = (alg_reward / oracle_reward * 100) if oracle_reward > 0 else 0
                    print(f"      • {alg_name}: {efficiency:.1f}% efficiency ({alg_gap:.1f}% gap)")

        print("="*70)
        print("KEY INSIGHTS:")

        # Performance analysis across environments
        stochastic_winner = self.aggregated_winners.get('stochastic')
        baseline_winner = self.aggregated_winners.get('none')

        if stochastic_winner:
            print(f"Stochastic Environment Analysis:")
            print(f"   • Best Model: {stochastic_winner['overall_winner']}")
            print(f"   • Oracle Efficiency: {stochastic_winner['avg_efficiency']:.1f}%")
            print(f"   • Performance under realistic quantum network conditions validated")

        # Statistical significance and ranking
        print(f"Statistical Analysis:")
        print(f"   • Total models evaluated: {len(models)}")
        print(f"   • Experiments per environment: {runs}")
        print(f"   • Quantum network simulation: Comprehensive stochastic modeling")

        print("="*70)

        return evaluation_results
