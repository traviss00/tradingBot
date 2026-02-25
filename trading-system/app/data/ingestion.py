"""Data ingestion and management."""

import logging
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path

from app.core.exceptions import DataException
from app.core.config import settings


logger = logging.getLogger(__name__)


class DataProvider:
    """Fetch and manage market data."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize data provider.
        
        Args:
            cache_dir: Directory to cache data
        """
        self.cache_dir = Path(cache_dir or "data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_historical_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        
        Args:
            symbol: Stock symbol (e.g., AAPL)
            start_date: Start date
            end_date: End date
            interval: 1m, 5m, 15m, 1h, 1d, etc.
            use_cache: Use cached data if available
            
        Returns:
            DataFrame with OHLCV columns
        """
        cache_file = self._get_cache_path(symbol, interval)
        
        # Try cache first
        if use_cache and cache_file.exists():
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            if len(df) > 0:
                logger.info(f"Loaded {len(df)} rows from cache for {symbol}")
                return df
        
        # Fetch from yfinance
        try:
            logger.info(f"Fetching {symbol} from {start_date} to {end_date}")
            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False,
            )
            
            if df.empty:
                raise DataException(f"No data found for {symbol}")
            
            # Standardize column names
            df.columns = [col.lower() for col in df.columns]
            
            # Ensure required columns
            required_cols = ["open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in required_cols):
                raise DataException(f"Missing OHLCV columns for {symbol}")
            
            # Cache the data
            df.to_csv(cache_file)
            logger.info(f"Cached {len(df)} rows for {symbol}")
            
            return df
        
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise DataException(f"Failed to fetch data for {symbol}: {e}")
    
    def _get_cache_path(self, symbol: str, interval: str) -> Path:
        """Get cache file path for symbol."""
        return self.cache_dir / f"{symbol}_{interval}.csv"
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate OHLCV data integrity.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid
            
        Raises:
            DataException: If data is invalid
        """
        if df.empty:
            raise DataException("DataFrame is empty")
        
        required_cols = ["open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_cols):
            raise DataException(f"Missing required columns: {required_cols}")
        
        # Check for NaN values
        if df[required_cols].isna().any().any():
            logger.warning("Found NaN values in data, forward filling")
            df[required_cols] = df[required_cols].fillna(method="ffill")
        
        # Check OHLC integrity
        if (df["high"] < df["low"]).any():
            raise DataException("High price < Low price detected")
        
        if (df["high"] < df["close"]).any() or (df["low"] > df["close"]).any():
            logger.warning("Close price outside high-low range, adjusting")
            df["high"] = df[["high", "close"]].max(axis=1)
            df["low"] = df[["low", "close"]].min(axis=1)
        
        return True


class DataSplitter:
    """Time-series aware data splitting."""
    
    @staticmethod
    def time_series_split(
        df: pd.DataFrame,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data into train/val/test maintaining time order.
        
        Args:
            df: Full dataset
            train_ratio: Training set ratio
            val_ratio: Validation set ratio
            
        Returns:
            (train_df, val_df, test_df)
        """
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        train = df.iloc[:train_end]
        val = df.iloc[train_end:val_end]
        test = df.iloc[val_end:]
        
        logger.info(f"Train: {len(train)} | Val: {len(val)} | Test: {len(test)}")
        
        return train, val, test
    
    @staticmethod
    def walk_forward_split(
        df: pd.DataFrame,
        train_window: int,
        test_window: int,
        step: int = 1,
    ) -> list[tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generate walk-forward splits for validation.
        
        Args:
            df: Full dataset
            train_window: Training window size (days)
            test_window: Test window size (days)
            step: Step size for sliding window
            
        Returns:
            List of (train, test) splits
        """
        splits = []
        
        for i in range(0, len(df) - train_window - test_window, step):
            train = df.iloc[i : i + train_window]
            test = df.iloc[i + train_window : i + train_window + test_window]
            
            if len(test) >= test_window:
                splits.append((train, test))
        
        logger.info(f"Generated {len(splits)} walk-forward splits")
        return splits


class DataCleaner:
    """Clean and preprocess market data."""
    
    @staticmethod
    def remove_gaps(df: pd.DataFrame, threshold: float = 0.05) -> pd.DataFrame:
        """
        Remove or fill price gaps > threshold.
        
        Args:
            df: DataFrame with OHLCV
            threshold: Gap threshold as percentage
            
        Returns:
            Cleaned DataFrame
        """
        df = df.copy()
        
        # Calculate gaps
        gaps = abs((df["open"] - df["close"].shift(1)) / df["close"].shift(1))
        large_gaps = gaps[gaps > threshold].index
        
        if len(large_gaps) > 0:
            logger.warning(f"Found {len(large_gaps)} large gaps, filling forward")
            df.loc[large_gaps, "open"] = df.loc[large_gaps, "close"].shift(1)
        
        return df
    
    @staticmethod
    def handle_outliers(df: pd.DataFrame, column: str, z_threshold: float = 3) -> pd.DataFrame:
        """
        Handle price outliers using Z-score.
        
        Args:
            df: DataFrame with OHLCV
            column: Column to check (e.g., 'close')
            z_threshold: Z-score threshold
            
        Returns:
            DataFrame with outliers handled
        """
        df = df.copy()
        
        from scipy import stats
        z_scores = np.abs(stats.zscore(df[column]))
        outliers = z_scores > z_threshold
        
        if outliers.any():
            logger.warning(f"Found {outliers.sum()} outliers in {column}")
            df.loc[outliers, column] = df.loc[outliers, column].rolling(
                window=3, center=True
            ).mean()
        
        return df
