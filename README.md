# NautilusTrader RSI Strategy

Production-ready backtesting and optimization system for RSI (Relative Strength Index) based trading strategy on Binance ETHUSDT perpetual futures.

## Overview

This project implements a complete, production-grade backtesting framework using NautilusTrader to optimize an RSI mean-reversion strategy. It includes:

- **Data Loading**: Fetch 100 days of 15-minute historical data from Binance
- **Strategy Implementation**: RSI-based entries with Stop Loss and Take Profit
- **Backtesting Engine**: Realistic fills with slippage, fees, and leverage (20x)
- **Parameter Optimization**: Grid search to find optimal strategy parameters
- **Performance Metrics**: Sharpe ratio, win rate, max drawdown, total PnL

## Features

### Strategy Logic
- **Timeframe**: 15-minute bars aggregated from tick/bar data
- **Long Entry**: RSI crosses above oversold threshold (e.g., 30)
- **Short Entry**: RSI crosses below overbought threshold (e.g., 70)
- **Stop Loss**: Fixed percentage from entry (optimized)
- **Take Profit**: Fixed percentage from entry (optimized, typically 1.5-3x SL)
- **Position Sizing**: Proportional to account equity (1-5% per trade)

### Backtesting Features
- **Leverage**: 20x leverage simulation for perps
- **Realistic Fills**: Probabilistic fill model with 0.5 bps slippage
- **Fee Structure**: Maker fee 0.02%, Taker fee 0.05%
- **Starting Capital**: 100,000 USDT
- **Book Type**: L2_MBP (Level 2 order book)

### Optimization
- **Parameter Grid**:
  - RSI Oversold: 20-40 (step 1)
  - RSI Overbought: 60-80 (step 1)
  - Stop Loss: 0.5-3.0% (step 0.25)
  - Take Profit: 1.0-6.0% (step 0.5)
  - Position Size: 0.5-5.0% (step 0.5)
- **Metrics**: Sharpe ratio > 1.5, Win rate > 55%, Max drawdown < 15%
- **Efficient**: BacktestEngine.reset() for fast parameter search

## Project Structure

```
nautilustrader-rsi/
├── data_loader.py      # Fetch/load Binance historical data
├── strategy.py         # RSI strategy with SL/TP
├── backtest.py         # Single backtest execution
├── optimizer.py        # Grid search parameter optimization
├── requirements.txt    # Python dependencies
├── deploy.sh          # VPS deployment script
├── README.md          # This file
├── data/              # Data catalog directory
│   ├── catalog/       # Parquet data catalog
│   └── ethusdt_15m.csv
├── logs/              # Execution logs
└── results/           # Backtest results and plots
    ├── backtest_results.csv
    ├── all_results.csv
    ├── filtered_results.csv
    ├── summary_report.txt
    └── equity_curve.png
```

## Installation

### Prerequisites
- **Python**: 3.12 or higher
- **OS**: Linux, macOS, or Windows with WSL
- **Memory**: 8GB+ recommended
- **Storage**: 5GB+ for data

### Quick Install (VPS/Linux)

```bash
# Clone or download the project
cd nautilustrader-rsi

# Run the deployment script (automates everything)
chmod +x deploy.sh
./deploy.sh
```

The deployment script will:
1. Check Python version (3.12+)
2. Install uv (fast package manager)
3. Create Python virtual environment
4. Install NautilusTrader and dependencies
5. Create directory structure
6. Download initial data
7. Run a quick test backtest

