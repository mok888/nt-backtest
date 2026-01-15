"""
Data Loader Module - Fetches and prepares Binance ETHUSDT perpetual futures data
Downloads 100 days of 15-minute bars and stores them in Parquet catalog
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal

from nautilus_trader.core.datetime import dt_to_unix_nanos
from nautilus_trader.model.currencies import ETH, USDT
from nautilus_trader.model.data import Bar, BarType, BarSpecification
from nautilus_trader.model.enums import (
    BarAggregation,
    PriceType,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoPerpetual
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.persistence.catalog import ParquetDataCatalog


class BinanceDataLoader:
    """
    Loads historical data from Binance for backtesting
    """

    def __init__(self, catalog_path: str = "./data/catalog"):
        """
        Initialize the data loader

        Args:
            catalog_path: Path to store/load parquet data catalog
        """
        self.catalog_path = Path(catalog_path)
        self.catalog_path.mkdir(parents=True, exist_ok=True)
        self.catalog = ParquetDataCatalog(str(self.catalog_path))

        # Binance ETHUSDT Perpetual Futures instrument
        self.instrument_id = InstrumentId(symbol=Symbol("ETHUSDT.P"), venue=Venue("BINANCE"))
        self.instrument = self._create_instrument()

    def _create_instrument(self) -> CryptoPerpetual:
        """
        Create the ETHUSDT perpetual futures instrument

        Returns:
            CryptoPerpetual: The futures instrument configuration
        """
        instrument = CryptoPerpetual(
            instrument_id=self.instrument_id,
            raw_symbol=Symbol("ETHUSDT"),
            base_currency=ETH,
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
            max_notional=Money(Decimal("10000000"), USDT),
            min_notional=Money(Decimal("5"), USDT),
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

    def download_historical_data(
        self,
        days: int = 100,
        timeframe: str = "15m"
    ) -> pd.DataFrame:
        """
        Download historical 15-minute bars from Binance

        Args:
            days: Number of days of historical data to fetch
            timeframe: Bar timeframe (default: 15m)

        Returns:
            DataFrame: Historical OHLCV bars
        """
        try:
            # Try to fetch from Binance API via ccxt if available
            try:
                import ccxt

                print(f"Fetching {days} days of {timeframe} bars from Binance...")
                exchange = ccxt.binanceusdm()

                # Calculate timeframe in milliseconds
                timeframe_ms = {
                    "1m": 60000,
                    "5m": 300000,
                    "15m": 900000,
                    "1h": 3600000,
                    "4h": 14400000,
                    "1d": 86400000,
                }

                since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
                all_ohlcv = []

                while since < exchange.milliseconds():
                    ohlcv = exchange.fetch_ohlcv(
                        "ETH/USDT:USDT",
                        timeframe=timeframe,
                        since=since,
                        limit=1000
                    )
                    if len(ohlcv) == 0:
                        break
                    all_ohlcv.extend(ohlcv)
                    since = ohlcv[-1][0] + 1

                # Convert to DataFrame
                df = pd.DataFrame(
                    all_ohlcv,
                    columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                )
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                print(f"Downloaded {len(df)} bars from Binance")

                return df

            except ImportError:
                print("ccxt not installed, using synthetic data generation...")
                return self._generate_synthetic_data(days=days, timeframe=timeframe)

        except Exception as e:
            print(f"Error fetching Binance data: {e}")
            print("Falling back to synthetic data generation...")
            return self._generate_synthetic_data(days=days, timeframe=timeframe)

    def _generate_synthetic_data(
        self,
        days: int = 100,
        timeframe: str = "15m"
    ) -> pd.DataFrame:
        """
        Generate synthetic price data for testing purposes

        Args:
            days: Number of days to generate
            timeframe: Bar timeframe

        Returns:
            DataFrame: Synthetic OHLCV bars
        """
        print(f"Generating {days} days of synthetic {timeframe} bars...")

        # Calculate number of bars
        bars_per_day = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1,
        }
        n_bars = days * bars_per_day.get(timeframe, 96)

        # Generate realistic price movement
        np.random.seed(42)  # For reproducibility
        base_price = 3500.0

        # Random walk with drift
        returns = np.random.normal(0.0005, 0.01, n_bars)  # Small upward drift with volatility
        prices = base_price * np.cumprod(1 + returns)

        # Create OHLCV from close prices with some noise
        df = pd.DataFrame(index=pd.date_range(
            start=datetime.now() - timedelta(days=days),
            periods=n_bars,
            freq=timeframe
        ))

        # Generate OHLC from close prices with some noise
        df['close'] = prices

        # High/Low as max/min of close with some volatility
        volatility = 0.02
        df['high'] = df['close'] * (1 + np.random.uniform(0, volatility, n_bars))
        df['low'] = df['close'] * (1 - np.random.uniform(0, volatility, n_bars))

        # Open as previous close (or close for first bar)
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])

        # Volume
        df['volume'] = np.random.lognormal(10, 0.5, n_bars) * 1000

        # Reorder columns
        df = df[['open', 'high', 'low', 'close', 'volume']]

        print(f"Generated {len(df)} synthetic bars")
        return df

    def save_to_catalog(self, df: pd.DataFrame) -> None:
        """
        Save DataFrame to Parquet catalog

        Args:
            df: DataFrame with OHLCV data
        """
        # Create bar type
        bar_type = BarType(
            instrument_id=self.instrument_id,
            bar_spec=BarSpecification(
                step=15,
                aggregation=BarAggregation.MINUTE,
                price_type=PriceType.LAST
            ),
        )

        # Convert DataFrame to NautilusTrader format
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

        # Write to catalog
        print(f"Saving {len(bars)} bars to catalog...")
        try:
            self.catalog.write_data(bars)
            print(f"Data saved to {self.catalog_path}")
        except Exception as e:
            print(f"Error saving to catalog: {e}")
            raise

    def load_from_catalog(self) -> pd.DataFrame:
        """
        Load bars from Parquet catalog

        Returns:
            DataFrame: Historical OHLCV bars
        """
        print(f"Loading data from catalog: {self.catalog_path}")

        # Query bars from catalog
        bars = self.catalog.bars(
            instrument_ids=[self.instrument_id],
            start_ns=None,
            end_ns=None,
        )

        if not bars:
            raise ValueError(
                "No data found in catalog. Run download_historical_data() first."
            )

        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'timestamp': bar.ts_init / 1_000_000_000,  # Convert to seconds
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': float(bar.volume),
            }
            for bar in bars
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        print(f"Loaded {len(df)} bars from catalog")
        return df

    def get_data(
        self,
        days: int = 100,
        force_download: bool = False
    ) -> pd.DataFrame:
        """
        Get data - download if needed or load from catalog

        Args:
            days: Number of days of data
            force_download: Force re-download even if catalog exists

        Returns:
            DataFrame: Historical OHLCV bars
        """
        if force_download or not self._catalog_exists():
            print("Downloading fresh data from Binance...")
            df = self.download_historical_data(days=days)
            # Clear existing catalog data to prevent overlapping intervals
            self._clear_catalog()
            self.save_to_catalog(df)
            return df
        else:
            print("Loading data from existing catalog...")
            return self.load_from_catalog()

    def _clear_catalog(self) -> None:
        """
        Clear existing catalog data for this instrument to prevent overlapping intervals
        """
        try:
            from nautilus_trader.model.data import Bar
            self.catalog.delete_data_range(
                Bar,
                self.instrument_id,
                start=None,
                end=None,
            )
            print("Cleared existing catalog data")
        except Exception as e:
            print(f"Warning: Could not clear catalog: {e}")
            # If clearing fails, try to recreate catalog
            try:
                import shutil
                catalog_path = str(self.catalog_path)
                if Path(catalog_path).exists():
                    shutil.rmtree(catalog_path)
                    Path(catalog_path).mkdir(parents=True, exist_ok=True)
                    self.catalog = ParquetDataCatalog(str(self.catalog_path))
                    print("Recreated catalog directory")
            except Exception as e2:
                print(f"Warning: Could not recreate catalog: {e2}")

    def _catalog_exists(self) -> bool:
        """Check if catalog has data"""
        try:
            bars = self.catalog.bars(instrument_ids=[self.instrument_id], limit=1)
            return len(bars) > 0
        except (FileNotFoundError, KeyError, AttributeError):
            return False


def main() -> None:
    """Example usage"""
    loader = BinanceDataLoader(catalog_path="./data/catalog")

    # Get 100 days of data
    df = loader.get_data(days=100, force_download=True)

    print(f"\nData shape: {df.shape}")
    print(f"\nData range: {df.index[0]} to {df.index[-1]}")
    print(f"\nFirst 5 rows:")
    print(df.head())
    print(f"\nLast 5 rows:")
    print(df.tail())

    # Save to CSV for analysis
    try:
        df.to_csv("./data/ethusdt_15m.csv")
        print(f"\nData saved to ./data/ethusdt_15m.csv")
    except Exception as e:
        print(f"Error saving CSV: {e}")
        raise


if __name__ == "__main__":
    main()
