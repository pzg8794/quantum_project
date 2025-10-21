
import time
import threading
import numpy as np
import matplotlib.pyplot as plt
from quantum_experiments_updated import QuantumExperimentRunner as ExperimentRunner

class MultiRunEvaluator:
    """
    Enhanced Multi-Run Evaluator with Clear Stochastic vs Adversarial Testing

    Supports both individual environment testing and direct Stochastic vs Adversarial comparison.
    """

    def __init__(self, base_seed=12345, base_frames=4000, frame_step=2000, 
                 attack_type="markov", attack_intensity=1.0, enable_progress=False):

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

        print(f"🔬 Multi-Run Evaluator Initialized")
        print(f"📊 Attack Type: {attack_type}")
        print(f"🎯 Frame Range: {base_frames} → {base_frames + 2*frame_step} (step: {frame_step})")

    def run_experiments(self, attack_type=None, num_experiments=3):
        """
        Run experiments for a specific attack type.

        Args:
            attack_type: Override default attack type
            num_experiments: Number of frame count experiments (default: 3)
        """
        if attack_type:
            self.attack_type = attack_type
            if attack_type not in self.env_experiments:
                self.env_experiments[attack_type] = {}

        print(f"🚀 STARTING EXPERIMENTS: {self.attack_type.upper()}")

        # Attack category identification
        category_map = {
            'none': 'Baseline (No Attacks)',
            'stochastic': 'Stochastic (Natural Random Failures)', 
            'random': 'Stochastic (Natural Random Failures)',
            'markov': 'Adversarial (Structured Strategic)',
            'adaptive': 'Adversarial (Reactive Strategic)',
            'onlineadaptive': 'Adversarial (Online Adaptive Strategic)'
        }

        attack_category = category_map.get(self.attack_type, 'Unknown')
        print(f"🏷️  Category: {attack_category}")
        print("="*60)

        self.start_time = time.time()

        for i in range(num_experiments):
            current_frames = self.base_frames + (i * self.frame_step)
            exp_id = i + 1

            print(f"📈 EXPERIMENT {exp_id}: {current_frames} frames")
            print("-" * 40)

            # Create runner for this experiment
            runner = ExperimentRunner(
                base_seed=self.base_seed + i * 1000,
                attack_type=self.attack_type,
                attack_intensity=self.attack_intensity,
                enable_progress=self.enable_progress
            )

            # Run experiment
            try:
                experiment_results = runner.run_experiment(frame_count=current_frames)
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

                print(f"✅ Experiment {exp_id} completed successfully")

            except Exception as e:
                print(f"❌ Experiment {exp_id} failed: {e}")
                continue

        self.total_time = time.time() - self.start_time
        print(f"⏱️  Total experiment time: {self.total_time:.1f}s")
        print(f"🎯 Experiments completed for {self.attack_type}")

        return self.env_experiments[self.attack_type]

    def run_stochastic_vs_adversarial_comparison(self):
        """
        Run direct Stochastic vs Adversarial comparison.

        This method provides a clear comparison between:
        - Stochastic: Natural random failures (random/probabilistic attacks)
        - Adversarial: Strategic intelligent attacks (adaptive attacks)
        """

        print(f"" + "="*70)
        print("🎯 STOCHASTIC vs ADVERSARIAL COMPARISON")
        print("="*70)
        print("📊 Testing algorithm robustness against:")
        print("   🎲 Stochastic: Natural random failures/noise")
        print("   🧠 Adversarial: Strategic intelligent attacks")
        print("="*70)

        # Define the two key scenarios
        test_scenarios = {
            'stochastic': 'Stochastic (Natural Random Failures)',
            'adaptive': 'Adversarial (Strategic Reactive Attacks)'
        }

        # Run experiments for both scenarios
        comparison_results = {}

        for attack_type, description in test_scenarios.items():
            print(f"🔬 TESTING: {description}")
            print("="*50)

            # Store original attack type
            original_attack_type = self.attack_type

            # Run experiments for this attack type
            self.attack_type = attack_type
            if attack_type not in self.env_experiments:
                self.env_experiments[attack_type] = {}

            experiment_results = self.run_experiments(attack_type=attack_type, num_experiments=3)
            comparison_results[attack_type] = experiment_results

            # Restore original attack type
            self.attack_type = original_attack_type

        # Analysis and comparison
        print(f"" + "="*70)
        print("📊 STOCHASTIC vs ADVERSARIAL ANALYSIS")
        print("="*70)

        for attack_type, description in test_scenarios.items():
            print(f"🏷️  {description.upper()}:")

            # Get results for highest frame count (most comprehensive)
            highest_exp = max(comparison_results[attack_type].keys())
            exp_data = comparison_results[attack_type][highest_exp]

            oracle_reward = exp_data['oracle_reward']
            winner = exp_data['winner']
            winner_gap = exp_data['gaps'].get(winner, float('inf'))
            winner_reward = exp_data['results'][winner]['final_reward']

            print(f"   🏆 Best Algorithm: {winner}")
            print(f"   📈 Oracle Efficiency: {(winner_reward/oracle_reward*100):.1f}%")
            print(f"   📊 Oracle Gap: {winner_gap:.1f}%")

            # Show all algorithm performance
            print(f"   📋 All Algorithms:")
            for alg_name in ['EXPNeuralUCB', 'GNeuralUCB', 'EXPUCB']:
                if alg_name in exp_data['results']:
                    alg_reward = exp_data['results'][alg_name]['final_reward']
                    alg_gap = exp_data['gaps'].get(alg_name, float('inf'))
                    efficiency = (alg_reward / oracle_reward * 100) if oracle_reward > 0 else 0
                    print(f"      • {alg_name}: {efficiency:.1f}% efficiency ({alg_gap:.1f}% gap)")

        print(f"" + "="*70)
        print("🎯 KEY INSIGHTS:")

        # Compare EXPNeuralUCB performance in both scenarios
        stochastic_exp = max(comparison_results['stochastic'].keys())
        adversarial_exp = max(comparison_results['adaptive'].keys())

        stochastic_data = comparison_results['stochastic'][stochastic_exp]
        adversarial_data = comparison_results['adaptive'][adversarial_exp]

        exp_stochastic = stochastic_data['results']['EXPNeuralUCB']['final_reward']
        exp_adversarial = adversarial_data['results']['EXPNeuralUCB']['final_reward']

        robustness_loss = ((exp_stochastic - exp_adversarial) / exp_stochastic * 100) if exp_stochastic > 0 else 0

        print(f"📊 EXPNeuralUCB Robustness Analysis:")
        print(f"   • Stochastic Performance: {exp_stochastic:.2f}")
        print(f"   • Adversarial Performance: {exp_adversarial:.2f}")
        print(f"   • Robustness Loss: {robustness_loss:.1f}%")

        if robustness_loss < 5:
            print(f"   ✅ HIGHLY ROBUST: Minimal performance degradation under adversarial attacks")
        elif robustness_loss < 15:
            print(f"   ⚠️  MODERATELY ROBUST: Some performance loss under adversarial attacks")
        else:
            print(f"   ❌ LOW ROBUSTNESS: Significant performance degradation under adversarial attacks")

        print("="*70)

        return comparison_results

    def print_summary(self, attack_type=None):
        """Print comprehensive results summary."""
        if attack_type:
            target_type = attack_type
        else:
            target_type = self.attack_type

        if target_type not in self.env_experiments:
            print(f"❌ No results found for attack_type='{target_type}'")
            return

        experiments = self.env_experiments[target_type]

        print(f"" + "="*60)
        print(f"📊 COMPREHENSIVE SUMMARY: {target_type.upper()}")
        print("="*60)

        # Get all algorithms from first experiment
        first_exp = next(iter(experiments.values()))
        algorithms = [alg for alg in first_exp['results'].keys() if alg != 'Oracle']

        for alg in algorithms:
            rewards = [exp['results'][alg]['final_reward'] for exp in experiments.values()]
            gaps = [exp['gaps'][alg] for exp in experiments.values()]

            print(f"🤖 {alg}:")
            print(f"   📈 Rewards: {np.mean(rewards):.1f} ± {np.std(rewards):.1f}")
            print(f"   📊 Avg Gap: {np.mean(gaps):.1f}%")
            print(f"   🏆 Wins: {sum(1 for exp in experiments.values() if exp['winner'] == alg)}/{len(experiments)}")

        # Oracle efficiency analysis
        oracle_rewards = [exp['oracle_reward'] for exp in experiments.values()]
        print(f"🎯 Oracle Performance: {np.mean(oracle_rewards):.1f} ± {np.std(oracle_rewards):.1f}")

        # Best performing algorithm
        winner_counts = {}
        for exp in experiments.values():
            winner = exp['winner']
            winner_counts[winner] = winner_counts.get(winner, 0) + 1

        best_algorithm = max(winner_counts, key=winner_counts.get)
        print(f"🏆 Best Overall Algorithm: {best_algorithm} ({winner_counts[best_algorithm]}/{len(experiments)} wins)")

# Usage functions
def test_stochastic_vs_adversarial():
    """
    Main function to test Stochastic vs Adversarial scenarios.

    This provides the clearest comparison for research purposes.
    """
    evaluator = MultiRunEvaluator(
        base_seed=12345,
        base_frames=4000,
        frame_step=2000,
        attack_intensity=1.0,
        enable_progress=True
    )

    # Run the comparison
    results = evaluator.run_stochastic_vs_adversarial_comparison()

    return evaluator, results

def test_individual_environment(attack_type="adaptive"):
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
#     print("🎯 Running Stochastic vs Adversarial Comparison...")
#     evaluator, comparison_results = test_stochastic_vs_adversarial()