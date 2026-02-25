"""Strategy execution and signal generation."""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Tuple
from datetime import datetime
from enum import Enum

from app.core.config import settings
from app.features.regime_detection import RegimeDetector
from app.core.utils import calculate_position_size


logger = logging.getLogger(__name__)


class Signal(Enum):
    """Trading signals."""
    BUY = 1
    SELL = -1
    HOLD = 0


class StrategyConfig:
    """Strategy configuration."""
    
    def __init__(self):
        self.min_confidence = 0.55  # Minimum probability threshold
        self.max_consecutive_losses = 3
        self.avoid_sideways_markets = True
        self.avoid_high_volatility = True
        self.use_regime_filter = True
        self.risk_per_trade = 0.01  # 1% per trade


class TradingStrategy:
    """Main trading strategy."""
    
    def __init__(self, model=None, config: Optional[StrategyConfig] = None):
        """
        Initialize strategy.
        
        Args:
            model: Trained ML model
            config: Strategy configuration
        """
        self.model = model
        self.config = config or StrategyConfig()
        self.regime_detector = RegimeDetector()
        self.consecutive_losses = 0
        self.last_signals: Dict[str, str] = {}
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        confidence_threshold: float = 0.55,
    ) -> Tuple[Signal, float]:
        """
        Generate trading signal for a symbol.
        
        Args:
            df: OHLCV DataFrame with features
            symbol: Asset symbol
            confidence_threshold: Confidence threshold for trading
            
        Returns:
            (signal, confidence_probability)
        """
        if df.empty:
            return Signal.HOLD, 0.0
        
        latest = df.iloc[-1]
        
        # Get ML probability
        if self.model is None:
            logger.warning("No model loaded, returning HOLD")
            return Signal.HOLD, 0.0
        
        X = df[[col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]].tail(1)
        try:
            proba = self.model.predict_proba(X)[0]
            prob_up = proba[1]  # Probability of upward move
        except Exception as e:
            logger.error(f"Model prediction error: {e}")
            return Signal.HOLD, 0.0
        
        # Apply filters
        if self.config.use_regime_filter:
            signal = self._apply_regime_filter(df, prob_up)
            if signal != Signal.HOLD:
                return signal, prob_up
        
        if self.config.avoid_sideways_markets:
            if self._is_sideways(df):
                logger.debug(f"{symbol}: Sideways market detected")
                return Signal.HOLD, 0.0
        
        if self.config.avoid_high_volatility:
            if self._is_high_volatility(df):
                logger.debug(f"{symbol}: High volatility detected")
                return Signal.HOLD, 0.0
        
        # Generate signal based on probability
        if prob_up > confidence_threshold:
            return Signal.BUY, prob_up
        elif prob_up < (1 - confidence_threshold):
            return Signal.SELL, 1 - prob_up
        else:
            return Signal.HOLD, prob_up
    
    def _apply_regime_filter(
        self,
        df: pd.DataFrame,
        prob_up: float,
    ) -> Signal:
        """Apply regime-based filters."""
        if len(df) < 30:
            return Signal.HOLD
        
        returns = np.log(df["close"] / df["close"].shift(1)).dropna()
        
        # Volatility regime
        vol_regime = RegimeDetector.volatility_regime(returns)
        current_vol_regime = vol_regime.iloc[-1]
        
        # Don't trade in high volatility shocks
        if current_vol_regime > 0:  # High volatility
            if prob_up > 0.65:
                return Signal.BUY
            elif prob_up < 0.35:
                return Signal.SELL
            else:
                return Signal.HOLD
        
        # Trend regime
        trend_regime = RegimeDetector.trend_regime(df["close"])
        current_trend = trend_regime.iloc[-1]
        
        # Trade with trend
        if current_trend > 0 and prob_up > 0.55:
            return Signal.BUY
        elif current_trend < 0 and prob_up < 0.45:
            return Signal.SELL
        elif current_trend == 0:
            # Mean reversion in sideways market
            mr_signal = RegimeDetector.mean_reversion_signal(df["close"])
            current_mr = mr_signal.iloc[-1]
            
            if current_mr < 0 and prob_up > 0.55:  # Oversold
                return Signal.BUY
            elif current_mr > 0 and prob_up < 0.45:  # Overbought
                return Signal.SELL
        
        return Signal.HOLD
    
    def _is_sideways(self, df: pd.DataFrame, period: int = 20) -> bool:
        """Check if market is moving sideways."""
        recent = df.tail(period)
        close = recent["close"]
        
        high = close.max()
        low = close.min()
        
        # If range is small and no clear trend, it's sideways
        range_pct = (high - low) / low
        
        # Low range threshold
        return range_pct < 0.02  # Less than 2% range
    
    def _is_high_volatility(self, df: pd.DataFrame, period: int = 20) -> bool:
        """Check if volatility is abnormally high."""
        returns = np.log(df["close"] / df["close"].shift(1)).dropna()
        recent_vol = returns.tail(period).std()
        
        # Compare to historical average
        historical_vol = returns.tail(100).std()
        
        # High volatility if recent > 1.5x historical
        return recent_vol > historical_vol * 1.5


class ExecutionManager:
    """Manage trade execution."""
    
    def __init__(self, api_client):
        """Initialize execution manager."""
        self.api_client = api_client
        self.execution_log = []
    
    async def execute_signal(
        self,
        symbol: str,
        signal: Signal,
        price: float,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> bool:
        """
        Execute a trading signal.
        
        Args:
            symbol: Asset symbol
            signal: Trading signal
            price: Current price
            quantity: Order quantity
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if executed
        """
        if signal == Signal.HOLD:
            return False
        
        try:
            side = "BUY" if signal == Signal.BUY else "SELL"
            
            order = await self.api_client.place_order(
                instrument_id=symbol,
                side=side,
                quantity=quantity,
                order_type="MARKET",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            
            self.execution_log.append({
                "timestamp": datetime.utcnow(),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_id": order.get("id"),
            })
            
            logger.info(f"Executed {side} order for {symbol}: {quantity} @ {price}")
            
            return True
        
        except Exception as e:
            logger.error(f"Execution failed for {symbol}: {e}")
            return False