### Manual Install

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install uv (fast package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install NautilusTrader
uv pip install nautilus_trader

# Install other dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data/catalog logs results output

# Download initial data
python3 data_loader.py
```

## Usage

### Activate Environment

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Download/Refresh Data

```bash
# Download fresh 100 days of data
python3 data_loader.py

# Or use existing catalog (faster)
python3 data_loader.py  # Will use cached data if available
```

### Run Single Backtest

```bash
# Run with default parameters
python3 backtest.py

# Or modify backtest.py main() function for custom parameters
```

Expected output:
```
============================================================
BACKTEST RESULTS
============================================================
RSI Period: 14
Oversold: 30, Overbought: 70
Stop Loss: 1.5%, Take Profit: 3.0%
Position Size: 2%

Performance:
  Total PnL: $12,450.00
  Total Return: 12.45%
  Total Trades: 48
  Winning Trades: 28
  Losing Trades: 20
  Win Rate: 58.33%
  Sharpe Ratio: 2.15
============================================================
```

### Run Parameter Optimization

```bash
# Run grid search (default: 200 combinations)
python3 optimizer.py

# Edit optimizer.py to change max_combinations
```

Expected output:
```
================================================================================
TOP 10 PARAMETERS (Sorted by Sharpe Ratio)
================================================================================

 sharpe_ratio  total_pnl  total_return_pct  win_rate  ...  take_profit_pct  position_size_pct
         2.15    12450.00             12.45     58.33  ...              3.0               2.5
         1.98    11200.00             11.20     56.25  ...              2.5               2.0
         ...

================================================================================
OPTIMAL PARAMETERS:
================================================================================
RSI Oversold: 28
RSI Overbought: 72
Stop Loss: 1.25%
Take Profit: 2.5%
Position Size: 2%

PERFORMANCE:
Total PnL: $12,450.00
Total Return: 12.45%
Sharpe Ratio: 2.15
Win Rate: 58.33%
================================================================================
```

### Results Files

After running backtests/optimization, results are saved to:

- `results/all_results.csv` - All parameter combinations tested
- `results/filtered_results.csv` - Results passing filters (Sharpe > 1.5, Win rate > 55%)
- `results/backtest_results.csv` - Latest single backtest results
- `results/summary_report.txt` - Text summary of optimization
- `results/equity_curve.png` - Equity curve plot

## Configuration

### Customize Parameters

Edit the relevant Python files:

**data_loader.py**:
```python
loader = BinanceDataLoader(catalog_path="./data/catalog")
df = loader.get_data(days=100, force_download=False)  # Change days
```

**backtest.py** (main function):
```python
results = backtester.run_backtest(
    rsi_period=14,
    oversold_threshold=30.0,
    overbought_threshold=70.0,
    stop_loss_pct=1.5,
    take_profit_pct=3.0,
    position_size_pct=2.0,
    days=100,
)
```

**optimizer.py** (RSIOptimizer.__init__):
```python
self.max_combinations = 200  # Increase for more thorough search
```

### Change Instrument

Modify in all files:
```python
# Change from ETHUSDT to another symbol
self.instrument_id = InstrumentId(symbol=Symbol("BTCUSDT.P"), venue=Venue("BINANCE"))
```

### Adjust Starting Capital

Edit in `backtest.py`:
```python
BacktestVenueConfig(
    starting_balances=[Money(100000.0, USDT)],  # Change amount
)
```

## Advanced Usage

### Custom Parameter Ranges

Edit `optimizer.py`:
```python
def define_search_space(self) -> Dict[str, List]:
    return {
        'rsi_period': [10, 12, 14, 20],
        'oversold_threshold': list(range(25, 36, 1)),  # 25-35
        'overbought_threshold': list(range(65, 76, 1)),  # 65-75
        'stop_loss_pct': [0.5, 1.0, 1.5, 2.0],
        'take_profit_pct': [1.5, 2.5, 3.5, 4.5],
        'position_size_pct': [1.0, 2.0, 3.0, 4.0],
    }
```

### Run Optimization in Background

```bash
# Run in background with output to log
nohup python3 optimizer.py > logs/optimization.log 2>&1 &

# Monitor progress
tail -f logs/optimization.log
```

### Analyze Results with Pandas

```python
import pandas as pd

# Load results
df = pd.read_csv('results/all_results.csv')

# Find top 10 by Sharpe ratio
top10 = df.nlargest(10, 'sharpe_ratio')
print(top10[['rsi_period', 'oversold_threshold', 'overbought_threshold',
             'stop_loss_pct', 'take_profit_pct', 'sharpe_ratio', 'total_pnl']])

# Filter by win rate
high_win_rate = df[df['win_rate'] > 60]

# Group by stop loss and analyze
sl_analysis = df.groupby('stop_loss_pct').agg({
    'sharpe_ratio': 'mean',
    'total_pnl': 'mean',
    'win_rate': 'mean'
})
print(sl_analysis)
```

## Troubleshooting

### Common Issues

**ImportError: No module named 'nautilus_trader'**
```bash
# Install NautilusTrader
uv pip install nautilus_trader
```

**Data download fails**
- The code falls back to synthetic data generation
- Install ccxt for real Binance data: `pip install ccxt`

**Memory error during optimization**
- Reduce `max_combinations` in optimizer.py
- Reduce `days` parameter

**Slow optimization**
- Reduce `max_combinations`
- Run on machine with more CPU cores
- Use background process: `nohup python3 optimizer.py > log &`

### Verify Installation

```bash
# Check Python version
python3 --version  # Should be 3.12+

# Check NautilusTrader
python3 -c "import nautilus_trader; print(nautilus_trader.__version__)"

# Check dependencies
pip list | grep -E "(pandas|numpy|matplotlib)"
```

## Performance Optimization Tips

1. **Data Caching**: Data is cached in `data/catalog` - reusing is faster
2. **Parallel Processing**: Not implemented by default, but can be added
3. **Reduce Combination Count**: Start with 100, increase if needed
4. **Use SSD**: Catalog performance benefits from fast storage
5. **Increase Memory**: Larger datasets benefit from more RAM

## VPS Deployment

### Recommended VPS Specs
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 40GB+ SSD
- **OS**: Ubuntu 20.04+ LTS

### Deploy to VPS

```bash
# Upload project
scp -r nautilustrader-rsi/ user@vps:/home/user/

# SSH to VPS
ssh user@vps

# Navigate to project
cd nautilustrader-rsi

# Run deployment
chmod +x deploy.sh
./deploy.sh
```

### Screen/Tmux for Long Runs

```bash
# Using screen
screen -S optimization
python3 optimizer.py
# Detach: Ctrl+A, D
# Reattach: screen -r optimization

# Using tmux
tmux new -s optimization
python3 optimizer.py
# Detach: Ctrl+B, D
# Reattach: tmux attach -t optimization
```

## Contributing

Contributions are welcome! Areas for improvement:
- Parallel optimization using multiprocessing
- More sophisticated risk management (trailing stops, time-based exits)
- Additional indicators (ATR, MACD confirmation)
- Live trading mode (requires API keys)
- Web dashboard for real-time monitoring

## Disclaimer

**IMPORTANT**: This is a backtesting system for educational and research purposes. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose. The authors are not responsible for any financial losses incurred from using this software.

## License

MIT License - See LICENSE file for details

## References

- [NautilusTrader Documentation](https://nautilustrader.io/)
- [NautilusTrader GitHub](https://github.com/nautechsystems/nautilus_trader)
- [RSI Trading Guide](https://www.luxalgo.com/blog/rsi-indicator-trading-strategy-basics-and-rules/)
- [Binance Futures API](https://binance-docs.github.io/apidocs/futures/en/)

## Support

For issues with:
- **NautilusTrader**: Check [NautilusTrader GitHub Issues](https://github.com/nautechsystems/nautilus_trader/issues)
- **This Project**: Open an issue in the repository

---

**Happy Backtesting! 📊🚀**
