---
description: How to implement a SignalMixin for generating trading signals
examples:
  - src/mixins/signals/momentum.py
  - src/mixins/signals/volume.py
related_files:
  - src/mixins/signals/base.py
  - src/strategies/base.py
---

# Implementing a SignalMixin

SignalMixins generate trading signals (BUY, SELL, HOLD) based on market data and computed features.

## Base Class

All SignalMixins inherit from `SignalMixinBase`:

```python
# src/mixins/signals/base.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
import pandas as pd

class Signal(Enum):
    BUY = 1
    SELL = -1
    HOLD = 0

class SignalMixinBase(ABC):
    """Base class for all signal-generating mixins."""

    @abstractmethod
    def compute_signal(self, data: pd.DataFrame) -> Signal:
        """Compute trading signal from current data.

        Args:
            data: DataFrame with OHLCV and any computed features.
                  Index is timestamp, latest row is current bar.

        Returns:
            Signal enum value (BUY, SELL, or HOLD)
        """
        pass

    def validate_data(self, data: pd.DataFrame, required_columns: list[str]) -> bool:
        """Check that required columns exist and have valid data."""
        for col in required_columns:
            if col not in data.columns:
                return False
            if data[col].isna().all():
                return False
        return True
```

## Implementation Pattern

Here's how to implement a new SignalMixin:

```python
# src/mixins/signals/my_signal.py
from typing import Optional
import pandas as pd

from src.mixins.signals.base import SignalMixinBase, Signal

class MySignalMixin(SignalMixinBase):
    """Generate signals based on [describe your logic].

    This mixin requires the following features to be computed:
    - feature_1: Description of feature 1
    - feature_2: Description of feature 2

    Parameters:
        threshold: Signal threshold (default: 0.5)
        lookback: Number of bars to consider (default: 20)
    """

    # Declare required features (for validation)
    REQUIRED_FEATURES = ["feature_1", "feature_2"]

    def __init__(self, threshold: float = 0.5, lookback: int = 20):
        self.threshold = threshold
        self.lookback = lookback

    def compute_signal(self, data: pd.DataFrame) -> Signal:
        """Compute signal from data.

        Logic:
        - BUY when [condition]
        - SELL when [condition]
        - HOLD otherwise
        """
        # 1. Validate required data exists
        if not self.validate_data(data, self.REQUIRED_FEATURES):
            return Signal.HOLD

        # 2. Get current values (latest row)
        current = data.iloc[-1]

        # 3. Apply signal logic
        if current["feature_1"] > self.threshold:
            return Signal.BUY
        elif current["feature_1"] < -self.threshold:
            return Signal.SELL
        else:
            return Signal.HOLD
```

## Key Requirements

### 1. Always Validate Data

Never assume data exists or is valid:

```python
def compute_signal(self, data: pd.DataFrame) -> Signal:
    # Check minimum data length
    if len(data) < self.lookback:
        return Signal.HOLD

    # Check required columns
    if not self.validate_data(data, self.REQUIRED_FEATURES):
        return Signal.HOLD

    # Check for NaN in current row
    current = data.iloc[-1]
    if current[self.REQUIRED_FEATURES].isna().any():
        return Signal.HOLD

    # Now safe to compute signal
    ...
```

### 2. Avoid Lookahead Bias

Only use data that would have been available at the time:

```python
# WRONG - uses future data
def compute_signal(self, data: pd.DataFrame) -> Signal:
    future_avg = data["close"].mean()  # Includes future!
    ...

# CORRECT - only uses past data
def compute_signal(self, data: pd.DataFrame) -> Signal:
    past_avg = data["close"].iloc[:-1].mean()  # Excludes current
    ...
```

### 3. Handle Edge Cases

```python
def compute_signal(self, data: pd.DataFrame) -> Signal:
    # Empty data
    if data.empty:
        return Signal.HOLD

    # Insufficient history
    if len(data) < self.lookback:
        return Signal.HOLD

    # All NaN values
    if data["close"].isna().all():
        return Signal.HOLD

    # Proceed with signal logic
    ...
```

### 4. Document Dependencies

Clearly document which FeatureMixins are required:

```python
class MACDSignalMixin(SignalMixinBase):
    """Signal based on MACD crossovers.

    Required FeatureMixins:
        - MACDFeatureMixin: Provides 'macd', 'macd_signal', 'macd_hist' columns

    Usage:
        class MyStrategy(BaseStrategy, MACDFeatureMixin, MACDSignalMixin):
            pass
    """
```

## Testing Your SignalMixin

```python
# tests/mixins/signals/test_my_signal.py
import pytest
import pandas as pd
from src.mixins.signals.my_signal import MySignalMixin, Signal

class TestMySignalMixin:
    def test_buy_signal(self):
        mixin = MySignalMixin(threshold=0.5)
        data = pd.DataFrame({
            "close": [100, 101, 102],
            "feature_1": [0.3, 0.4, 0.6],  # Above threshold
            "feature_2": [1.0, 1.0, 1.0],
        })
        assert mixin.compute_signal(data) == Signal.BUY

    def test_hold_on_missing_data(self):
        mixin = MySignalMixin()
        data = pd.DataFrame({"close": [100]})  # Missing features
        assert mixin.compute_signal(data) == Signal.HOLD

    def test_hold_on_nan(self):
        mixin = MySignalMixin()
        data = pd.DataFrame({
            "close": [100],
            "feature_1": [float("nan")],
            "feature_2": [1.0],
        })
        assert mixin.compute_signal(data) == Signal.HOLD
```

## Composing with Strategy

```python
# src/strategies/my_strategy.py
from src.strategies.base import BaseStrategy
from src.mixins.features.rsi import RSIFeatureMixin
from src.mixins.signals.my_signal import MySignalMixin

class MyStrategy(BaseStrategy, RSIFeatureMixin, MySignalMixin):
    """Strategy using RSI feature and my custom signal logic."""

    def __init__(self, rsi_period: int = 14, signal_threshold: float = 0.5):
        RSIFeatureMixin.__init__(self, period=rsi_period)
        MySignalMixin.__init__(self, threshold=signal_threshold)
```
