# ===== Multi-run evaluator for the new stack =====
import time
import threading
import matplotlib.pyplot as plt
from quantum_experiments import QuantumExperimentRunner as ExperimentRunner


class MultiRunEvaluator:
    """
    ENHANCED: Evaluator with proper Oracle-relative gap analysis
    Works with QuantumExperimentRunner + AdversarialQuantumEnvironment
    Features: Correct performance analysis, clean output, gap tracking
    """

    def __init__(
        self,
        base_seed=12345,
        base_frames=4000,
        frame_step=2000,
        attack_type="markov",        # 'none' | 'random' | 'markov' | 'adaptive'
        attack_intensity=1.0,
        enable_progress=False,
    ):
        self.env_experiments = {}
        self.base_seed = base_seed
        self.base_frames = base_frames
        self.frame_step = frame_step
        self.attack_type = attack_type
        self.attack_intensity = attack_intensity
        self.enable_progress = enable_progress

        self.env_experiments[self.attack_type] = {}   # exp_id -> {"results": dict, "frame_count": int, "gaps": dict}
        self.all_results = []   # flat list of dicts (exp_id, frame_count, algorithm, final_reward)
        self.start_time = None
        self.total_time = 0

        # NEW: Gap analysis tracking
        self.gap_analysis = {}  # algorithm -> [gap1, gap2, gap3, ...]

        # Beautiful initialization output
        self._print_initialization_banner()

    def _print_initialization_banner(self):
        """Clean initialization banner"""
        print("\n" + "=" * 50)
        print("QUANTUM MULTIRUN EVALUATOR INITIALIZED")
        print("=" * 50)
        print(f"Configuration:")
        print(f"   - Base frames:     {self.base_frames:,}")
        print(f"   - Frame step:      {self.frame_step:,}")
        print(f"   - Base seed:       {self.base_seed}")
        print(f"   - Attack strategy: {self.attack_type.upper()}")
        print(f"   - Attack intensity: {self.attack_intensity:.1f}")
        print(f"   - Progress bars:   {'Enabled' if self.enable_progress else 'Disabled'}")
        print(f"   - Analysis method: Oracle-relative gap analysis")
        print("=" * 50 + "\n")

    def _calculate_oracle_gaps(self, results):
        """NEW: Calculate Oracle-relative performance gaps"""
        oracle_score = results.get("Oracle", {}).get("final_reward", 1.0)
        gaps = {}
        
        algorithms = ["EXPNeuralUCB", "GNeuralUCB", "EXPUCB"]
        for alg in algorithms:
            alg_score = results.get(alg, {}).get("final_reward", 0.0)
            # Gap formula: (Oracle - Algorithm) / Oracle
            gap_percent = ((oracle_score - alg_score) / oracle_score * 100) if oracle_score > 0 else 100.0
            gaps[alg] = gap_percent
        
        return gaps

    def _find_experiment_winner(self, results):
        """NEW: Properly identify winner among learning algorithms"""
        learning_algs = ["EXPNeuralUCB", "GNeuralUCB", "EXPUCB"]
        scores = [(alg, results.get(alg, {}).get("final_reward", 0.0)) for alg in learning_algs]
        winner_name, winner_score = max(scores, key=lambda x: x[1])
        return winner_name

    def run_env_threaded_experiment(self, frame_count, exp_id, attack_type=None):
        """ENHANCED: Run experiment with gap analysis"""
        exp_start = time.time()
        if attack_type is not None: self.attack_type = attack_type
        
        # Clean experiment header
        print(f"\n" + "=" * 40)
        print(f"EXPERIMENT {exp_id}")
        print(f"=" * 40)
        print(f"Frame Count: {frame_count:,}")
        print(f"Attack: {self.attack_type} (intensity={self.attack_intensity:.1f})")
        print("-" * 40)

        # Fresh runner per experiment
        runner = ExperimentRunner(
            base_seed=self.base_seed,
            attack_type=self.attack_type,
            attack_intensity=self.attack_intensity,
            enable_progress=self.enable_progress,
        )

        # Thread target function
        def _target():
            runner.run_single_experiment(frame_count, exp_id)

        # Run experiment
        t = threading.Thread(target=_target, name=f"EvaluatorExp_{exp_id}")
        t.start()
        t.join()

        # Pull results from the runner
        results = runner.get_results().copy()
        exp_time = time.time() - exp_start
        
        # NEW: Calculate gaps and winner
        gaps = self._calculate_oracle_gaps(results)
        winner = self._find_experiment_winner(results)
        
        # Store experiment data with gap analysis
        self.env_experiments[self.attack_type].update({exp_id:{
            "results": results, 
            "frame_count": frame_count, 
            "id": exp_id,
            "execution_time": exp_time,
            "gaps": gaps,
            "winner": winner,
            "attack_type": self.attack_type
        }})

        # NEW: Track gaps for trend analysis
        for alg, gap in gaps.items():
            if alg not in self.gap_analysis:
                self.gap_analysis[alg] = []
            self.gap_analysis[alg].append(gap)

        # Flatten into a tidy list for analysis
        for alg, payload in results.items():
            self.all_results.append({
                "exp_id": exp_id,
                "frame_count": frame_count,
                "algorithm": alg,
                "final_reward": float(payload.get("final_reward", 0.0)),
            })

        # Clean experiment completion output
        self._print_experiment_completion(exp_id, results, gaps, winner, exp_time)

        # Cleanup runner resources
        runner.full_experiment_cleanup()

    def _print_experiment_completion(self, exp_id, results, gaps, winner, exp_time):
        """ENHANCED: Clean completion summary with correct winner and gaps"""
        print(f"\nEXPERIMENT {exp_id} COMPLETED")
        print(f"Execution Time: {exp_time:.1f}s")
        print("Results:")
        
        # Get key results
        oracle = results.get("Oracle", {}).get("final_reward", 0.0)
        expnu = results.get("EXPNeuralUCB", {}).get("final_reward", 0.0)
        gneu = results.get("GNeuralUCB", {}).get("final_reward", 0.0)
        expucb = results.get("EXPUCB", {}).get("final_reward", 0.0)
        
        # Display with correct winner and gaps
        print(f"   Oracle:       {oracle:8.2f} (theoretical maximum)")
        
        winner_mark_exp = " [WINNER]" if winner == "EXPNeuralUCB" else ""
        print(f"   EXPNeuralUCB: {expnu:8.2f} ({gaps['EXPNeuralUCB']:5.1f}% gap){winner_mark_exp}")
        
        winner_mark_gneu = " [WINNER]" if winner == "GNeuralUCB" else ""
        print(f"   GNeuralUCB:   {gneu:8.2f} ({gaps['GNeuralUCB']:5.1f}% gap){winner_mark_gneu}")
        
        winner_mark_exp3 = " [WINNER]" if winner == "EXPUCB" else ""
        print(f"   EXPUCB:       {expucb:8.2f} ({gaps['EXPUCB']:5.1f}% gap){winner_mark_exp3}")
        
        print(f"   Winner: {winner}")
        print("-" * 40)

    def run_experiments(self, num_experiments=3, attack_type="markov"):
        """ENHANCED: Run multiple experiments with gap tracking"""
        self.start_time = time.time()
        
        # Clean evaluation start banner
        print("\n" + "=" * 50)
        print("STARTING QUANTUM MULTIRUN EVALUATION")
        print("=" * 50)
        print(f"Planning {num_experiments} experiments")
        
        # Show planned frame counts
        planned_frames = [self.base_frames + (i * self.frame_step) for i in range(num_experiments)]
        print(f"Frame counts: {', '.join(f'{fc:,}' for fc in planned_frames)}")
        print("=" * 50 + "\n")

        # Run experiments
        for i in range(num_experiments):
            exp_id = i + 1
            frame_count = self.base_frames + (i * self.frame_step)
            
            print(f"\nPROGRESS: Experiment {exp_id}/{num_experiments}")
            self.run_env_threaded_experiment(frame_count, exp_id, attack_type)

        self.total_time = time.time() - self.start_time

        # Clean completion summary
        self._print_evaluation_completion(num_experiments)
        self.print_summary()
        self.plot_rewards()

    def _print_evaluation_completion(self, num_experiments):
        """Clean evaluation completion banner"""
        print("\n" + "=" * 50)
        print("QUANTUM EVALUATION COMPLETED!")
        print("=" * 50)
        print(f"Total experiments: {num_experiments}")
        print(f"Total time: {self.total_time:.1f}s")
        print(f"Average time per experiment: {self.total_time/num_experiments:.1f}s")
        print("=" * 50)

    def _calculate_gap_trends(self):
        """NEW: Calculate gap improvement/decline trends"""
        trends = {}
        for alg, gaps in self.gap_analysis.items():
            if len(gaps) >= 2:
                # Gap trend: negative = improvement (gap closing), positive = decline (gap widening)
                initial_gap = gaps[0]
                final_gap = gaps[-1]
                trend = final_gap - initial_gap  # Positive = gap widening, Negative = gap closing
                trends[alg] = {
                    'initial_gap': initial_gap,
                    'final_gap': final_gap,
                    'gap_change': trend,
                    'improvement': -trend  # Convert to improvement metric (positive = better)
                }
        return trends

    def print_summary(self):
        """ENHANCED: Summary with proper Oracle-relative gap analysis"""
        print("\n" + "=" * 60)
        print("           DETAILED EXPERIMENT ANALYSIS")
        print("=" * 60)
        
        # Attack strategy info
        print(f"\nAttack Configuration:")
        print(f"   Strategy: {self.attack_type.upper()}")
        print(f"   Intensity: {self.attack_intensity:.1f}")
        
        # Per-experiment detailed results
        print(f"\nPer-Experiment Results:")
        print("-" * 80)
        
        for exp_id, record in self.env_experiments[self.attack_type].items():
            fc = record["frame_count"]
            res = record["results"]
            gaps = record["gaps"]
            winner = record["winner"]
            exec_time = record.get("execution_time", 0)

            oracle = res.get("Oracle", {}).get("final_reward", 0.0)
            expnu = res.get("EXPNeuralUCB", {}).get("final_reward", 0.0)
            gneu = res.get("GNeuralUCB", {}).get("final_reward", 0.0)
            expucb = res.get("EXPUCB", {}).get("final_reward", 0.0)
            
            print(f"\nEXPERIMENT {exp_id} ({fc:,} frames, {exec_time:.1f}s)")
            print(f"   |")
            print(f"   +-- Oracle:       {oracle:8.2f} (theoretical maximum)")
            print(f"   +-- EXPNeuralUCB: {expnu:8.2f} ({gaps['EXPNeuralUCB']:5.1f}% gap)")
            print(f"   +-- GNeuralUCB:   {gneu:8.2f} ({gaps['GNeuralUCB']:5.1f}% gap)")
            print(f"   +-- EXPUCB:       {expucb:8.2f} ({gaps['EXPUCB']:5.1f}% gap)")
            print(f"   Winner: {winner}")

        # NEW: Proper gap trend analysis
        self._print_gap_analysis()

    def _print_gap_analysis(self):
        """NEW: Proper Oracle-relative gap trend analysis"""
        print(f"\nORACLE-RELATIVE GAP ANALYSIS:")
        print("-" * 60)
        
        trends = self._calculate_gap_trends()
        
        # Sort by improvement (gap reduction)
        sorted_trends = sorted(trends.items(), key=lambda x: x[1]['improvement'], reverse=True)
        
        print(f"\nLEARNING PERFORMANCE (Gap Reduction to Oracle):")
        for rank, (alg, data) in enumerate(sorted_trends, 1):
            initial = data['initial_gap']
            final = data['final_gap'] 
            improvement = data['improvement']
            
            if improvement > 0:
                trend_desc = f"{improvement:+.1f}pp improvement (gap closing)"
            else:
                trend_desc = f"{abs(improvement):+.1f}pp decline (gap widening)"
            
            rank_marker = f"#{rank}"
            print(f"   {rank_marker}: {alg:<12} -> {trend_desc}")
            print(f"        Gap: {initial:.1f}% -> {final:.1f}%")
        
        print(f"\nInterpretation:")
        print(f"   - Lower gaps = Better performance relative to Oracle")
        print(f"   - Gap reduction = Algorithm learning and improving")  
        print(f"   - Best learner closes the gap to Oracle over time")
        print("-" * 60)

    def get_algorithm_data(self, algorithm_name):
        """Return list of (frame_count, final_reward) for a given algorithm, sorted by frames."""
        pairs = [
            (r["frame_count"], r["final_reward"])
            for r in self.all_results
            if r["algorithm"] == algorithm_name
        ]
        return sorted(pairs, key=lambda x: x[0])

    def get_gap_data(self, algorithm_name):
        """NEW: Get gap trend data for plotting"""
        gaps = self.gap_analysis.get(algorithm_name, [])
        frame_counts = [self.base_frames + (i * self.frame_step) for i in range(len(gaps))]
        return list(zip(frame_counts, gaps))

    def plot_rewards(self, algorithms=("EXPNeuralUCB", "GNeuralUCB", "EXPUCB")):
        """ENHANCED: Clean dual plotting - rewards and gaps"""
        print("\nGenerating performance visualization...")
        
        # Create subplot layout
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Colors for consistency
        colors = {'EXPNeuralUCB': '#e74c3c', 'GNeuralUCB': '#3498db', 'EXPUCB': '#2ecc71'}
        
        # Plot 1: Reward Performance
        for alg in algorithms:
            data = self.get_algorithm_data(alg)
            if not data:
                continue
            xs, ys = zip(*data)
            color = colors.get(alg, '#f39c12')
            ax1.plot(xs, ys, marker="o", linewidth=3, markersize=8, 
                    color=color, label=alg)
        
        # Oracle reference line
        oracle = self.get_algorithm_data("Oracle")
        if oracle:
            xs, ys = zip(*oracle)
            ax1.plot(xs, ys, linestyle="--", marker="x", linewidth=2, 
                    markersize=10, color='black', label="Oracle (Theoretical Max)")
        
        ax1.set_xlabel("Frame Count", fontsize=12, fontweight='bold')
        ax1.set_ylabel("Final Reward", fontsize=12, fontweight='bold')
        ax1.set_title(f"Algorithm Performance - {self.attack_type.upper()} Attack", fontsize=14, fontweight='bold')
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Gap Analysis
        for alg in algorithms:
            gap_data = self.get_gap_data(alg)
            if not gap_data:
                continue
            xs, gaps = zip(*gap_data)
            color = colors.get(alg, '#f39c12')
            ax2.plot(xs, gaps, marker="s", linewidth=3, markersize=8, 
                    color=color, label=f"{alg} Gap", linestyle=':')
        
        ax2.set_xlabel("Frame Count", fontsize=12, fontweight='bold')
        ax2.set_ylabel("Oracle Gap (%)", fontsize=12, fontweight='bold')
        ax2.set_title("Learning Analysis: Oracle-Relative Gap Reduction", fontsize=14, fontweight='bold')
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.invert_yaxis()  # Lower gaps at top (better performance)
        
        # Format axes
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        plt.tight_layout()
        plt.show()
        
        print("Visualization complete!")


# ===== USAGE EXAMPLES =====

def run_evaluation(attack_type="markov", frames=2000, step=1000, best_seed=12345, attack_intensity=1.0, enable_progress=False):
    """ENHANCED: Run evaluation with proper gap analysis"""
    evaluator = MultiRunEvaluator(
        base_seed=best_seed,
        base_frames=frames,
        frame_step=step,
        attack_type=attack_type,
        attack_intensity=attack_intensity,
        enable_progress=enable_progress
    )
    
    evaluator.run_experiments(num_experiments=3, attack_type=attack_type)
    return evaluator

def compare_attack_strategies():
    """NEW: Compare different attack strategies"""
    strategies = ['none', 'random', 'markov', 'adaptive']
    results = {}
    
    for strategy in strategies:
        print(f"\n{'='*60}")
        print(f"TESTING {strategy.upper()} ATTACK STRATEGY")
        print(f"{'='*60}")
        results[strategy] = run_evaluation(attack_type=strategy, frames=2000, step=1000)
    
    return results

# Ready to run:
# evaluator = run_evaluation("markov")
# all_results = compare_attack_strategies()
