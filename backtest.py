"""
Backtest Engine Module - Main backtesting orchestration
Runs the RSI strategy on historical data with proper venue configuration
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Any

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import FillModel, FeeModel, LatencyModel
from nautilus_trader.backtest.modules import FXRolloverInterestModule
from nautilus_trader.config import BacktestVenueConfig, BacktestDataConfig, BacktestRunConfig
from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import (
    BarAggregation,
    BookType,
    OmsType,
    AccountType,
    PriceType,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Money, Price, Quantity
from decimal import Decimal

from strategy import RSIStrategy, RSIConfig
from data_loader import BinanceDataLoader


class RSIBacktester:
    """
    Backtest engine for RSI strategy
    """

    def __init__(
        self,
        catalog_path: str = "./data/catalog",
        output_dir: str = "./results",
    ):
        """
        Initialize backtester

        Args:
            catalog_path: Path to data catalog
            output_dir: Path for output files
        """
        self.catalog_path = Path(catalog_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data loader
        self.data_loader = BinanceDataLoader(str(self.catalog_path))

        # Instrument
        self.instrument_id = InstrumentId(symbol=Symbol("ETHUSDT.P"), venue=Venue("BINANCE"))
        self.instrument = self._create_instrument()

        # Backtest engine
        self.engine = None

    def _create_instrument(self) -> CryptoPerpetual:
        """
        Create ETHUSDT perpetual futures instrument

        Returns:
            CryptoPerpetual: The instrument
        """
        instrument = CryptoPerpetual(
            instrument_id=self.instrument_id,
            raw_symbol=Symbol("ETHUSDT"),
            base_currency=None,
            quote_currency=USDT,
            settlement_currency=USDT,
            is_inverse=False,
            price_precision=2,
            price_increment=Price.from_str("0.01"),
            size_precision=3,
            size_increment=Quantity.from_str("0.001"),
            lot_size=Quantity.from_str("0.001"),
            max_quantity=Quantity.from_str("1000000"),
            min_quantity=Quantity.from_str("0.001"),
            max_notional=Price.from_str("10000000"),
            min_notional=Price.from_str("5.0"),
            max_price=Price.from_str("1000000"),
            min_price=Price.from_str("0.001"),
            margin_init=Decimal("0.05"),  # 20x leverage
            margin_maint=Decimal("0.03"),
            maker_fee=Decimal("0.0002"),  # 0.02%
            taker_fee=Decimal("0.0005"),  # 0.05%
            ts_event=0,
            ts_init=0,
        )
        return instrument

    def _create_venue_config(self) -> BacktestVenueConfig:
        """
        Create venue configuration with leverage and fill model

        Returns:
            BacktestVenueConfig: Venue configuration
        """
        return BacktestVenueConfig(
            name="BINANCE",
            oms_type=OmsType.NETTING,
            account_type=AccountType.MARGIN,
            base_currency=USDT,
            starting_balances=[Money(100000.0, USDT)],  # 100K USDT starting capital
            book_type=BookType.L2_MBP,
            fill_model=FillModel(
                latency_ns=1_000_000,  # 1ms latency
                slippage_bps=Decimal("0.5"),  # 0.5 bps slippage
                probabilistic=True,
            ),
            fee_model=FeeModel(
                maker_fee=Decimal("0.0002"),  # 0.02%
                taker_fee=Decimal("0.0005"),  # 0.05%
            ),
            leverage=Decimal("20.0"),  # 20x leverage for perps
        )

    def _create_bar_type(self) -> BarType:
        """
        Create 15-minute bar type

        Returns:
            BarType: 15-minute bar type
        """
        from nautilus_trader.model.data import BarSpecification

        return BarType(
            instrument_id=self.instrument_id,
            bar_spec=BarSpecification(
                step=15,
                aggregation=BarAggregation.MINUTE,
                price_type=PriceType.LAST,
            ),
        )

    def run_backtest(
        self,
        rsi_period: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        stop_loss_pct: float = 1.5,
        take_profit_pct: float = 3.0,
        position_size_pct: float = 2.0,
        days: int = 100,
    ) -> Dict[str, Any]:
        """
        Run a single backtest with given parameters

        Args:
            rsi_period: RSI period
            oversold_threshold: RSI oversold level
            overbought_threshold: RSI overbought level
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            position_size_pct: Position size as % of equity
            days: Number of days of data to use

        Returns:
            Dict with backtest results
        """
        print(f"\n{'='*60}")
        print(f"Running Backtest")
        print(f"{'='*60}")
        print(f"RSI Period: {rsi_period}")
        print(f"Oversold: {oversold_threshold}, Overbought: {overbought_threshold}")
        print(f"Stop Loss: {stop_loss_pct}%, Take Profit: {take_profit_pct}%")
        print(f"Position Size: {position_size_pct}%")
        print(f"Data: {days} days")
        print(f"{'='*60}\n")

        # Load data
        df = self.data_loader.get_data(days=days, force_download=False)

        # Create backtest engine config
        engine_config = BacktestEngineConfig(
            trader_id="BACKTESTER-001",
            log_level="INFO",
        )

        # Create venue config
        venue_config = self._create_venue_config()

        # Create backtest engine
        self.engine = BacktestEngine(config=engine_config)
        self.engine.add_venue(venue=venue_config, instrument=self.instrument)

        # Create bar type
        bar_type = self._create_bar_type()

        # Create strategy config
        config = RSIConfig(
            rsi_period=rsi_period,
            oversold_threshold=oversold_threshold,
            overbought_threshold=overbought_threshold,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            position_size_pct=position_size_pct,
            instrument_id=self.instrument_id,
        )

        # Create and add strategy
        strategy = RSIStrategy(
            config=config,
            instrument_id=self.instrument_id,
            bar_type=bar_type,
        )
        self.engine.add_strategy(strategy)

        # Convert DataFrame to NautilusTrader bars and add to engine
        self._add_data_to_engine(df, bar_type)

        # Run backtest
        self.engine.run()

        # Get results
        results = self._extract_results(
            rsi_period, oversold_threshold, overbought_threshold,
            stop_loss_pct, take_profit_pct, position_size_pct
        )

        # Reset engine for next run
        self.engine.reset()

        return results

    def _add_data_to_engine(self, df: pd.DataFrame, bar_type: BarType) -> None:
        """
        Add DataFrame bars to backtest engine

        Args:
            df: DataFrame with OHLCV data
            bar_type: Bar type for the data
        """
        bars = []
        for timestamp, row in df.iterrows():
            bar = Bar(
                bar_type=bar_type,
                open=Price.from_str(str(row['open'])),
                high=Price.from_str(str(row['high'])),
                low=Price.from_str(str(row['low'])),
                close=Price.from_str(str(row['close'])),
                volume=Quantity.from_str(str(row['volume'])),
                ts_event=dt_to_unix_nanos(timestamp),
                ts_init=dt_to_unix_nanos(timestamp),
            )
            bars.append(bar)

        # Add bars to engine
        self.engine.add_data(bars)
        print(f"Added {len(bars)} bars to backtest engine")

    def _extract_results(
        self,
        rsi_period: int,
        oversold_threshold: float,
        overbought_threshold: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        position_size_pct: float,
    ) -> Dict[str, Any]:
        """
        Extract backtest results from engine

        Args:
            Various strategy parameters

        Returns:
            Dict with performance metrics
        """
        # Generate reports
        account_report = self.engine.trader.generate_account_report()
        positions_report = self.engine.trader.generate_positions_report()
        fills_report = self.engine.trader.generate_order_fills_report()

        # Extract key metrics
        results = {
            "rsi_period": rsi_period,
            "oversold_threshold": oversold_threshold,
            "overbought_threshold": overbought_threshold,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "position_size_pct": position_size_pct,
        }

        # Extract from account report
        if account_report:
            results["total_pnl"] = float(account_report.get("PNL_MTD", 0))
            results["total_return_pct"] = float(account_report.get("return_pct", 0)) * 100
            results["starting_balance"] = float(account_report.get("starting_balance", 0))
            results["ending_balance"] = float(account_report.get("ending_balance", 0))

        # Extract from positions report
        if positions_report is not None and len(positions_report) > 0:
            results["total_trades"] = len(positions_report)
            results["winning_trades"] = sum(1 for p in positions_report if p.realized_pnl > 0)
            results["losing_trades"] = sum(1 for p in positions_report if p.realized_pnl <= 0)
            results["win_rate"] = (results["winning_trades"] / results["total_trades"] * 100) if results["total_trades"] > 0 else 0

            # Calculate Sharpe ratio (simplified)
            if len(positions_report) > 1:
                returns = [float(p.realized_pnl) for p in positions_report]
                import numpy as np
                if np.std(returns) > 0:
                    results["sharpe_ratio"] = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
                else:
                    results["sharpe_ratio"] = 0

            # Calculate max drawdown
            if results["starting_balance"] > 0:
                peak = results["starting_balance"]
                max_dd = 0
                # This is a simplified calculation - proper DD requires equity curve
                results["max_drawdown_pct"] = max_dd
            else:
                results["max_drawdown_pct"] = 0

        return results

    def print_results(self, results: Dict[str, Any]) -> None:
        """
        Print backtest results in a formatted table

        Args:
            results: Results dictionary
        """
        print(f"\n{'='*60}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*60}")
        print(f"RSI Period: {results['rsi_period']}")
        print(f"Oversold: {results['oversold_threshold']}, Overbought: {results['overbought_threshold']}")
        print(f"Stop Loss: {results['stop_loss_pct']}%, Take Profit: {results['take_profit_pct']}%")
        print(f"Position Size: {results['position_size_pct']}%")
        print(f"\nPerformance:")
        print(f"  Total PnL: ${results.get('total_pnl', 0):,.2f}")
        print(f"  Total Return: {results.get('total_return_pct', 0):.2f}%")
        print(f"  Total Trades: {results.get('total_trades', 0)}")
        print(f"  Winning Trades: {results.get('winning_trades', 0)}")
        print(f"  Losing Trades: {results.get('losing_trades', 0)}")
        print(f"  Win Rate: {results.get('win_rate', 0):.2f}%")
        print(f"  Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        print(f"{'='*60}\n")

    def save_results(self, results: Dict[str, Any], filename: str = "backtest_results.csv") -> None:
        """
        Save results to CSV

        Args:
            results: Results dictionary
            filename: Output filename
        """
        df = pd.DataFrame([results])
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")

    def plot_equity_curve(self, results: Dict[str, Any]) -> None:
        """
        Plot equity curve (placeholder - requires full equity data)

        Args:
            results: Results dictionary
        """
        # This would require tracking equity over time from the engine
        # For now, we'll create a simple placeholder
        fig, ax = plt.subplots(figsize=(12, 6))

        starting_balance = results.get('starting_balance', 100000)
        ending_balance = results.get('ending_balance', starting_balance)

        ax.plot([0, 1], [starting_balance, ending_balance], 'b-', linewidth=2)
        ax.set_title(f"Equity Curve - RSI Strategy")
        ax.set_xlabel("Time")
        ax.set_ylabel("Portfolio Value (USDT)")
        ax.grid(True, alpha=0.3)

        output_path = self.output_dir / "equity_curve.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Equity curve saved to {output_path}")
        plt.close()


def main():
    """Run a single backtest example"""
    backtester = RSIBacktester(
        catalog_path="./data/catalog",
        output_dir="./results",
    )

    # Run backtest with default parameters
    results = backtester.run_backtest(
        rsi_period=14,
        oversold_threshold=30.0,
        overbought_threshold=70.0,
        stop_loss_pct=1.5,
        take_profit_pct=3.0,
        position_size_pct=2.0,
        days=100,
    )

    # Print and save results
    backtester.print_results(results)
    backtester.save_results(results)
    backtester.plot_equity_curve(results)


if __name__ == "__main__":
    main()
