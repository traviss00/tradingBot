"""Technical indicator feature engineering."""

import numpy as np
import pandas as pd
import talib
import logging

logger = logging.getLogger(__name__)


class TechnicalFeatures:
    """Generate technical indicator features."""
    
    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add RSI (Relative Strength Index)."""
        df[f"rsi_{period}"] = talib.RSI(df["close"], timeperiod=period)
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Add MACD (Moving Average Convergence Divergence)."""
        macd, macd_signal, macd_hist = talib.MACD(
            df["close"],
            fastperiod=fast,
            slowperiod=slow,
            signalperiod=signal,
        )
        df[f"macd_{fast}_{slow}"] = macd
        df[f"macd_signal_{signal}"] = macd_signal
        df[f"macd_hist_{fast}_{slow}_{signal}"] = macd_hist
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
        """Add Bollinger Bands."""
        upper, middle, lower = talib.BBANDS(
            df["close"],
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev,
        )
        df[f"bb_upper_{period}"] = upper
        df[f"bb_middle_{period}"] = middle
        df[f"bb_lower_{period}"] = lower
        df[f"bb_width_{period}"] = upper - lower
        df[f"bb_position_{period}"] = (df["close"] - lower) / (upper - lower)
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add ATR (Average True Range)."""
        df[f"atr_{period}"] = talib.ATR(
            df["high"],
            df["low"],
            df["close"],
            timeperiod=period,
        )
        return df
    
    @staticmethod
    def add_ema(df: pd.DataFrame, periods: list[int] = [12, 26, 50, 200]) -> pd.DataFrame:
        """Add Exponential Moving Averages."""
        for period in periods:
            df[f"ema_{period}"] = talib.EMA(df["close"], timeperiod=period)
        return df
    
    @staticmethod
    def add_sma(df: pd.DataFrame, periods: list[int] = [20, 50, 200]) -> pd.DataFrame:
        """Add Simple Moving Averages."""
        for period in periods:
            df[f"sma_{period}"] = talib.SMA(df["close"], timeperiod=period)
        return df
    
    @staticmethod
    def add_momentum(df: pd.DataFrame, period: int = 10) -> pd.DataFrame:
        """Add Momentum indicator."""
        df[f"momentum_{period}"] = talib.MOM(df["close"], timeperiod=period)
        return df
    
    @staticmethod
    def add_rate_of_change(df: pd.DataFrame, period: int = 12) -> pd.DataFrame:
        """Add Rate of Change (ROC)."""
        df[f"roc_{period}"] = talib.ROC(df["close"], timeperiod=period)
        return df
    
    @staticmethod
    def add_stochastic(df: pd.DataFrame, fastk_period: int = 14, slowk_period: int = 3, slowd_period: int = 3) -> pd.DataFrame:
        """Add Stochastic Oscillator."""
        slowk, slowd = talib.STOCH(
            df["high"],
            df["low"],
            df["close"],
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period,
        )
        df[f"stoch_k_{fastk_period}"] = slowk
        df[f"stoch_d_{fastk_period}"] = slowd
        return df
    
    @staticmethod
    def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add ADX (Average Directional Index)."""
        df[f"adx_{period}"] = talib.ADX(
            df["high"],
            df["low"],
            df["close"],
            timeperiod=period,
        )
        return df
    
    @staticmethod
    def add_obv(df: pd.DataFrame) -> pd.DataFrame:
        """Add OBV (On-Balance Volume)."""
        df["obv"] = talib.OBV(df["close"], df["volume"])
        return df


class VolumeFeatures:
    """Volume-based features."""
    
    @staticmethod
    def add_volume_sma(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Add volume SMA."""
        df[f"vol_sma_{period}"] = df["volume"].rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_volume_ratio(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Add volume ratio (current/average)."""
        vol_avg = df["volume"].rolling(window=period).mean()
        df[f"vol_ratio_{period}"] = df["volume"] / vol_avg
        return df
    
    @staticmethod
    def add_volume_spike(df: pd.DataFrame, period: int = 20, threshold: float = 2.0) -> pd.DataFrame:
        """Add volume spike indicator."""
        vol_mean = df["volume"].rolling(window=period).mean()
        vol_std = df["volume"].rolling(window=period).std()
        
        df[f"vol_spike_{period}"] = (
            (df["volume"] - vol_mean) / (vol_std + 1e-9) > threshold
        ).astype(int)
        
        return df


class PriceActionFeatures:
    """Price action features."""
    
    @staticmethod
    def add_returns(df: pd.DataFrame, periods: list[int] = [1, 5, 10, 20]) -> pd.DataFrame:
        """Add log returns."""
        for period in periods:
            df[f"returns_{period}"] = np.log(df["close"] / df["close"].shift(period))
        return df
    
    @staticmethod
    def add_volatility(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Add rolling volatility."""
        df[f"volatility_{period}"] = df["returns_1"].rolling(window=period).std()
        return df
    
    @staticmethod
    def add_high_low_ratio(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add high-low range ratio."""
        df[f"hl_ratio_{period}"] = (
            (df["high"] - df["low"]) / df["close"]
        ).rolling(window=period).mean()
        return df
    
    @staticmethod
    def add_close_position(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add close position within candle."""
        high_low_range = df["high"] - df["low"]
        close_position = (df["close"] - df["low"]) / (high_low_range + 1e-9)
        df[f"close_position_{period}"] = close_position.rolling(window=period).mean()
        return df


class FeatureEngineer:
    """Main feature engineering pipeline."""
    
    def __init__(self, feature_set: str = "standard"):
        """
        Initialize feature engineer.
        
        Args:
            feature_set: 'standard' or 'extended'
        """
        self.feature_set = feature_set
        self.features_added = []
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply feature engineering pipeline.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with engineered features
        """
        df = df.copy()
        
        # Add returns first (needed for volatility)
        df = PriceActionFeatures.add_returns(df)
        
        if self.feature_set == "standard":
            df = self._add_standard_features(df)
        elif self.feature_set == "extended":
            df = self._add_extended_features(df)
        
        # Drop NaN rows (from indicators initialization)
        df = df.dropna()
        
        logger.info(f"Generated {len(self.features_added)} features")
        
        return df
    
    def _add_standard_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add standard feature set."""
        df = TechnicalFeatures.add_rsi(df)
        df = TechnicalFeatures.add_macd(df)
        df = TechnicalFeatures.add_bollinger_bands(df)
        df = TechnicalFeatures.add_atr(df)
        df = TechnicalFeatures.add_ema(df)
        df = TechnicalFeatures.add_sma(df)
        df = VolumeFeatures.add_volume_sma(df)
        df = VolumeFeatures.add_volume_ratio(df)
        df = PriceActionFeatures.add_volatility(df)
        
        self.features_added = [col for col in df.columns if col not in ["open", "high", "low", "close", "volume"]]
        
        return df
    
    def _add_extended_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add extended feature set."""
        df = self._add_standard_features(df)
        
        df = TechnicalFeatures.add_momentum(df)
        df = TechnicalFeatures.add_rate_of_change(df)
        df = TechnicalFeatures.add_stochastic(df)
        df = TechnicalFeatures.add_adx(df)
        df = TechnicalFeatures.add_obv(df)
        df = VolumeFeatures.add_volume_spike(df)
        df = PriceActionFeatures.add_high_low_ratio(df)
        df = PriceActionFeatures.add_close_position(df)
        
        self.features_added = [col for col in df.columns if col not in ["open", "high", "low", "close", "volume"]]
        
        return df
