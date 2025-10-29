import time, gc
import numpy as np, copy
from daqr.config.experiment_config import ExperimentConfiguration
from daqr.evaluation.experiment_runner import QuantumExperimentRunner


class MultiRunEvaluator:
    """
    Enhanced Multi-Run Evaluator for Comprehensive Model Evaluation

    Supports comprehensive model testing in realistic quantum network conditions
    with focus on stochastic environment analysis and baseline comparison.
    """
    def __init__(self, configs=None, base_frames=4000, frame_step=2000, base_seed=12345, 
                 runs=None, attack_type=None, models=None, scenarios=None,
                 attack_intensity=None, enable_progress=False):
        """
        Initialize the multi-run evaluator.
        Args:
            configs: Configuration object (QuantumConfig)
            base_seed: Base random seed for reproducibility
            base_frames: Starting frame count for experiments
            frame_step: Incremental step for frame counts
            attack_type: Type of environment to simulate
            attack_intensity: Intensity level of the attack/environmental effect
            enable_progress: If True, show progress bars during experiments
            models: List of models/algorithms to evaluate
            scenarios: Dictionary of scenarios to test {scenario_key: description}
        """
        self.configs = configs if configs else ExperimentConfiguration()
        self.scenarios_stats = {}
        self.env_experiments = {}
        self.evaluation_results = {}

        self.base_seed = base_seed
        self.frame_step = frame_step
        self.base_frames = base_frames
        self.enable_progress = enable_progress
        
        self.total_time = 0
        self.start_time = None
        
        # self.runs = runs
        # self.models = models
        # self.attack_type = attack_type
        # self.test_scenarios = scenarios
        # self.attack_intensity = attack_intensity

        self.cal_winner = True
        self.env_type = 'stochastic'
        self.update_configs(runs, models, attack_type, scenarios, attack_intensity)

        print("Multi-Run Evaluator Initialized")
        print(f"Environment Type: {attack_type}")
        print(f"Frame Range: {base_frames} -> {base_frames + (self.configs.runs-1)*frame_step} (step: {frame_step})")


    def run_experiment(self, exp_no, offset=100, models=None, attack_category="Stochastic", attack_rate=0.25):
        self.update_configs(models=models, attack_rate=attack_rate)

        frame_count = self.base_frames + (exp_no * self.frame_step)
        exp_id = exp_no + 1
        print(f"EXPERIMENT {exp_id}: {frame_count} frames")
        print("-" * 40)

        # Configure attack scenario ONCE (per scenario batch is fine; here per exp is safe too)
        self.configs.set_attack_strategy(
            attack_rate=self.configs.attack_rate,
            attack_type=self.configs.attack_type,
            attack_intensity=self.configs.attack_intensity
        )

        # Ask the allocator for dynamic qubit allocation (routing layer)
        route_stats = {}  # Plug in prior results if you want feedback-driven routing
        if hasattr(self.configs, 'allocator') and self.configs.allocator is not None:
            qubit_cap = tuple(self.configs.allocator.allocate(
                timestep=exp_no,
                route_stats=route_stats
            ))
        else:
            # Conservative fallback; prefer allocator presence
            qubit_cap = (8, 10, 8, 9)

        # Create runner and pass the precomputed qubit_cap
        runner = QuantumExperimentRunner(
            config=self.configs,
            base_seed=self.base_seed + exp_no * offset,
            attack_type=self.configs.attack_type,
            attack_intensity=self.configs.attack_intensity,
            enable_progress=self.enable_progress
        )

        try:
            experiment_results = runner.run_experiment(
                frame_count=frame_count,
                models=self.configs.models,
                qubit_cap=qubit_cap  # critical: pass routing-derived capacities
                capacity=self.configs.
            )
            experiment_results['attack_category'] = attack_category
            experiment_results['exp_id'] = exp_id
            self.env_experiments[self.configs.attack_type][exp_id] = experiment_results
            print(f"Experiment {exp_id} completed successfully in environment {self.configs.attack_type}")
        except Exception as e:
            print(f"Experiment {exp_id} failed: {e}")
            raise
        finally:
            del runner
            gc.collect()

        return self.env_experiments[self.configs.attack_type][exp_id]
    

    def run_experiments(self, runs=None, attack_type=None, models=None):
        """
        Run experiments for a specific environment type.

        Args:
            attack_type: Override default attack type
            exps_num: Number of frame count experiments (default: 3)
            algorithms: List of algorithms to test
        """
        self.update_configs(runs, models, attack_type)

        print(f"\nSTARTING EXPERIMENTS: {self.configs.attack_type.upper()}")
        attack_category = self.configs.category_map.get(self.configs.attack_type, 'Unknown')
        print(f"Category: {attack_category}")
        print("="*60)

        self.start_time = time.time()
        for i in range(0, self.configs.runs):
            self.run_experiment(exp_no=i, attack_category=attack_category)
        self.total_time = time.time() - self.start_time

        print(f"Total experiment time: {self.total_time:.1f}s")
        print(f"Experiments completed for {self.configs.attack_type}")
        return self.env_experiments[self.configs.attack_type]

    def calculate_scenario_performance(self, scenario):
        """
        Calculate overall performance metrics for each scenario.
        """
        if scenario not in self.scenarios_stats: return

        print("\n" + "="*70)
        print(f"DETAILED SCENARIO PERFORMANCE: {scenario.upper()}")
        print("="*70)

        stats = self.scenarios_stats[scenario]
        if stats:
            description = self.configs.test_scenarios.get(scenario).title()
            print(f"SCENARIO: \t{description.upper()}")
            print("-" * 40)
            
            winner = stats.get('overall_winner', 'N/A')
            total_exps = stats.get('total_experiments', 0)
            winner_metrics = stats.get('winner_avg_metrics', {})
            print(f"Recommended Model: \t{winner} (Won {winner_metrics.get('wins', 0)}/{total_exps} experiments)")
            
            if winner_metrics:
                print(f"\tWinner Avg Gap: \t{winner_metrics.get('avg_gap', 0):.1f}%")
                print(f"\tWinner Avg Efficiency: \t{winner_metrics.get('avg_efficiency', 0):.1f}%")

            print("\nOverall Models Performance:")
            # Access the nested dictionary for all models' metrics
            all_metrics = stats.get('all_model_metrics', {})
            
            # Sort models by their true average efficiency for a ranked view
            sorted_models = sorted(
                all_metrics.items(), 
                key=lambda item: item[1].get('avg_efficiency', 0),
                reverse=True
            )

            for model_name, metrics in sorted_models:
                if model_name == 'Oracle': continue
                wins_str = f"(Won {metrics.get('wins', 0)}/{total_exps} experiments)"
                print(f"\t• {model_name:<15}: \t{metrics.get('avg_efficiency', 0):.1f}% Efficiency \t{wins_str}")
            print("="*70)



    def calculate_scenarios_performance(self):
        """
        Calculate overall performance metrics for each scenario.
        """

        print("\n" + "="*70)
        print("COMPREHENSIVE SCENARIO PERFORMANCE ANALYSIS")
        print("="*70)

        for scenario, stats in self.scenarios_stats.items():
            print(f"SCENARIO: {scenario.upper()}")
            print(f"\t• Total Experiments: {stats['total_experiments']}")

            print(f"\t• Overall Winner: {stats['overall_winner']}")
            print(f"\t• Oracle Avg Reward: {stats['oracle_avg_reward']:.2f}")

            print(f"\t• Winner Avg Gap: {stats['avg_gap']:.2f}%")
            print(f"\t• Winner Avg Reward: {stats['avg_reward']:.2f}")
            print(f"\t• Winner Avg Efficiency: {stats['avg_efficiency']:.2f}%")
            
            print("\t• Win Counts:")
            for model, model_data in stats['all_model_metrics'].items():
                print(f"\t\t- {model}: {model_data['wins']} wins")
            print("-"*70)

            self.calculate_scenario_performance(scenario)

    def get_scenarios_stats(self, scenario=None):
        """
        Get the comprehensive scenarios statistics.
        """
        if scenario:
            if scenario not in self.scenarios_stats:
                print(f"Scenario '{scenario}' not found in statistics.")
                return {}
            
            return copy.deepcopy(self.scenarios_stats.get(scenario, {}))    
        
        return copy.deepcopy(self.scenarios_stats)
    
    def calculate_scenario_winner(self, comparison_results, scenario, baseline_model='Oracle', update_results=True):
        """
        FIXED: Calculate efficiency per experiment, then average.
        """
        if scenario not in comparison_results: return {}
        all_experiments = comparison_results[scenario]
        exps_no = len(all_experiments)
        if exps_no == 0: return {}

        model_totals = {}
        winner_efficients = {}
        total_oracle_reward = 0
        scenarios_stats = {}
        for exp_data in all_experiments.values():
            exp_oracle = exp_data['results'][baseline_model]['final_reward']
            for model_name, model_result in exp_data['results'].items():
                if model_name not in model_totals:
                    model_totals[model_name] = {'avg_reward':0, 'avg_gap':0, 'efficiency_list':[], 'wins':0, 'avg_efficiency':0, 'reward_list':[], 'creward_list':[]}
                
                model_reward = model_result.get('final_reward', 0.0)
                model_totals[model_name]['avg_reward'] += model_reward
                model_totals[model_name]['reward_list'].append(model_reward)
                model_totals[model_name]['avg_gap'] += model_result.get('gap', 0)
                model_totals[model_name]['efficiency_list'].append(model_result.get('efficiency', 0.0))
                model_totals[model_name]['creward_list'].extend(model_result['model_results']['reward_list'])

            total_oracle_reward = total_oracle_reward + exp_oracle    
            model_totals[exp_data.get('winner')]['wins'] = model_totals[exp_data.get('winner')]['wins'] + 1

        # Calculate final averages
        for model_name, totals in model_totals.items():
            avg_gap = totals['avg_gap'] / exps_no if totals['avg_gap'] > 0 else 0.0
            avg_reward = totals['avg_reward']/exps_no if totals['avg_reward'] > 0 else 0.0
            avg_efficiency = sum(totals['efficiency_list'])/exps_no if totals['efficiency_list'] else 0.0

            model_totals[model_name]['avg_gap'] = float(avg_gap)
            model_totals[model_name]['avg_reward'] = float(avg_reward)
            model_totals[model_name]['avg_efficiency'] = float(avg_efficiency)
            
            if model_name == 'Oracle': continue
            winner_efficients[model_name] = model_totals[model_name]['avg_efficiency'] 

        oracle_avg_reward = total_oracle_reward / exps_no if total_oracle_reward > 0 else float('nan')    
        efficiency_winner = max(winner_efficients, key=winner_efficients.get) if winner_efficients else "N/A"
        
        scenarios_stats[scenario] = {
            'total_experiments': exps_no,
            'win_counts': winner_efficients,
            'all_model_metrics': model_totals,
            'overall_winner': efficiency_winner,
            'oracle_avg_reward': float(oracle_avg_reward),
            'avg_gap': model_totals[efficiency_winner]['avg_gap'],
            'avg_reward': model_totals[efficiency_winner]['avg_reward'],
            'winner_avg_metrics': model_totals.get(efficiency_winner, {}),
            'avg_efficiency': model_totals[efficiency_winner]['avg_efficiency']
        }
        print(f"Scenario '{scenario}' evaluation completed.")

        if update_results:
            self.scenarios_stats[scenario] = scenarios_stats[scenario]
            self.evaluation_results[scenario].update({'avg_efficiency_stats':self.scenarios_stats[scenario]})
        
        return scenarios_stats


    def calculate_scenarios_winner(self, comparison_results, scenarios=None):
        """
        Wrapper to calculate winner stats for all specified scenarios.
        """
        self.update_configs(scenarios=scenarios)
        
        for scenario in self.configs.test_scenarios.keys():
            if scenario in comparison_results:
                self.calculate_scenario_winner(comparison_results, scenario)
        
        self.evaluation_results.update({'scenarios_results':self.scenarios_stats})
        self.calculate_scenarios_performance()
        self.generate_key_insights()


    def get_evaluation_results(self, scenario=None, exp_id=-1):
        """
        Get the comprehensive evaluation results, filtered by scenario and/or experiment ID.
        
        Supports:
        - Full scenario results (averaged stats + all experiments)
        - Single experiment (e.g., last run for isolated plotting)
        - Maintains structure for visualization (e.g., peak/last run via exp_id=-1)
        
        Args:
            scenario (str): Target scenario (e.g., 'stochastic', 'none').
            exp_id (int): Specific experiment ID; -1 for last (highest frame) run.
        
        Returns:
            dict: Filtered results with {scenario: {exp_id: data, 'avg_efficiency_stats': stats}}.
        """
        try:
            if scenario is None:
                # Return all scenarios if none specified
                return copy.deepcopy(self.evaluation_results)
            
            if scenario not in self.evaluation_results:
                raise ValueError(f"Scenario '{scenario}' not found in evaluation results.")
            
            scenario_results = copy.deepcopy(self.evaluation_results[scenario])
            if exp_id is None: return scenario_results
            
            # Handle exp_id filtering
            exp_keys = [key for key in scenario_results.keys() if key != 'avg_efficiency_stats']  
            if exp_id not in exp_keys and exp_id > 0:
                raise ValueError(f"Experiment ID '{exp_id}' not found in scenario '{scenario}' results.")
            
            if exp_id < 0: exp_id = exp_keys[-1]
            # Build filtered results for single exp_id
            filtered_results = {scenario: {exp_id: copy.deepcopy(scenario_results[exp_id])}}
            # Recalculate stats for this single experiment (no averaging needed, but for consistency)
            single_stats = self.calculate_scenario_winner(filtered_results, scenario, update_results=False)
            filtered_results[scenario]['avg_efficiency_stats'] = single_stats[scenario]  # Use single-run as "avg"
            # Add scenarios_results for framework compatibility (e.g., plotting)
            filtered_results['scenarios_results'] = single_stats
            
            return filtered_results
        except Exception as e:
            print(f"Error retrieving evaluation results: {e}")

        return {}


    def run_scenario_model_evaluation(self, runs=None, models=None, attack_type=None):
        """
        Wrapper to run comprehensive evaluation for a single scenario.
        """
        self.update_configs(runs, models, attack_type)

        print(f"TESTING ENVIRONMENT SCENARIO: {self.configs.test_scenarios[self.configs.attack_type].upper()}")
        print("="*50)
        return self.run_experiments()

    def generate_key_insights(self):
        """
        Generate key insights from the evaluation results.
        """
        print("KEY INSIGHTS:")
        # Performance retention analysis if both stochastic and baseline exist
        exp_ran = 0
        models_length = 0
        if 'stochastic' in self.scenarios_stats and self.scenarios_stats['stochastic'] and 'none' in self.scenarios_stats and self.scenarios_stats['none']:

            baseline_stats = self.scenarios_stats['none']['avg_efficiency_stats'] if 'avg_efficiency_stats' in self.scenarios_stats['none'] else self.scenarios_stats['none']
            stoch_stats = self.scenarios_stats['stochastic']['avg_efficiency_stats'] if 'avg_efficiency_stats' in self.scenarios_stats['stochastic'] else self.scenarios_stats['stochastic']

            exp_ran = stoch_stats['total_experiments']
            models_length = len(self.configs.models)

            best_model = stoch_stats['overall_winner']
            stoch_performance = stoch_stats['avg_reward']
            baseline_performance = baseline_stats['avg_reward']
            
            # Calculate realistic performance retention
            perf_retention = (stoch_performance / baseline_performance * 100) if baseline_performance > 0 else 100
            
            print(f"Best Performing Model Analysis ({best_model}):")
            print(f"\t• Stochastic Performance:    \t{stoch_performance:.3f}")
            print(f"\t• Baseline Performance:      \t{baseline_performance:.3f}")
            print(f"\t• Performance Retention:     \t{perf_retention:.1f}%")
            
            if perf_retention   > 95: 
                print(f"\tEXCELLENT:          \tMinimal performance loss under realistic conditions")
            elif perf_retention > 85: 
                print(f"\tGOOD:               \tAcceptable performance under stochastic conditions")
            elif perf_retention > 75: 
                print(f"\tMODERATE:           \tSome degradation under realistic network conditions")
            else:                     
                print(f"\tNEEDS IMPROVEMENT:  \tSignificant performance loss in stochastic environment")

        elif 'stochastic' in self.scenarios_stats and self.scenarios_stats['stochastic']:
            # Stochastic-only analysis
            exp_ran = self.scenarios_stats['stochastic']['total_experiments']
            models_length = len(self.configs.models)
            
            stoch_stats = self.scenarios_stats['stochastic']
            print(f"Stochastic Environment Analysis:")
            print(f"\t• Best Model:         \t{stoch_stats['overall_winner']}")
            print(f"\t• Oracle Efficiency:  \t{stoch_stats['avg_efficiency']:.1f}%")
            print(f"\t• Performance under realistic quantum network conditions validated")

        # Statistical significance and ranking
        print(f"Statistical Analysis:")
        print(f"\t• Total models evaluated:     \t{models_length}")
        print(f"\t• Experiments per environment:\t{exp_ran}")
        print(f"\t• Quantum network simulation: \tComprehensive stochastic modeling")
        
        print("="*70)


    def run_scenarios_model_evaluation(self, runs=None, models=None, attack_type=None, scenarios=None, cal_winner=True):
        """
        Run comprehensive model evaluation in realistic quantum network conditions.

        This method provides thorough analysis of:
        - Model performance under natural stochastic conditions
        - Oracle efficiency and convergence analysis
        - Statistical significance and ranking
        - Baseline comparison for validation
        """
        print("="*70)
        print("SCENARIOS MODEL EVALUATION")
        print("="*70)
        print("Testing algorithm performance against:")
        print("\t• Stochastic:  \tNatural quantum decoherence and network failures")
        print("\t• Baseline:    \tOptimal conditions for validation")
        print("="*70)
        self.update_configs(runs, models, attack_type, scenarios)

        print(f"Models to Test:             \t{', '.join(self.configs.models)}")
        print(f"Test Scenarios:             \t{', '.join(self.configs.test_scenarios.values())}")
        print(f"Experiments per Scenario:   \t{self.configs.runs}")
        print("="*70)

        # Run experiments for all specified scenarios
        self.evaluation_results = {}
        for attack_type in self.configs.test_scenarios.keys():
            self.configs.attack_type = attack_type
            experiment_results = self.run_scenario_model_evaluation()
            self.evaluation_results[attack_type] = copy.deepcopy(experiment_results)
        
        if cal_winner: self.calculate_scenarios_winner(self.evaluation_results)
        return self.evaluation_results

    def print_summary(self, attack_type=None, baseline_model='Oracle'):
        """Print comprehensive results summary."""
        self.update_configs(attack_type=attack_type)

        if attack_type: target_type = attack_type
        else: target_type = self.configs.attack_type

        if target_type not in self.env_experiments:
            print(f"No results found for attack_type='{target_type}'")
            return

        experiments = self.env_experiments[target_type]

        print("="*60)
        print(f"COMPREHENSIVE SUMMARY: {target_type.upper()}")
        print("="*60)

        # Get all algorithms from first experiment
        first_exp = next(iter(experiments.values()))
        for alg in first_exp['results'].keys():
            if alg == baseline_model: continue
            rewards = [exp['results'][alg]['final_reward'] for exp in experiments.values()]
            gaps = [exp['results'][alg]['gap']  for exp in experiments.values()]

            print(f"{alg}:")
            print(f"\tRewards:  \t{np.mean(rewards):.1f} ± {np.std(rewards):.1f}")
            print(f"\tAvg Gap:  \t{np.mean(gaps):.1f}%")
            print(f"\tWins:     \t{sum(1 for exp in experiments.values() if exp['winner'] == alg)}/{len(experiments)}")

        # Oracle efficiency analysis
        oracle_rewards = [exp['results'][baseline_model]['final_reward'] for exp in experiments.values()]
        print(f"Oracle Performance: \t{np.mean(oracle_rewards):.1f} ± {np.std(oracle_rewards):.1f}")

        # Best performing algorithm
        winner_counts = {}
        for exp in experiments.values():
            winner = exp['winner']
            winner_counts[winner] = winner_counts.get(winner, 0) + 1

        best_algorithm = max(winner_counts, key=winner_counts.get)
        print(f"Best Overall Algorithm: \t{best_algorithm} ({winner_counts[best_algorithm]}/{len(experiments)} wins)")
        
    def cleanup(self, verbose=False, cooldown_seconds=1):
        """
        Clean up multi-run evaluator resources.
        
        This is critical for long-running batch experiments that create
        many evaluators sequentially.
        
        Args:
            verbose: If True, print detailed cleanup information
        """
        cleanup_items = []
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        
        # 1. Deep clean env_experiments (nested dictionaries with results)
        if hasattr(self, 'env_experiments'):
            for attack_type, experiments in self.env_experiments.items():
                if isinstance(experiments, dict):
                    for exp_id, exp_data in experiments.items():
                        if isinstance(exp_data, dict):
                            # Clear nested experiment data
                            exp_data.clear()
                    experiments.clear()
                cleanup_items.append(f"env_experiments[{attack_type}]")
            self.env_experiments.clear()
        
        # 2. Clear all_results (list of result dictionaries)
        if hasattr(self, 'all_results'):
            if isinstance(self.all_results, list):
                self.all_results.clear()
            cleanup_items.append("all_results")
        
        # 3. Clear gap_analysis (algorithm performance tracking)
        if hasattr(self, 'gap_analysis'):
            if isinstance(self.gap_analysis, dict):
                for alg_name, gaps in self.gap_analysis.items():
                    if isinstance(gaps, list):
                        gaps.clear()
                self.gap_analysis.clear()
            cleanup_items.append("gap_analysis")
        
        # 4. Clear evaluation results (from comprehensive evaluation)
        if hasattr(self, 'evaluation_results'):
            if isinstance(self.evaluation_results, dict):
                self.evaluation_results.clear()
            cleanup_items.append("evaluation_results")
        
        # 5. Clear scenario statistics
        if hasattr(self, 'scenarios_stats'):
            if isinstance(self.scenarios_stats, dict):
                self.scenarios_stats.clear()
            cleanup_items.append("scenarios_stats")
        
        # 6. Reset timing information
        if hasattr(self, 'start_time'):
            self.start_time = None
        if hasattr(self, 'total_time'):
            self.total_time = 0
        
        # 7. PyTorch CUDA cleanup (in case models were cached)
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                cleanup_items.append("CUDA cache")
        except ImportError:
            pass
        
        # 8. Force garbage collection
        collected = gc.collect()
        cleanup_items.append(f"GC:{collected} objects")
        
        # Mandatory cooldown
        cleanup_items.append(f"cooldown:{cooldown_seconds}s")
        if cooldown_seconds > 0: time.sleep(cooldown_seconds)
        if verbose: print(f"✓ MultiRunEvaluator cleaned: \t{', '.join(cleanup_items)}")
    
    def __del__(self):
        """Destructor to ensure cleanup on deletion."""
        try:
            self.cleanup(verbose=False)
        except Exception as e:
            print(f"Error during MultiRunEvaluator cleanup: {e}")
    

    def update_configs(self, runs=None, models=None, scenarios=None, attack_type=None, intensity=None, attack_rate=None):
        self.configs.update_configs(runs, models, scenarios, attack_rate, intensity, attack_rate)

        if self.configs.attack_type not in self.env_experiments:
            self.env_experiments[self.configs.attack_type] = {}
        
    # Usage functions
    def test_stochastic_environment(self, runs=None, models=None, scenarios=None, attack_type='stochastic', cal_winner=True):
        """
        Main function to test models in stochastic quantum network conditions.
        
        Provides comprehensive model evaluation for research purposes.
        """
        self.update_configs(runs, models, attack_type, scenarios)
        
        # Run the comprehensive evaluation
        results = self.run_scenarios_model_evaluation(cal_winner=cal_winner,)

        return results


    def test_individual_environment(self, attack_type="stochastic"):
        """Test a single environment type."""

        self.run_experiments()
        self.print_summary()

        return self
