# quantum_mab_models_visualizer.py

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from quantum_framework_updated import MultiRunEvaluator, test_stochastic_environment, test_individual_environment

class QuantumEvaluatorVisualizer:
    """
    Quantum MAB Models Evaluation Framework - Advanced Visualization Engine
    
    Features:
    - Stochastic-focused evaluation with comparative analysis
    - Comprehensive multi-model performance visualization
    - Statistical significance testing and ranking
    - Publication-quality research visualizations
    - Configurable evaluation scenarios
    """

    def __init__(self, framework_config=None):
        self.framework_config = framework_config or {}
        self.evaluators = {}  
        self.evaluation_results = {}  
        self.model_rankings = {}
        self._setup_framework_style()

    def _setup_framework_style(self):
        plt.style.use('seaborn-v0_8')

        # Comprehensive model color palette (expandable)
        self.model_colors = {
            # Neural Bandit Models
            'Oracle': '#2c3e50',
            'CEXPNeuralUCB': '#e74c3c', 
            'EXPNeuralUCB': '#c0392b',
            'GNeuralUCB': '#3498db',
            # 'NeuralUCB': '#2980b9',
            
            # Traditional Models
            'UCB': '#27ae60',
            'LinUCB': '#2ecc71',
            'ThompsonSampling': '#16a085',
            'EpsilonGreedy': '#1abc9c',
            
            # Advanced Models  
            'EXPUCB': '#9b59b6',
            'KernelUCB': '#8e44ad',
            
            # Contextual Models
            'CMAB': '#f39c12',
            'iCMAB': '#e67e22'
        }

        # Environment categorization (framework-aligned)
        self.env_colors = {
            # Baseline
            'none': '#95a5a6',
            
            # Stochastic (natural failures) - Blues/Greens
            'stochastic': '#3498db',
            'random': '#5dade2',
            
            # Adversarial (strategic attacks) - Reds/Oranges
            'markov': '#9b59b6',
            'adaptive': '#e67e22', 
            'onlineadaptive': '#c0392b'
        }

        # Framework evaluation categories
        self.category_colors = {
            'Baseline': '#95a5a6',
            'Stochastic': '#3498db', 
            'Adversarial': '#e74c3c',
            'Comprehensive': '#8e44ad'
        }

    def run_comprehensive_model_evaluation(self, primary_environment='stochastic', 
                                         test_models=None, statistical_validation=True):
        """
        Run comprehensive evaluation of all available models in framework.
        
        Primary method for Quantum MAB Models Evaluation Framework.
        """
        if test_models is None:
            test_models = self.framework_config.get('models', [])
        
        print(f"Executing Quantum MAB Models Evaluation Framework")
        print(f"Primary Environment: {primary_environment.upper()}")
        print(f"Models to evaluate: {len(test_models) if isinstance(test_models, list) else sum(len(models) for models in test_models.values())}")
        
        # Execute primary evaluation
        evaluator, results = self._run_framework_evaluation(
            primary_environment, [model for model in test_models.values()], statistical_validation
        )
        
        # Store results for analysis
        self.evaluators[f'framework_{primary_environment}'] = evaluator
        self.evaluation_results = results
        
        return results

    def _run_framework_evaluation(self, environment, models, statistical_validation):
        """Internal framework evaluation execution."""
        # Use framework configuration parameters
        config = self.framework_config
        
        test_scenarios = {environment: f"{environment.title()} Environment"}
        if environment == 'stochastic':
            # Add baseline comparison for stochastic focus
            test_scenarios['none'] = 'Baseline (Optimal Conditions)'
            
        return test_stochastic_environment(
            runs=config.get('exp_num', 1),
            base_frames=config.get('base_frames', 100), 
            frame_step=config.get('frame_step', 200),
            models=models,
            selected_model=config.get('main_model', 'CEXPNeuralUCB'),
            test_scenarios=test_scenarios
        )

    def run_stochastic_test(self, runs=1, base_frames=100, frame_step=200, models=None, selected_model="CEXPNeuralUCB", test_scenarios=None, attack_type='stochastic'):
        """
        Legacy compatibility method for existing code.
        Maintained for backward compatibility while transitioning to framework.
        """
        if models is None: models = ["CEXPNeuralUCB", 'EXPNeuralUCB', 'GNeuralUCB', 'EXPUCB', 'Oracle']
        if test_scenarios is None:
            test_scenarios = {'stochastic': 'Stochastic (Natural Network Failures)', 'adaptive': 'Adversarial (Strategic Attacks)'}
        
        print("Running Quantum MAB Models Evaluation...")
        evaluator, results = test_stochastic_environment(
            runs=runs, base_frames=base_frames, frame_step=frame_step, 
            models=models, attack_type=attack_type, 
            test_scenarios=test_scenarios
        )

        # Store results
        self.evaluators['stochastic_vs_adversarial'] = evaluator
        self.evaluation_results = results
        return evaluator, results

    def create_stochastic_evaluation_plots(self):
        """Create comprehensive stochastic-focused evaluation visualizations."""
        if not self.evaluation_results:
            print("No evaluation results found. Run evaluation first.")
            return

        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(
            'QUANTUM MAB MODELS EVALUATION FRAMEWORK\n'
            'Stochastic Environment Performance Analysis',
            fontsize=16, fontweight='bold'
        )

        # Extract BOTH averaged and peak results
        stochastic_data = self._extract_primary_results('stochastic')
        if not stochastic_data:
            print("No stochastic evaluation data available.")
            return

        # Use averaged data for most plots
        avg_data = stochastic_data['averaged']
        
        # 1. Model Performance Ranking (averaged)
        self._plot_model_performance_ranking(axes[0,0], avg_data)
        
        # 2. Averaged vs Peak Efficiency Comparison (NEW!)
        self._plot_efficiency_comparison(axes[0,1], stochastic_data)
        
        # 3. Model Category Comparison (averaged)
        self._plot_model_categories(axes[0,2], avg_data)
        
        # 4. Performance Distribution (averaged)
        self._plot_performance_distribution(axes[1,0], avg_data)
        
        # 5. Gap Analysis (averaged)
        self._plot_gap_analysis(axes[1,1], avg_data) 
        
        # 6. Framework Summary (averaged + peak info)
        self._plot_framework_summary(axes[1,2], stochastic_data)

        plt.tight_layout()
        plt.savefig('quantum_mab_models_stochastic_evaluation.png', dpi=300, bbox_inches='tight')
        plt.show()

        # Generate numerical summary
        self._print_framework_summary(avg_data)


    def _extract_primary_results(self, environment):
        """
        Extract BOTH averaged AND peak results for comprehensive analysis.
        Handles 'stochastic', 'none', and other environment keys.
        """
        if environment not in self.evaluation_results:
            # Fallback: if 'stochastic' not found, try 'none' (baseline)
            if environment == 'stochastic' and 'none' in self.evaluation_results:
                environment = 'none'
            else:
                return None
        
        env_results = self.evaluation_results[environment]
        if not env_results:
            return None
        
        # [REST OF THE METHOD STAYS THE SAME]
        # 1. GET PEAK (HIGHEST FRAME COUNT) EXPERIMENT
        highest_exp = max(env_results.keys())
        peak_data = env_results[highest_exp]
        peak_frames = peak_data.get('frame_count', highest_exp)
        
        # 2. CALCULATE AVERAGED DATA
        num_experiments = len(env_results)
        algorithm_totals = {}
        total_oracle = 0
        
        for exp_id, exp_data in env_results.items():
            total_oracle += exp_data['oracle_reward']
            
            for alg, alg_result in exp_data['results'].items():
                if alg not in algorithm_totals:
                    algorithm_totals[alg] = {
                        'total_reward': 0,
                        'total_gap': 0,
                        'count': 0
                    }
                
                algorithm_totals[alg]['total_reward'] += alg_result['final_reward']
                algorithm_totals[alg]['total_gap'] += alg_result.get('gap', 0)
                algorithm_totals[alg]['count'] += 1
        
        # Build averaged result structure
        avg_oracle = total_oracle / num_experiments
        averaged_results = {}
        
        for alg, stats in algorithm_totals.items():
            averaged_results[alg] = {
                'final_reward': stats['total_reward'] / stats['count'],
                'gap': stats['total_gap'] / stats['count']
            }
        
        return {
            'averaged': {
                'oracle_reward': avg_oracle,
                'results': averaged_results,
                'winner': max(averaged_results, key=lambda x: averaged_results[x]['final_reward'])
            },
            'peak': peak_data,
            'peak_frames': peak_frames
        }



    def _plot_model_performance_ranking(self, ax, data):
        """Plot comprehensive model performance ranking."""
        oracle_reward = data['oracle_reward']
        model_efficiencies = []
        model_names = []
        
        for model, result in data['results'].items():
            if model != 'Oracle':  # Exclude oracle from ranking
                efficiency = (result['final_reward'] / oracle_reward * 100) if oracle_reward > 0 else 0
                model_efficiencies.append(efficiency)
                model_names.append(model)
        
        # Sort by efficiency
        sorted_data = sorted(zip(model_names, model_efficiencies), key=lambda x: x[1], reverse=True)
        sorted_names, sorted_efficiencies = zip(*sorted_data) if sorted_data else ([], [])
        
        colors = [self.model_colors.get(model, 'gray') for model in sorted_names]
        bars = ax.bar(range(len(sorted_names)), sorted_efficiencies, color=colors, alpha=0.8)
        
        ax.set_xlabel('Models (Ranked by Performance)')
        ax.set_ylabel('Oracle Efficiency (%)')
        ax.set_title('Model Performance Ranking\nStochastic Environment')
        ax.set_xticks(range(len(sorted_names)))
        ax.set_xticklabels(sorted_names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3)
        
        # Add efficiency labels
        for bar, efficiency in zip(bars, sorted_efficiencies):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                   f'{efficiency:.1f}%', ha='center', va='bottom', fontweight='bold')

    def _plot_oracle_efficiency(self, ax, data):
        """Plot oracle efficiency comparison."""
        oracle_reward = data['oracle_reward']
        
        # Calculate efficiencies for all models
        efficiencies = []
        model_names = []
        
        for model, result in data['results'].items():
            efficiency = (result['final_reward'] / oracle_reward * 100) if oracle_reward > 0 else 0
            efficiencies.append(efficiency)
            model_names.append(model)
        
        colors = [self.model_colors.get(model, 'gray') for model in model_names]
        ax.scatter(range(len(model_names)), efficiencies, c=colors, s=100, alpha=0.7)
        
        ax.axhline(y=100, color='red', linestyle='--', alpha=0.5, label='Oracle Baseline')
        ax.set_xlabel('Models')
        ax.set_ylabel('Oracle Efficiency (%)')
        ax.set_title('Oracle Efficiency Comparison')
        ax.set_xticks(range(len(model_names)))
        ax.set_xticklabels(model_names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_model_categories(self, ax, data):
        """Plot performance by model category."""
        # Categorize models
        categories = {
            'Neural Bandits': ['CEXPNeuralUCB', 'EXPNeuralUCB', 'GNeuralUCB', 'NeuralUCB'],
            'Traditional': ['UCB', 'LinUCB', 'ThompsonSampling', 'EpsilonGreedy'],
            'Advanced': ['EXPUCB', 'KernelUCB'],
            'Contextual': ['CMAB', 'iCMAB']
        }
        
        category_performance = {}
        oracle_reward = data['oracle_reward']
        
        for category, models in categories.items():
            category_efficiencies = []
            for model in models:
                if model in data['results']:
                    efficiency = (data['results'][model]['final_reward'] / oracle_reward * 100) if oracle_reward > 0 else 0
                    category_efficiencies.append(efficiency)
            
            if category_efficiencies:
                category_performance[category] = np.mean(category_efficiencies)
        
        if category_performance:
            categories = list(category_performance.keys())
            performances = list(category_performance.values())
            
            ax.bar(categories, performances, color=['#e74c3c', '#27ae60', '#9b59b6', '#f39c12'], alpha=0.7)
            ax.set_ylabel('Average Oracle Efficiency (%)')
            ax.set_title('Performance by Model Category')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3)

    def _plot_efficiency_comparison(self, ax, data):
        """
        Plot averaged vs peak efficiency comparison.
        Shows both overall performance and best-case achievement.
        """
        avg_data = data['averaged']
        peak_data = data['peak']
        peak_frames = data['peak_frames']
        
        models = list(avg_data['results'].keys())
        
        # Calculate efficiencies
        avg_efficiencies = []
        peak_efficiencies = []
        
        for model in models:
            # Averaged efficiency
            avg_eff = (avg_data['results'][model]['final_reward'] / 
                    avg_data['oracle_reward'] * 100) if avg_data['oracle_reward'] > 0 else 0
            avg_efficiencies.append(avg_eff)
            
            # Peak efficiency
            peak_eff = (peak_data['results'][model]['final_reward'] / 
                        peak_data['oracle_reward'] * 100) if peak_data['oracle_reward'] > 0 else 0
            peak_efficiencies.append(peak_eff)
        
        x = np.arange(len(models))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, avg_efficiencies, width, 
                    label='Averaged', alpha=0.85, color='#3498db')
        bars2 = ax.bar(x + width/2, peak_efficiencies, width, 
                    label=f'Peak ({peak_frames} frames)', alpha=0.85, color='#e74c3c')
        
        ax.set_title('Oracle Efficiency: Averaged vs Peak\n(Multi-Experiment Analysis)', 
                    fontweight='bold')
        ax.set_xlabel('Models')
        ax.set_ylabel('Oracle Efficiency (%)')
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)


    def _plot_performance_distribution(self, ax, data):
        """Plot performance distribution across models."""
        oracle_reward = data['oracle_reward']
        efficiencies = []
        
        for model, result in data['results'].items():
            if model != 'Oracle':
                efficiency = (result['final_reward'] / oracle_reward * 100) if oracle_reward > 0 else 0
                efficiencies.append(efficiency)
        
        if efficiencies:
            ax.hist(efficiencies, bins=10, alpha=0.7, color='#3498db', edgecolor='black')
            ax.axvline(np.mean(efficiencies), color='red', linestyle='--', label=f'Mean: {np.mean(efficiencies):.1f}%')
            ax.set_xlabel('Oracle Efficiency (%)')
            ax.set_ylabel('Number of Models')
            ax.set_title('Performance Distribution')
            ax.legend()
            ax.grid(True, alpha=0.3)

    def _plot_gap_analysis(self, ax, data):
        """Plot oracle gap analysis."""
        gaps = []
        model_names = []
        
        # for model, gap in data.get('gaps', {}).items():
        #     if model != 'Oracle':
        #         gaps.append(gap)
        #         model_names.append(model)
        
        for model, model_res in data['results'].items():
            if model != 'Oracle':
                gaps.append(model_res.get('gap', {}))
                model_names.append(model)

        if gaps and model_names:
            colors = [self.model_colors.get(model, 'gray') for model in model_names]
            ax.bar(model_names, gaps, color=colors, alpha=0.7)
            ax.set_ylabel('Oracle Gap (%)')
            ax.set_title('Oracle Gap Analysis\n(Lower = Better)')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3)

    def _plot_framework_summary(self, ax, data):
        """Plot framework evaluation summary."""
        # Handle new nested structure
        if 'averaged' in data:
            avg_data = data['averaged']
            winner = avg_data.get('winner', 'Unknown')
            oracle_reward = avg_data['oracle_reward']  # ← FIXED
            num_models = len(avg_data['results']) - 1
        else:
            # Fallback for old format
            winner = data.get('winner', 'Unknown')
            oracle_reward = data['oracle_reward']
            num_models = len(data['results']) - 1
        
        summary_data = {
            'Best Model': winner,
            'Oracle Reward': f"{oracle_reward:.3f}",
            'Total Models': str(num_models),
            'Environment': 'Stochastic'
        }
        
        ax.text(0.1, 0.8, 'FRAMEWORK SUMMARY', fontsize=14, fontweight='bold', transform=ax.transAxes)
        
        y_pos = 0.6
        for key, value in summary_data.items():
            ax.text(0.1, y_pos, f'{key}: {value}', fontsize=12, transform=ax.transAxes)
            y_pos -= 0.1
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')


    def _print_framework_summary(self, data):
        """Print comprehensive numerical summary."""
        print("\n" + "="*70)
        print("QUANTUM MAB MODELS EVALUATION FRAMEWORK - RESULTS SUMMARY")
        print("="*70)
        
        oracle_reward = data['oracle_reward']
        winner = data.get('winner', 'Unknown')
        
        print(f"Environment: STOCHASTIC")
        print(f"Best Performing Model: {winner}")
        print(f"Oracle Baseline: {oracle_reward:.3f}")
        print(f"Total Models Evaluated: {len(data['results']) - 1}")  # Exclude Oracle
        
        print(f"\nDETAILED MODEL PERFORMANCE:")
        print("-" * 50)
        
        # Sort models by performance
        model_performance = []
        for model, result in data['results'].items():
            if model != 'Oracle':
                efficiency = (result['final_reward'] / oracle_reward * 100) if oracle_reward > 0 else 0
                # gap = data['gaps'].get(model, float('inf'))
                gap = result.get('gap', float('inf'))
                model_performance.append((model, efficiency, gap, result['final_reward']))
        
        # Sort by efficiency (descending)
        model_performance.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (model, efficiency, gap, reward) in enumerate(model_performance, 1):
            print(f"{rank:2d}. {model:<15}: {efficiency:6.1f}% efficiency, {gap:6.1f}% gap, {reward:.3f} reward")


    def plot_stochastic_vs_adversarial_comparison(self):
        """
        Generate comprehensive robustness visualization - displays in notebook.
        This method displays plots directly in the notebook.
        """
        print("Creating stochastic vs adversarial comparison visualization...")

        # Guard: no results
        if not self.evaluation_results:
            print("No evaluation results found. Running basic framework display...")
            self._create_basic_comparison_plot()
            return

        # Figure layout
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(
            'Quantum MAB Models: Stochastic vs Adversarial Robustness Analysis',
            fontsize=16, fontweight='bold'
        )

        # Select the stochastic environment results (prefer 'stochastic', then 'random')
        stoch_data = None
        stoch_env_key = None
        for key in ('stochastic', 'random'):
            if key in self.evaluation_results:
                stoch_data = self.evaluation_results[key]
                stoch_env_key = key
                break

        # Select the adversarial environment results (prefer 'adaptive', then 'onlineadaptive', then 'markov')
        adversarial_data = None
        adv_env_key = None
        for key in ('adaptive', 'onlineadaptive', 'markov'):
            if key in self.evaluation_results:
                adversarial_data = self.evaluation_results[key]
                adv_env_key = key
                break

        # From each environment’s dict of experiments, pick a single experiment to compare
        # Heuristic: choose the experiment with the largest frame_count (safe fallback if nested)
        def _best_exp(exp_dict):
            # exp_dict expected: {exp_id: experiment_result_dict, ...}
            if not isinstance(exp_dict, dict) or not exp_dict:
                return None
            def exp_len(item):
                _, d = item
                if isinstance(d, dict):
                    # primary: top-level frame_count; fallback: results.frame_count
                    return d.get('frame_count', d.get('results', {}).get('frame_count', 0))
                return 0
            try:
                return max(exp_dict.items(), key=exp_len)[1]
            except ValueError:
                return None

        stoch_results = _best_exp(stoch_data) if stoch_data else None
        adv_results   = _best_exp(adversarial_data) if adversarial_data else None

        # Top row: stochastic-only panels (if available)
        if stoch_results:
            self._plot_model_performance_ranking(axes[0, 0], stoch_results)
            self._plot_oracle_efficiency(axes[0, 1], stoch_results)
            self._plot_reward_evolution(axes[0, 2], stoch_results)
            self._plot_statistical_analysis(axes[1, 0], stoch_results)
        else:
            for r, c, msg in [(0,0,'No stochastic results'), (0,1,'No stochastic results'),
                            (0,2,'No stochastic results'), (1,0,'No stochastic results')]:
                ax = axes[r, c]
                ax.text(0.5, 0.5, msg, ha='center', va='center', transform=ax.transAxes, fontsize=12)
                ax.set_axis_off()

        # Bottom row center: robustness comparison if both envs present; else single-env panel
        if stoch_results and adv_results:
            self._plot_robustness_comparison(axes[1, 1], stoch_results, adv_results)
            # Bottom row right: research summary (can use the full adversarial_data dict)
            self._plot_research_summary(axes[1, 2], stoch_results, adversarial_data)
        else:
            # Informative message on robustness panel when one side is missing
            ax = axes[1, 1]
            ax.text(0.5, 0.5, 'Need both stochastic and adversarial results to compare.',
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_axis_off()
            # Summary with whatever is available
            self._plot_research_summary(axes[1, 2], stoch_results or adv_results, None)

        plt.tight_layout()
        plt.savefig('stochastic_vs_adversarial_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()


    def _plot_model_performance_ranking(self, ax, results):
        """Plot model performance ranking."""
        models = list(results['results'].keys())
        final_rewards = [results['results'][model]['final_reward'] for model in models]
        
        colors = [self.model_colors.get(model, '#888888') for model in models]
        
        bars = ax.bar(models, final_rewards, color=colors, alpha=0.8)
        ax.set_title('Model Performance Ranking\n(Final Cumulative Reward)', fontweight='bold')
        ax.set_xlabel('Models')
        ax.set_ylabel('Final Reward')
        ax.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, reward in zip(bars, final_rewards):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max(final_rewards)*0.01,
                    f'{reward:.2f}', ha='center', va='bottom', fontweight='bold')

    def _plot_oracle_efficiency(self, ax, results):
        """Plot Oracle efficiency for each model."""
        models = list(results['results'].keys())
        oracle_reward = results['oracle_reward']
        efficiencies = []
        
        for model in models:
            model_reward = results['results'][model]['final_reward']
            efficiency = (model_reward / oracle_reward * 100) if oracle_reward > 0 else 0
            efficiencies.append(efficiency)
        
        colors = [self.model_colors.get(model, '#888888') for model in models]
        
        bars = ax.bar(models, efficiencies, color=colors, alpha=0.8)
        ax.set_title('Oracle Efficiency Comparison\n(% of Oracle Performance)', fontweight='bold')
        ax.set_xlabel('Models')
        ax.set_ylabel('Oracle Efficiency (%)')
        ax.tick_params(axis='x', rotation=45)
        ax.axhline(y=100, color='red', linestyle='--', alpha=0.7, label='Oracle Baseline')
        ax.legend()
        
        # Add value labels
        for bar, eff in zip(bars, efficiencies):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{eff:.1f}%', ha='center', va='bottom', fontweight='bold')

    def _plot_reward_evolution(self, ax, results):
        """Plot reward evolution over time."""
        models = list(results['results'].keys())
        
        for model in models:
            model_data = results['results'][model]
            if 'model_results' in model_data and 'reward_list' in model_data['model_results']:
                rewards = model_data['model_results']['reward_list']
                color = self.model_colors.get(model, '#888888')
                ax.plot(rewards, label=model, color=color, linewidth=2, alpha=0.8)
        
        ax.set_title('Reward Evolution Over Time', fontweight='bold')
        ax.set_xlabel('Time Steps')
        ax.set_ylabel('Cumulative Reward')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_statistical_analysis(self, ax, results):
        """Plot statistical analysis of model performance."""
        # print(results['results'])
        models = list(results['results'].keys())
        # gaps = [results[model].get('gap', float('inf')) for model in models]
        gaps = [results['gaps'].get(model, float('inf')) for model in models]
        # Filter out infinite gaps
        finite_gaps = [(model, gap) for model, gap in zip(models, gaps) if gap != float('inf')]
        # finite_gaps = [(model, results[model].get('gap', float('inf'))) for model in results.keys()]
        
        if finite_gaps:
            models_filtered, gaps_filtered = zip(*finite_gaps)
            colors = [self.model_colors.get(model, '#888888') for model in models_filtered]
            
            bars = ax.bar(models_filtered, gaps_filtered, color=colors, alpha=0.8)
            ax.set_title('Oracle Gap Analysis\n(Lower is Better)', fontweight='bold')
            ax.set_xlabel('Models')
            ax.set_ylabel('Oracle Gap (%)')
            ax.tick_params(axis='x', rotation=45)
            
            # Add value labels
            for bar, gap in zip(bars, gaps_filtered):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + max(gaps_filtered)*0.01,
                        f'{gap:.1f}%', ha='center', va='bottom', fontweight='bold')
        else:
            ax.text(0.5, 0.5, 'No Statistical Data Available', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)

    def _plot_robustness_comparison(self, ax, stoch_results, adv_results):
        # Intersect and exclude Oracle
        models = sorted(m for m in stoch_results['results'].keys()
                        if m in adv_results['results'] and m != 'Oracle')

        stoch_rewards = [stoch_results['results'][m]['final_reward'] for m in models]
        adv_rewards   = [adv_results['results'][m]['final_reward']   for m in models]

        # Optional: normalize for fair comparison
        # s_oracle = stoch_results['oracle_reward'] or 1.0
        # a_oracle = adv_results['oracle_reward'] or 1.0
        # stoch_rewards = [r / s_oracle * 100 for r in stoch_rewards]
        # adv_rewards   = [r / a_oracle * 100 for r in adv_rewards]
        # ylabel = 'Oracle Efficiency (%)'  # if normalized
        ylabel = 'Final Reward'  # if not normalized

        x = np.arange(len(models))
        width = 0.38
        bars1 = ax.bar(x - width/2, stoch_rewards, width,
                    label='Stochastic', alpha=0.85, color=self.env_colors.get('stochastic', '#3498db'))
        bars2 = ax.bar(x + width/2, adv_rewards,   width,
                    label='Adversarial', alpha=0.85, color=self.env_colors.get('adaptive', '#e67e22'))

        ax.set_title('Environment Robustness Comparison', fontweight='bold')
        ax.set_xlabel('Models')
        ax.set_ylabel(ylabel)
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)


    def _plot_single_environment_analysis(self, ax, results):
        """Plot single environment analysis when no adversarial data."""
        ax.text(0.5, 0.5, 'Stochastic Environment Analysis\n\nFocused Evaluation Complete\nAdversarial Data Not Available', 
                ha='center', va='center', transform=ax.transAxes, fontsize=12, 
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        ax.set_title('Single Environment Analysis', fontweight='bold')

    def _plot_research_summary(self, ax, stoch_results, adv_results):
        """Plot research summary and insights."""
        models = list(stoch_results['results'].keys())
        oracle_reward = stoch_results['oracle_reward']
        
        summary_text = "RESEARCH INSIGHTS:\n\n"
        
        # Find best performing model
        best_model = max(models, key=lambda m: stoch_results['results'][m]['final_reward'])
        best_reward = stoch_results['results'][best_model]['final_reward']
        best_efficiency = (best_reward / oracle_reward * 100) if oracle_reward > 0 else 0
        
        summary_text += f"• Best Model: {best_model}\n"
        summary_text += f"• Oracle Efficiency: {best_efficiency:.1f}%\n\n"
        
        if adv_results:
            summary_text += "• Adversarial Robustness: Evaluated\n"
            summary_text += "• Environment Comparison: Available\n"
        else:
            summary_text += "• Stochastic Performance: Validated\n"
            summary_text += "• Framework Focus: Single Environment\n"
        
        summary_text += f"\n• Total Models Evaluated: {len(models)}\n"
        summary_text += f"• Quantum Network Simulation: Complete"
        
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        ax.set_title('Research Summary', fontweight='bold')
        ax.axis('off')

    def _create_basic_comparison_plot(self):
        """Create basic comparison plot when no data available."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.text(0.5, 0.5, 'Stochastic vs Adversarial Comparison\n\nNo evaluation data available.\nRun model evaluation first.', 
                ha='center', va='center', transform=ax.transAxes, fontsize=14,
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        ax.set_title('Quantum MAB Models Robustness Analysis', fontsize=16, fontweight='bold')
        ax.axis('off')
        
        plt.tight_layout()
        plt.savefig('stochastic_vs_adversarial_comparison.png', dpi=300, bbox_inches='tight')
        plt.show()  # DISPLAYS in notebook


# Compatibility functions for existing code
def test_stochastic_vs_adversarial_visualization():
    """Legacy compatibility function."""
    viz = QuantumEvaluatorVisualizer()
    evaluator, results = viz.run_stochastic_test()
    viz.create_stochastic_evaluation_plots()
    return viz, evaluator, results

def test_comprehensive_environments():
    """Test comprehensive framework evaluation."""
    viz = QuantumEvaluatorVisualizer()
    results = viz.run_comprehensive_model_evaluation()
    viz.create_stochastic_evaluation_plots()
    return viz

# if __name__ == "__main__":
#     print("Quantum MAB Models Evaluation Framework - Visualization Engine")
#     viz = QuantumEvaluatorVisualizer()
#     results = viz.run_comprehensive_model_evaluation()
#     viz.create_stochastic_evaluation_plots()
