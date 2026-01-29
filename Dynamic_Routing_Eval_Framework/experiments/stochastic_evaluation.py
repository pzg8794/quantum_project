# quantum_mab_models_stochastic_evaluation.py

"""
Quantum MAB Models Evaluation Framework - Stochastic Testing Module

This script provides comprehensive stochastic evaluation of multiple MAB models
for quantum network routing scenarios. Configurable for different environment types.

Framework Features:
- Comprehensive model comparison in stochastic environments
- Configurable for future adversarial/other environment types  
- Rigorous statistical evaluation and ranking
- Publication-quality visualization and reporting

Usage:
    python quantum_mab_models_stochastic_evaluation.py
"""

# Import the updated visualizer class
from daqr.evaluation.visualizer import QuantumEvaluatorVisualizer

# Framework Configuration
FRAMEWORK_CONFIG = {
    'primary_environment': 'stochastic',
    'test_all_models': True,
    'evaluation_mode': 'comprehensive',
    'statistical_validation': True,
    'generate_reports': True
}

# Available Models for Testing (expandable)
AVAILABLE_MODELS = {
    'neural_bandits': ['EXPNeuralUCB', 'CPursuitNeuralUCB', 'NeuralUCB'],
    'traditional': ['UCB', 'LinUCB', 'ThompsonSampling'],
    'advanced': ['KernelUCB', 'EpsilonGreedy'], 
    'contextual': ['CMAB', 'iCMAB'],
    'reference': ['Oracle']
}

# Supported Environment Types (configurable)
ENVIRONMENT_TYPES = {
    'stochastic': 'Natural random failures and network noise',
    'baseline': 'Optimal conditions with no attacks', 
    'adversarial': 'Strategic intelligent attacks',
    'adaptive': 'Reactive adversarial attacks',
    'markov': 'Structured strategic attacks'
}

def run_stochastic_models_evaluation():
    """
    Main function for Quantum MAB Models Evaluation Framework.
    
    Performs comprehensive stochastic testing of all available models.
    Generates statistical rankings and performance comparisons.
    """
    
    print("=" * 70)
    print("QUANTUM MAB MODELS EVALUATION FRAMEWORK")
    print("=" * 70)
    print(f"Primary Environment: {FRAMEWORK_CONFIG['primary_environment'].upper()}")
    print(f"Environment Description: {ENVIRONMENT_TYPES[FRAMEWORK_CONFIG['primary_environment']]}")
    print("=" * 70)
    
    # Initialize framework with updated visualizer
    viz = QuantumEvaluatorVisualizer(framework_config=FRAMEWORK_CONFIG)
    
    # Count total models for testing
    total_models = sum(len(models) for models in AVAILABLE_MODELS.values())
    print(f"Testing {total_models} models across multiple categories:")
    
    for category, models in AVAILABLE_MODELS.items():
        print(f"  {category.replace('_', ' ').title()}: {', '.join(models)}")
    
    print("=" * 70)
    
    # Run comprehensive evaluation
    print(f"Executing comprehensive {FRAMEWORK_CONFIG['primary_environment']} evaluation...")
    
    # Primary stochastic evaluation
    evaluation_results = run_primary_evaluation(viz)
    
    # Generate performance analysis
    performance_analysis = analyze_model_performance(evaluation_results)
    
    # Generate reports
    if FRAMEWORK_CONFIG['generate_reports']:
        generate_comprehensive_reports(performance_analysis, viz)
    
    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED")
    print("=" * 70)
    
    return viz, evaluation_results, performance_analysis

def run_primary_evaluation(visualizer):
    """
    Run primary stochastic evaluation of all models.
    
    Args:
        visualizer: QuantumEvaluatorVisualizer instance
        
    Returns:
        Dictionary containing evaluation results for all models
    """
    
    primary_env = FRAMEWORK_CONFIG['primary_environment']
    print(f"Running primary {primary_env} environment testing...")
    
    # Run comprehensive test focused on stochastic environment
    evaluation_results = visualizer.run_comprehensive_model_evaluation(
        primary_environment=primary_env,
        test_models=AVAILABLE_MODELS,
        statistical_validation=FRAMEWORK_CONFIG['statistical_validation']
    )
    
    return evaluation_results

