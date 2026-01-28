# quantum_mab_models_visualizer.py

import matplotlib.pyplot as plt
import gc, time, copy
import seaborn as sns
import pandas as pd
import numpy as np

import os
import json
import pickle
from datetime import datetime
from pathlib import Path

from daqr.config.experiment_config import ExperimentConfiguration

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

    def __init__(self, comparison_results={}, framework_config=None, config=None, output_dir=None, allocator=None):
        """
        Initialize the visualization engine with framework configuration.
        Args:
            framework_config (dict): Configuration for the evaluation framework.
            evaluator (MultiRunEvaluator): Evaluator instance for running tests.
            config (ExperimentConfiguration): Experiment configuration instance.
        """
        self.config = config if config is not None else ExperimentConfiguration()
        self.framework_config = copy.deepcopy(framework_config) or {}
        self.evaluation_results = copy.deepcopy(comparison_results)
        self.model_rankings = {}
        self.evaluators = {}
        self._setup_framework_style()
        self.viz_data = {}
        self.allocator = allocator
        
        # Storage configuration with FIXED session timestamp
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = output_dir or '../results'
        self.output_dir = Path(self.output_dir)
        self.session_id = self.session_timestamp
        self.exp_dir = None
    


    def set_session_timestamp(self, timestamp=None):
        """
        Manually set or reset the session timestamp.
        Useful when you want to group multiple evaluation runs under the same timestamp.
        
        Args:
            timestamp (str): Timestamp in format YYYYMMDD_HHMMSS. If None, generates new one.
        """
        if timestamp:
            self.session_timestamp = timestamp
        else:
            self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = self.session_timestamp
        print(f"✓ Session timestamp set to: {self.session_timestamp}")

    def _categorize_single_model(self, model_name):
        """
        Categorize a single model based on YOUR naming convention:
        
        - Oracle/RandomAlg: BASELINE (always excluded from categorization)
        - NeuralUCB: Starts with 'GNeural' or 'EXP' (quantum paper models)
        - Hybrid: Ends with 'NeuralUCB' but NOT a pure quantum model
        - iCMAB: Starts with 'i'
        - CMAB: Starts with 'C'
        
        Returns None for baseline models (Oracle, RandomAlg).
        """
        # ALWAYS exclude baseline models
        if model_name in ['Oracle', 'RandomAlg']:
            return None
        
        # Rule 1: NeuralUCB = starts with 'GNeural' OR 'EXP'
        if model_name.startswith('GNeural') or model_name.startswith('EXP'):
            return 'NeuralUCB'
        
        # Rule 2: Hybrid = ends with 'NeuralUCB' (already excluded pure quantum above)
        if model_name.endswith('NeuralUCB'):
            return 'Hybrid'
        
        # Rule 3: iCMAB = starts with 'i'
        if model_name.startswith('i'):
            return 'iCMAB'
        
        # Rule 4: CMAB = starts with 'C'
        if model_name.startswith('C'):
            return 'CMAB'
        
        # Default fallback
        return 'NeuralUCB'
    
    def _detect_model_category(self, models_tested):
        """
        Detect experiment category based on NON-BASELINE models tested.
        
        Priority:
        1. Hybrid (if any hybrid models)
        2. iCMAB (if any iCMAB models)
        3. CMAB (if any CMAB models)
        4. NeuralUCB (default)
        """
        if not models_tested:
            return 'NeuralUCB'
        
        # Get categories (excluding baselines)
        categories = []
        for model in models_tested:
            cat = self._categorize_single_model(model)
            if cat:  # Skip None (Oracle, RandomAlg)
                categories.append(cat)
        
        if not categories:
            return 'NeuralUCB'
        
        # Priority-based detection
        if 'Hybrid' in categories:
            return 'Hybrid'
        if 'iCMAB' in categories:
            return 'iCMAB'
        if 'CMAB' in categories:
            return 'CMAB'
        
        return 'NeuralUCB'


    def _setup_framework_style(self):
        plt.style.use('seaborn-v0_8')

        # Comprehensive model color palette (expandable)
        self.model_colors = {
            # Neural Bandit Models
            'Oracle': '#2c3e50',              # Dark gray (baseline)
            
            # Contextual Models (Red family - reactive)
            'CPursuitNeuralUCB': '#e74c3c',   # Bright red
            'EXPNeuralUCB': '#c0392b',        # Dark red
            'CEXPNeuralUCB': '#2980b9',       # Blue (contextual + adversarial)
            
            # Informative Models (Orange/Coral family - predictive)
            'iCPursuitNeuralUCB': '#ff6b6b',  # ✓ Coral red (lighter than CPursuit)
            # OR
            'iCPursuitNeuralUCB': '#e67e22',  # ✓ Orange (matches iCMAB theme)
            
            'GNeuralUCB': '#3498db',          # Blue
            
            # Traditional Models (Green family)
            'UCB': '#27ae60',
            'LinUCB': '#2ecc71',
            'ThompsonSampling': '#16a085',
            'EpsilonGreedy': '#1abc9c',
            
            # Advanced Models (Purple family)
            'EXPUCB': '#9b59b6',
            'KernelUCB': '#8e44ad',
            
            # Contextual/Informative Base Models (Orange family)
            'CMAB': '#f39c12',                # Gold
            'iCMAB': '#e67e22'                # Orange
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


    def _create_experiment_directory(self, environment_name, experiment_id, num_runs, model_category=None, models_tested=None):
        """
        Create hierarchical directory with category layer.
        
        Structure:
        Environments/
        └── {Environment}/
            └── {Category}/  ← Hybrid/CMAB/iCMAB/NeuralUCB
                └── Experiment_{id}_{runs}_Runs_{timestamp}/
                    ├── results/
                    ├── plots/
                    └── metadata/
        """
        env_name = environment_name.replace('/', '_').replace(' ', '_').title()
        
        # Auto-detect category if not provided
        if model_category is None:
            model_category = self._detect_model_category(models_tested or [])

        allocator_type = str(self.allocator) if self.allocator else "None"

        
        # Build path with category layer
        experiment_dir = (
            self.output_dir / 
            "Environments" / 
            env_name / 
            allocator_type /
            model_category /
            f"Experiment_{experiment_id}_{num_runs}_Runs_{self.session_timestamp}"
        )
        
        # Create subdirectories
        (experiment_dir / "results").mkdir(parents=True, exist_ok=True)
        (experiment_dir / "plots").mkdir(parents=True, exist_ok=True)
        (experiment_dir / "metadata").mkdir(parents=True, exist_ok=True)
        
        print(f"✓ Created: {str(experiment_dir).split('/')[-1]}")
        print(f"  └─ Category: {model_category}")
        
        return experiment_dir, model_category
    

    def save_experiment_results(self, environment_name, experiment_id, results, num_runs=None, model_category=None, save_format='both'):
        """
        Save experiment results with automatic categorization.
        
        Args:
            environment_name: 'stochastic', 'adversarial', etc.
            experiment_id: Unique experiment identifier
            results: Results dictionary
            num_runs: Number of runs (auto-detected if None)
            model_category: Category (auto-detected if None)
            save_format: 'json', 'pickle', or 'both'
        """
        # Extract models tested
        models_tested = []
        if isinstance(results, dict) and 'results' in results:
            models_tested = list(results['results'].keys())
        
        # Auto-detect num_runs if not provided
        if num_runs is None:
            if 'total_experiments' in results:
                num_runs = results['total_experiments']
            elif models_tested:
                # Don't count Oracle as a "run"
                num_runs = len([m for m in models_tested if m != 'Oracle'])
            else:
                num_runs = 1
        
        # Create directory with auto-detected category
        self.exp_dir, detected_category = self._create_experiment_directory(
            environment_name, 
            experiment_id, 
            num_runs,
            model_category=model_category,
            models_tested=models_tested
        )
        
        # Enhanced metadata
        metadata = {
            'environment': environment_name,
            'experiment_id': experiment_id,
            'num_runs': num_runs,
            'model_category': detected_category,
            'models_tested': models_tested,
            'timestamp': datetime.now().isoformat(),
            'session_timestamp': self.session_timestamp,
            'session_id': self.session_id,
            'framework_config': self.framework_config,
            "allocator_type": str(self.allocator), 
            "allocator_config": self.allocator.get_config() if self.allocator else {}
        }
        
        saved_paths = {}
        
        # Save metadata
        metadata_path = self.exp_dir / "metadata" / "experiment_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
        saved_paths['metadata'] = str(metadata_path)
        print(f"✓ Metadata: {str(metadata_path).split('/')[-1]}")
        
        # Save results in requested format
        if save_format in ['json', 'both']:
            json_safe_results = self._make_json_safe(results)
            results_json_path = self.exp_dir / "results" / f"experiment_{experiment_id}_results.json"
            with open(results_json_path, 'w') as f:
                json.dump(json_safe_results, f, indent=2, default=str)
            saved_paths['json'] = str(results_json_path)
            print(f"✓ JSON: {str(results_json_path).split('/')[-1]}")
        
        if save_format in ['pickle', 'both']:
            results_pickle_path = self.exp_dir / "results" / f"experiment_{experiment_id}_results.pkl"
            with open(results_pickle_path, 'wb') as f:
                pickle.dump(results, f)
            saved_paths['pickle'] = str(results_pickle_path)
            print(f"✓ Pickle: {str(results_pickle_path).split('/')[-1]}")
        
        # Save human-readable summary
        summary_path = self.exp_dir / "results" / "experiment_summary.txt"
        self._write_experiment_summary(summary_path, environment_name, results, metadata)
        saved_paths['summary'] = str(summary_path)
        print(f"✓ Summary: {str(summary_path).split('/')[-1]}")
        
        return {
            'experiment_directory': str(self.exp_dir),
            'model_category': detected_category,
            'files': saved_paths
        }
    
    
    def save_all_evaluation_results(self, save_format='both'):
        """
        Save ALL evaluation results from current session.
        """
        if not self.evaluation_results:
            print("⚠ No evaluation results to save.")
            return {}
        
        saved_experiments = {}
        category_summary = {'Hybrid': 0, 'CMAB': 0, 'iCMAB': 0, 'NeuralUCB': 0}
        
        print("="*70)
        print(f"SAVING EVALUATION RESULTS (Session: {self.session_timestamp})")
        print("="*70)
        
        for environment, env_results in self.evaluation_results.items():
            if environment == 'scenarios_results':
                continue
            
            # Get experiment IDs
            exp_ids = [k for k in env_results.keys() if isinstance(k, int) or (isinstance(k, str) and k.isdigit())]
            
            if not exp_ids:
                exp_ids = [k for k in env_results.keys() if k != 'avg_efficiency_stats']
            
            if not exp_ids:
                print(f"⚠ No experiments for: {environment}")
                continue
            
            # Get correct num_runs
            num_runs = self.framework_config.get('exp_num', len(exp_ids))
            if 'avg_efficiency_stats' in env_results:
                stats = env_results['avg_efficiency_stats']
                if 'total_experiments' in stats:
                    num_runs = stats['total_experiments']
            
            # Save each experiment
            for exp_id in exp_ids:
                exp_results = env_results[exp_id]
                
                saved_info = self.save_experiment_results(
                    environment_name=environment,
                    experiment_id=exp_id,
                    results=exp_results,
                    num_runs=num_runs,
                    save_format=save_format
                )
                
                category = saved_info['model_category']
                category_summary[category] += 1
                saved_experiments[f"{environment}_exp{exp_id}_{category}"] = saved_info
        
        print("="*70)
        print(f"✓ Saved {len(saved_experiments)} experiments")
        print(f"✓ Session: {self.session_timestamp}")
        print("\nCategory Breakdown:")
        for cat, count in category_summary.items():
            if count > 0:
                print(f"  • {cat}: {count} experiments")
        print("="*70)
        
        return {
            'experiments': saved_experiments,
            'category_summary': category_summary,
            'session_timestamp': self.session_timestamp
        }
    
    
    def _make_json_safe(self, obj):
        """
        Recursively convert numpy arrays and other non-serializable objects to JSON-safe format.
        """
        if isinstance(obj, dict):
            return {k: self._make_json_safe(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_safe(item) for item in obj]
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        else:
            return obj
    
    def _write_experiment_summary(self, filepath, environment, results, metadata):
        """
        Write a human-readable experiment summary to a text file.
        """
        with open(filepath, 'w') as f:
            f.write("="*70 + "\n")
            f.write("QUANTUM MAB MODELS EVALUATION - EXPERIMENT SUMMARY\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Environment: {environment.upper()}\n")
            f.write(f"Model Category: {metadata['model_category']}\n")
            f.write(f"Experiment ID: {metadata['experiment_id']}\n")
            f.write(f"Number of Runs: {metadata['num_runs']}\n")
            f.write(f"Timestamp: {metadata['timestamp']}\n")
            f.write(f"Session: {metadata['session_id']}\n\n")
            
            if 'results' in results:
                f.write("-"*70 + "\n")
                f.write("MODEL PERFORMANCE\n")
                f.write("-"*70 + "\n\n")
                
                for model, model_results in results['results'].items():
                    f.write(f"{model}:\n")
                    f.write(f"  Reward: {model_results.get('final_reward', 0):.6f}\n")
                    f.write(f"  Efficiency: {model_results.get('efficiency', 0):.2f}%\n")
                    f.write(f"  Gap: {model_results.get('gap', 0):.2f}%\n\n")
                
                if 'winner' in results:
                    f.write(f"{'='*70}\n")
                    f.write(f"WINNER: {results['winner']}\n")
                    f.write(f"{'='*70}\n")
    
    def load_experiment_results(self, experiment_dir, load_format='pickle'):
        """
        Load previously saved experiment results from disk.
        
        Args:
            experiment_dir (str): Path to experiment directory
            load_format (str): 'json' or 'pickle'
        
        Returns:
            dict: Loaded experiment results and metadata
        """
        exp_path = Path(experiment_dir)
        
        if not exp_path.exists():
            raise FileNotFoundError(f"Not found: {experiment_dir}")
        
        # Load metadata
        metadata_path = exp_path / "metadata" / "experiment_metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Load results
        if load_format == 'pickle':
            results_files = list((exp_path / "results").glob("*_results.pkl"))
            if results_files:
                with open(results_files[0], 'rb') as f:
                    results = pickle.load(f)
        else:
            results_files = list((exp_path / "results").glob("*_results.json"))
            if results_files:
                with open(results_files[0], 'r') as f:
                    results = json.load(f)
        
        print(f"✓ Loaded: {experiment_dir}")
        return {'metadata': metadata, 'results': results}



    def run_comprehensive_model_evaluation(self, evaluator, primary_environment='stochastic', models=None):
        """
        Run comprehensive evaluation of all available models in framework.
        
        Primary method for Quantum MAB Models Evaluation Framework.
        """
        if models is None: models = self.framework_config.get('models', [])
        
        print(f"Executing Quantum MAB Models Evaluation Framework")
        print(f"Primary Environment: {primary_environment.upper()}")
        print(f"Models to evaluate: {len(models)} models")
        
        # Execute primary evaluation
        results = self._run_framework_evaluation(evaluator, primary_environment, models)
        
        # Store results for analysis
        self.evaluation_results = results
        
        return results

    def _run_framework_evaluation(self, evaluator, environment, models=None, scenarios=None):
        """Internal framework evaluation execution."""
        # Use framework configuration parameters
        config = self.framework_config
        if scenarios is None: scenarios = self.config.test_scenarios
        if environment == 'stochastic': scenarios['none'] = 'Baseline (Optimal Conditions)'
            
        return evaluator.test_stochastic_environment(
            models=models,
            test_scenarios=scenarios,
            runs=config.get('exp_num', 1),
            frame_step=config.get('frame_step', 200),
            base_frames=config.get('base_frames', 100), 
            selected_model=config.get('main_model', 'CPursuitNeuralUCB')
        )

    def set_stochastic_results(self, results = None):
        """
        Legacy compatibility method for existing code.
        Maintained for backward compatibility while transitioning to framework.
        """
        # Store results
        if results: self.evaluation_results = results

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


    def _extract_primary_results(self, environment, evaluation_results=None):
        """
        Extract averaged efficiency stats directly from pre-computed data.
        NO RECALCULATION - uses avg_efficiency_stats from framework.
        """
        # print("TEST")
        # print(self.evaluation_results)

        if evaluation_results is None:
            evaluation_results = self.evaluation_results

        if environment not in evaluation_results:
            # Fallback: if 'stochastic' not found, try 'none' (baseline)
            if environment == 'stochastic' and 'none' in evaluation_results:
                environment = 'none'
            else:
                return None

        env_results = evaluation_results[environment]
        if not env_results:
            return None
        
        # GET PRE-COMPUTED STATS - NO RECALCULATION
        avg_efficiency_stats = env_results.get('avg_efficiency_stats')
        if not avg_efficiency_stats:
            return None
        
        # Extract all model metrics
        all_model_metrics = avg_efficiency_stats.get('all_model_metrics', {})
        oracle_avg_reward = avg_efficiency_stats.get('oracle_avg_reward', 0)
        exp_num = avg_efficiency_stats.get('total_experiments', 1)
        winner = avg_efficiency_stats.get('overall_winner', 'N/A')
        
        # Build averaged results from pre-computed metrics
        averaged_results = {}
        for model_name, metrics in all_model_metrics.items():
            averaged_results[model_name] = {
                'wins':         metrics.get('wins', 0),
                'gap':          metrics.get('avg_gap', 0),
                'final_reward': metrics.get('avg_reward', 0),
                'reward_list':  metrics.get('reward_list', 1),
                'creward_list': metrics.get('creward_list', 1),
                'efficiency':   metrics.get('avg_efficiency', 0)
            }
        
        # Get peak data (highest frame experiment)
        exp_keys = [k for k in env_results.keys() if k != 'avg_efficiency_stats']
        if not exp_keys:
            peak_data = {}
            peak_frames = 0
        else:
            highest_exp = max(exp_keys)
            peak_data = env_results[highest_exp]
            peak_frames = peak_data.get('frames_count', highest_exp)
        
        return {
            'averaged': {
                'oracle_reward': oracle_avg_reward,
                'results': averaged_results,
                'winner': winner
            },
            'exp_num': exp_num,
            'peak': peak_data,
            'peak_frames': peak_frames
        }

    def _plot_oracle_efficiency(self, ax, results):
        """Plot Oracle efficiency using PRE-COMPUTED efficiency."""
        if 'results' not in results or 'oracle_reward' not in results:
            ax.text(0.5, 0.5, 'No efficiency data available', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        efficiencies = []
        for model, result in results['results'].items():
            if model.lower() != 'oracle':
                # Use PRE-COMPUTED efficiency
                efficiency = result.get('efficiency', 0)
                efficiencies.append((model, efficiency))
        
        if not efficiencies:
            ax.text(0.5, 0.5, 'No models to display',
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        # Sort by efficiency
        efficiencies.sort(key=lambda x: x[1], reverse=True)
        models, effs = zip(*efficiencies)
        
        colors = [self._get_or_generate_color(model) for model in models]
        bars = ax.bar(models, effs, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        
        ax.set_title('Oracle Efficiency Comparison\n(% of Oracle Performance)', fontweight='bold')
        ax.set_xlabel('Models', fontsize=11, fontweight='bold')
        ax.set_ylabel('Oracle Efficiency (%)', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', rotation=45)
        ax.axhline(y=100, color='gold', linestyle='--', linewidth=2, alpha=0.7, label='Oracle (100%)')
        ax.legend(loc='lower right')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar, eff in zip(bars, effs):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{eff:.1f}%', ha='center', va='bottom', fontweight='bold')


    def _plot_model_categories(self, ax, data):
        """Plot performance by model category using PRE-COMPUTED efficiency."""
        categories = {
            'Neural Bandits': ['CEXPNeuralUCB', 'EXPNeuralUCB', 'GNeuralUCB', 'NeuralUCB'],
            'Traditional': ['UCB', 'LinUCB', 'ThompsonSampling', 'EpsilonGreedy'],
            'Advanced': ['EXPUCB', 'KernelUCB'],
            'Contextual': ['CMAB', 'iCMAB']
        }
        
        category_performance = {}
        
        for category, models in categories.items():
            category_efficiencies = []
            for model in models:
                if model in data['results']:
                    # Use PRE-COMPUTED efficiency
                    efficiency = data['results'][model].get('efficiency', 0)
                    category_efficiencies.append(efficiency)
            
            if category_efficiencies:
                category_performance[category] = np.mean(category_efficiencies)
        
        if category_performance:
            categories_list = list(category_performance.keys())
            performances = list(category_performance.values())
            
            ax.bar(categories_list, performances, 
                color=['#e74c3c', '#27ae60', '#9b59b6', '#f39c12'], alpha=0.7)
            ax.set_ylabel('Average Oracle Efficiency (%)', fontweight='bold')
            ax.set_title('Performance by Model Category', fontweight='bold')
            ax.tick_params(axis='x', rotation=45)
            ax.grid(True, alpha=0.3, axis='y')


    def _plot_efficiency_comparison(self, ax, data):
        """Plot averaged vs peak efficiency using PRE-COMPUTED data."""
        if 'averaged' not in data or 'peak' not in data:
            ax.text(0.5, 0.5, 'Insufficient data for comparison',
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        avg_data = data['averaged']
        peak_data = data['peak']
        peak_frames = data.get('peak_frames', 0)
        
        if 'results' not in avg_data or 'results' not in peak_data:
            ax.text(0.5, 0.5, 'Missing results data',
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        models = list(avg_data['results'].keys())
        
        avg_efficiencies = []
        peak_efficiencies = []
        
        for model in models:
            # Use PRE-COMPUTED efficiencies
            avg_eff = avg_data['results'][model].get('efficiency', 0)
            avg_efficiencies.append(avg_eff)
            
            # Peak efficiency (may need calculation if not pre-computed)
            if 'efficiency' in peak_data['results'].get(model, {}):
                peak_eff = peak_data['results'][model]['efficiency']
            else:
                peak_reward = peak_data['results'][model].get('final_reward', 0)
                peak_oracle = peak_data.get('oracle_reward', 1)
                peak_eff = (peak_reward / peak_oracle * 100) if peak_oracle > 0 else 0
            peak_efficiencies.append(peak_eff)
        
        x = np.arange(len(models))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, avg_efficiencies, width, 
                    label='Averaged', alpha=0.85, color='#3498db')
        bars2 = ax.bar(x + width/2, peak_efficiencies, width, 
                    label=f'Peak ({peak_frames} frames)', alpha=0.85, color='#e74c3c')
        
        ax.set_title('Oracle Efficiency: Averaged vs Peak\n(Multi-Experiment Analysis)', 
                    fontweight='bold')
        ax.set_xlabel('Models', fontweight='bold')
        ax.set_ylabel('Oracle Efficiency (%)', fontweight='bold')
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
        """Plot performance distribution using PRE-COMPUTED efficiency."""
        if 'results' not in data:
            ax.text(0.5, 0.5, 'No distribution data available',
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        efficiencies = []
        for model, result in data['results'].items():
            if model.lower() != 'oracle':
                # Use PRE-COMPUTED efficiency
                efficiency = result.get('efficiency', 0)
                efficiencies.append(efficiency)
        
        if efficiencies:
            ax.hist(efficiencies, bins=10, alpha=0.7, color='#3498db', edgecolor='black')
            ax.axvline(np.mean(efficiencies), color='red', linestyle='--', 
                    label=f'Mean: {np.mean(efficiencies):.1f}%', linewidth=2)
            ax.set_xlabel('Oracle Efficiency (%)', fontweight='bold')
            ax.set_ylabel('Number of Models', fontweight='bold')
            ax.set_title('Performance Distribution', fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

    def _get_or_generate_color(self, model_name):
        """Get existing color or auto-generate for new models."""
        if model_name in self.model_colors:
            return self.model_colors[model_name]
        
        # Generate consistent color from model name
        import hashlib, colorsys
        hash_val = int(hashlib.md5(model_name.encode()).hexdigest(), 16)
        hue = (hash_val % 360) / 360.0
        r, g, b = colorsys.hls_to_rgb(hue, 0.5, 0.6)
        color = f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
        self.model_colors[model_name] = color  # Cache it
        return color
    
    def _plot_gap_analysis(self, ax, data):
        """Plot oracle gap analysis."""
        gaps = []
        model_names = []
        
        for model, model_res in data['results'].items():
            if model != 'Oracle':
                gaps.append(model_res.get('gap', {}))
                model_names.append(model)

        if gaps and model_names:
            colors = [self._get_or_generate_color(model) for model in model_names]
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


    # ADD THIS AS A STANDALONE METHOD IN THE CLASS (NOT NESTED):
    def _best_exp(self, exp_dict):
        """Pick experiment - handles both single and multi-run structures."""
        if not exp_dict:
            return None
        
        # Case 1: It's already a single experiment result (has 'results' key directly)
        if isinstance(exp_dict, dict) and 'results' in exp_dict:
            return exp_dict
        
        # Case 2: It's a dict of experiments {exp_id: experiment_data}
        if isinstance(exp_dict, dict):
            # Pick the one with largest frames_count
            best_exp = None
            max_frames = 0
            
            for exp_id, exp_data in exp_dict.items():
                if isinstance(exp_data, dict) and 'results' in exp_data:
                    frames = exp_data.get('frames_count', exp_data.get('results', {}).get('frames_count', 0))
                    if frames > max_frames:
                        max_frames = frames
                        best_exp = exp_data
            
            return best_exp
        
        return None


    def get_viz_data(self, environment='stochastic'):
        """Retrieve processed visualization data."""
        if environment in self.viz_data: return self.viz_data[environment]
        return {}
    
    def plot_scenarios_comparison(self, eval_results=None, scen_data=None, baseline_data=None, scenario='stochastic'):
        """Generate comprehensive robustness visualization using pre-computed stats."""
        print(f"Creating  {scenario} vs basline comparison visualization...")

        if not self.evaluation_results and eval_results is None:
            print("No evaluation results found. Running basic framework display...")
            self._create_basic_comparison_plot()
            return

        scenario_data = f"{scenario}_data"
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Quantum MAB Models: Stochastic vs Baseline Robustness Analysis',
                    fontsize=16, fontweight='bold')

        if scen_data is None:
            # Get stochastic data using _extract_primary_results (uses avg_efficiency_stats)
            self.viz_data[scenario_data] = self._extract_primary_results(scenario, eval_results)
            if not self.viz_data[scenario_data]:
                # Try fallback
                self.viz_data[scenario_data] = self._extract_primary_results('random', eval_results)
            scen_data = self.viz_data[scenario_data]
        
        baseline = ''
        if baseline_data is None:
            # Get baseline/none data
            baseline = 'baseline'
            baseline_data = f'{baseline}_data'
            self.viz_data[baseline_data] = self._extract_primary_results('none', eval_results)
            if not self.viz_data[baseline_data]:
                self.viz_data[baseline_data] = self._extract_primary_results('baseline', eval_results)
            if not self.viz_data[baseline_data]:
                self.viz_data[baseline_data] = self._extract_primary_results('no_attack', eval_results)
            baseline_data = self.viz_data[baseline_data]

        # Extract averaged results (already computed by framework)
        scenario_results = scen_data['averaged'] if scen_data else None
        baseline_results = baseline_data['averaged'] if baseline_data else None

        # Plot all 6 panels
        if scenario_results:
            self._plot_model_performance_ranking(axes[0, 0], scenario_results, scenario)
            self._plot_oracle_efficiency(axes[0, 1], scenario_results)
            self._plot_reward_evolution(axes[0, 2], scenario_results, scenario_data)
            self._plot_statistical_analysis(axes[1, 0], scenario_results)
        else:
            for (r, c) in [(0,0), (0,1), (0,2), (1,0)]:
                axes[r, c].text(0.5, 0.5, f'No {scenario} results', 
                            ha='center', va='center', transform=axes[r, c].transAxes)
                axes[r, c].set_axis_off()

        # Bottom row comparison (stochastic vs baseline)
        if scenario_results and baseline_results:
            self._plot_robustness_comparison(axes[1, 1], scenario_results, baseline_results, scenario)
            self._plot_research_summary(axes[1, 2], scenario_results, baseline_results)
        elif scenario_results:
            self._plot_single_environment_summary(axes[1, 1], scenario_results, scenario.title())
            self._plot_research_summary(axes[1, 2], scenario_results, None)
        else:
            axes[1, 1].text(0.5, 0.5, 'Need both environments for comparison',
                        ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_axis_off()
            axes[1, 2].text(0.5, 0.5, 'No results available',
                        ha='center', va='center', transform=axes[1, 2].transAxes)
            axes[1, 2].set_axis_off()


        # --- Build comparison results directory ---
        allocator_type = str(self.allocator) if self.allocator else "None"
        model_category = self._detect_model_category(
            list(scenario_results['results'].keys()) if scenario_results else []
        )

        # Create unified "comparison" directory under /results
        exp_dir = (
            self.output_dir /
            "comparison" /
            allocator_type /
            model_category
        )
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Use timestamped filename for traceability
        baseline_suffix = f"_vs_{baseline}" if baseline else ""
        timestamp = self.session_timestamp
        plot_filename = f"{allocator_type}_{scenario}{baseline_suffix}_{timestamp}.png"
        plot_path = exp_dir / plot_filename

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"✓ Comparison plot saved as: {str(plot_path).split('/')[-1]}")
        plt.show()


    def plot_stochastic_vs_adversarial_comparison(self, eval_results=None, stoch_data=None, baseline_data=None, scenario='stochastic'):
        """Generate comprehensive robustness visualization using pre-computed stats."""
        print(f"Creating  {scenario} vs basline comparison visualization...")

        if not self.evaluation_results and eval_results is None:
            print("No evaluation results found. Running basic framework display...")
            self._create_basic_comparison_plot()
            return

        scenario_data = f"{scenario}_data"
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Quantum MAB Models: Stochastic vs Baseline Robustness Analysis',
                    fontsize=16, fontweight='bold')

        if stoch_data is None:
            # Get stochastic data using _extract_primary_results (uses avg_efficiency_stats)
            self.viz_data[scenario_data] = self._extract_primary_results(scenario, eval_results)
            if not self.viz_data[scenario_data]:
                # Try fallback
                self.viz_data[scenario_data] = self._extract_primary_results('random', eval_results)
            stoch_data = self.viz_data[scenario_data]
        
        baseline = ''
        if baseline_data is None:
            # Get baseline/none data
            baseline = 'baseline'
            baseline_data = f'{baseline}_data'
            # Get baseline/none data
            self.viz_data[baseline_data] = self._extract_primary_results('none', eval_results)
            if not self.viz_data[baseline_data]:
                self.viz_data[baseline_data] = self._extract_primary_results('baseline', eval_results)
            if not self.viz_data[baseline_data]:
                self.viz_data[baseline_data] = self._extract_primary_results('no_attack', eval_results)
            baseline_data = self.viz_data[baseline_data]

        # Extract averaged results (already computed by framework)
        stoch_results = stoch_data['averaged'] if stoch_data else None
        baseline_results = baseline_data['averaged'] if baseline_data else None

        # Plot all 6 panels
        if stoch_results:
            self._plot_model_performance_ranking(axes[0, 0], stoch_results)
            self._plot_oracle_efficiency(axes[0, 1], stoch_results)
            self._plot_reward_evolution(axes[0, 2], stoch_results)
            self._plot_statistical_analysis(axes[1, 0], stoch_results)
        else:
            for (r, c) in [(0,0), (0,1), (0,2), (1,0)]:
                axes[r, c].text(0.5, 0.5, 'No stochastic results', 
                            ha='center', va='center', transform=axes[r, c].transAxes)
                axes[r, c].set_axis_off()

        # Bottom row comparison (stochastic vs baseline)
        if stoch_results and baseline_results:
            self._plot_robustness_comparison(axes[1, 1], stoch_results, baseline_results)
            self._plot_research_summary(axes[1, 2], stoch_results, baseline_results)
        elif stoch_results:
            self._plot_single_environment_summary(axes[1, 1], stoch_results, 'Stochastic')
            self._plot_research_summary(axes[1, 2], stoch_results, None)
        else:
            axes[1, 1].text(0.5, 0.5, 'Need both environments for comparison',
                        ha='center', va='center', transform=axes[1, 1].transAxes)
            axes[1, 1].set_axis_off()
            axes[1, 2].text(0.5, 0.5, 'No results available',
                        ha='center', va='center', transform=axes[1, 2].transAxes)
            axes[1, 2].set_axis_off()

        # --- Build comparison results directory ---
        allocator_type = str(self.allocator) if self.allocator else "None"
        model_category = self._detect_model_category(
            list(stoch_results['results'].keys()) if stoch_results else []
        )

        # Create unified "comparison" directory under /results
        exp_dir = (
            self.output_dir /
            "comparison" /
            allocator_type /
            model_category
        )
        exp_dir.mkdir(parents=True, exist_ok=True)

        # Use timestamped filename for traceability
        baseline_suffix = f"_vs_{baseline}_comparison" if baseline else ""
        timestamp = self.session_timestamp
        plot_filename = f"{allocator_type}_{scenario}{baseline_suffix}_{timestamp}.png"
        plot_path = exp_dir / plot_filename

        plt.tight_layout()
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        print(f"✓ Comparison plot saved as: {str(plot_path).split('/')[-1]}")
        plt.show()

    def _plot_single_environment_summary(self, ax, stochresults, environment_name):
        """Plot single environment summary using pre-computed winner and efficiency."""
        if not stochresults or 'results' not in stochresults:
            ax.text(0.5, 0.5, 'No results available', 
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            return
        
        oracle_reward = stochresults.get('oracle_reward', 1)
        winner = stochresults.get('winner', 'N/A')
        
        models = list(stochresults['results'].keys())
        non_oracle_models = [m for m in models if m.lower() != 'oracle']
        
        if not non_oracle_models:
            ax.text(0.5, 0.5, 'No models to summarize', 
                ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            return
        
        # Use pre-computed data
        if winner and winner != 'N/A':
            winner_data = stochresults['results'].get(winner, {})
            best_efficiency = winner_data.get('efficiency', 0)
        else:
            best_efficiency = 0
        
        # Create summary text
        summary_text = f"**{environment_name} ENVIRONMENT SUMMARY**\n\n"
        summary_text += f"Best Model: {winner}\n"
        summary_text += f"Oracle Efficiency: {best_efficiency:.1f}%\n"
        summary_text += f"Total Models: {len(non_oracle_models)}\n"
        summary_text += f"Oracle Baseline: {oracle_reward:.3f}\n\n"
        summary_text += "✓ Framework Validation Complete\n"
        summary_text += "✓ Single Environment Analysis"
        
        ax.text(0.05, 0.95, summary_text, 
            transform=ax.transAxes, 
            fontsize=10, 
            verticalalignment='top',
            fontfamily='monospace',
            bbox=dict(boxstyle='round', 
                        facecolor='lightyellow', 
                        alpha=0.8, 
                        edgecolor='black', 
                        linewidth=2))
        
        ax.set_title('Single Environment Analysis', fontweight='bold', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')


    def _plot_model_performance_ranking(self, ax, data, scenario='Stochastic'):
        """
        Plot model performance ranking using PRE-COMPUTED efficiency ONLY.
        Data must come from _extract_primary_results()['averaged'].
        """
        if not data or 'results' not in data:
            ax.text(0.5, 0.5, 'No model metrics available', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        model_efficiencies = []
        model_names = []
        
        for model, result in data['results'].items():
            if model.lower() != 'oracle':  # Exclude oracle from ranking
                model_efficiencies.append(result['efficiency'])
                model_names.append(model)
        
        if not model_names:
            ax.text(0.5, 0.5, 'No models to rank', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        # Sort by efficiency
        sorted_data = sorted(zip(model_names, model_efficiencies), key=lambda x: x[1], reverse=True)
        sorted_names, sorted_efficiencies = zip(*sorted_data)
        
        # Get winner from data
        winner = data.get('winner', sorted_names[0])
        
        # Color winner green
        colors = [self._get_or_generate_color(model) for model in sorted_names]
        
        y_pos = np.arange(len(sorted_names))
        bars = ax.barh(y_pos, sorted_efficiencies, color=colors, alpha=0.8, 
                    edgecolor='black', linewidth=1.5)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(sorted_names, fontsize=10, fontweight='bold')
        ax.set_xlabel('Oracle Efficiency (%)', fontsize=11, fontweight='bold')
        ax.set_title(f'Model Performance Ranking\n({scenario.title()} Environment)', fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Add efficiency labels
        for i, (bar, efficiency) in enumerate(zip(bars, sorted_efficiencies)):
            label = f'{efficiency:.1f}%'
            if sorted_names[i] == winner:
                label += ' ✓'
            ax.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2.,
                    label, ha='left', va='center', fontweight='bold', fontsize=9)


    def _plot_oracle_efficiency(self, ax, results, baseline_model='Oracle'):
        """Plot Oracle efficiency using PRE-COMPUTED data - NO RECALCULATION."""
        if not results or 'results' not in results:
            ax.text(0.5, 0.5, 'No data available', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        models = []
        efficiencies = []
        
        # USE PRE-COMPUTED EFFICIENCY
        for model, result in results['results'].items():
            if model.lower() == baseline_model.lower(): continue  # Skip baseline model
            models.append(model)
            efficiencies.append(result['efficiency'])
        
        if not models:
            ax.set_axis_off()
            return
        
        colors = [self._get_or_generate_color(model) for model in models]
        
        bars = ax.bar(models, efficiencies, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax.set_title('Oracle Efficiency Comparison\n(% of Oracle Performance)', fontweight='bold')
        ax.set_xlabel('Models', fontsize=11, fontweight='bold')
        ax.set_ylabel('Oracle Efficiency (%)', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', rotation=45)
        ax.axhline(y=100, color='gold', linestyle='--', linewidth=2, alpha=0.7, label='Oracle (100%)')
        ax.legend(loc='lower right')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar, eff in zip(bars, efficiencies):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{eff:.1f}%', ha='center', va='bottom', fontweight='bold')


    def _plot_reward_evolution(self, ax, results, reward_type='reward_list', scen_data='stochastic_data'):
        """
        DYNAMIC: Plot any metric evolution across experiments.
        reward_type: 'reward_list', 'efficiency_list', 'gap_list', 'creward_list'
        """
        if not results or 'results' not in results:
            ax.text(0.5, 0.5, 'No time-series data available', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        models = list(results['results'].keys())
        plot_count = 0
        
        # Auto-switch to cumulative reward for single experiment
        if self.viz_data[scen_data] and self.viz_data[scen_data]['exp_num'] == 1:
            reward_type = 'creward_list'
        
        for model in models:
            model_data = results['results'][model]
            if reward_type in model_data:
                values = model_data[reward_type]
                color = self._get_or_generate_color(model)
                ax.plot(values, label=model, color=color, linewidth=2, alpha=0.8)
                plot_count += 1
        
        if plot_count == 0:
            ax.text(0.5, 0.5, f'No {reward_type} data available', 
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return
        
        # ENHANCED DYNAMIC LABELS
        metric_name = reward_type.replace('_', ' ').title().replace(' List', '')
        
        # Map reward types to descriptive labels
        ylabel_map = {
            'reward_list': 'Final Reward per Run',
            'efficiency_list': 'Oracle Efficiency (%)',
            'gap_list': 'Gap to Oracle',
            'creward_list': 'Cumulative Reward',
        }
        
        # Adjust title and xlabel based on single vs multi-experiment
        if self.viz_data[scen_data]['exp_num'] == 1:
            title = 'Cumulative Reward Over Time (Single Experiment)'
            xlabel = 'Decision Frame'
            ylabel = 'Cumulative Reward'
        else:
            title = f'{metric_name} Evolution Across Runs'
            xlabel = 'Experiment Run Index'
            ylabel = ylabel_map.get(reward_type, f'{metric_name} Value')
        
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_xlabel(xlabel, fontsize=11, fontweight='bold')
        ax.set_ylabel(ylabel, fontsize=11, fontweight='bold')
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)



    def _plot_statistical_analysis(self, ax, results):
        """
        Plot oracle gap analysis using PRE-COMPUTED gap data.
        Now uses 'gap' from results['results'][model].
        """
        if not results or 'results' not in results:
            ax.text(0.5, 0.5, 'No statistical data available', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_axis_off()
            return
        
        models = []
        gaps = []
        
        # Extract gap from each model's results
        for model, result in results['results'].items():
            if model.lower() != 'oracle':
                gap = result.get('gap', None)
                if gap is not None and gap != float('inf'):
                    models.append(model)
                    gaps.append(gap)
        
        if not models:
            ax.text(0.5, 0.5, 'No Gap Data Available', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_axis_off()
            return
        
        colors = [self._get_or_generate_color(model) for model in models]
        
        bars = ax.bar(models, gaps, color=colors, alpha=0.8, 
                    edgecolor='black', linewidth=1.5)
        ax.set_title('Oracle Gap Analysis\n(Lower is Better)', fontweight='bold')
        ax.set_xlabel('Models', fontsize=11, fontweight='bold')
        ax.set_ylabel('Oracle Gap (%)', fontsize=11, fontweight='bold')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels
        max_gap = max(gaps) if gaps else 1
        for bar, gap in zip(bars, gaps):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + max_gap*0.01,
                    f'{gap:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=9)


    def _plot_robustness_comparison(self, ax, stoch_results, adv_results, scenario='Stochastic'):
        """Plot robustness comparison between stochastic and baseline environments."""
        if not stoch_results or not adv_results:
            ax.text(0.5, 0.5, 'Need both environments for comparison', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_axis_off()
            return
        
        models = sorted(m for m in stoch_results['results'].keys()
                        if m in adv_results['results'] and m.lower() != 'oracle')

        if not models:
            ax.text(0.5, 0.5, 'No common models found', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_axis_off()
            return

        stoch_rewards = [stoch_results['results'][m]['final_reward'] for m in models]
        adv_rewards = [adv_results['results'][m]['final_reward'] for m in models]

        # Get Oracle rewards for percentage calculation
        stoch_oracle = stoch_results['results'].get('Oracle', {}).get('final_reward', 1)
        adv_oracle = adv_results['results'].get('Oracle', {}).get('final_reward', 1)

        x = np.arange(len(models))
        width = 0.38
        
        bars1 = ax.bar(x - width/2, stoch_rewards, width,
            label=scenario.title(), alpha=0.85, color=self.env_colors.get('stochastic', '#3498db'),
            edgecolor='black', linewidth=1.2)
        bars2 = ax.bar(x + width/2, adv_rewards, width,
            label='Baseline/Adversarial', alpha=0.85, color=self.env_colors.get('adaptive', '#e67e22'),
            edgecolor='black', linewidth=1.2)

        # Add percentage labels on bars
        for i, (bar1, bar2, s_reward, a_reward) in enumerate(zip(bars1, bars2, stoch_rewards, adv_rewards)):
            # Stochastic percentage
            s_pct = (s_reward / stoch_oracle * 100) if stoch_oracle > 0 else 0
            height1 = bar1.get_height()
            ax.text(bar1.get_x() + bar1.get_width()/2., height1,
                    f'{s_pct:.1f}%',
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
            
            # Baseline/Adversarial percentage
            a_pct = (a_reward / adv_oracle * 100) if adv_oracle > 0 else 0
            height2 = bar2.get_height()
            ax.text(bar2.get_x() + bar2.get_width()/2., height2,
                    f'{a_pct:.1f}%',
                    ha='center', va='bottom', fontsize=8, fontweight='bold')

        ax.set_title('Environment Robustness Comparison', fontweight='bold', fontsize=12)
        ax.set_xlabel('Models', fontsize=11, fontweight='bold')
        ax.set_ylabel('Final Reward (Averaged)', fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.legend(fontsize=10, loc='best')
        ax.grid(axis='y', alpha=0.3, linestyle='--')

    def _plot_single_environment_analysis(self, ax, results):
        """Plot single environment analysis when no adversarial data."""
        ax.text(0.5, 0.5, 'Stochastic Environment Analysis\n\nFocused Evaluation Complete\nAdversarial Data Not Available', 
                ha='center', va='center', transform=ax.transAxes, fontsize=12, 
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        ax.set_title('Single Environment Analysis', fontweight='bold')

    def _plot_research_summary(self, ax, stoch_results, adv_results):
        """Plot research summary using pre-computed data."""
        if not stoch_results or 'results' not in stoch_results:
            ax.text(0.5, 0.5, 'No results available for summary', 
                    ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            return
        
        oracle_reward = stoch_results.get('oracle_reward', 1)
        winner = stoch_results.get('winner', 'N/A')
        
        models = list(stoch_results['results'].keys())
        non_oracle_models = [m for m in models if m.lower() != 'oracle']
        
        summary_text = "RESEARCH INSIGHTS:\n\n"
        
        if winner and winner != 'N/A':
            winner_data = stoch_results['results'].get(winner, {})
            winner_efficiency = winner_data.get('efficiency', 0)
            summary_text += f"• Best Model: {winner}\n"
            summary_text += f"• Oracle Efficiency: {winner_efficiency:.1f}%\n\n"
        
        if adv_results:
            summary_text += "• Adversarial Robustness: Evaluated\n"
            summary_text += "• Environment Comparison: Available\n"
        else:
            summary_text += "• Stochastic Performance: Validated\n"
            summary_text += "• Framework Focus: Single Environment\n"
        
        summary_text += f"\n• Total Models Evaluated: {len(non_oracle_models)}\n"
        summary_text += f"• Quantum Network Simulation: Complete"
        
        ax.text(0.05, 0.95, summary_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8, 
                        edgecolor='black', linewidth=2))
        ax.set_title('Research Summary', fontweight='bold', fontsize=12)
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

    def cleanup(self, verbose=False, cooldown_seconds=1):
        """Clean up visualizer resources."""
        cleanup_items = []
        
        plt.close('all')  # Close all figures
        cleanup_items.append("all matplotlib figures")
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        
        if hasattr(self, 'evaluators'):
            for eval_key, evaluator in self.evaluators.items():
                if hasattr(evaluator, 'cleanup'):
                    evaluator.cleanup(verbose=verbose)
            self.evaluators.clear()
            cleanup_items.append("evaluators")
        
        if hasattr(self, 'evaluation_results'):
            if isinstance(self.evaluation_results, dict):
                self.evaluation_results.clear()
            cleanup_items.append("evaluation_results")
        
        if hasattr(self, 'model_rankings'):
            self.model_rankings.clear()
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                cleanup_items.append("CUDA cache")
        except ImportError:
            pass
        
        collected = gc.collect()
        cleanup_items.append(f"GC:{collected} objects")
        
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        if verbose: print(f"✓ QuantumEvaluatorVisualizer cleaned: {', '.join(cleanup_items)}")

    def plot_model_similarity(self, model1='GNeuralUCB', model2='iCPursuitNeuralUCB'):
        """Plot trajectory divergence between similar models."""
        stoch_data = self.get_viz_data('stochastic_data')
        if not stoch_data or 'averaged' not in stoch_data: return
        
        results = stoch_data['averaged']['results']
        if model1 not in results or model2 not in results: return
        
        data1, data2 = results[model1], results[model2]
        # Access raw trajectories if available via evaluator
        raw1 = self._extract_raw_trajectory(model1)
        raw2 = self._extract_raw_trajectory(model2)
        
        fig, axes = plt.subplots(2, 1, figsize=(10, 8))
        axes[0].plot(raw1['rewardlist'], label=model1, alpha=0.8)
        axes[0].plot(raw2['rewardlist'], label=model2, alpha=0.8)
        axes[0].set_title('Reward Trajectories (100 frames too short?)')
        axes[0].legend()
        
        diff = abs(data1['final_reward'] - data2['final_reward'])
        axes[1].bar(['Efficiency Diff %', 'Gap Diff %'], 
                    [abs(data1['efficiency'] - data2['efficiency']),
                    abs(data1['gap'] - data2['gap'])])
        axes[1].text(0, 0.5, f'Final Reward Diff: {diff:.3f}', transform=axes[1].transAxes)
        plt.savefig('model_similarity.png')
        plt.show()

    def plot_frame_scaling(self, models=['GNeuralUCB', 'iCPursuitNeuralUCB'], frames=[100, 500, 1000]):
        """Test divergence at baseline scales."""
        scaling_data = {}
        for frame in frames:
            # Re-run evaluator.get_evaluation_results with custom frames
            evaluator.set_frame_budget(frame)
            results = evaluator.get_evaluation_results('stochastic')
            for model in models:
                if model in results:
                    scaling_data.setdefault(model, []).append(results[model]['final_reward'])
        
        df = pd.DataFrame(scaling_data, index=frames)
        df.plot(kind='line', marker='o')
        plt.title('Performance Divergence vs Frame Count')
        plt.ylabel('Final Reward')
        plt.savefig('frame_scaling.png')
        plt.show()
        print(df)

    def __del__(self):
        """Destructor to ensure cleanup on deletion."""
        try:
            self.cleanup(verbose=False)
        except:
            pass