"""
Optimizer Module - Grid search optimization for RSI strategy parameters
Searches for optimal combinations of RSI thresholds, Stop Loss, Take Profit, and position sizing
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
from itertools import product
import time

from backtest import RSIBacktester


class RSIOptimizer:
    """
    Grid search optimizer for RSI strategy parameters

    Optimizes:
    - RSI oversold threshold (20-40)
    - RSI overbought threshold (60-80)
    - Stop Loss % (0.5-3.0)
    - Take Profit % (1.0-6.0)
    - Position Size % (0.5-5.0)
    """

    def __init__(
        self,
        catalog_path: str = "./data/catalog",
        output_dir: str = "./results",
        max_combinations: int = 500,
    ):
        """
        Initialize optimizer

        Args:
            catalog_path: Path to data catalog
            output_dir: Path for output files
            max_combinations: Maximum parameter combinations to test
        """
        self.catalog_path = Path(catalog_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_combinations = max_combinations

        # Create backtester instance
        self.backtester = RSIBacktester(
            catalog_path=str(self.catalog_path),
            output_dir=str(self.output_dir),
        )

    def define_search_space(self) -> Dict[str, List[float]]:
        """
        Define parameter search space

        Returns:
            Dictionary with parameter ranges
        """
        return {
            'rsi_period': [14],  # Fixed for now, can vary if needed
            'oversold_threshold': list(range(20, 41, 1)),  # 20-40, step 1
            'overbought_threshold': list(range(60, 81, 1)),  # 60-80, step 1
            'stop_loss_pct': [i * 0.25 for i in range(2, 13)],  # 0.5-3.0, step 0.25
            'take_profit_pct': [i * 0.5 for i in range(2, 13)],  # 1.0-6.0, step 0.5
            'position_size_pct': [i * 0.5 for i in range(1, 11)],  # 0.5-5.0, step 0.5
        }

    def generate_parameter_combinations(self) -> List[Dict[str, Any]]:
        """
        Generate all parameter combinations

        Returns:
            List of parameter dictionaries
        """
        search_space = self.define_search_space()

        # Generate all combinations using itertools.product
        keys = list(search_space.keys())
        values = list(search_space.values())

        all_combinations = [
            dict(zip(keys, combo))
            for combo in product(*values)
        ]

        # Limit to max_combinations
        if len(all_combinations) > self.max_combinations:
            print(f"Warning: Total combinations ({len(all_combinations)}) exceeds max ({self.max_combinations})")
            print(f"Sampling {self.max_combinations} random combinations...")
            np.random.seed(42)  # For reproducibility
            indices = np.random.choice(len(all_combinations), self.max_combinations, replace=False)
            combinations = [all_combinations[i] for i in indices]
        else:
            combinations = all_combinations

        print(f"Generated {len(combinations)} parameter combinations to test")
        return combinations

    def run_grid_search(
        self,
        days: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Run grid search optimization

        Args:
            days: Number of days of data to use
            filters: Optional filters to apply (e.g., {'sharpe_min': 1.5, 'win_rate_min': 55})

        Returns:
            DataFrame with all results sorted by Sharpe ratio
        """
        print(f"\n{'='*60}")
        print(f"GRID SEARCH OPTIMIZATION")
        print(f"{'='*60}\n")

        # Get parameter combinations
        combinations = self.generate_parameter_combinations()

        # Run backtests
        results = []
        total_combinations = len(combinations)

        for i, params in enumerate(combinations, 1):
            start_time = time.time()

            print(f"\n[{i}/{total_combinations}] Testing: "
                  f"RSI({params['rsi_period']}), "
                  f"OS={params['oversold_threshold']}, OB={params['overbought_threshold']}, "
                  f"SL={params['stop_loss_pct']}%, TP={params['take_profit_pct']}%, "
                  f"Size={params['position_size_pct']}%")

            # Run backtest
            try:
                result = self.backtester.run_backtest(
                    rsi_period=params['rsi_period'],
                    oversold_threshold=params['oversold_threshold'],
                    overbought_threshold=params['overbought_threshold'],
                    stop_loss_pct=params['stop_loss_pct'],
                    take_profit_pct=params['take_profit_pct'],
                    position_size_pct=params['position_size_pct'],
                    days=days,
                )
                results.append(result)
            except Exception as e:
                print(f"Error in backtest: {e}")
                # Add failed result for tracking
                result = params.copy()
                result['error'] = str(e)
                result['total_pnl'] = 0
                result['total_return_pct'] = 0
                result['sharpe_ratio'] = 0
                results.append(result)

            elapsed_time = time.time() - start_time
            print(f"Completed in {elapsed_time:.2f}s")

        # Convert to DataFrame
        results_df = pd.DataFrame(results)

        # Sort by Sharpe ratio
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)

        # Save all results
        self._save_results(results_df, "all_results.csv")

        # Apply filters if provided
        if filters:
            filtered_df = self._apply_filters(results_df, filters)
            self._save_results(filtered_df, "filtered_results.csv")
        else:
            filtered_df = results_df

        return filtered_df

    def _apply_filters(
        self,
        df: pd.DataFrame,
        filters: Dict[str, Any],
    ) -> pd.DataFrame:
        """
        Apply filters to results

        Args:
            df: Results DataFrame
            filters: Filter criteria

        Returns:
            Filtered DataFrame
        """
        filtered_df = df.copy()

        if 'sharpe_min' in filters:
            filtered_df = filtered_df[filtered_df['sharpe_ratio'] >= filters['sharpe_min']]

        if 'win_rate_min' in filters:
            filtered_df = filtered_df[filtered_df['win_rate'] >= filters['win_rate_min']]

        if 'max_drawdown_max' in filters:
            filtered_df = filtered_df[filtered_df['max_drawdown_pct'] <= filters['max_drawdown_max']]

        return filtered_df

    def _save_results(self, df: pd.DataFrame, filename: str) -> None:
        """
        Save results to CSV

        Args:
            df: Results DataFrame
            filename: Output filename
        """
        output_path = self.output_dir / filename
        try:
            df.to_csv(output_path, index=False)
            print(f"\nResults saved to {output_path}")
        except Exception as e:
            print(f"Error saving results to CSV: {e}")
            raise

    def print_top_results(
        self,
        df: pd.DataFrame,
        top_n: int = 10,
    ) -> None:
        """
        Print top N results

        Args:
            df: Results DataFrame
            top_n: Number of top results to display
        """
        print(f"\n{'='*80}")
        print(f"TOP {top_n} PARAMETERS (Sorted by Sharpe Ratio)")
        print(f"{'='*80}\n")

        # Select top N
        top_df = df.head(top_n)

        # Format for display
        display_cols = [
            'sharpe_ratio',
            'total_pnl',
            'total_return_pct',
            'win_rate',
            'total_trades',
            'oversold_threshold',
            'overbought_threshold',
            'stop_loss_pct',
            'take_profit_pct',
            'position_size_pct',
        ]

        # Filter columns that exist
        existing_cols = [col for col in display_cols if col in top_df.columns]

        print(top_df[existing_cols].to_string(index=False))

        # Print optimal parameters
        if len(top_df) > 0:
            best = top_df.iloc[0]
            print(f"\n{'='*80}")
            print(f"OPTIMAL PARAMETERS:")
            print(f"{'='*80}")
            print(f"RSI Oversold: {best.get('oversold_threshold', 'N/A')}")
            print(f"RSI Overbought: {best.get('overbought_threshold', 'N/A')}")
            print(f"Stop Loss: {best.get('stop_loss_pct', 'N/A')}%")
            print(f"Take Profit: {best.get('take_profit_pct', 'N/A')}%")
            print(f"Position Size: {best.get('position_size_pct', 'N/A')}%")
            print(f"\nPERFORMANCE:")
            print(f"Total PnL: ${best.get('total_pnl', 0):,.2f}")
            print(f"Total Return: {best.get('total_return_pct', 0):.2f}%")
            print(f"Sharpe Ratio: {best.get('sharpe_ratio', 0):.2f}")
            print(f"Win Rate: {best.get('win_rate', 0):.2f}%")
            print(f"{'='*80}\n")

    def analyze_parameter_impact(self, df: pd.DataFrame) -> None:
        """
        Analyze impact of each parameter on performance

        Args:
            df: Results DataFrame
        """
        print(f"\n{'='*80}")
        print(f"PARAMETER IMPACT ANALYSIS")
        print(f"{'='*80}\n")

        # Define parameters to analyze
        params_to_analyze = [
            'oversold_threshold',
            'overbought_threshold',
            'stop_loss_pct',
            'take_profit_pct',
            'position_size_pct',
        ]

        for param in params_to_analyze:
            if param not in df.columns:
                continue

            # Group by parameter and compute mean metrics
            grouped = df.groupby(param).agg({
                'sharpe_ratio': 'mean',
                'total_return_pct': 'mean',
                'win_rate': 'mean',
                'total_pnl': 'mean',
            }).reset_index()

            # Sort by Sharpe ratio
            grouped = grouped.sort_values('sharpe_ratio', ascending=False)

            print(f"\nImpact of {param}:")
            print(grouped.head(10).to_string(index=False))
            print("-" * 80)

    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """
        Generate a text summary report

        Args:
            df: Results DataFrame

        Returns:
            Summary report as string
        """
        report = []
        report.append("="*80)
        report.append("RSI STRATEGY OPTIMIZATION SUMMARY REPORT")
        report.append("="*80)
        report.append("")

        # Overall statistics
        report.append("OVERALL STATISTICS:")
        report.append(f"  Total combinations tested: {len(df)}")
        report.append(f"  Successful backtests: {len(df[df['total_pnl'] > 0])}")
        report.append(f"  Failed backtests: {len(df[df['total_pnl'] <= 0])}")
        report.append("")

        # Best performance
        best = df.iloc[0]
        report.append("BEST PERFORMANCE:")
        report.append(f"  Sharpe Ratio: {best['sharpe_ratio']:.2f}")
        report.append(f"  Total PnL: ${best['total_pnl']:,.2f}")
        report.append(f"  Total Return: {best['total_return_pct']:.2f}%")
        report.append(f"  Win Rate: {best['win_rate']:.2f}%")
        report.append(f"  Total Trades: {best['total_trades']}")
        report.append("")

        # Optimal parameters
        report.append("OPTIMAL PARAMETERS:")
        report.append(f"  RSI Oversold: {best['oversold_threshold']}")
        report.append(f"  RSI Overbought: {best['overbought_threshold']}")
        report.append(f"  Stop Loss: {best['stop_loss_pct']}%")
        report.append(f"  Take Profit: {best['take_profit_pct']}%")
        report.append(f"  Position Size: {best['position_size_pct']}%")
        report.append("")

        # Top 3 parameters
        report.append("TOP 3 PARAMETER COMBINATIONS:")
        for i in range(min(3, len(df))):
            row = df.iloc[i]
            report.append(f"\n  #{i+1}: Sharpe={row['sharpe_ratio']:.2f}, PnL=${row['total_pnl']:,.2f}")
            report.append(f"      OS={row['oversold_threshold']}, OB={row['overbought_threshold']}, "
                         f"SL={row['stop_loss_pct']}%, TP={row['take_profit_pct']}%, Size={row['position_size_pct']}%")

        report.append("")
        report.append("="*80)

        return "\n".join(report)


def main() -> None:
    """Run grid search optimization"""
    optimizer = RSIOptimizer(
        catalog_path="./data/catalog",
        output_dir="./results",
        max_combinations=200,  # Limit to 200 for faster execution
    )

    # Define filters for acceptable performance
    filters = {
        'sharpe_min': 1.5,
        'win_rate_min': 55,
    }

    # Run grid search
    results_df = optimizer.run_grid_search(
        days=100,
        filters=filters,
    )

    # Print top results
    optimizer.print_top_results(results_df, top_n=10)

    # Analyze parameter impact
    optimizer.analyze_parameter_impact(results_df)

    # Generate summary report
    report = optimizer.generate_summary_report(results_df)
    print(report)

    # Save report
    report_path = Path("./results/summary_report.txt")
    try:
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\nSummary report saved to {report_path}")
    except Exception as e:
        print(f"Error saving summary report: {e}")
        raise


if __name__ == "__main__":
    main()
