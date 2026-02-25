"""
Configuration management for the trading system.
Supports environment-based configuration with validation.
"""

from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    user: str = Field(default="postgres")
    password: str = Field(default="postgres")
    db: str = Field(default="trading_system")
    
    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisConfig(BaseSettings):
    """Redis cache configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: str = Field(default="")
    
    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class Trading212Config(BaseSettings):
    """Trading 212 API configuration."""
    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.trading212.com")
    account_id: str = Field(default="")
    demo_mode: bool = Field(default=True)
    request_timeout: int = Field(default=30)
    rate_limit: int = Field(default=100)  # requests per minute


class MLConfig(BaseSettings):
    """Machine learning configuration."""
    model_type: Literal["logistic_regression", "xgboost", "lightgbm", "ensemble"] = "xgboost"
    lookback_period: int = Field(default=60)  # days
    prediction_horizon: int = Field(default=1)  # candles ahead
    feature_set: str = Field(default="standard")  # standard, extended
    train_test_split: float = Field(default=0.8)
    validation_split: float = Field(default=0.1)
    random_state: int = Field(default=42)
    n_trials: int = Field(default=50)  # Optuna hyperparameter trials


class BacktestConfig(BaseSettings):
    """Backtesting configuration."""
    start_date: str = Field(default="2023-01-01")
    end_date: str = Field(default="2024-01-01")
    initial_capital: float = Field(default=10000.0)
    commission: float = Field(default=0.001)  # 0.1%
    slippage: float = Field(default=0.0005)  # 0.05%
    timeframe: Literal["1h", "4h", "1d"] = "1d"


class RiskConfig(BaseSettings):
    """Risk management configuration."""
    max_position_size: float = Field(default=0.05)  # 5% of capital per trade
    min_position_size: float = Field(default=100.0)  # minimum dollar amount
    max_concurrent_positions: int = Field(default=3)
    max_daily_loss_pct: float = Field(default=0.02)  # 2% daily max loss
    stop_loss_atr_multiple: float = Field(default=2.0)
    take_profit_risk_reward: float = Field(default=2.0)
    volatility_adjustment: bool = Field(default=True)


class Settings(BaseSettings):
    """Main application settings."""
    
    # App
    app_name: str = "Trading System"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False)
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = Field(default="INFO")
    
    # Security
    jwt_secret: str = Field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24)
    api_key_header: str = Field(default="X-API-Key")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=4)
    
    # Subconfigs
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    trading212: Trading212Config = Trading212Config()
    ml: MLConfig = MLConfig()
    backtest: BacktestConfig = BacktestConfig()
    risk: RiskConfig = RiskConfig()
    
    # Monitoring
    enable_prometheus: bool = Field(default=True)
    metrics_port: int = Field(default=8001)
    
    # Trading
    trading_enabled: bool = Field(default=False)  # Safety flag
    paper_trading: bool = Field(default=True)
    symbols: list[str] = Field(default_factory=lambda: ["AAPL", "MSFT", "GOOGL"])
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False


def get_settings() -> Settings:
    """Load and cache settings."""
    return Settings()


# Singleton instance
settings = get_settings()
