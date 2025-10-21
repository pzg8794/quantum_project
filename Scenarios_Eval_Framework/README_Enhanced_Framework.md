# Enhanced Quantum Routing Framework: Stochastic vs Adversarial Analysis

## Overview
This enhanced framework provides clear distinction between **Stochastic** (natural failures) and **Adversarial** (strategic attacks) scenarios for quantum routing algorithm evaluation.

## Key Files

### Core Framework
- `quantum_experiments_updated.py` - Enhanced experiment runner with clear attack categorization
- `quantum_framework_updated.py` - Multi-run evaluator with Stochastic vs Adversarial comparison
- `quantum_visualizer_enhanced_v2.py` - Advanced visualization with robustness analysis

### Testing
- `test_stochastic_vs_adversarial.py` - Main demonstration script

## Attack Categories

### Baseline
- `none`: No attacks (deterministic baseline)

### Stochastic (Natural Failures)  
- `stochastic`: Natural random failures/noise
- `random`: Alias for stochastic (backward compatibility)

### Adversarial (Strategic Attacks)
- `markov`: Structured adversarial with memory
- `adaptive`: Reactive adversarial learning from algorithm behavior  
- `onlineadaptive`: Real-time adaptive adversarial

## Usage

### Quick Stochastic vs Adversarial Test
```python
python test_stochastic_vs_adversarial.py
```

### Programmatic Usage
```python
from quantum_visualizer_enhanced_v2 import test_stochastic_vs_adversarial_visualization

# Run main comparison test
viz, evaluator, results = test_stochastic_vs_adversarial_visualization()
```

### Individual Environment Testing
```python  
from quantum_framework_updated import test_individual_environment

# Test specific environment
evaluator = test_individual_environment(attack_type="stochastic")
```

## Research Benefits

1. **Clear Categorization**: Explicit distinction between natural and strategic failures
2. **Robustness Metrics**: Quantified performance loss under adversarial attacks  
3. **Comprehensive Analysis**: Cross-environment comparison with statistical validation
4. **Academic Rigor**: Publication-ready visualizations and analysis

## Generated Outputs

- `stochastic_vs_adversarial_comparison.png` - Main comparison visualization
- `comprehensive_environment_comparison.png` - Multi-environment analysis
- Numerical analysis and robustness metrics

## Key Research Insights

- **EXPNeuralUCB** demonstrates superior adversarial robustness
- **Quantified robustness loss** provides clear performance metrics
- **Category-based analysis** validates theoretical predictions
- **Comprehensive evaluation** supports academic claims
