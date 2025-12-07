---
description: How to implement a FeatureMixin for computing derived market features
examples:
  - src/mixins/features/rsi.py
  - src/mixins/features/bollinger.py
  - src/mixins/features/macd.py
related_files:
  - src/mixins/features/base.py
  - src/data/pipeline.py
---

# Implementing a FeatureMixin

FeatureMixins compute derived features from raw market data (OHLCV). These features are then used by SignalMixins to generate trading signals.

## Base Class

All FeatureMixins inherit from `FeatureMixinBase`:

```python
# src/mixins/features/base.py
from abc import ABC, abstractmethod
from typing import List
import pandas as pd

class FeatureMixinBase(ABC):
    """Base class for all feature-computing mixins."""

    @property
    @abstractmethod
    def feature_columns(self) -> List[str]:
        """Return list of column names this mixin adds to the DataFrame."""
        pass

    @abstractmethod
    def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute features and add them to the DataFrame.

        Args:
            data: DataFrame with at minimum OHLCV columns:
                  - open, high, low, close, volume
                  - Index should be timestamp

        Returns:
            DataFrame with new feature columns added.
            Original data should not be modified (return a copy).
        """
        pass

    def validate_ohlcv(self, data: pd.DataFrame) -> bool:
        """Check that required OHLCV columns exist."""
        required = ["open", "high", "low", "close", "volume"]
        return all(col in data.columns for col in required)
```

## Implementation Pattern

Here's how to implement a new FeatureMixin:

```python
# src/mixins/features/my_feature.py
from typing import List
import pandas as pd
import numpy as np

from src.mixins.features.base import FeatureMixinBase

class MyFeatureMixin(FeatureMixinBase):
    """Compute [describe your feature].

    This mixin adds the following columns:
    - my_feature: Description of the feature
    - my_feature_signal: Optional secondary output

    Parameters:
        period: Lookback period for calculation (default: 14)
        smoothing: Smoothing factor (default: 2)
    """

    def __init__(self, period: int = 14, smoothing: int = 2):
        self.period = period
        self.smoothing = smoothing

    @property
    def feature_columns(self) -> List[str]:
        """Columns added by this mixin."""
        return ["my_feature", "my_feature_signal"]

    def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute my_feature from OHLCV data."""
        # 1. Validate input
        if not self.validate_ohlcv(data):
            raise ValueError("Data must contain OHLCV columns")

        # 2. Create a copy to avoid modifying original
        result = data.copy()

        # 3. Compute the feature
        # Example: Simple moving average ratio
        sma = result["close"].rolling(window=self.period).mean()
        result["my_feature"] = (result["close"] - sma) / sma

        # 4. Compute secondary outputs if any
        result["my_feature_signal"] = result["my_feature"].rolling(
            window=self.smoothing
        ).mean()

        return result
```

## Key Requirements

### 1. Always Return a Copy

Never modify the input DataFrame in place:

```python
# WRONG - modifies original
def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
    data["my_feature"] = ...  # Modifies original!
    return data

# CORRECT - works on copy
def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["my_feature"] = ...
    return result
```

### 2. Handle Insufficient Data Gracefully

Features that require lookback periods will produce NaN for initial rows:

```python
def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()

    # This produces NaN for first (period-1) rows - that's OK!
    result["sma"] = result["close"].rolling(window=self.period).mean()

    # Don't try to fill or drop NaN here - let SignalMixin handle it
    return result
```

### 3. Avoid Lookahead Bias

This is critical! Only use past/present data, never future:

```python
# WRONG - center=True uses future data!
result["sma"] = result["close"].rolling(window=20, center=True).mean()

# CORRECT - only uses past data
result["sma"] = result["close"].rolling(window=20, center=False).mean()

# WRONG - shift(-1) uses future data!
result["next_return"] = result["close"].pct_change().shift(-1)

# CORRECT - shift(1) uses past data
result["prev_return"] = result["close"].pct_change().shift(1)
```

### 4. Use Vectorized Operations

Avoid loops - use pandas/numpy vectorized operations for performance:

```python
# WRONG - slow loop
def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["my_feature"] = 0.0
    for i in range(self.period, len(result)):
        result.iloc[i, result.columns.get_loc("my_feature")] = (
            result["close"].iloc[i-self.period:i].mean()
        )
    return result

# CORRECT - fast vectorized
def compute_features(self, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["my_feature"] = result["close"].rolling(window=self.period).mean()
    return result
```

### 5. Document Dependencies and Outputs

