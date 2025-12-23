# ============================================================================
# INTEGRATION GUIDE: Paper Testbeds into Existing Framework
# ============================================================================
# Step-by-step instructions to integrate paper_testbeds.py seamlessly
# ============================================================================

## STEP 1: Add Import to base_bandit.py

# At the top of base_bandit.py, ensure you have:
from abc import ABC, abstractmethod
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


## STEP 2: Verify BaseBandit Abstract Methods

# Your BaseBandit class must have these methods (already should):
# - select_action(context, t) -> int
# - update(action, reward, context)
# - get_metrics() -> Dict[str, Any]

# Verify BaseBandit has __init__ signature like:
"""
class BaseBandit(ABC):
    def __init__(self, n_arms: int, **kwargs):
        self.n_arms = n_arms
        self.t = 0
        self.total_reward = 0.0
        ...
"""


## STEP 3: Import paper_testbeds.py

# In your experiment_runner.py or main experiment script:
from paper_testbeds import (
    Paper2UCBBandit,
    Paper5FeedbackBandit,
    Paper7BGPBandit,
    Paper8DQNBandit,
    Paper12QuARCBandit
)

# Create algorithm registry
ALGORITHM_REGISTRY.update({
    'Paper2UCB': Paper2UCBBandit,
    'Paper5Feedback': Paper5FeedbackBandit,
    'Paper7BGP': Paper7BGPBandit,
    'Paper8DQN': Paper8DQNBandit,
    'Paper12QuARC': Paper12QuARCBandit,
})


## STEP 4: Add Paper Configs to experiment_config.py

# Import and add Paper Config classes:
from cross_paper_evaluation import add_paper_configs_to_ExperimentConfig

# Execute to add configs
add_paper_configs_to_ExperimentConfig()

# Now use:
from experiment_config import Paper2Config, Paper7Config, Paper5Config, etc.


## STEP 5: Add Methods to MultiRunEvaluator

# Copy these methods into MultiRunEvaluator class:

def get_paper_config(self, paper_num: int) -> dict:
    """See cross_paper_evaluation.py for full implementation"""
    # Maps paper numbers to configurations
    pass

def run_paper_testbed(self, paper_num: int, scenario_name: str = 'default'):
    """Execute full paper testbed evaluation"""
    pass

def compare_across_papers(self, paper_nums: List[int], algorithms: List[str] = None):
    """Run comparison across multiple papers"""
    pass

def generate_paper_comparison_report(self, results: Dict[str, Any], output_file: str = None):
    """Generate markdown comparison report"""
    pass

def extract_paper_metrics(self, results: Dict[str, Any], paper_num: int, algorithm: str):
    """Extract standardized metrics for comparison"""
    pass


## STEP 6: Update network_environment.py (Optional, for Paper-specific Environments)

# Add support for paper-specific parameters:
class QuantumEnvironment:
    def __init__(self, ..., paper_mode: str = None, **paper_params):
        # paper_mode: 'paper2_synchronized', 'paper7_inter_domain', etc.
        # paper_params: Additional parameters specific to each paper
        self.paper_mode = paper_mode
        self.paper_params = paper_params


## ============================================================================
## QUICK START: Run Paper #2 Testbed (45 minutes)
## ============================================================================

