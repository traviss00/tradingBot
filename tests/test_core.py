"""Unit tests for trading system."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.core.utils import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_position_size,
)
from app.data.ingestion import DataProvider, DataSplitter
from app.features.technical_indicators import FeatureEngineer


class TestUtilities:
    """Test utility functions."""
    
    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation."""
        returns = [0.01, 0.02, -0.01, 0.015, 0.005]
        sharpe = calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
        assert sharpe != 0  # Should have non-zero ratio
    
    def test_calculate_max_drawdown(self):
        """Test max drawdown calculation."""
        equity = [100, 105, 103, 110, 100, 95]
        max_dd = calculate_max_drawdown(equity)
        
        assert max_dd < 0  # Drawdown is negative
        assert max_dd >= -1.0  # Max drawdown is between -1 and 0
    
    def test_calculate_position_size(self):
        """Test position size calculation."""
        capital = 100000
        risk_pct = 0.01
        stop_loss_dist = 2.0
        
        size = calculate_position_size(capital, risk_pct, stop_loss_dist)
        
        assert size > 0
        assert size == pytest.approx(500, rel=0.01)


class TestDataProcessing:
    """Test data processing."""
    
    @pytest.fixture
    def sample_ohlcv(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        close = 100 + np.cumsum(np.random.randn(100) * 0.5)
        
        df = pd.DataFrame({
            "open": close + np.random.randn(100) * 0.1,
            "high": close + abs(np.random.randn(100) * 0.3),
            "low": close - abs(np.random.randn(100) * 0.3),
            "close": close,
            "volume": np.random.randint(1000000, 10000000, 100),
        }, index=dates)
        
        return df
    
    def test_data_splitter(self, sample_ohlcv):
        """Test time-series aware data splitting."""
        train, val, test = DataSplitter.time_series_split(sample_ohlcv)
        
        assert len(train) + len(val) + len(test) == len(sample_ohlcv)
        assert len(train) > len(val) > len(test)
    
    def test_walk_forward_split(self, sample_ohlcv):
        """Test walk-forward split."""
        splits = DataSplitter.walk_forward_split(
            sample_ohlcv,
            train_window=50,
            test_window=10,
        )
        
        assert len(splits) > 0
        for train, test in splits:
            assert len(train) == 50
            assert len(test) <= 10


class TestFeatures:
    """Test feature engineering."""
    
    @pytest.fixture
    def sample_ohlcv(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=200, freq="D")
        close = 100 + np.cumsum(np.random.randn(200) * 0.5)
        
        df = pd.DataFrame({
            "open": close + np.random.randn(200) * 0.1,
            "high": close + abs(np.random.randn(200) * 0.3),
            "low": close - abs(np.random.randn(200) * 0.3),
            "close": close,
            "volume": np.random.randint(1000000, 10000000, 200),
        }, index=dates)
        
        return df
    
    def test_feature_engineering_standard(self, sample_ohlcv):
        """Test standard feature engineering."""
        engineer = FeatureEngineer(feature_set="standard")
        features_df = engineer.engineer_features(sample_ohlcv)
        
        assert len(features_df) < len(sample_ohlcv)  # Rows removed due to NaN
        assert len(features_df.columns) > 5  # Should have more columns than OHLCV
        assert not features_df.isna().any().any()  # No NaN values


class TestBacktest:
    """Test backtesting functionality."""
    
    def test_backtest_engine(self):
        """Test basic backtest engine."""
        from app.backtest.engine import BacktestEngine
        
        engine = BacktestEngine(initial_capital=10000.0)
        
        # Simulate some signals
        engine.add_signal(
            timestamp=datetime(2024, 1, 1),
            symbol="TEST",
            signal="BUY",
            price=100.0,
            quantity=10.0,
        )
        
        engine.update_position_prices({"TEST": 105.0})
        
        assert len(engine.equity_curve) > 0
        assert engine.equity_curve[-1] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
