"""Regime detection and market analysis."""

import numpy as np
import pandas as pd
import logging
from sklearn.preprocessing import StandardScaler


logger = logging.getLogger(__name__)


class RegimeDetector:
    """Detect market regimes (volatility, trend, etc.)."""
    
    @staticmethod
    def volatility_regime(
        returns: pd.Series,
        window: int = 30,
        high_vol_threshold: float = 0.02,
    ) -> pd.Series:
        """
        Classify volatility regime.
        
        Args:
            returns: Daily returns
            window: Lookback window
            high_vol_threshold: Threshold for high volatility
            
        Returns:
            Series with regime: -1 (low), 0 (normal), 1 (high)
        """
        rolling_vol = returns.rolling(window=window).std()
        vol_mean = rolling_vol.mean()
        vol_std = rolling_vol.std()
        
        regime = pd.Series(0, index=returns.index)
        regime[rolling_vol < (vol_mean - vol_std)] = -1  # Low volatility
        regime[rolling_vol > (vol_mean + vol_std)] = 1   # High volatility
        
        return regime
    
    @staticmethod
    def trend_regime(prices: pd.Series, window: int = 50) -> pd.Series:
        """
        Classify trend regime.
        
        Args:
            prices: Close prices
            window: Lookback window
            
        Returns:
            Series with regime: -1 (downtrend), 0 (sideways), 1 (uptrend)
        """
        sma = prices.rolling(window=window).mean()
        
        # Use ADX-like approach
        high = prices.rolling(window=window).max()
        low = prices.rolling(window=window).min()
        range_pct = (high - low) / low
        
        # Uptrend if price above SMA and range is expanding
        regime = pd.Series(0, index=prices.index)
        regime[(prices > sma) & (range_pct > range_pct.mean())] = 1
        regime[(prices < sma) & (range_pct > range_pct.mean())] = -1
        
        return regime
    
    @staticmethod
    def mean_reversion_signal(
        prices: pd.Series,
        window: int = 20,
        std_threshold: float = 2.0,
    ) -> pd.Series:
        """
        Detect mean reversion signals.
        
        Args:
            prices: Close prices
            window: Lookback window
            std_threshold: Standard deviation threshold
            
        Returns:
            Series with signals: -1 (oversold), 0 (normal), 1 (overbought)
        """
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        
        z_score = (prices - sma) / (std + 1e-9)
        
        signal = pd.Series(0, index=prices.index)
        signal[z_score < -std_threshold] = -1  # Oversold
        signal[z_score > std_threshold] = 1    # Overbought
        
        return signal
    
    @staticmethod
    def regime_change_detection(regime: pd.Series, window: int = 5) -> pd.Series:
        """
        Detect regime changes.
        
        Args:
            regime: Regime series
            window: Window to detect change
            
        Returns:
            Boolean series indicating regime changes
        """
        regime_shift = regime.diff().abs() > 0
        return regime_shift.rolling(window=window).max().astype(bool)


class DrawdownAnalyzer:
    """Analyze drawdowns in equity curve."""
    
    @staticmethod
    def calculate_drawdowns(equity: pd.Series) -> dict:
        """
        Calculate drawdown statistics.
        
        Args:
            equity: Equity curve
            
        Returns:
            Dictionary with drawdown metrics
        """
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max
        
        return {
            "max_drawdown": drawdown.min(),
            "current_drawdown": drawdown.iloc[-1],
            "avg_drawdown": drawdown[drawdown < 0].mean(),
            "drawdown_duration": (drawdown < 0).sum(),
        }
    
    @staticmethod
    def identify_drawdown_periods(equity: pd.Series, threshold: float = 0.05) -> list:
        """
        Identify periods with drawdown > threshold.
        
        Args:
            equity: Equity curve
            threshold: Drawdown threshold
            
        Returns:
            List of drawdown periods
        """
        running_max = equity.expanding().max()
        drawdown = (equity - running_max) / running_max
        
        in_drawdown = drawdown < -threshold
        periods = []
        
        start = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start is None:
                start = i
            elif not is_dd and start is not None:
                periods.append((start, i))
                start = None
        
        if start is not None:
            periods.append((start, len(equity)))
        
        return periods


class TrendAnalyzer:
    """Analyze trend characteristics."""
    
    @staticmethod
    def calculate_trend_strength(
        prices: pd.Series,
        window: int = 20,
    ) -> pd.Series:
        """
        Calculate trend strength using ADX-like method.
        
        Args:
            prices: Close prices
            window: Lookback window
            
        Returns:
            Series with trend strength (0-100)
        """
        high_prices = prices.rolling(window=2).max()
        low_prices = prices.rolling(window=2).min()
        
        plus_dm = high_prices.diff().apply(lambda x: x if x > 0 else 0)
        minus_dm = (-low_prices.diff()).apply(lambda x: x if x > 0 else 0)
        
        tr = pd.Series(index=prices.index, dtype=float)
        for i in range(1, len(prices)):
            tr.iloc[i] = max(
                prices.iloc[i] - prices.iloc[i - 1],
                abs(prices.iloc[i] - prices.iloc[i - 1]),
                0,
            )
        
        atr = tr.rolling(window=window).mean()
        
        plus_di = (plus_dm.rolling(window=window).mean() / atr) * 100
        minus_di = (minus_dm.rolling(window=window).mean() / atr) * 100
        
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9)) * 100
        adx = dx.rolling(window=window).mean()
        
        return adx