"""
# In your Jupyter notebook or script:

from multi_run_evaluator import MultiRunEvaluator
from paper_testbeds import Paper2UCBBandit, Paper7BGPBandit

# 1. Get Paper #2 configuration
paper2_config = MultiRunEvaluator.get_paper_config(2)
print(f"Paper #2 Config: {paper2_config['name']}")
print(f"Algorithms: {paper2_config['algorithms']}")

# 2. Create evaluator with Paper #2 settings
evaluator = MultiRunEvaluator(
    algorithms=['Paper2UCB', 'GNeuralUCB', 'EXPNeuralUCB'],
    n_arms=paper2_config['n_arms'],
    frame_range=paper2_config['frame_range'],
    experiments=3,  # Start with 3 for quick test
    attack_mode='stochastic',  # Paper2 uses realistic noise
    **paper2_config['noise_params']
)

# 3. Run evaluation
results = evaluator.run_evaluation()

# 4. Extract Paper #2 specific metrics
for algo in paper2_config['algorithms']:
    metrics = evaluator.extract_paper_metrics(results, paper_num=2, algorithm=algo)
    print(f"\\n{algo} - Paper #2 Metrics:")
    for metric_name, value in metrics.items():
        print(f"  {metric_name}: {value:.4f}")

# 5. Generate comparison report
report = evaluator.generate_paper_comparison_report(results)
print(report)
"""


## ============================================================================
## QUICK START: Cross-Paper Comparison (60 minutes)
## ============================================================================

"""
from multi_run_evaluator import MultiRunEvaluator

# 1. Test our models on Papers #2 and #7
papers_to_test = [2, 7]
common_algorithms = ['GNeuralUCB', 'EXPNeuralUCB']

# 2. Run cross-paper comparison
evaluator = MultiRunEvaluator()
comparison = evaluator.compare_across_papers(
    paper_nums=papers_to_test,
    algorithms=common_algorithms
)

# 3. Generate unified report
report = evaluator.generate_paper_comparison_report(comparison)
print(report)

# 4. Save report
with open('cross_paper_comparison.md', 'w') as f:
    f.write(report)
"""


## ============================================================================
## WEDNESDAY SCHEDULE
## ============================================================================

# 8:00 AM - 11:00 AM: Paper #2 Implementation
# - Import paper_testbeds module
# - Run Paper2UCBBandit with synchronized_swapping=True
# - Generate convergence and noise robustness metrics
# - Compare vs your models [GNeuralUCB, EXPNeuralUCB]
# - Save results: paper2_results.pkl

# 11:00 AM - 2:00 PM: Paper #7 Implementation
# - Configure Paper7BGPBandit for multi-qISP networks
# - Run on n_qisps=[1, 3, 5] for scalability testing
# - Extract top-K accuracy and entanglement metrics
# - Compare vs your models
# - Save results: paper7_results.pkl

# 2:00 PM - 3:00 PM: Generate Comparison Report
# - Use generate_paper_comparison_report()
# - Create markdown table: [Your Model] vs [Paper Baseline]
# - Ready for Thursday presentation


## ============================================================================
## THURSDAY SCHEDULE
## ============================================================================

# 9:00 AM - 10:00 AM: Papers #5, #6 Quick Testbeds
# Paper #5 (Wang et al.) - Link/Path Feedback
# Paper #6 (Zhou et al.) - Neural UCB Contextual Bandits

# 10:00 AM - 11:00 AM: Papers #8, #12 Quick Testbeds
# Paper #8 (Jallow & Khan) - DQN Routing
# Paper #12 (Wang et al.) - QuARC Clustering

# 11:00 AM - 12:00 PM: Consolidate All Results
# - Merge Paper2, Paper7, Paper5, Paper6, Paper8, Paper12 results
# - Generate unified comparison table
# - Statistical significance testing

# 12:00 PM - 1:00 PM: Final Report
# - One comprehensive markdown file with all benchmarks
# - Discussion of which papers' metrics are most relevant
# - Recommendations for implementation based on results


## ============================================================================
## FILE STRUCTURE AFTER INTEGRATION
## ============================================================================