```python
class BollingerFeatureMixin(FeatureMixinBase):
    """Compute Bollinger Bands.

    Input Requirements:
        - close: Closing prices

    Output Columns:
        - bb_middle: Middle band (SMA)
        - bb_upper: Upper band (middle + num_std * std)
        - bb_lower: Lower band (middle - num_std * std)
        - bb_width: Band width ((upper - lower) / middle)
        - bb_pct: %B indicator ((close - lower) / (upper - lower))

    Parameters:
        period: SMA period (default: 20)
        num_std: Number of standard deviations (default: 2.0)
    """
```

## Common Feature Patterns

### Moving Averages

```python
# Simple Moving Average
result["sma_20"] = result["close"].rolling(window=20).mean()

# Exponential Moving Average
result["ema_20"] = result["close"].ewm(span=20, adjust=False).mean()

# Volume-Weighted Moving Average
result["vwma_20"] = (
    (result["close"] * result["volume"]).rolling(window=20).sum() /
    result["volume"].rolling(window=20).sum()
)
```

### Momentum Indicators

```python
# Rate of Change
result["roc_10"] = result["close"].pct_change(periods=10) * 100

# Momentum
result["momentum_10"] = result["close"] - result["close"].shift(10)

# RSI (Relative Strength Index)
delta = result["close"].diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
result["rsi_14"] = 100 - (100 / (1 + rs))
```

### Volatility Indicators

```python
# ATR (Average True Range)
high_low = result["high"] - result["low"]
high_close = (result["high"] - result["close"].shift()).abs()
low_close = (result["low"] - result["close"].shift()).abs()
true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
result["atr_14"] = true_range.rolling(window=14).mean()

# Historical Volatility
result["hvol_20"] = result["close"].pct_change().rolling(window=20).std() * np.sqrt(252)
```

## Testing Your FeatureMixin

```python
# tests/mixins/features/test_my_feature.py
import pytest
import pandas as pd
import numpy as np
from src.mixins.features.my_feature import MyFeatureMixin

class TestMyFeatureMixin:
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        return pd.DataFrame({
            "open": np.random.randn(100).cumsum() + 100,
            "high": np.random.randn(100).cumsum() + 101,
            "low": np.random.randn(100).cumsum() + 99,
            "close": np.random.randn(100).cumsum() + 100,
            "volume": np.random.randint(1000, 10000, 100),
        }, index=dates)

    def test_adds_expected_columns(self, sample_data):
        mixin = MyFeatureMixin(period=14)
        result = mixin.compute_features(sample_data)

        assert "my_feature" in result.columns
        assert "my_feature_signal" in result.columns

    def test_does_not_modify_input(self, sample_data):
        mixin = MyFeatureMixin()
        original_cols = list(sample_data.columns)

        result = mixin.compute_features(sample_data)

        assert list(sample_data.columns) == original_cols
        assert "my_feature" not in sample_data.columns

    def test_nan_for_insufficient_history(self, sample_data):
        mixin = MyFeatureMixin(period=14)
        result = mixin.compute_features(sample_data)

        # First (period-1) rows should be NaN
        assert result["my_feature"].iloc[:13].isna().all()
        # After that, should have values
        assert result["my_feature"].iloc[14:].notna().all()

    def test_no_lookahead_bias(self, sample_data):
        """Verify feature at time t only uses data from times <= t."""
        mixin = MyFeatureMixin(period=14)

        # Compute on full data
        full_result = mixin.compute_features(sample_data)

        # Compute on truncated data (missing last 10 rows)
        truncated = sample_data.iloc[:-10]
        truncated_result = mixin.compute_features(truncated)

        # Values at same timestamps should be identical
        # (if there's lookahead bias, they would differ)
        common_idx = truncated_result.index
        pd.testing.assert_series_equal(
            full_result.loc[common_idx, "my_feature"],
            truncated_result["my_feature"],
        )
```

## Composing Multiple FeatureMixins

```python
# src/strategies/multi_feature_strategy.py
from src.strategies.base import BaseStrategy
from src.mixins.features.rsi import RSIFeatureMixin
from src.mixins.features.bollinger import BollingerFeatureMixin
from src.mixins.features.macd import MACDFeatureMixin
from src.mixins.signals.composite import CompositeSignalMixin

class MultiFeatureStrategy(
    BaseStrategy,
    RSIFeatureMixin,
    BollingerFeatureMixin,
    MACDFeatureMixin,
    CompositeSignalMixin,
):
    """Strategy using multiple technical indicators.

    Features computed:
    - RSI (14-period)
    - Bollinger Bands (20-period, 2 std)
    - MACD (12, 26, 9)
    """

    def __init__(self):
        RSIFeatureMixin.__init__(self, period=14)
        BollingerFeatureMixin.__init__(self, period=20, num_std=2.0)
        MACDFeatureMixin.__init__(self, fast=12, slow=26, signal=9)
        CompositeSignalMixin.__init__(self)
```