def analyze_model_performance(results):
    """
    Analyze and rank model performance from evaluation results.
    
    Args:
        results: Raw evaluation results from testing
        
    Returns:
        Dictionary containing performance analysis and rankings
    """
    
    print("\nAnalyzing model performance...")
    
    analysis = {
        'model_rankings': {},
        'performance_metrics': {},
        'statistical_significance': {},
        'recommendations': []
    }
    
    if results and 'stochastic' in results:
        stoch_data = results['stochastic']
        
        if stoch_data:
            # Get highest experiment number
            highest_exp = max(stoch_data.keys())
            exp_results = stoch_data[highest_exp]
            
            # Extract performance metrics
            oracle_reward = exp_results.get('oracle_reward', 1)
            model_results = exp_results.get('results', {})
            winner = exp_results.get('winner', 'Unknown')
            
            print(f"Best Performing Model: {winner}")
            print(f"Oracle Reward Baseline: {oracle_reward:.3f}")
            
            # Calculate efficiency rankings
            efficiencies = {}
            for model_name, model_data in model_results.items():
                if model_name != 'Oracle':  # Exclude oracle from rankings
                    final_reward = model_data.get('final_reward', 0)
                    efficiency = (final_reward / oracle_reward * 100) if oracle_reward > 0 else 0
                    efficiencies[model_name] = efficiency
            
            # Sort by efficiency
            sorted_models = sorted(efficiencies.items(), key=lambda x: x[1], reverse=True)
            
            print("\nModel Performance Rankings (Oracle Efficiency %):")
            print("-" * 50)
            for rank, (model, efficiency) in enumerate(sorted_models, 1):
                print(f"{rank:2d}. {model:<15}: {efficiency:6.1f}%")
                
                # Performance category
                if efficiency >= 90:
                    category = "EXCELLENT"
                elif efficiency >= 75:
                    category = "GOOD"
                elif efficiency >= 50:
                    category = "ACCEPTABLE"
                else:
                    category = "NEEDS IMPROVEMENT"
                    
                analysis['model_rankings'][model] = {
                    'rank': rank,
                    'efficiency': efficiency,
                    'category': category
                }
            
            # Generate recommendations
            if sorted_models:
                top_model, top_efficiency = sorted_models[0]
                analysis['recommendations'].append(
                    f"Recommended model for stochastic environments: {top_model} ({top_efficiency:.1f}% efficiency)"
                )
                
                # Identify models needing improvement
                poor_models = [model for model, eff in sorted_models if eff < 50]
                if poor_models:
                    analysis['recommendations'].append(
                        f"Models requiring optimization: {', '.join(poor_models)}"
                    )
    
    return analysis

