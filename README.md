# Trading System - Quick Start Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- Trading 212 API key (optional for paper trading)
- 2GB RAM minimum

## Quick Start (5 minutes)

### Option 1: Docker (Recommended)

```bash
# Clone and setup
cd trading-system
cp .env.example .env

# Update API key if you have one (otherwise leave as-is for paper trading)
# nano .env

# Start all services
docker-compose up -d

# Check services are running
curl http://localhost:8000/health

# Access dashboard
# http://localhost:8501
```

### Option 2: Local Python

```bash
# Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env

# Run API (Terminal 1)
python -m uvicorn app.main:app --reload

# Run Dashboard (Terminal 2)
streamlit run app/ui/dashboard.py

# Access at:
# - API: http://localhost:8000
# - Dashboard: http://localhost:8501
# - Docs: http://localhost:8000/docs
```

## First Training Run

```python
# save as train_model.py
from app.training.training_pipeline import TrainingPipeline
from app.data.ingestion import DataProvider
from app.features.technical_indicators import FeatureEngineer
import logging

logging.basicConfig(level=logging.INFO)

# Download data
print("Downloading historical data...")
provider = DataProvider()
df = provider.get_historical_data(
    "AAPL",
    start_date="2023-01-01",
    end_date="2024-01-01"
)

# Engineer features
print("Engineering features...")
engineer = FeatureEngineer(feature_set="standard")
features_df = engineer.engineer_features(df)

# Create target: 1 if price goes up next day
features_df["target"] = (
    features_df["close"].shift(-1) > features_df["close"]
).astype(int)
features_df = features_df.dropna()

# Train model
print("Training model...")
pipeline = TrainingPipeline(model_type="xgboost")
model, report = pipeline.run(
    df=features_df,
    tune_hyperparams=True,
    n_trials=30,
)

# Save
model.save("models/model.pkl")
print("✅ Model saved!")
print(f"Test Accuracy: {report['test_metrics']['accuracy']:.2%}")
print(f"Test F1: {report['test_metrics']['f1']:.2%}")
```

Run it:
```bash
python train_model.py
```

## First Backtest

```python
# save as backtest.py
from app.backtest.engine import BacktestEngine
from app.data.ingestion import DataProvider
from app.features.technical_indicators import FeatureEngineer
from app.models.prediction_models import create_model
import pandas as pd

# Get data
provider = DataProvider()
df = provider.get_historical_data("AAPL", start_date="2023-01-01")

# Engineer features
engineer = FeatureEngineer()
df = engineer.engineer_features(df)

# Load model
model = create_model("xgboost")
model = model.load("models/model.pkl")

# Generate signals
df["proba"] = model.predict_proba(df[[c for c in df.columns if c not in ['open','high','low','close','volume']]])[:, 1]
df["signal"] = df["proba"].apply(lambda x: "BUY" if x > 0.6 else ("SELL" if x < 0.4 else "HOLD"))

# Backtest
engine = BacktestEngine(initial_capital=10000)
result = engine.backtest(df, signal_col="signal")

# Print results
print(f"Total Trades: {result.total_trades}")
print(f"Win Rate: {result.win_rate:.2%}")
print(f"Total P&L: ${result.total_pnl:.2f}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.max_drawdown:.2%}")
```

Run it:
```bash
python backtest.py
```

## Configuration

Edit `.env` to configure:

```bash
# Risk settings
RISK__MAX_CONCURRENT_POSITIONS=3
RISK__MAX_DAILY_LOSS_PCT=0.02  # 2% max daily loss
RISK__MAX_POSITION_SIZE=0.05   # 5% per trade

# Trading
TRADING_ENABLED=false           # Always start with false
PAPER_TRADING=true              # Use paper trading first
SYMBOLS=AAPL,MSFT,GOOGL

# ML
ML__MODEL_TYPE=xgboost
ML__FEATURE_SET=standard

# API (if using Trading 212)
TRADING212__API_KEY=your_key_here
TRADING212__DEMO_MODE=true
```

## Dashboard Features

Once running, access at `http://localhost:8501`:

- **Account**: View balance, P&L, positions
- **Model**: Check accuracy, feature importance
- **Backtest**: Review historical performance
- **Logs**: Monitor system activity
- **Settings**: Configure parameters

## Common Tasks

### Check API Health
```bash
curl http://localhost:8000/health
```

### View API Documentation
```
http://localhost:8000/docs
```

### Get Account Info
```bash
curl http://localhost:8000/account
```

### View Positions
```bash
curl http://localhost:8000/positions
```

### Run Tests
```bash
pytest tests/ -v
```

### View Logs
```bash
tail -f logs/trading_system.log
```

## Next Steps

1. ✅ Run training and backtest above
2. 🧪 Test paper trading with small capital
3. 📊 Review backtest metrics and optimize
4. 🔒 Ensure risk management is correct
5. 📈 Paper trade for 2-4 weeks
6. 💰 Deploy with real capital (if confident)

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change port in .env
```

### Missing talib
```bash
# Install system dependencies
pip install ta-lib

# If pip install fails, use conda
conda install -c conda-forge ta-lib
```

### Docker Issues
```bash
# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Database Connection Error
```bash
# Wait for postgres to start
docker-compose up postgres
sleep 10
docker-compose up

# Or check postgres is healthy
docker-compose ps
```

## Resources

- **API Docs**: http://localhost:8000/docs (when running)
- **Architecture**: See `ARCHITECTURE.md`
- **Code**: Well-commented in each module
- **Tests**: `tests/` directory for examples

## Security Warnings

⚠️ **Before trading with real money:**
- Never hardcode API keys (use .env)
- Always use paper trading first
- Test with small amounts
- Monitor continuously
- Ensure proper risk limits are set
- Understand regulations in your jurisdiction

---

**Happy Trading! 🚀**

For issues, check logs and documentation.

## License

This project is licensed under the MIT License.
