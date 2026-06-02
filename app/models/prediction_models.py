"""Machine learning models for price prediction."""

import numpy as np
import pandas as pd
import logging
from typing import Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import xgboost as xgb
import lightgbm as lgb
import joblib
from pathlib import Path
from datetime import datetime


logger = logging.getLogger(__name__)


class BaseModel:
    """Base model class."""
    
    def __init__(self, name: str):
        self.name = name
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False
    
    def train(self, X: pd.DataFrame, y: pd.Series):
        """Train the model."""
        raise NotImplementedError
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        raise NotImplementedError
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability."""
        raise NotImplementedError
    
    def save(self, path: str):
        """Save model to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info(f"Saved {self.name} to {path}")
    
    @staticmethod
    def load(path: str):
        """Load model from disk."""
        model = joblib.load(path)
        logger.info(f"Loaded model from {path}")
        return model


class LogisticRegressionModel(BaseModel):
    """Logistic Regression for classification."""
    
    def __init__(self, **kwargs):
        super().__init__("LogisticRegression")
        self.model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            **kwargs
        )
    
    def train(self, X: pd.DataFrame, y: pd.Series):
        """Train logistic regression."""
        logger.info(f"Training {self.name}")
        
        self.feature_names = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)
        
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Log training performance
        train_score = self.model.score(X_scaled, y)
        logger.info(f"{self.name} training accuracy: {train_score:.4f}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability."""
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)


class XGBoostModel(BaseModel):
    """XGBoost for classification."""
    
    def __init__(self, **kwargs):
        super().__init__("XGBoost")
        
        default_params = {
            "objective": "binary:logistic",
            "max_depth": 6,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }
        default_params.update(kwargs)
        
        self.model = xgb.XGBClassifier(**default_params)
    
    def train(self, X: pd.DataFrame, y: pd.Series, eval_set=None):
        """Train XGBoost."""
        logger.info(f"Training {self.name}")
        
        self.feature_names = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)
        
        eval_set_scaled = None
        if eval_set:
            eval_X, eval_y = eval_set
            eval_X_scaled = self.scaler.transform(eval_X)
            eval_set_scaled = [(eval_X_scaled, eval_y)]
        
        self.model.fit(
            X_scaled,
            y,
            eval_set=eval_set_scaled,
            verbose=False,
        )
        self.is_trained = True
        
        train_score = self.model.score(X_scaled, y)
        logger.info(f"{self.name} training accuracy: {train_score:.4f}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability."""
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """Get feature importance."""
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]
        
        return pd.DataFrame({
            "feature": [self.feature_names[i] for i in indices],
            "importance": importances[indices],
        })


class LightGBMModel(BaseModel):
    """LightGBM for classification."""
    
    def __init__(self, **kwargs):
        super().__init__("LightGBM")
        
        default_params = {
            "objective": "binary",
            "metric": "auc",
            "num_leaves": 31,
            "learning_rate": 0.1,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "random_state": 42,
            "verbose": -1,
        }
        default_params.update(kwargs)
        
        self.model = lgb.LGBMClassifier(**default_params)
    
    def train(self, X: pd.DataFrame, y: pd.Series, eval_set=None):
        """Train LightGBM."""
        logger.info(f"Training {self.name}")
        
        self.feature_names = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)
        
        eval_set_scaled = None
        if eval_set:
            eval_X, eval_y = eval_set
            eval_X_scaled = self.scaler.transform(eval_X)
            eval_set_scaled = [(eval_X_scaled, eval_y)]
        
        self.model.fit(
            X_scaled,
            y,
            eval_set=eval_set_scaled,
        )
        self.is_trained = True
        
        train_score = self.model.score(X_scaled, y)
        logger.info(f"{self.name} training accuracy: {train_score:.4f}")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions."""
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability."""
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """Get feature importance."""
        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]
        
        return pd.DataFrame({
            "feature": [self.feature_names[i] for i in indices],
            "importance": importances[indices],
        })


class EnsembleModel(BaseModel):
    """Ensemble of multiple models."""
    
    def __init__(self, models: list[BaseModel] = None):
        super().__init__("Ensemble")
        self.models = models or []
    
    def add_model(self, model: BaseModel):
        """Add model to ensemble."""
        self.models.append(model)
    
    def train(self, X: pd.DataFrame, y: pd.Series, eval_set=None):
        """Train all models in ensemble."""
        logger.info(f"Training {self.name} with {len(self.models)} models")
        
        for model in self.models:
            if hasattr(model.train, '__self__'):
                # Has eval_set parameter
                model.train(X, y, eval_set=eval_set)
            else:
                model.train(X, y)
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Average predictions from all models."""
        predictions = np.array([m.predict(X) for m in self.models])
        return np.round(predictions.mean(axis=0)).astype(int)
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Average probabilities from all models."""
        probas = np.array([m.predict_proba(X) for m in self.models])
        return probas.mean(axis=0)


def create_model(model_type: str, **kwargs) -> BaseModel:
    """Factory function to create models."""
    models = {
        "logistic_regression": LogisticRegressionModel,
        "xgboost": XGBoostModel,
        "lightgbm": LightGBMModel,
    }
    
    if model_type not in models:
        raise ValueError(f"Unknown model type: {model_type}")
    
    return models[model_type](**kwargs)
