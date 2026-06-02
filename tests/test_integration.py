"""Integration tests."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestIntegration:
    """Integration tests for full pipeline."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for integration testing."""
        dates = pd.date_range(start="2023-01-01", periods=500, freq="D")
        close = 100 + np.cumsum(np.random.randn(500) * 0.5)
        
        df = pd.DataFrame({
            "open": close + np.random.randn(500) * 0.1,
            "high": close + abs(np.random.randn(500) * 0.3),
            "low": close - abs(np.random.randn(500) * 0.3),
            "close": close,
            "volume": np.random.randint(1000000, 10000000, 500),
        }, index=dates)
        
        return df
    
    def test_full_pipeline(self, sample_data):
        """Test complete data -> features -> model -> backtest pipeline."""
        from app.features.technical_indicators import FeatureEngineer
        from app.models.prediction_models import create_model
        from app.training.training_pipeline import ModelTrainer
        from app.backtest.engine import BacktestEngine
        
        # Feature engineering
        engineer = FeatureEngineer(feature_set="standard")
        features_df = engineer.engineer_features(sample_data)
        
        # Create target (simple: 1 if next close > current close else 0)
        features_df["target"] = (
            features_df["close"].shift(-1) > features_df["close"]
        ).astype(int)
        features_df = features_df.dropna()
        
        # Train model
        trainer = ModelTrainer(model_type="xgboost")
        X_train, X_test, y_train, y_test = trainer.prepare_training_data(
            features_df,
            test_size=0.2,
        )
        
        trainer.train(X_train, y_train)
        
        # Generate predictions
        predictions = trainer.model.predict(X_test)
        
        assert len(predictions) == len(y_test)
        assert all(p in [0, 1] for p in predictions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
