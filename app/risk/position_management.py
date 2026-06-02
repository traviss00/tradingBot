"""Risk management system."""

import logging
import numpy as np
import pandas as pd
from typing import Optional
from datetime import datetime
from dataclasses import dataclass

from app.core.exceptions import RiskException, InsufficientFundsException
from app.core.config import settings
from app.core.utils import calculate_position_size


logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Current risk metrics."""
    capital: float
    equity: float
    daily_pnl: float
    daily_pnl_pct: float
    open_positions: int
    position_value: float
    leverage: float
    margin_usage: float
    max_loss_today: float


class PositionSizer:
    """Calculate position sizes based on risk."""
    
    def __init__(self, risk_config=None):
        """Initialize position sizer."""
        self.config = risk_config or settings.risk
    
    def calculate_size_by_risk(
        self,
        capital: float,
        stop_loss_price: float,
        entry_price: float,
        risk_pct: float = 0.01,
    ) -> float:
        """
        Calculate position size using risk percentage.
        
        Args:
            capital: Available capital
            stop_loss_price: Stop loss price
            entry_price: Entry price
            risk_pct: Risk percentage (default 1%)
            
        Returns:
            Position size in shares
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            raise ValueError("Prices must be positive")
        
        stop_loss_distance = abs(entry_price - stop_loss_price)
        if stop_loss_distance == 0:
            raise ValueError("Stop loss distance is zero")
        
        risk_amount = capital * risk_pct
        position_size = risk_amount / stop_loss_distance
        
        # Ensure minimum position size
        if position_size * entry_price < self.config.min_position_size:
            logger.warning(f"Position size {position_size} below minimum")
            return 0.0
        
        return position_size
    
    def calculate_size_by_volatility(
        self,
        capital: float,
        atr: float,
        price: float,
        base_risk_pct: float = 0.01,
    ) -> float:
        """
        Calculate position size adjusted for volatility (ATR).
        
        Args:
            capital: Available capital
            atr: Average True Range
            price: Current price
            base_risk_pct: Base risk percentage
            
        Returns:
            Position size in shares
        """
        if not self.config.volatility_adjustment:
            return capital * base_risk_pct / price
        
        # Inverse volatility scaling
        # High volatility -> smaller position
        vol_ratio = atr / price  # Volatility as % of price
        volatility_factor = 0.02 / (vol_ratio + 0.02)  # Normalize
        volatility_factor = max(0.5, min(2.0, volatility_factor))  # Bound between 0.5-2.0
        
        adjusted_risk = base_risk_pct * volatility_factor
        return capital * adjusted_risk / price
    
    def calculate_fractional_size(
        self,
        capital: float,
        entry_price: float,
        fraction: float = 0.02,
    ) -> float:
        """
        Calculate position using fixed fraction of capital.
        
        Args:
            capital: Available capital
            entry_price: Entry price
            fraction: Fraction of capital to risk (default 2%)
            
        Returns:
            Position size in shares
        """
        position_value = capital * fraction
        position_size = position_value / entry_price
        
        return position_size


class StopLossTakeProfitCalculator:
    """Calculate stop loss and take profit levels."""
    
    @staticmethod
    def calculate_atr_stop(
        price: float,
        atr: float,
        multiple: float = 2.0,
        side: str = "BUY",
    ) -> float:
        """
        Calculate stop loss using ATR multiple.
        
        Args:
            price: Current price
            atr: Average True Range
            multiple: ATR multiple (default 2.0)
            side: BUY or SELL
            
        Returns:
            Stop loss price
        """
        stop_distance = atr * multiple
        
        if side == "BUY":
            return price - stop_distance
        else:
            return price + stop_distance
    
    @staticmethod
    def calculate_risk_reward_target(
        entry_price: float,
        stop_loss_price: float,
        risk_reward_ratio: float = 2.0,
        side: str = "BUY",
    ) -> float:
        """
        Calculate take profit using risk-reward ratio.
        
        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_reward_ratio: Risk-reward ratio (default 2:1)
            side: BUY or SELL
            
        Returns:
            Take profit price
        """
        risk_distance = abs(entry_price - stop_loss_price)
        reward_distance = risk_distance * risk_reward_ratio
        
        if side == "BUY":
            return entry_price + reward_distance
        else:
            return entry_price - reward_distance
    
    @staticmethod
    def calculate_support_resistance(
        df: pd.DataFrame,
        lookback: int = 20,
    ) -> Tuple[float, float]:
        """
        Calculate support and resistance levels.
        
        Args:
            df: OHLCV DataFrame
            lookback: Lookback period
            
        Returns:
            (support, resistance)
        """
        recent = df.tail(lookback)
        
        support = recent["low"].min()
        resistance = recent["high"].max()
        
        return support, resistance


