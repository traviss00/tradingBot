"""Core utilities and helpers."""

from typing import Any
from datetime import datetime
import hashlib


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    import bcrypt
    return bcrypt.checkpw(password.encode(), hashed.encode())


def calculate_sharpe_ratio(returns: list[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio.
    
    Args:
        returns: List of period returns
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Sharpe ratio
    """
    import numpy as np
    
    if not returns or len(returns) < 2:
        return 0.0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)  # Daily rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)


def calculate_max_drawdown(equity_curve: list[float]) -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        equity_curve: List of portfolio values
        
    Returns:
        Max drawdown as percentage
    """
    import numpy as np
    
    if not equity_curve or len(equity_curve) < 2:
        return 0.0
    
    equity = np.array(equity_curve)
    running_max = np.maximum.accumulate(equity)
    drawdown = (equity - running_max) / running_max
    
    return float(np.min(drawdown))


def calculate_sortino_ratio(returns: list[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sortino ratio (downside deviation only).
    
    Args:
        returns: List of period returns
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Sortino ratio
    """
    import numpy as np
    
    if not returns or len(returns) < 2:
        return 0.0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - (risk_free_rate / 252)
    
    downside_returns = returns_array[returns_array < 0]
    downside_std = np.std(downside_returns)
    
    if downside_std == 0:
        return 0.0
    
    return np.mean(excess_returns) / downside_std * np.sqrt(252)


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """
    Calculate Compound Annual Growth Rate.
    
    Args:
        start_value: Initial value
        end_value: Final value
        years: Number of years
        
    Returns:
        CAGR as percentage
    """
    if start_value <= 0 or years <= 0:
        return 0.0
    
    return ((end_value / start_value) ** (1 / years) - 1) * 100


def format_currency(value: float, decimals: int = 2) -> str:
    """Format value as currency."""
    return f"${value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage."""
    return f"{value:.{decimals}f}%"


def calculate_position_size(
    capital: float,
    risk_pct: float,
    stop_loss_distance: float,
) -> float:
    """
    Calculate position size based on risk.
    
    Args:
        capital: Total capital
        risk_pct: Risk per trade as % of capital
        stop_loss_distance: Distance to stop loss (in price units)
        
    Returns:
        Position size in shares
    """
    if stop_loss_distance <= 0:
        return 0.0
    
    risk_amount = capital * risk_pct
    position_size = risk_amount / stop_loss_distance
    
    return position_size


def timestamp_to_datetime(timestamp: int | float) -> datetime:
    """Convert Unix timestamp to datetime."""
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp."""
    return int(dt.timestamp())
