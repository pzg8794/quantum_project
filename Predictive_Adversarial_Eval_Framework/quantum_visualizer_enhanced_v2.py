
# quantum_visualizer_enhanced_v2.py

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from quantum_framework_updated import MultiRunEvaluator, test_stochastic_vs_adversarial, test_individual_environment

class EnhancedQuantumVisualizer:
    """
    Advanced Quantum Algorithm Visualization with Clear Stochastic vs Adversarial Analysis

    Features:
    - Clear distinction between Stochastic (natural failures) and Adversarial (strategic attacks)
    - Dedicated Stochastic vs Adversarial comparison plots
    - Enhanced robustness analysis
    - Comprehensive cross-environment evaluation
    """

    def __init__(self):
        self.evaluators = {}  # {attack_type: evaluator_instance}
        self.comparison_results = {}  # For stochastic vs adversarial results
        self._setup_style()

    def _setup_style(self):
        plt.style.use('seaborn-v0_8')

        # Algorithm colors
        self.colors = {
            'Oracle': '#2c3e50',
            'EXPNeuralUCB': '#e74c3c',
            'GNeuralUCB': '#3498db', 
            'EXPUCB': '#2ecc71'
        }

        # Enhanced environment/attack type colors with clear categorization
        self.env_colors = {
            # Baseline
            'none': '#95a5a6',

            # Stochastic (blues/greens for natural)
            'stochastic': '#3498db',
            'random': '#5dade2',

            # Adversarial (reds/oranges for strategic)
            'markov': '#9b59b6',
            'adaptive': '#e67e22', 
            'onlineadaptive': '#c0392b'
        }

        # Category colors for clear distinction
        self.category_colors = {
            'Baseline': '#95a5a6',
            'Stochastic': '#3498db',
            'Adversarial': '#e74c3c'
        }

    def run_test(self, attack_type="adaptive"):
        """Run test for individual attack type."""
        print(f"🔬 Running test for {attack_type} environment...")
        evaluator = test_individual_environment(attack_type=attack_type)
        self.evaluators[attack_type] = evaluator
        return evaluator

    def run_stochastic_vs_adversarial_test(self, runs=1, base_frames=4000, frame_step=2000, models=["EXPNeuralUCB", 'GNeuralUCB', 'EXPUCB', 'Oracle'], selected_model="EXPNeuralUCB", test_scenarios={'stochastic': 'Stochastic (Natural Random Failures)', 'adaptive': 'Adversarial (Strategic Reactive Attacks)'}):
        """
        Run the main Stochastic vs Adversarial comparison test.

        This is the key test for demonstrating algorithm robustness.
        """
        print(f"🎯 Running Stochastic vs Adversarial Comparison Test...")
        evaluator, comparison_results = test_stochastic_vs_adversarial(runs=runs, base_frames=base_frames, frame_step=frame_step, models=models, selected_model=selected_model, test_scenarios=test_scenarios)

        # Store results
        self.evaluators['stochastic_vs_adversarial'] = evaluator
        self.comparison_results = comparison_results

        return evaluator, comparison_results

    def plot_stochastic_vs_adversarial_comparison(self):
        """
        Create comprehensive Stochastic vs Adversarial comparison plots.

        This is the primary visualization for research presentations.
        """
        if not self.comparison_results:
            print("❌ No comparison results found. Run run_stochastic_vs_adversarial_test() first.")
            return

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(
            'STOCHASTIC vs ADVERSARIAL ROBUSTNESS ANALYSIS\n'
            'Natural Random Failures vs Strategic Intelligent Attacks',
            fontsize=16, fontweight='bold'
        )

        # Extract data for highest frame count from both scenarios
        scenarios = ['stochastic', 'adaptive']
        scenario_labels = {
            'stochastic': 'Stochastic\n(Natural Failures)',
            'adaptive': 'Adversarial\n(Strategic Attacks)'
        }

        scenario_data = {}
        for scenario in scenarios:
            if scenario in self.comparison_results:
                # Get highest frame count experiment
                highest_exp = max(self.comparison_results[scenario].keys())
                scenario_data[scenario] = self.comparison_results[scenario][highest_exp]

        if not scenario_data:
            print("❌ No valid comparison data found.")
            return

        # 1. Algorithm Performance Comparison
        algorithms = ['EXPNeuralUCB', 'GNeuralUCB', 'EXPUCB']
        scenario_names = list(scenario_data.keys())

        # Performance bar chart
        bar_width = 0.25
        x_pos = np.arange(len(algorithms))

        for i, scenario in enumerate(scenario_names):
            if scenario not in scenario_data:
                continue

            data = scenario_data[scenario]
            oracle_reward = data['oracle_reward']

            efficiencies = []
            for alg in algorithms:
                if alg in data['results']:
                    alg_reward = data['results'][alg]['final_reward']
                    efficiency = (alg_reward / oracle_reward * 100) if oracle_reward > 0 else 0
                    efficiencies.append(efficiency)
                else:
                    efficiencies.append(0)

            color = self.category_colors['Stochastic'] if scenario == 'stochastic' else self.category_colors['Adversarial']
            axes[0,0].bar(x_pos + i*bar_width, efficiencies, bar_width, 
                         label=scenario_labels[scenario], color=color, alpha=0.8)

        axes[0,0].set_xlabel('Algorithm')
        axes[0,0].set_ylabel('Oracle Efficiency (%)')
        axes[0,0].set_title('Algorithm Performance Comparison')
        axes[0,0].set_xticks(x_pos + bar_width/2)
        axes[0,0].set_xticklabels(algorithms, rotation=45)
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)

        # 2. Robustness Loss Analysis
        robustness_data = []
        for alg in algorithms:
            if alg in scenario_data['stochastic']['results'] and alg in scenario_data['adaptive']['results']:
                stoch_reward = scenario_data['stochastic']['results'][alg]['final_reward']
                adv_reward = scenario_data['adaptive']['results'][alg]['final_reward']

                if stoch_reward > 0:
                    robustness_loss = ((stoch_reward - adv_reward) / stoch_reward * 100)
                    robustness_data.append(max(0, robustness_loss))  # Ensure non-negative
                else:
                    robustness_data.append(0)

        if robustness_data:
            colors = [self.colors[alg] for alg in algorithms]
            bars = axes[0,1].bar(algorithms, robustness_data, color=colors, alpha=0.7)
            axes[0,1].set_xlabel('Algorithm')
            axes[0,1].set_ylabel('Performance Loss (%)')
            axes[0,1].set_title('Robustness Loss Under Adversarial Attacks\n(Lower = More Robust)')
            axes[0,1].tick_params(axis='x', rotation=45)
            axes[0,1].grid(True, alpha=0.3)

            # Add value labels on bars
            for bar, value in zip(bars, robustness_data):
                height = bar.get_height()
                axes[0,1].text(bar.get_x() + bar.get_width()/2., height + 0.5,
                              f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')

        # 3. Oracle Gap Comparison
        gap_comparison = []
        for scenario in scenario_names:
            if scenario not in scenario_data:
                continue
            gaps = []
            for alg in algorithms:
                if alg in scenario_data[scenario]['gaps']:
                    gaps.append(scenario_data[scenario]['gaps'][alg])
                else:
                    gaps.append(float('inf'))
            gap_comparison.append(gaps)

        if gap_comparison:
            x_pos = np.arange(len(algorithms))
            for i, (scenario, gaps) in enumerate(zip(scenario_names, gap_comparison)):
                color = self.category_colors['Stochastic'] if scenario == 'stochastic' else self.category_colors['Adversarial']
                axes[1,0].bar(x_pos + i*bar_width, gaps, bar_width, 
                             label=scenario_labels[scenario], color=color, alpha=0.8)

        axes[1,0].set_xlabel('Algorithm')
        axes[1,0].set_ylabel('Oracle Gap (%)')
        axes[1,0].set_title('Oracle Gap Comparison\n(Lower = Better)')
        axes[1,0].set_xticks(x_pos + bar_width/2)
        axes[1,0].set_xticklabels(algorithms, rotation=45)
        axes[1,0].legend()
        axes[1,0].grid(True, alpha=0.3)
        axes[1,0].invert_yaxis()  # Lower is better

        # 4. Winner Analysis
        winner_data = {}
        for scenario in scenario_names:
            if scenario in scenario_data:
                winner = scenario_data[scenario]['winner']
                winner_data[scenario_labels[scenario]] = winner

        if winner_data:
            scenarios_list = list(winner_data.keys())
            winners = list(winner_data.values())

            # Count algorithm wins
            algorithm_wins = {}
            for winner in winners:
                algorithm_wins[winner] = algorithm_wins.get(winner, 0) + 1

            # Create pie chart of winners
            if algorithm_wins:
                colors_pie = [self.colors.get(alg, 'gray') for alg in algorithm_wins.keys()]
                axes[1,1].pie(algorithm_wins.values(), labels=algorithm_wins.keys(), 
                             autopct='%1.0f%%', colors=colors_pie, startangle=90)
                axes[1,1].set_title('Algorithm Dominance\nAcross Scenarios')

        plt.tight_layout()
        plt.savefig('stochastic_vs_adversarial_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()

        # Print numerical summary
        print("\n" + "="*70)
        print("📊 NUMERICAL SUMMARY:")
        print("="*70)

        for scenario in scenario_names:
            if scenario in scenario_data:
                data = scenario_data[scenario]
                oracle_reward = data['oracle_reward']
                winner = data['winner']

                print(f"\n🏷️  {scenario_labels[scenario].upper()}:")
                print(f"   🏆 Winner: {winner}")

                for alg in algorithms:
                    if alg in data['results']:
                        alg_reward = data['results'][alg]['final_reward']
                        efficiency = (alg_reward / oracle_reward * 100) if oracle_reward > 0 else 0
                        gap = data['gaps'].get(alg, float('inf'))
                        print(f"   • {alg}: {efficiency:.1f}% efficiency, {gap:.1f}% gap")

    def plot_all_environments_comparison(self, attack_types):
        """Compare multiple environment types including stochastic vs adversarial."""
        # Ensure we have results for all requested attack types
        missing = [env for env in attack_types if env not in self.evaluators]
        if missing:
            print(f"❌ Missing environments: {missing}")
            print("Run tests for these environments first.")
            return

        # Create comprehensive dashboard
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(
            'COMPREHENSIVE ENVIRONMENT COMPARISON\n'
            'Baseline | Stochastic (Natural) | Adversarial (Strategic)', 
            fontsize=16, fontweight='bold'
        )

        # Collect all data with clear categorization
        all_data = []
        category_map = {
            'none': 'Baseline',
            'stochastic': 'Stochastic', 
            'random': 'Stochastic',
            'markov': 'Adversarial',
            'adaptive': 'Adversarial',
            'onlineadaptive': 'Adversarial'
        }

        for attack_type in attack_types:
            if attack_type not in self.evaluators:
                continue

            evaluator = self.evaluators[attack_type]
            if attack_type not in evaluator.env_experiments:
                continue

            experiments = evaluator.env_experiments[attack_type]

            # Get highest frame count experiment
            highest_exp = max(experiments.keys()) if experiments else 1
            exp_data = experiments.get(highest_exp, {})

            if 'results' not in exp_data:
                continue

            category = category_map.get(attack_type, 'Unknown')
            oracle_reward = exp_data.get('oracle_reward', 1)

            for alg_name in ['EXPNeuralUCB', 'GNeuralUCB', 'EXPUCB']:
                if alg_name in exp_data['results']:
                    alg_reward = exp_data['results'][alg_name]['final_reward']
                    gap = exp_data['gaps'].get(alg_name, float('inf'))
                    efficiency = (alg_reward / oracle_reward * 100) if oracle_reward > 0 else 0

                    all_data.append({
                        'environment': attack_type,
                        'category': category,
                        'algorithm': alg_name,
                        'final_reward': alg_reward,
                        'gap_percent': gap,
                        'efficiency': efficiency
                    })

        if not all_data:
            print("❌ No data available for plotting.")
            return

        df = pd.DataFrame(all_data)

        # 1. Efficiency by Category
        if not df.empty:
            category_order = ['Baseline', 'Stochastic', 'Adversarial']
            available_categories = [cat for cat in category_order if cat in df['category'].unique()]

            sns.boxplot(data=df, x='category', y='efficiency', hue='algorithm', 
                       order=available_categories, ax=axes[0,0])
            axes[0,0].set_title('Algorithm Efficiency by Environment Category')
            axes[0,0].set_ylabel('Oracle Efficiency (%)')
            axes[0,0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # 2. Gap Comparison Heatmap
        pivot_gap = df.pivot_table(index='environment', columns='algorithm', 
                                  values='gap_percent', aggfunc='mean')
        if not pivot_gap.empty:
            sns.heatmap(pivot_gap, annot=True, fmt='.1f', cmap='RdYlGn_r',
                       ax=axes[0,1], cbar_kws={'label': 'Oracle Gap % (Lower=Better)'})
            axes[0,1].set_title('Oracle Gap Heatmap')

        # 3. Algorithm Ranking
        avg_efficiency = df.groupby('algorithm')['efficiency'].mean().sort_values(ascending=False)
        colors = [self.colors.get(alg, 'gray') for alg in avg_efficiency.index]
        axes[0,2].bar(range(len(avg_efficiency)), avg_efficiency.values, color=colors)
        axes[0,2].set_xticks(range(len(avg_efficiency)))
        axes[0,2].set_xticklabels(avg_efficiency.index, rotation=45)
        axes[0,2].set_title('Overall Algorithm Ranking')
        axes[0,2].set_ylabel('Average Efficiency (%)')

        # 4. Category Performance
        category_performance = df.groupby('category')['efficiency'].mean().sort_values()
        category_colors = [self.category_colors.get(cat, 'gray') for cat in category_performance.index]
        axes[1,0].bar(range(len(category_performance)), category_performance.values, 
                     color=category_colors, alpha=0.7)
        axes[1,0].set_xticks(range(len(category_performance)))
        axes[1,0].set_xticklabels(category_performance.index, rotation=45)
        axes[1,0].set_title('Environment Category Difficulty\n(Lower = More Challenging)')
        axes[1,0].set_ylabel('Average Algorithm Efficiency (%)')

        # 5. Robustness Matrix (comparison between categories)
        if 'Stochastic' in df['category'].unique() and 'Adversarial' in df['category'].unique():
            robustness_data = []
            for alg in df['algorithm'].unique():
                stoch_data = df[(df['category'] == 'Stochastic') & (df['algorithm'] == alg)]
                adv_data = df[(df['category'] == 'Adversarial') & (df['algorithm'] == alg)]

                if not stoch_data.empty and not adv_data.empty:
                    stoch_eff = stoch_data['efficiency'].mean()
                    adv_eff = adv_data['efficiency'].mean()
                    robustness_loss = ((stoch_eff - adv_eff) / stoch_eff * 100) if stoch_eff > 0 else 0
                    robustness_data.append({'algorithm': alg, 'robustness_loss': max(0, robustness_loss)})

            if robustness_data:
                robust_df = pd.DataFrame(robustness_data)
                colors = [self.colors.get(alg, 'gray') for alg in robust_df['algorithm']]
                bars = axes[1,1].bar(robust_df['algorithm'], robust_df['robustness_loss'], 
                                    color=colors, alpha=0.7)
                axes[1,1].set_title('Robustness Loss: Stochastic → Adversarial\n(Lower = More Robust)')
                axes[1,1].set_ylabel('Performance Loss (%)')
                axes[1,1].tick_params(axis='x', rotation=45)
                axes[1,1].grid(True, alpha=0.3)

                # Add value labels
                for bar, row in zip(bars, robustness_data):
                    height = bar.get_height()
                    axes[1,1].text(bar.get_x() + bar.get_width()/2., height + 0.5,
                                  f'{row["robustness_loss"]:.1f}%', 
                                  ha='center', va='bottom', fontweight='bold')

        # 6. Environment Difficulty Ranking
        env_difficulty = df.groupby('environment')['gap_percent'].mean().sort_values()
        colors = [self.env_colors.get(env, 'gray') for env in env_difficulty.index]
        axes[1,2].bar(range(len(env_difficulty)), env_difficulty.values, color=colors, alpha=0.8)
        axes[1,2].set_xticks(range(len(env_difficulty)))
        axes[1,2].set_xticklabels(env_difficulty.index, rotation=45)
        axes[1,2].set_title('Environment Difficulty Ranking\n(Higher = More Difficult)')
        axes[1,2].set_ylabel('Average Oracle Gap (%)')

        plt.tight_layout()
        plt.savefig('comprehensive_environment_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()


# Test functions
def test_stochastic_vs_adversarial_visualization():
    """
    Main test function for Stochastic vs Adversarial comparison.

    This is the primary function for research demonstrations.
    """
    viz = EnhancedQuantumVisualizer()

    # Run the comparison test
    evaluator, comparison_results = viz.run_stochastic_vs_adversarial_test()

    # Create the comparison visualization
    viz.plot_stochastic_vs_adversarial_comparison()

    return viz, evaluator, comparison_results

def test_comprehensive_environments():
    """Test all environment types including the new categorization."""
    viz = EnhancedQuantumVisualizer()

    # Test environments across all categories
    environments = ["none", "stochastic", "adaptive", "markov"]

    for env in environments:
        print(f"\n{'='*50}\nTESTING {env.upper()}\n{'='*50}")
        viz.run_test(env)

    # Create comprehensive comparison
    viz.plot_all_environments_comparison(environments)

    return viz

# if __name__ == "__main__":
#     print("🎯 RUNNING STOCHASTIC vs ADVERSARIAL VISUALIZATION TEST")
#     viz, evaluator, results = test_stochastic_vs_adversarial_visualization()
