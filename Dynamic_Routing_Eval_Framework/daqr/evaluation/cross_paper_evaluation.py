# ============================================================================
# CROSS-PAPER EVALUATION EXTENSION
# ============================================================================
# Add these methods to MultiRunEvaluator class to enable paper comparisons
# ============================================================================

def add_to_MultiRunEvaluator():
    """
    These methods should be added to the MultiRunEvaluator class
    """
    
    # METHOD 1: Paper-Specific Configuration
    @staticmethod
    def get_paper_config(paper_num: int) -> dict:
        """
        Get standardized test configuration for each paper
        
        Usage:
            config = MultiRunEvaluator.get_paper_config(2)
            evaluator = MultiRunEvaluator(**config)
        """
        paper_configs = {
            2: {  # Chaudhary et al. (2023)
                'name': 'Paper2_UCBRouteSelection',
                'algorithms': ['Paper2UCBBandit', 'GNeuralUCB', 'EXPNeuralUCB'],
                'n_arms': 8,
                'n_nodes': 15,
                'frame_range': (400, 1400, 200),  # 400->1400 by 200 steps
                'experiments': 600,
                'noise_params': {
                    'p_bsm': 0.2,
                    'p_gate_errors': 0.2,
                    'fiber_attenuation': 0.05,
                    'decoherence_rate': 0.25
                },
                'test_scenarios': {
                    'synchronized_swapping': {'synchronized_swapping': True},
                    'non_synchronized_swapping': {'synchronized_swapping': False},
                    'high_noise': {'p_bsm': 0.4, 'p_gate_errors': 0.4}
                }
            },
            
            7: {  # Liu et al. (2024)
                'name': 'Paper7_QuantumBGP',
                'algorithms': ['Paper7BGPBandit', 'GNeuralUCB', 'EXPNeuralUCB'],
                'n_paths': 15,
                'k': 5,
                'n_qisps': 3,
                'frame_range': (100, 1000, 100),
                'network_scales': ['small', 'medium', 'large'],
                'test_scenarios': {
                    'single_qisp': {'n_qisps': 1},
                    'multi_qisp_balanced': {'n_qisps': 3},
                    'multi_qisp_unbalanced': {'n_qisps': 5}
                }
            },
            
            5: {  # Wang et al. (2025)
                'name': 'Paper5_LearningBestPaths',
                'algorithms': ['Paper5FeedbackBandit', 'GNeuralUCB', 'EXPNeuralUCB'],
                'n_arms': 10,
                'frame_range': (100, 800, 100),
                'test_scenarios': {
                    'link_level': {'feedback_type': 'link'},
                    'path_level': {'feedback_type': 'path'},
                    'combined': {'feedback_type': 'combined'}
                }
            },
            
            8: {  # Jallow & Khan (2025)
                'name': 'Paper8_DQNRouting',
                'algorithms': ['Paper8DQNBandit', 'GNeuralUCB', 'EXPNeuralUCB'],
                'n_arms': 8,
                'frame_range': (100, 2000, 200),
                'test_scenarios': {
                    'low_learning_rate': {'learning_rate': 0.001},
                    'standard_learning_rate': {'learning_rate': 0.01},
                    'high_learning_rate': {'learning_rate': 0.1}
                }
            },
            
            12: {  # Wang et al. (2024)
                'name': 'Paper12_QuARCClustering',
                'algorithms': ['Paper12QuARCBandit', 'GNeuralUCB', 'EXPNeuralUCB'],
                'n_arms': 10,
                'n_clusters': 3,
                'frame_range': (100, 1000, 100),
                'test_scenarios': {
                    'few_clusters': {'n_clusters': 2},
                    'balanced_clusters': {'n_clusters': 3},
                    'many_clusters': {'n_clusters': 5}
                }
            }
        }
        
        if paper_num not in paper_configs:
            raise ValueError(f"Paper {paper_num} not configured. Available: {list(paper_configs.keys())}")
        
        return paper_configs[paper_num]
    
    
    # METHOD 2: Run Paper Testbed
    def run_paper_testbed(self, paper_num: int, scenario_name: str = 'default'):
        """
        Run full evaluation for a specific paper testbed
        
        Args:
            paper_num: Paper number (2, 5, 7, 8, 12)
            scenario_name: Specific scenario to run (from test_scenarios)
            
        Returns:
            results: Evaluation results with paper-specific metrics
        """
        config = self.get_paper_config(paper_num)
        logger.info(f"Starting Paper #{paper_num} Testbed: {config['name']}")
        
        # Get scenario parameters if specified
        scenario_params = {}
        if scenario_name != 'default' and 'test_scenarios' in config:
            if scenario_name in config['test_scenarios']:
                scenario_params = config['test_scenarios'][scenario_name]
        
        results = {}
        
        # Run for each algorithm in paper config
        for algo_name in config.get('algorithms', []):
            logger.info(f"  Running {algo_name}...")
            
            # Would integrate with existing framework
            # results[algo_name] = self.run_algorithm(algo_name, **scenario_params)
        
        return results
    
    
    # METHOD 3: Cross-Paper Comparison
    def compare_across_papers(self, 
                             paper_nums: List[int],
                             algorithms: List[str] = None) -> Dict[str, Any]:
        """
        Run cross-paper comparison of algorithms
        
        Args:
            paper_nums: List of paper numbers to compare
            algorithms: Algorithms to test on all papers
                       (None = use paper defaults)
                       
        Returns:
            comparison_results: Unified results across all papers
        """
        
        if algorithms is None:
            # Find common algorithms across papers
            all_algos = set()
            for pnum in paper_nums:
                config = self.get_paper_config(pnum)
                all_algos.update(config.get('algorithms', []))
            algorithms = list(all_algos & {'GNeuralUCB', 'EXPNeuralUCB'})
        
        comparison_results = {
            'summary': {},
            'by_paper': {},
            'cross_paper_ranking': None
        }
        
        logger.info(f"Cross-Paper Comparison: Papers {paper_nums}")
        logger.info(f"Testing algorithms: {algorithms}")
        
        # Run each paper
        for paper_num in paper_nums:
            logger.info(f"\n--- Paper #{paper_num} ---")
            config = self.get_paper_config(paper_num)
            
            paper_results = {}
            for algo in algorithms:
                if algo in config.get('algorithms', []):
                    # Run algorithm on this paper's testbed
                    # paper_results[algo] = self.run_paper_algorithm(paper_num, algo)
                    pass
            
            comparison_results['by_paper'][paper_num] = paper_results
        
        return comparison_results
    
    
    # METHOD 4: Generate Comparison Report
    def generate_paper_comparison_report(self, 
                                        results: Dict[str, Any],
                                        output_file: str = None) -> str:
        """
        Generate markdown report comparing performance across papers
        
        Args:
            results: Results from compare_across_papers()
            output_file: Optional file to save report
            
        Returns:
            report_text: Formatted comparison report
        """
        
        report_lines = [
            "# Cross-Paper Testbed Comparison",
            "",
            "## Summary",
            "",
        ]
        
        # Build comparison table
        report_lines.extend([
            "| Paper | Algorithm | Metric | [Our Model] | [Paper Baseline] | Gap |",
            "|-------|-----------|--------|-------------|------------------|-----|",
        ])
        
        # Would populate with actual results
        
        report_text = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            logger.info(f"Report saved to {output_file}")
        
        return report_text
    
    
    # METHOD 5: Standardized Metrics Extraction
    def extract_paper_metrics(self, 
                             results: Dict[str, Any],
                             paper_num: int,
                             algorithm: str) -> Dict[str, float]:
        """
        Extract paper-specific metrics for standardized comparison
        
        Args:
            results: Raw evaluation results
            paper_num: Paper number
            algorithm: Algorithm name
            
        Returns:
            metrics: Standardized metrics dict
        """
        
        metrics = {}
        
        if paper_num == 2:
            # Paper2 metrics: convergence, noise robustness
            metrics = {
                'convergence_step': results.get('convergence_step'),
                'best_arm_reward': results.get('best_arm_reward'),
                'exploration_efficiency': results.get('exploration_efficiency'),
                'synchronized_swapping_gain': results.get('synchronized_gain', 0),
            }
        
        elif paper_num == 7:
            # Paper7 metrics: top-K accuracy, resource efficiency
            metrics = {
                'topk_accuracy': results.get('topk_accuracy'),
                'entanglement_consumed': results.get('total_entanglement_consumed'),
                'inter_domain_efficiency': results.get('inter_domain_load_balance'),
                'scalability_score': results.get('network_scale'),
            }
        
        elif paper_num == 5:
            # Paper5 metrics: feedback granularity impact
            metrics = {
                'link_feedback_efficiency': results.get('link_updates'),
                'path_feedback_efficiency': results.get('path_updates'),
                'feedback_granularity_gain': results.get('feedback_gain'),
            }
        
        elif paper_num == 8:
            # Paper8 metrics: Q-value convergence
            metrics = {
                'q_value_convergence_step': results.get('q_convergence'),
                'q_value_stability': results.get('q_stability'),
                'learning_efficiency': results.get('learning_efficiency'),
            }
        
        elif paper_num == 12:
            # Paper12 metrics: clustering efficiency, starvation prevention
            metrics = {
                'cluster_balance': results.get('cluster_reward_balance'),
                'starvation_events': results.get('starvation_events'),
                'multi_path_efficiency': results.get('multi_path_efficiency'),
            }
        
        return metrics


