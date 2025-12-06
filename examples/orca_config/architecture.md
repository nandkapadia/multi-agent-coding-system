# Trading System Architecture

## Overview

This is a modular algorithmic trading platform using a **mixin-based architecture** for composable strategy components.

## Core Layers

```
┌─────────────────────────────────────────────────────────────┐
│                      API / CLI Layer                         │
│  FastAPI endpoints, CLI commands, WebSocket feeds            │
├─────────────────────────────────────────────────────────────┤
│                    Strategy Layer                            │
│  BaseStrategy + SignalMixins + FeatureMixins                │
├─────────────────────────────────────────────────────────────┤
│                   Execution Layer                            │
│  OrderManager, BrokerClient, RiskManager                    │
├─────────────────────────────────────────────────────────────┤
│                     Data Layer                               │
│  DataPipeline, MarketDataFeed, HistoricalDataLoader         │
├─────────────────────────────────────────────────────────────┤
│                   Storage Layer                              │
│  PostgreSQL (trades), Redis (state), TimescaleDB (ticks)    │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Patterns

### Mixin Composition

Strategies are built by composing mixins:

```python
class MyStrategy(
    BaseStrategy,
    MomentumSignalMixin,      # Signal generation
    RSIFeatureMixin,          # Feature: RSI
    BollingerFeatureMixin,    # Feature: Bollinger Bands
):
    pass
```

### Data Flow

1. **MarketDataFeed** → Raw ticks/bars
2. **DataPipeline** → Cleaned, aligned DataFrames
3. **FeatureMixins** → Derived features (RSI, MACD, etc.)
4. **SignalMixins** → Trading signals (BUY/SELL/HOLD)
5. **BaseStrategy** → Order decisions
6. **RiskManager** → Risk checks
7. **OrderManager** → Order execution
8. **BrokerClient** → Broker API

### Module Dependencies

```
strategies/
├── base.py           # BaseStrategy - all strategies inherit from this
├── momentum.py       # MomentumStrategy implementation
└── mean_reversion.py # MeanReversionStrategy implementation

mixins/
├── signals/
│   ├── base.py       # SignalMixin base class
│   ├── momentum.py   # MomentumSignalMixin
│   └── volume.py     # VolumeSignalMixin
└── features/
    ├── base.py       # FeatureMixin base class
    ├── rsi.py        # RSIFeatureMixin
    ├── macd.py       # MACDFeatureMixin
    └── bollinger.py  # BollingerFeatureMixin

execution/
├── order_manager.py  # Order lifecycle management
├── broker_client.py  # Broker API abstraction
└── risk_manager.py   # Position/risk limits

data/
├── pipeline.py       # DataPipeline - main data orchestration
├── feeds/            # Real-time data feeds
└── loaders/          # Historical data loaders
```

## Critical Paths

These are the highest-risk code paths:

1. **Order Execution** (`execution/order_manager.py`)
   - Money is at stake
   - Must handle partial fills, rejections, timeouts

2. **Risk Management** (`execution/risk_manager.py`)
   - Prevents catastrophic losses
   - Must never be bypassed

3. **Data Pipeline** (`data/pipeline.py`)
   - Lookahead bias can invalidate backtests
   - Missing data handling is critical

4. **Signal Generation** (`mixins/signals/`)
   - Logic bugs = bad trades
   - Must handle edge cases (no data, NaN values)

## Testing Strategy

- **Unit tests**: Each mixin independently
- **Integration tests**: Strategy + data pipeline
- **Backtest validation**: Known strategies on known data
- **Paper trading**: Live data, simulated execution