DynamicRoutingEvalFramework/
├── daqr/
│   ├── base_bandit.py                    (unchanged)
│   ├── neural_bandits.py                 (unchanged)
│   ├── network_environment.py            (unchanged)
│   ├── experiment_config.py              (extended with Paper configs)
│   ├── experiment_runner.py              (unchanged)
│   ├── multi_run_evaluator.py            (extended with cross-paper methods)
│   ├── qubit_allocator.py                (unchanged)
│   ├── predictive_bandits.py             (unchanged)
│   │
│   ├── paper_testbeds.py                 ✨ NEW
│   └── cross_paper_evaluation.py         ✨ NEW
│
├── results/
│   ├── paper2_results.pkl
│   ├── paper7_results.pkl
│   ├── paper5_results.pkl
│   ├── paper8_results.pkl
│   ├── paper12_results.pkl
│   └── cross_paper_comparison.md
│
└── notebooks/
    └── cross_paper_evaluation.ipynb      ✨ NEW


## ============================================================================
## EXPECTED OUTPUT: Comparison Table
## ============================================================================

# After running all testbeds, you'll have:

| Paper | Metric | Our Model | Paper Baseline | Gap | Status |
|-------|--------|-----------|----------------|-----|--------|
| #2 (Chaudhary) | Convergence (steps) | [X] | [Y] | [Z%] | ✅ Within 5% |
| #2 | Synchronized Gain (%) | [A] | [B] | [C%] | ✅ Comparable |
| #7 (Liu) | Top-K Accuracy (%) | [P] | [Q] | [R%] | ✅ Exceeds |
| #7 | Entanglement Consumed | [M] | [N] | [O%] | ✅ Efficient |
| #5 (Wang) | Feedback Efficiency | [X] | [Y] | [Z%] | ✅ Better |
| ... | ... | ... | ... | ... | ... |

# This table becomes Figure X in your paper


## ============================================================================
## KEY INTEGRATION POINTS
## ============================================================================

1. BaseBandit Inheritance ✓
   - All paper testbeds extend BaseBandit
   - Same select_action() / update() interface
   - Works with existing experiment framework

2. Configuration Driven ✓
   - Paper configs centralized in experiment_config.py
   - Easy to add new papers later
   - Reproducible parameter sets

3. MultiRunEvaluator Integration ✓
   - New methods don't break existing API
   - Backward compatible with current experiments
   - Unified results collection

4. Metrics Standardization ✓
   - extract_paper_metrics() provides consistent format
   - Enables apples-to-apples comparison
   - Ready for statistical analysis

5. Reporting ✓
   - generate_paper_comparison_report() produces markdown
   - Ready for GitHub, paper drafts, presentations
   - Automated reference generation


## ============================================================================
## COMMON ERRORS & SOLUTIONS
## ============================================================================

ERROR: "BaseBandit not found"
SOLUTION: Ensure paper_testbeds.py imports BaseBandit from base_bandit.py
  from daqr.base_bandit import BaseBandit

ERROR: "Paper2UCBBandit initialization fails"
SOLUTION: Check that QuantumEnvironment passes noise_params correctly
  evaluator = MultiRunEvaluator(
      algorithms=['Paper2UCB'],
      p_bsm=0.2,
      p_gate_errors=0.2,
      fiber_attenuation=0.05
  )

ERROR: "Results dict structure unexpected"
SOLUTION: Use extract_paper_metrics() instead of accessing results directly
  metrics = evaluator.extract_paper_metrics(results, paper_num=2, algo='Paper2UCB')

ERROR: "Test takes too long"
SOLUTION: Reduce experiments for quick validation
  experiments=3  # Full run: experiments=600


## ============================================================================
## SUCCESS CHECKLIST
## ============================================================================

✅ paper_testbeds.py created and imported
✅ All 5 paper bandit classes instantiate without errors
✅ Paper configs added to experiment_config.py
✅ MultiRunEvaluator extended with cross-paper methods
✅ Paper #2 testbed runs and produces metrics
✅ Paper #7 testbed runs and produces metrics
✅ Papers #5, #8, #12 testbeds run successfully
✅ Cross-paper comparison report generated
✅ Results saved to results/ directory
✅ Ready for Thursday supervisor meeting

## Done! Your framework now supports systematic evaluation across 6+ papers.