def generate_comprehensive_reports(analysis, visualizer):
    """
    Generate comprehensive evaluation reports and visualizations.
    
    Args:
        analysis: Performance analysis results
        visualizer: QuantumEvaluatorVisualizer instance
    """
    
    print("\nGenerating comprehensive reports...")
    
    # Generate visualizations using the new method name
    visualizer.create_stochastic_evaluation_plots()
    
    print("Generated Files:")
    print("  - quantum_mab_models_stochastic_evaluation.png")  # Updated filename
    print("  - model_performance_rankings.png")
    print("  - comprehensive_comparison.png")
    
    # Print summary report
    print("\n" + "=" * 70)
    print("PERFORMANCE SUMMARY REPORT")
    print("=" * 70)
    
    if analysis['recommendations']:
        print("Key Recommendations:")
        for i, rec in enumerate(analysis['recommendations'], 1):
            print(f"{i}. {rec}")
    
    # Performance categories summary
    categories = {}
    for model, data in analysis['model_rankings'].items():
        cat = data['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(model)
    
    if categories:
        print("\nPerformance Categories:")
        for category, models in categories.items():
            print(f"  {category}: {', '.join(models)}")
    
    print("=" * 70)

def configure_framework(environment_type='stochastic', include_adversarial=False):
    """
    Configure framework for different testing scenarios.
    
    Args:
        environment_type: Primary environment to test ('stochastic', 'adversarial', etc.)
        include_adversarial: Whether to include adversarial comparison
    """
    
    FRAMEWORK_CONFIG['primary_environment'] = environment_type
    
    if include_adversarial:
        FRAMEWORK_CONFIG['comparison_environments'] = ['stochastic', 'adaptive']
        print(f"Framework configured for {environment_type} with adversarial comparison")
    else:
        print(f"Framework configured for {environment_type} focused evaluation")

def test_model_categories():
    """
    Test individual model categories for detailed analysis.
    """
    
    print("\nTesting Model Categories:")
    print("=" * 50)
    
    viz = QuantumEvaluatorVisualizer(framework_config=FRAMEWORK_CONFIG)
    
    category_results = {}
    
    for category, models in AVAILABLE_MODELS.items():
        if category != 'reference':  # Skip Oracle for category testing
            print(f"\nTesting {category.replace('_', ' ').title()} Models: {', '.join(models)}")
            
            # Test category performance (if this method exists)
            try:
                results = viz.test_model_category(
                    models=models,
                    environment=FRAMEWORK_CONFIG['primary_environment']
                )
                category_results[category] = results
            except AttributeError:
                # Method doesn't exist yet - placeholder for future implementation
                print(f"  Category testing not yet implemented for {category}")
                category_results[category] = None
    
    return category_results

# Legacy compatibility functions
def test_stochastic_vs_adversarial_visualization():
    """Legacy compatibility function."""
    viz = QuantumEvaluatorVisualizer()
    evaluator, results = viz.run_stochastic_vs_adversarial_test()
    viz.create_stochastic_evaluation_plots()
    return viz, evaluator, results

def test_comprehensive_environments():
    """Test comprehensive framework evaluation."""
    viz = QuantumEvaluatorVisualizer()
    results = viz.run_comprehensive_model_evaluation()
    viz.create_stochastic_evaluation_plots()
    return viz

# # Main execution
# if __name__ == "__main__":
#     # Run main evaluation
#     main_viz, main_results, main_analysis = run_stochastic_models_evaluation()
    
#     # Optional: Test individual model categories
#     print("\n" + "=" * 70)
#     choice = input("Run detailed model category analysis? (y/n): ").lower().strip()
#     if choice == 'y':
#         category_results = test_model_categories()
#         print("\nModel category analysis completed!")
    
#     # Optional: Configure for adversarial comparison
#     print("\n" + "=" * 70)
#     choice = input("Add adversarial environment comparison? (y/n): ").lower().strip()
#     if choice == 'y':
#         configure_framework('stochastic', include_adversarial=True)
#         adversarial_viz, adversarial_results, adversarial_analysis = run_stochastic_models_evaluation()
#         print("\nAdversarial comparison completed!")
    
#     print("\nQuantum MAB Models Evaluation Framework - All testing completed!")
#     print("Check generated PNG files for detailed visualizations.")

# ============================================================================
# Paper 7 Helper Functions
# ============================================================================

def generate_paper7_paths(topology, k: int, n_qisps: int, seed: int):
    """Generate k-shortest paths between n_qisps ISP nodes."""
    import itertools
    rng = np.random.default_rng(seed)
    nodes = list(topology.nodes)
    
    if len(nodes) < n_qisps:
        raise ValueError(f"Topology has {len(nodes)} nodes, need {n_qisps} for ISPs")
    
    isp_nodes = rng.choice(nodes, size=n_qisps, replace=False)
    all_paths = []
    
    for src, dst in itertools.combinations(isp_nodes, 2):
        try:
            path_generator = nx.shortest_simple_paths(topology, src, dst, weight='distance')
            paths = list(itertools.islice(path_generator, k))
            all_paths.extend(paths)
        except nx.NetworkXNoPath:
            continue
    
    return all_paths


def generate_paper7_contexts(paths, topology):
    """Generate context vectors: [hop_count, avg_degree, path_length]."""
    contexts = []
    
    for path in paths:
        hop_count = len(path) - 1
        degrees = [topology.degree(node) for node in path]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0.0
        
        path_length = 0.0
        for i in range(len(path) - 1):
            edge_data = topology.get_edge_data(path[i], path[i+1])
            path_length += edge_data.get('distance', 1.0)
        
        context_vector = np.array([hop_count, avg_degree, path_length])
        contexts.append(context_vector)
    
    return contexts


def get_physics_params(
    physics_model: str = "default",
    current_frames: int = 4000,
    base_seed: int = 42,
    **kwargs
):
    """
    Main physics parameter dispatcher supporting Paper 2, Paper 7, Paper 12.
    
    For Paper 7, kwargs can include:
        - n_ases, k, n_qisps, use_synthetic, reward_mode, use_context_rewards
    """
    
    if physics_model == "paper7":
        from daqr.core.topology_generator import Paper7ASTopologyGenerator
        from daqr.core.quantum_physics import Paper7RewardFunction
        
        # Extract Paper 7 params from kwargs or use defaults
        n_ases = kwargs.get('n_ases', 50)
        k = kwargs.get('k', 5)
        n_qisps = kwargs.get('n_qisps', 3)
        use_synthetic = kwargs.get('use_synthetic', False)
        reward_mode = kwargs.get('reward_mode', 'neghop')
        use_context_rewards = kwargs.get('use_context_rewards', True)
        
        # Generate topology
        topo_gen = Paper7ASTopologyGenerator()
        final_topology = topo_gen.generate(
            n_ases=n_ases,
            use_synthetic=use_synthetic,
            seed=base_seed
        )
        
        # Generate paths
        paths = generate_paper7_paths(final_topology, k, n_qisps, base_seed)
        contexts = generate_paper7_contexts(paths, final_topology)
        
        print(f"Paper7 Paths: {len(paths)} paths from {k}-shortest between {n_qisps} ISPs")
        
        # Optional rewards
        external_rewards = None
        if use_context_rewards:
            reward_func = Paper7RewardFunction(mode=reward_mode)
            external_rewards = []
            for ctx in contexts:
                reward = reward_func.compute(ctx)
                external_rewards.append([reward])
            print(f"Paper7 Rewards: Context-aware (mode={reward_mode})")
        
        return (
            None,              # noisemodel
            None,              # fidelitycalculator
            final_topology,    # externaltopology
            contexts,          # externalcontexts
            external_rewards,  # externalrewards
        )
    
    # Add paper2, paper12, default cases here...
    else:
        raise ValueError(f"Unknown physics_model: {physics_model}")
