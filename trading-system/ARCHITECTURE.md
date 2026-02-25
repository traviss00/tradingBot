# Trading System - Production Architecture

## System Overview

This is a **production-grade algorithmic trading system** designed for institutional-quality trading with strict risk management, robust backtesting, and deployment readiness.

### Key Features

- **ML-Driven**: XGBoost, LightGBM, and Logistic Regression models
- **Risk-First**: Strict position sizing, daily loss limits, max drawdown protection
- **Backtesting**: Walk-forward validation, commission/slippage simulation
- **Trading 212 Integration**: Async API client with retry logic and rate limiting
- **Paper Trading**: Simulated trading for safe testing
- **Monitoring**: Structured logging, metrics, health checks
- **Security**: JWT authentication, API key validation, bcrypt hashing
- **Containerized**: Docker + Docker Compose for local/cloud deployment

## Architecture

```
trading-system/
├── app/
│   ├── api/                    # Trading 212 API client
│   ├── core/                   # Config, logging, exceptions, utilities
│   ├── data/                   # Data ingestion and validation
│   ├── features/               # Technical indicators & regime detection
│   ├── models/                 # ML model implementations
│   ├── training/               # Training pipeline with hyperparameter tuning
│   ├── backtest/               # Backtesting engine
│   ├── execution/              # Strategy & signal generation
│   ├── risk/                   # Risk management system
│   ├── auth/                   # JWT & security
│   ├── monitoring/             # Metrics & observability
│   ├── ui/                     # Streamlit dashboard
│   └── main.py                 # FastAPI entry point
├── tests/                      # Unit & integration tests
├── docs/                       # Documentation
├── infra/                      # Infrastructure configs
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image
├── docker-compose.yml          # Local development stack
├── .env.example                # Environment template
└── README.md                   # Quick start guide
```

## Technology Stack

### Core
- **Python 3.11**: Modern, type-hinted codebase
- **pandas/numpy**: Data manipulation
- **scikit-learn**: Classical ML
- **XGBoost/LightGBM**: Gradient boosting

### ML/Training
- **Optuna**: Hyperparameter optimization
- **scikit-learn**: Feature scaling, metrics
- **MLflow**: Model tracking (optional)

### API & Web
- **FastAPI**: High-performance REST API
- **uvicorn**: ASGI server
- **Streamlit**: Interactive dashboard
- **httpx**: Async HTTP client

### Data & Storage
- **SQLAlchemy**: ORM (optional)
- **PostgreSQL**: Production database
- **Redis**: Caching & session store
- **yfinance**: Historical data (fallback)

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Local orchestration
- **pytest**: Testing framework
- **Python-Jose**: JWT handling

## Data Pipeline

### 1. Data Ingestion (`app/data/ingestion.py`)

```python
provider = DataProvider()
df = provider.get_historical_data(
    symbol="AAPL",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2024, 1, 1),
    interval="1d"
)
```

**Features:**
- Automatic caching
- Data validation & integrity checks
- Gap & outlier handling
- Time-series aware splitting

### 2. Feature Engineering (`app/features/`)

**Standard Features:**
- RSI, MACD, Bollinger Bands
- ATR, EMA/SMA
- Volume ratios
- Returns & volatility

**Extended Features:**
- Momentum, ROC, Stochastic
- ADX, OBV
- High-low ratios
- Close position

**Regime Detection:**
- Volatility regimes (low/normal/high)
- Trend detection
- Mean reversion signals
- Regime change alerts

### 3. Model Training (`app/training/`)

```python
pipeline = TrainingPipeline(model_type="xgboost")
model, report = pipeline.run(
    df=features_df,
    target_col="target",
    tune_hyperparams=True,
    n_trials=50,
)
```

**Validation:**
- Walk-forward validation
- Time-series splits
- Hyperparameter tuning with Optuna
- Feature importance analysis

### 4. Backtesting (`app/backtest/engine.py`)

```python
engine = BacktestEngine(initial_capital=10000)
result = engine.backtest(
    df=signals_df,
    signal_col="signal",
    price_col="close",
)

print(f"Win Rate: {result.win_rate:.2%}")
print(f"Sharpe: {result.sharpe_ratio:.2f}")
print(f"Max DD: {result.max_drawdown:.2%}")
```

**Metrics:**
- Total P&L and return percentage
- Win rate, profit factor
- Sharpe ratio, Sortino ratio
- Max drawdown
- CAGR

## Strategy Layer

### Signal Generation (`app/execution/strategy.py`)

```python
strategy = TradingStrategy(model=trained_model)
signal, confidence = strategy.generate_signal(
    df=features_df,
    symbol="AAPL",
    confidence_threshold=0.55,
)
```

**Filters Applied:**
- Volatility regime filtering
- Trend detection
- Mean reversion in sideways markets
- High volatility shock avoidance

### Execution (`app/execution/strategy.py`)

```python
executor = ExecutionManager(api_client=client)
await executor.execute_signal(
    symbol="AAPL",
    signal=Signal.BUY,
    price=150.0,
    quantity=10,
    stop_loss=148.0,
    take_profit=155.0,
)
```

## Risk Management (`app/risk/position_management.py`)

### Position Sizing

**By Risk Percentage:**
```python
sizer = PositionSizer()
size = sizer.calculate_size_by_risk(
    capital=100000,
    stop_loss_price=148.0,
    entry_price=150.0,
    risk_pct=0.01,  # 1% risk
)
```

**By Volatility:**
```python
size = sizer.calculate_size_by_volatility(
    capital=100000,
    atr=2.5,
    price=150.0,
)
```

