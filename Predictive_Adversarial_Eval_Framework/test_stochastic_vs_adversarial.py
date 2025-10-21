
# test_stochastic_vs_adversarial.py

"""
Demonstration Script: Stochastic vs Adversarial Testing

This script demonstrates the enhanced framework for clearly distinguishing 
between Stochastic (natural failures) and Adversarial (strategic attacks) scenarios.

Usage:
    python test_stochastic_vs_adversarial.py
"""

from quantum_visualizer_enhanced_v2 import EnhancedQuantumVisualizer, test_stochastic_vs_adversarial_visualization

def run_stochastic_vs_adversarial_test():
    """
    Main demonstration of Stochastic vs Adversarial testing.

    This provides clear evidence for:
    1. Algorithm performance in natural failure scenarios (Stochastic)
    2. Algorithm robustness against strategic attacks (Adversarial)  
    3. Comparative analysis of robustness loss
    """

    print("="*70)
    print("🎯 STOCHASTIC vs ADVERSARIAL ALGORITHM TESTING")
    print("="*70)
    print("📊 Testing Scenarios:")
    print("   🎲 STOCHASTIC: Natural random failures/noise")
    print("   🧠 ADVERSARIAL: Strategic intelligent attacks")
    print("="*70)

    # Run the comprehensive test
    viz, evaluator, comparison_results = test_stochastic_vs_adversarial_visualization()

    print("\n" + "="*70)
    print("✅ TESTING COMPLETED")
    print("="*70)
    print("📁 Generated Files:")
    print("   • stochastic_vs_adversarial_comparison.png")
    print("   • comprehensive_environment_comparison.png")
    print("\n📊 Results Summary:")

    # Extract key metrics for summary
    if comparison_results:
        print("   🎲 Stochastic Results:")
        if 'stochastic' in comparison_results:
            stoch_exp = max(comparison_results['stochastic'].keys())
            stoch_data = comparison_results['stochastic'][stoch_exp]
            winner = stoch_data['winner']
            winner_reward = stoch_data['results'][winner]['final_reward']
            oracle_reward = stoch_data['oracle_reward']
            efficiency = (winner_reward / oracle_reward * 100) if oracle_reward > 0 else 0
            print(f"     • Winner: {winner}")
            print(f"     • Oracle Efficiency: {efficiency:.1f}%")

        print("   🧠 Adversarial Results:")
        if 'adaptive' in comparison_results:
            adv_exp = max(comparison_results['adaptive'].keys())
            adv_data = comparison_results['adaptive'][adv_exp]
            winner = adv_data['winner']  
            winner_reward = adv_data['results'][winner]['final_reward']
            oracle_reward = adv_data['oracle_reward']
            efficiency = (winner_reward / oracle_reward * 100) if oracle_reward > 0 else 0
            print(f"     • Winner: {winner}")
            print(f"     • Oracle Efficiency: {efficiency:.1f}%")

        # Robustness Analysis
        if 'stochastic' in comparison_results and 'adaptive' in comparison_results:
            stoch_exp = max(comparison_results['stochastic'].keys())
            adv_exp = max(comparison_results['adaptive'].keys())

            stoch_exp_reward = comparison_results['stochastic'][stoch_exp]['results']['EXPNeuralUCB']['final_reward']
            adv_exp_reward = comparison_results['adaptive'][adv_exp]['results']['EXPNeuralUCB']['final_reward']

            robustness_loss = ((stoch_exp_reward - adv_exp_reward) / stoch_exp_reward * 100) if stoch_exp_reward > 0 else 0

            print("   📊 EXPNeuralUCB Robustness Analysis:")
            print(f"     • Performance Loss Under Attack: {robustness_loss:.1f}%")

            if robustness_loss < 5:
                print("     ✅ HIGHLY ROBUST algorithm")
            elif robustness_loss < 15:
                print("     ⚠️  MODERATELY ROBUST algorithm") 
            else:
                print("     ❌ LOW ROBUSTNESS algorithm")

    print("\n" + "="*70)
    print("🎯 RESEARCH INSIGHTS:")
    print("="*70)
    print("• EXPNeuralUCB designed for adversarial robustness")
    print("• Clear performance differentiation between natural vs strategic failures")
    print("• Quantified robustness metrics for academic evaluation")
    print("• Comprehensive comparison validates theoretical predictions")
    print("="*70)

    return viz, evaluator, comparison_results

def test_individual_environments():
    """Test individual environment types for detailed analysis."""

    print("\n🔬 TESTING INDIVIDUAL ENVIRONMENTS:")
    print("="*50)

    viz = EnhancedQuantumVisualizer()

    # Test each category
    test_environments = {
        "none": "Baseline (No Attacks)",
        "stochastic": "Stochastic (Natural Random Failures)",
        "adaptive": "Adversarial (Strategic Reactive Attacks)",
        "markov": "Adversarial (Structured Strategic Attacks)"
    }

    for env_type, description in test_environments.items():
        print(f"\n📊 Testing {description}...")
        viz.run_test(env_type)

    # Create comprehensive comparison
    print("\n📈 Creating comprehensive comparison visualization...")
    viz.plot_all_environments_comparison(list(test_environments.keys()))

    return viz

# if __name__ == "__main__":
#     # Run main Stochastic vs Adversarial test
#     main_viz, main_evaluator, main_results = main()

#     # Optionally run individual environment tests
#     print("\n" + "="*70)
#     choice = input("🔍 Run detailed individual environment tests? (y/n): ").lower().strip()
#     if choice == 'y':
#         individual_viz = test_individual_environments()
#         print("\n✅ Individual environment testing completed!")

#     print("\n🎯 All testing completed! Check generated PNG files for visualizations.")
