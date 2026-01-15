# Diagnosis

## Root Cause

The `Intervals are not disjoint` error occurs when NautilusTrader's `ParquetDataCatalog` detects overlapping time intervals in bar data. In your case, this happens because:

1. **Multiple catalog files exist**: Previous runs created multiple Parquet files with overlapping date ranges
2. **`_clear_catalog()` using `delete_data_range()` is insufficient**: This method may not delete all underlying Parquet files, leaving partial data that causes conflicts
3. **DataFrame may have duplicate/overlapping timestamps**: Binance API occasionally returns duplicate bars or data gaps that create overlaps

The error message shows: `Cleared existing catalog data` but the write still fails, indicating the clearing didn't fully remove all existing data.

## Fixed save_to_catalog Method

```python
def save_to_catalog(self, df: pd.DataFrame) -> None:
    """
    Save DataFrame to Parquet catalog

    Args:
        df: DataFrame with OHLCV data
    """
    import shutil

    # Ensure DataFrame has datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Sort DataFrame by index to ensure monotonic increasing timestamps
    df = df.sort_index()

    # Remove any duplicate timestamps (keep last occurrence)
    duplicate_count = df.index.duplicated().sum()
    if duplicate_count > 0:
        print(f"Warning: Found {duplicate_count} duplicate timestamps, removing...")
        df = df[~df.index.duplicated(keep='last')]

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

    # Delete and recreate catalog directory to prevent overlapping intervals
    catalog_path = str(self.catalog_path)
    if Path(catalog_path).exists():
        print(f"Deleting catalog directory: {catalog_path}")
        shutil.rmtree(catalog_path)

    # Reinitialize catalog
    Path(catalog_path).mkdir(parents=True, exist_ok=True)
    self.catalog = ParquetDataCatalog(str(self.catalog_path))
    print(f"Created new catalog at: {catalog_path}")

    # Write to catalog
    print(f"Saving {len(bars)} bars to catalog...")
    try:
        self.catalog.write_data(bars)
        print(f"Data saved to {self.catalog_path}")
    except Exception as e:
        print(f"Error saving to catalog: {e}")
        raise
```

## Test Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Delete old catalog directory completely
rm -rf data/catalog

# Run data loader (will create fresh catalog)
python3 data_loader.py

# Expected output:
# Downloading fresh data from Binance...
# Fetching 100 days of 15m bars from Binance...
# Downloaded 9600 bars from Binance
# Deleting catalog directory: ./data/catalog
# Created new catalog at: ./data/catalog
# Saving 9600 bars to catalog...
# Data saved to ./data/catalog

# Verify catalog structure
ls -la data/catalog/

# Verify data can be loaded
python3 -c "
from data_loader import BinanceDataLoader
loader = BinanceDataLoader('./data/catalog')
df = loader.load_from_catalog()
print(f'Loaded {len(df)} bars')
print(f'Range: {df.index[0]} to {df.index[-1]}')
print(f'Duplicates: {df.index.duplicated().sum()}')
print(f'Monotonic: {df.index.is_monotonic_increasing}')
"

# Run backtest to confirm data works
python3 backtest.py
```

## Prevention

### 1. Always Recreate Catalog for Fresh Data

When downloading fresh data, delete the entire catalog directory instead of using `delete_data_range()`:

```python
# Don't do this (may leave partial files):
catalog.delete_data_range(Bar, instrument_id, start=None, end=None)

# Do this (complete cleanup):
shutil.rmtree(catalog_path)
Path(catalog_path).mkdir(parents=True, exist_ok=True)
catalog = ParquetDataCatalog(catalog_path)
```

### 2. Validate DataFrame Before Writing

Always ensure DataFrame is:
- **Sorted by timestamp**: `df = df.sort_index()`
- **No duplicates**: `df = df[~df.index.duplicated(keep='last')]`
- **Monotonic increasing**: `df.index.is_monotonic_increasing == True`

### 3. Use Time-Slice Catalogs for Updates

If you need to update data incrementally, use time-slice operations:

```python
# Only write new data
existing_end = catalog.bars(...)[-1].ts_event
new_bars = [b for b in bars if b.ts_event > existing_end]
catalog.write_data(new_bars)
```

### 4. Add Catalog Validation in Backtest

Before running backtest, validate catalog data:

```python
bars = catalog.bars(instrument_ids=[instrument_id])
timestamps = [b.ts_event for b in bars]

# Check for duplicates
if len(timestamps) != len(set(timestamps)):
    print("Warning: Duplicate timestamps found in catalog")

# Check for monotonic order
if timestamps != sorted(timestamps):
    print("Warning: Catalog bars not in chronological order")
```

### 5. Production-Ready Script with Validation

```python
#!/usr/bin/env python3
"""
Production data loader with full validation
"""

import shutil
from pathlib import Path
import pandas as pd
from data_loader import BinanceDataLoader

def validate_dataframe(df: pd.DataFrame) -> bool:
    """Validate DataFrame before saving to catalog"""
    print("\n=== Validating DataFrame ===")
    
    # Check for duplicates
    duplicates = df.index.duplicated().sum()
    print(f"Duplicate timestamps: {duplicates}")
    if duplicates > 0:
        df = df[~df.index.duplicated(keep='last')]
        print(f"Removed {duplicates} duplicates")
    
    # Check monotonic order
    monotonic = df.index.is_monotonic_increasing
    print(f"Monotonic increasing: {monotonic}")
    if not monotonic:
        df = df.sort_index()
        print("Sorted by timestamp")
    
    # Check for gaps
    if len(df) > 1:
        time_diffs = df.index.to_series().diff()
        expected_diff = pd.Timedelta(minutes=15)
        gaps = time_diffs[time_diffs > expected_diff * 2]
        if len(gaps) > 0:
            print(f"Warning: Found {len(gaps)} time gaps > 30 minutes")
    
    print(f"Final shape: {df.shape}")
    print(f"Time range: {df.index[0]} to {df.index[-1]}")
    print("===========================\n")
    
    return df

def main():
    # Delete old catalog
    catalog_path = Path("./data/catalog")
    if catalog_path.exists():
        print(f"Deleting old catalog: {catalog_path}")
        shutil.rmtree(catalog_path)
    
    # Download fresh data
    loader = BinanceDataLoader("./data/catalog")
    print("Downloading data from Binance...")
    df = loader.download_historical_data(days=100)
    
    # Validate DataFrame
    df = validate_dataframe(df)
    
    # Save to catalog
    print("Saving to catalog...")
    loader.save_to_catalog(df)
    
    # Verify load
    print("Verifying catalog load...")
    loaded_df = loader.load_from_catalog()
    print(f"✓ Successfully loaded {len(loaded_df)} bars")
    
    return df

if __name__ == "__main__":
    main()
```

## Additional Debugging

If you still encounter errors:

```python
# Check catalog contents
catalog = ParquetDataCatalog("./data/catalog")
bars = catalog.bars(instrument_ids=[instrument_id])

# Print bar info
print(f"Total bars: {len(bars)}")
if len(bars) > 0:
    print(f"First bar: {bars[0]}")
    print(f"Last bar: {bars[-1]}")
    
    # Check for overlaps
    for i in range(len(bars) - 1):
        if bars[i].ts_init >= bars[i+1].ts_init:
            print(f"Overlap found at index {i}")
            print(f"  Bar {i}: ts_init={bars[i].ts_init}")
            print(f"  Bar {i+1}: ts_init={bars[i+1].ts_init}")
```

This fix ensures:
1. Complete catalog cleanup (deletes entire directory)
2. Data validation (sort, dedupe)
3. Fresh catalog initialization
4. Production-ready error handling
