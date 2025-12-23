# ============================================================================
# QUANTUM ROUTING PAPER - FIGURE DATA EXTRACTION & GENERATION
# ============================================================================
# This script extracts data from Master_Dataset_*.csv files and generates
# pgfplots-compatible LaTeX code with REAL numbers from your experiments
# ============================================================================

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class QuantumFigureGenerator:
    """Generate publication-ready figures from Master Datasets"""
    
    def __init__(self, dataset_paths):
        """Load all datasets"""
        self.datasets = {}
        self.combined_df = None
        
        for name, path in dataset_paths.items():
            try:
                df = pd.read_csv(path)
                self.datasets[name] = df
                print(f"✓ Loaded {name}: {df.shape[0]} rows")
            except Exception as e:
                print(f"✗ Failed to load {name}: {e}")
        
        # Combine all datasets
        if self.datasets:
            self.combined_df = pd.concat(self.datasets.values(), ignore_index=True)
            print(f"\n✓ Combined dataset: {self.combined_df.shape[0]} rows, {self.combined_df.shape[1]} cols")
    
    # ========== FIGURE 1: Context-Aware vs Non-Context ==========
    def fig1_context_aware(self):
        """Context-aware models (CPursuit, iCPursuit) vs Non-context (GNeural, EXPNeural)"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        # Map models to context/non-context
        context_models = {'CPURSUITNEURALUCB', 'ICPURSUITNEURALUCB', 'CPURSUIT', 'ICPURSUIT'}
        non_context = {'GNEURALUCB', 'EXPNEURALUCB', 'LINEARUCB', 'EXPUCB'}
        
        results = {}
        for scenario in ['MARKOV', 'STOCHASTIC', 'ADAPTIVE']:
            scenario_data = df[df['scenario'] == scenario]
            
            for model_type, models in [('context', context_models), ('non_context', non_context)]:
                model_data = scenario_data[scenario_data['model'].isin(models)]
                if len(model_data) > 0:
                    avg_eff = model_data['eff_pct'].mean()
                    results[f"{scenario}_{model_type}"] = avg_eff
        
        return results
    
    # ========== FIGURE 2: Capacity Paradox ==========
    def fig2_capacity_paradox(self):
        """Efficiency change from Tb (baseline) to 2T (double)"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        results = {}
        for scenario in ['STOCHASTIC', 'MARKOV', 'ADAPTIVE', 'ONLINEADAPTIVE', 'BASELINE']:
            scenario_data = df[df['scenario'] == scenario]
            
            tb_eff = scenario_data[scenario_data['cap_type'] == 'Tb']['eff_pct'].mean()
            t_eff = scenario_data[scenario_data['cap_type'] == 'T']['eff_pct'].mean()
            
            change = t_eff - tb_eff
            results[scenario] = change
        
        return results
    
    # ========== FIGURE 3: Algorithm-Allocator Co-Design ==========
    def fig3_allocator_codesign(self):
        """Average efficiency by allocator for key algorithms"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        key_models = ['CPURSUITNEURALUCB', 'ICPURSUITNEURALUCB', 'EXPNEURALUCB']
        results = {}
        
        for model in key_models:
            model_data = df[df['model'] == model]
            allocator_effs = {}
            
            for allocator in ['Default', 'Dynamic', 'Random', 'Thompson']:
                alloc_data = model_data[model_data['allocator'] == allocator]
                if len(alloc_data) > 0:
                    allocator_effs[allocator] = alloc_data['eff_pct'].mean()
            
            results[model] = allocator_effs
        
        return results
    
    # ========== FIGURE 4: Robustness Frontier (Min/Mean/Max) ==========
    def fig4_robustness_frontier(self):
        """Floor, mean, peak efficiency by model"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        results = {}
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            if len(model_data) > 10:  # Only models with enough data
                results[model] = {
                    'floor': model_data['eff_pct'].min(),
                    'mean': model_data['eff_pct'].mean(),
                    'peak': model_data['eff_pct'].max()
                }
        
        return results
    
    # ========== FIGURE 5: Threat-Adaptive Allocator Rules ==========
    def fig5_threat_rules(self):
        """Best allocator efficiency by detected attack type"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        results = {}
        for scenario in ['STOCHASTIC', 'MARKOV', 'ADAPTIVE', 'ONLINEADAPTIVE']:
            scenario_data = df[df['scenario'] == scenario]
            allocator_means = {}
            
            for allocator in scenario_data['allocator'].unique():
                alloc_data = scenario_data[scenario_data['allocator'] == allocator]
                allocator_means[allocator] = alloc_data['eff_pct'].mean()
            
            # Pick top allocator
            best_allocator = max(allocator_means, key=allocator_means.get)
            results[scenario] = {
                'best': best_allocator,
                'efficiency': allocator_means[best_allocator]
            }
        
        return results
    
    # ========== FIGURE 6: Stability (Coefficient of Variation) ==========
    def fig6_stability(self):
        """CV = (std / mean) * 100 for each algorithm"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        results = {}
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            if len(model_data) > 10:
                mean_eff = model_data['eff_pct'].mean()
                std_eff = model_data['eff_pct'].std()
                cv = (std_eff / mean_eff * 100) if mean_eff > 0 else 0
                results[model] = cv
        
        return results
    
    # ========== FIGURE 7: Attack-Allocator Heatmap ==========
    def fig7_heatmap(self):
        """2D matrix: scenario × allocator"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        pivot = df.pivot_table(
            values='eff_pct',
            index='scenario',
            columns='allocator',
            aggfunc='mean'
        )
        
        return pivot
    
    # ========== FIGURE 14: Win Rate ==========
    def fig14_winrate(self):
        """Count of times each model was scenario_winner"""
        df = self.combined_df.copy()
        
        # Count wins
        win_counts = {}
        for model in df['model'].unique():
            wins = len(df[df['scenario_winner'] == model])
            if wins > 0:
                win_counts[model] = wins
        
        return win_counts
    
    # ========== FIGURE 16: Worst vs Best Case ==========
    def fig16_safety_margins(self):
        """Min and max efficiency by model"""
        df = self.combined_df[self.combined_df['model'] != 'ORACLE'].copy()
        
        results = {}
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            if len(model_data) > 10:
                results[model] = {
                    'worst': model_data['eff_pct'].min(),
                    'best': model_data['eff_pct'].max()
                }
        
        return results
    
    # ========== Generate All Figures ==========
    def generate_all(self):
        """Extract data for all 16 figures"""
        print("\n" + "="*80)
        print("EXTRACTING DATA FOR ALL 16 FIGURES")
        print("="*80)
        
        all_data = {
            'fig1': self.fig1_context_aware(),
            'fig2': self.fig2_capacity_paradox(),
            'fig3': self.fig3_allocator_codesign(),
            'fig4': self.fig4_robustness_frontier(),
            'fig5': self.fig5_threat_rules(),
            'fig6': self.fig6_stability(),
            'fig7': self.fig7_heatmap(),
            'fig14': self.fig14_winrate(),
            'fig16': self.fig16_safety_margins()
        }
        
        return all_data


# ============================================================================
# USAGE
# ============================================================================

if __name__ == '__main__':
    # Define dataset paths
    datasets = {
        'iCMABs': 'Master_Dataset_iCMABs.csv',
        'CMABs': 'Master_Dataset_CMABs.csv',
        'EXP3': 'Master_Dataset_EXP3.csv',
        'Hybrid': 'Master_Dataset_Hybrid.csv'
    }
    
    # Initialize generator
    gen = QuantumFigureGenerator(datasets)
    
    # Extract all figure data
    if gen.combined_df is not None:
        figure_data = gen.generate_all()
        
        print("\n" + "="*80)
        print("SAMPLE OUTPUT: Figure 2 (Capacity Paradox)")
        print("="*80)
        print(figure_data['fig2'])
        
        print("\n" + "="*80)
        print("SAMPLE OUTPUT: Figure 4 (Robustness Frontier)")
        print("="*80)
        for model, metrics in figure_data['fig4'].items():
            print(f"{model}: floor={metrics['floor']:.1f}, mean={metrics['mean']:.1f}, peak={metrics['peak']:.1f}")
        
        # Save as JSON for LaTeX integration
        import json
        with open('figure_data.json', 'w') as f:
            json.dump({k: (v.to_dict() if hasattr(v, 'to_dict') else v) 
                       for k, v in figure_data.items()}, f, indent=2, default=str)
        
        print("\n✓ Figure data saved to figure_data.json")
    else:
        print("\n✗ No datasets loaded. Please check file paths.")