class RiskManager:
    """Main risk management system."""
    
    def __init__(self, initial_capital: float = 100000.0):
        """Initialize risk manager."""
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.equity = initial_capital
        self.open_positions = {}  # symbol -> position info
        self.daily_pnl = 0.0
        self.daily_start_equity = initial_capital
        self.position_sizer = PositionSizer()
        self.sl_tp_calculator = StopLossTakeProfitCalculator()
    
    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        """
        Register a new position.
        
        Args:
            symbol: Asset symbol
            side: BUY or SELL
            entry_price: Entry price
            quantity: Position size
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if position opened successfully
            
        Raises:
            RiskException: If risk limit violated
        """
        # Check max concurrent positions
        if len(self.open_positions) >= self.config.max_concurrent_positions:
            raise RiskException(
                f"Max concurrent positions ({self.config.max_concurrent_positions}) reached"
            )
        
        # Check position size limit
        position_value = entry_price * quantity
        max_position_value = self.equity * self.config.max_position_size
        
        if position_value > max_position_value:
            raise RiskException(
                f"Position size {position_value} exceeds max {max_position_value}"
            )
        
        # Check funds
        if side == "BUY" and position_value > self.capital:
            raise InsufficientFundsException(
                f"Insufficient capital: {position_value} > {self.capital}"
            )
        
        # Register position
        self.open_positions[symbol] = {
            "side": side,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "entry_time": datetime.utcnow(),
        }
        
        # Deduct capital if BUY
        if side == "BUY":
            self.capital -= position_value
        
        logger.info(f"Opened {side} position: {symbol} {quantity} @ {entry_price}")
        
        return True
    
    def close_position(self, symbol: str, exit_price: float) -> float:
        """
        Close an existing position.
        
        Args:
            symbol: Asset symbol
            exit_price: Exit price
            
        Returns:
            Realized P&L
            
        Raises:
            RiskException: If position doesn't exist
        """
        if symbol not in self.open_positions:
            raise RiskException(f"No position found for {symbol}")
        
        pos = self.open_positions.pop(symbol)
        
        quantity = pos["quantity"]
        entry_price = pos["entry_price"]
        side = pos["side"]
        
        # Calculate P&L
        if side == "BUY":
            pnl = (exit_price - entry_price) * quantity
            proceeds = exit_price * quantity
        else:
            pnl = (entry_price - exit_price) * quantity
            proceeds = entry_price * quantity
        
        # Add proceeds back
        self.capital += proceeds
        self.daily_pnl += pnl
        
        logger.info(f"Closed {side} position: {symbol} | P&L: ${pnl:.2f}")
        
        return pnl
    
    def update_equity(self, current_prices: dict):
        """
        Update equity with current market prices.
        
        Args:
            current_prices: Dict of symbol -> price
        """
        position_value = 0.0
        unrealized_pnl = 0.0
        
        for symbol, pos in self.open_positions.items():
            if symbol in current_prices:
                price = current_prices[symbol]
                qty = pos["quantity"]
                
                if pos["side"] == "BUY":
                    position_value += price * qty
                    unrealized_pnl += (price - pos["entry_price"]) * qty
                else:
                    position_value += (pos["entry_price"] - price) * qty
                    unrealized_pnl += (pos["entry_price"] - price) * qty
        
        self.equity = self.capital + position_value
    
    def get_metrics(self) -> RiskMetrics:
        """Get current risk metrics."""
        daily_pnl_pct = (self.daily_pnl / self.daily_start_equity * 100) if self.daily_start_equity > 0 else 0.0
        
        return RiskMetrics(
            capital=self.capital,
            equity=self.equity,
            daily_pnl=self.daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            open_positions=len(self.open_positions),
            position_value=self.equity - self.capital,
            leverage=self.equity / self.capital if self.capital > 0 else 0.0,
            margin_usage=(self.equity - self.capital) / self.equity if self.equity > 0 else 0.0,
            max_loss_today=self.daily_pnl,
        )
    
    def check_daily_loss_limit(self) -> bool:
        """Check if daily loss limit is exceeded."""
        max_daily_loss = self.initial_capital * settings.risk.max_daily_loss_pct
        
        if self.daily_pnl < -max_daily_loss:
            logger.warning(f"Daily loss limit exceeded: {self.daily_pnl} < {-max_daily_loss}")
            return False
        
        return True
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at market open)."""
        self.daily_pnl = 0.0
        self.daily_start_equity = self.equity