### Stop Loss & Take Profit

```python
sl = StopLossTakeProfitCalculator.calculate_atr_stop(
    price=150.0,
    atr=2.0,
    multiple=2.0,  # 2x ATR
)

tp = StopLossTakeProfitCalculator.calculate_risk_reward_target(
    entry_price=150.0,
    stop_loss_price=148.0,
    risk_reward_ratio=2.0,  # 2:1
)
```

### Risk Monitoring

```python
risk_manager = RiskManager(initial_capital=100000)

# Track position
risk_manager.open_position(
    symbol="AAPL",
    side="BUY",
    entry_price=150.0,
    quantity=10,
    stop_loss=148.0,
    take_profit=155.0,
)

# Check limits
if not risk_manager.check_daily_loss_limit():
    # Trading disabled for day
    pass
```

## API Endpoints

### Health & Status
- `GET /health` - System health check

### Authentication
- `POST /auth/login` - Login and get JWT token

### Account
- `GET /account` - Account information
- `GET /account/balance` - Current balance

### Positions
- `GET /positions` - Open positions
- `POST /positions/close/{symbol}` - Close position

### Trading
- `POST /trading/start` - Start trading
- `POST /trading/stop` - Stop trading
- `GET /trades` - Trade history

### Model
- `GET /model/status` - Model training status
- `POST /model/train` - Trigger training

### Backtest
- `GET /backtest/{symbol}` - Backtest results

### Monitoring
- `GET /metrics` - Prometheus metrics
- `GET /config` - Current configuration

## Getting Started

### 1. Setup Environment

```bash
# Clone repository
cd trading-system

# Copy environment template
cp .env.example .env

# Edit .env with your settings
# - Add Trading 212 API key
# - Configure risk parameters
# - Set symbols to trade
```

### 2. Local Development (Docker)

```bash
# Build and start services
docker-compose up -d

# Wait for services to be healthy
# - API: http://localhost:8000
# - Dashboard: http://localhost:8501
# - Postgres: localhost:5432
# - Redis: localhost:6379

# Check health
curl http://localhost:8000/health
```

### 3. Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env

# Run API server
python -m uvicorn app.main:app --reload

# In another terminal, run dashboard
streamlit run app/ui/dashboard.py
```

### 4. Train Model

```python
from app.training.training_pipeline import TrainingPipeline
from app.data.ingestion import DataProvider
from app.features.technical_indicators import FeatureEngineer

# Get data
provider = DataProvider()
df = provider.get_historical_data("AAPL", start_date="2023-01-01")

# Engineer features
engineer = FeatureEngineer()
features_df = engineer.engineer_features(df)
features_df["target"] = (features_df["close"].shift(-1) > features_df["close"]).astype(int)

# Train
pipeline = TrainingPipeline(model_type="xgboost")
model, report = pipeline.run(features_df, tune_hyperparams=True, n_trials=50)

# Save model
model.save("models/xgboost_model.pkl")
```

### 5. Run Backtest

```python
from app.backtest.engine import BacktestEngine

engine = BacktestEngine(initial_capital=100000)
result = engine.backtest(signals_df)

print(f"Total Trades: {result.total_trades}")
print(f"Win Rate: {result.win_rate:.2%}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
```

## Risk Management Guidelines

### Position Sizing
- Maximum 5% of capital per trade
- Volatility-adjusted sizing
- Never exceed 20% total invested

### Daily Limits
- Max 2% daily loss threshold
- Auto-disable trading if exceeded
- Reset at market open

### Trade Management
- 2x ATR stop loss
- 2:1 risk-reward ratio (default)
- Max 3 concurrent positions

### Drawdown Protection
- Monitor rolling 20-trade drawdown
- Alert on > 15% drawdown
- Consider strategy review at -20%

## Production Deployment

### AWS ECS

```bash
# Build image
docker build -t trading-system:latest .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag trading-system:latest <account>.dkr.ecr.<region>.amazonaws.com/trading-system:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/trading-system:latest

# Deploy with CloudFormation/Terraform
```

### Azure Container Apps

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image trading-system:latest .

# Deploy
az containerapp create --name trading-system \
  --resource-group <resource-group> \
  --image <acr-url>/trading-system:latest
```

### Kubernetes

```bash
kubectl apply -f infra/k8s/deployment.yaml
kubectl apply -f infra/k8s/service.yaml
```

## Monitoring & Observability

### Structured Logging

Logs are written to:
- `logs/trading_system.log` - All activity
- `logs/errors.log` - Errors only
- `logs/trades.log` - Trade activity

### Metrics

Prometheus-compatible metrics on port 8001:
- Open positions
- Daily P&L
- Sharpe ratio
- Win rate

### Health Checks

All services have health checks:
- API: `GET /health`
- Database: Connection test
- Redis: PING test

## Performance Targets

- **Return**: 10-25% annualized
- **Sharpe Ratio**: > 1.2
- **Max Drawdown**: < 20%
- **Win Rate**: > 55%
- **Profit Factor**: > 1.5

## Important Notes

⚠️ **This is NOT a guaranteed profit system**
- No trading system is profitable 100% of the time
- Past performance ≠ future results
- Always test in paper trading first
- Use appropriate risk management
- Monitor system continuously
- Comply with regulations in your jurisdiction

## Support & Contributing

For issues, questions, or contributions, please refer to the main README.

---

**Version**: 1.0.0  
**Last Updated**: 2024-02-25  
**Author**: Trading System Team
