"""Training pipeline with hyperparameter optimization."""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, Optional
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import optuna
from optuna.pruners import MedianPruner
from datetime import datetime
import json
from pathlib import Path

from app.models.prediction_models import create_model
from app.data.ingestion import DataSplitter
from app.core.config import settings


logger = logging.getLogger(__name__)


class ModelTrainer:
    """Train ML models with proper validation."""
    
    def __init__(self, model_type: str = "xgboost"):
        """
        Initialize trainer.
        
        Args:
            model_type: Type of model to train
        """
        self.model_type = model_type
        self.model = None
        self.metrics = {}
        self.history = []
    
    def prepare_training_data(
        self,
        df: pd.DataFrame,
        target_col: str = "target",
        test_size: float = 0.2,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Prepare training and test data.
        
        Args:
            df: Feature DataFrame
            target_col: Name of target column
            test_size: Test set size
            
        Returns:
            (X_train, X_test, y_train, y_test)
        """
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found")
        
        # Separate features and target
        y = df[target_col]
        X = df.drop(columns=[target_col])
        
        # Time-series aware split
        split_idx = int(len(df) * (1 - test_size))
        
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        
        logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")
        logger.info(f"Target distribution - Train: {y_train.value_counts().to_dict()}")
        logger.info(f"Target distribution - Test: {y_test.value_counts().to_dict()}")
        
        return X_train, X_test, y_train, y_test
    
    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ):
        """
        Train the model.
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features (optional)
            y_val: Validation target (optional)
        """
        logger.info(f"Training {self.model_type}")
        
        self.model = create_model(self.model_type)
        
        eval_set = None
        if X_val is not None and y_val is not None:
            eval_set = (X_val, y_val)
        
        self.model.train(X_train, y_train, eval_set=eval_set)
    
    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        set_name: str = "test",
    ) -> dict:
        """
        Evaluate model performance.
        
        Args:
            X_test: Test features
            y_test: Test target
            set_name: Name of dataset (for logging)
            
        Returns:
            Dictionary of metrics
        """
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)
        
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_proba[:, 1]),
        }
        
        logger.info(f"{set_name.upper()} Metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        return metrics
    
    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        window_size: int = 60,
        test_window: int = 10,
    ) -> list[dict]:
        """
        Walk-forward cross-validation.
        
        Args:
            X: Features
            y: Target
            window_size: Training window (days)
            test_window: Test window (days)
            
        Returns:
            List of metrics for each fold
        """
        splitter = DataSplitter()
        splits = splitter.walk_forward_split(
            X.assign(target=y),
            train_window=window_size,
            test_window=test_window,
        )
        
        cv_results = []
        
        for i, (train_df, test_df) in enumerate(splits):
            logger.info(f"Fold {i+1}/{len(splits)}")
            
            X_train = train_df.drop(columns=["target"])
            y_train = train_df["target"]
            X_test = test_df.drop(columns=["target"])
            y_test = test_df["target"]
            
            # Train model
            self.train(X_train, y_train)
            
            # Evaluate
            metrics = self.evaluate(X_test, y_test, set_name=f"fold_{i+1}")
            cv_results.append(metrics)
        
        # Summary
        avg_metrics = {
            k: np.mean([m[k] for m in cv_results])
            for k in cv_results[0].keys()
        }
        logger.info(f"Average CV Metrics: {avg_metrics}")
        
        return cv_results


class HyperparameterTuner:
    """Hyperparameter optimization with Optuna."""
    
    def __init__(self, model_type: str = "xgboost"):
        """Initialize tuner."""
        self.model_type = model_type
        self.best_params = {}
        self.best_score = -np.inf
        self.study = None
    
    def objective(
        self,
        trial: optuna.Trial,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> float:
        """Optuna objective function."""
        
        if self.model_type == "xgboost":
            params = {
                "max_depth": trial.suggest_int("max_depth", 4, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.5, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            }
        elif self.model_type == "lightgbm":
            params = {
                "num_leaves": trial.suggest_int("num_leaves", 20, 100),
                "learning_rate": trial.suggest_float("learning_rate", 0.001, 0.3, log=True),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
                "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            }
        else:
            return 0.0
        
        model = create_model(self.model_type, **params)
        model.train(X_train, y_train)
        
        y_pred = model.predict(X_val)
        score = accuracy_score(y_val, y_pred)
        
        return score
    
    def tune(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        n_trials: int = 50,
        timeout: Optional[int] = None,
    ) -> dict:
        """
        Run hyperparameter tuning.
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            n_trials: Number of trials
            timeout: Timeout in seconds
            
        Returns:
            Best parameters
        """
        logger.info(f"Tuning {self.model_type} with {n_trials} trials")
        
        sampler = optuna.samplers.TPESampler(seed=42)
        pruner = MedianPruner()
        
        self.study = optuna.create_study(
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
        )
        
        self.study.optimize(
            lambda trial: self.objective(trial, X_train, y_train, X_val, y_val),
            n_trials=n_trials,
            timeout=timeout,
            show_progress_bar=True,
        )
        
        self.best_params = self.study.best_params
        self.best_score = self.study.best_value
        
        logger.info(f"Best score: {self.best_score:.4f}")
        logger.info(f"Best params: {self.best_params}")
        
        return self.best_params


class TrainingPipeline:
    """End-to-end training pipeline."""
    
    def __init__(self, model_type: str = "xgboost"):
        """Initialize pipeline."""
        self.model_type = model_type
        self.trainer = ModelTrainer(model_type)
        self.tuner = HyperparameterTuner(model_type)
        self.training_report = {}
    
    def run(
        self,
        df: pd.DataFrame,
        target_col: str = "target",
        tune_hyperparams: bool = True,
        n_trials: int = 50,
    ):
        """
        Run complete training pipeline.
        
        Args:
            df: Feature DataFrame with target
            target_col: Name of target column
            tune_hyperparams: Tune hyperparameters
            n_trials: Number of tuning trials
        """
        logger.info(f"Starting training pipeline for {self.model_type}")
        
        # Prepare data
        X_train, X_test, y_train, y_test = self.trainer.prepare_training_data(
            df,
            target_col=target_col,
            test_size=0.2,
        )
        
        # Further split train for validation
        split_idx = int(len(X_train) * 0.8)
        X_tr = X_train.iloc[:split_idx]
        y_tr = y_train.iloc[:split_idx]
        X_val = X_train.iloc[split_idx:]
        y_val = y_train.iloc[split_idx:]
        
        # Hyperparameter tuning
        if tune_hyperparams:
            best_params = self.tuner.tune(X_tr, y_tr, X_val, y_val, n_trials=n_trials)
            logger.info(f"Training with best parameters: {best_params}")
            
            # Retrain with best params
            if best_params:
                self.trainer.model = create_model(self.model_type, **best_params)
            
            self.training_report["best_params"] = best_params
        
        # Final training
        self.trainer.train(X_tr, y_tr, X_val, y_val)
        
        # Evaluation
        train_metrics = self.trainer.evaluate(X_tr, y_tr, set_name="train")
        val_metrics = self.trainer.evaluate(X_val, y_val, set_name="val")
        test_metrics = self.trainer.evaluate(X_test, y_test, set_name="test")
        
        # Store report
        self.training_report.update({
            "model_type": self.model_type,
            "timestamp": datetime.now().isoformat(),
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "data_shapes": {
                "X_train": X_tr.shape,
                "X_val": X_val.shape,
                "X_test": X_test.shape,
            },
        })
        
        logger.info("Training pipeline completed")
        
        return self.trainer.model, self.training_report
    
    def save_report(self, path: str = "reports/training_report.json"):
        """Save training report."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.training_report, f, indent=2, default=str)
        logger.info(f"Saved training report to {path}")