# ============================================================================
# CONFIGURATION EXTENSION for experiment_config.py
# ============================================================================

def add_paper_configs_to_ExperimentConfig():
    """
    Add these Paper Config classes to experiment_config.py
    """
    
    class Paper2Config:
        """Configuration for Paper #2 testbed"""
        NAME = "Chaudhary_et_al_2023_UCB_Route_Selection"
        N_NODES = 15
        N_ARMS = 8
        FRAME_RANGE = (400, 1400, 200)
        EXPERIMENTS = 600
        NOISE_PARAMS = {
            'p_bsm': 0.2,
            'p_gate_errors': 0.2,
            'fiber_attenuation': 0.05,
            'decoherence_rate': 0.25
        }
        METRICS = ['convergence_step', 'best_arm_reward', 'exploration_efficiency']
    
    
    class Paper7Config:
        """Configuration for Paper #7 testbed"""
        NAME = "Liu_et_al_2024_Quantum_BGP"
        N_PATHS = 15
        K = 5
        N_QISPS = 3
        FRAME_RANGE = (100, 1000, 100)
        NETWORK_SCALES = ['small', 'medium', 'large']
        METRICS = ['topk_accuracy', 'entanglement_consumed', 'inter_domain_efficiency']
    
    
    class Paper5Config:
        """Configuration for Paper #5 testbed"""
        NAME = "Wang_et_al_2025_Learning_Best_Paths"
        N_ARMS = 10
        FRAME_RANGE = (100, 800, 100)
        FEEDBACK_TYPES = ['link', 'path', 'combined']
        METRICS = ['link_feedback_efficiency', 'path_feedback_efficiency']
    
    
    class Paper8Config:
        """Configuration for Paper #8 testbed"""
        NAME = "Jallow_Khan_2025_DQN_Routing"
        N_ARMS = 8
        FRAME_RANGE = (100, 2000, 200)
        LEARNING_RATES = [0.001, 0.01, 0.1]
        METRICS = ['q_convergence_step', 'q_stability']
    
    
    class Paper12Config:
        """Configuration for Paper #12 testbed"""
        NAME = "Wang_et_al_2024_QuARC_Clustering"
        N_ARMS = 10
        FRAME_RANGE = (100, 1000, 100)
        N_CLUSTERS = [2, 3, 5]
        METRICS = ['cluster_balance', 'starvation_events']
