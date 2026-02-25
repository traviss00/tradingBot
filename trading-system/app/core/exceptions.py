"""
Custom exception classes for the trading system.
"""


class TradingSystemException(Exception):
    """Base exception for trading system."""
    pass


class ConfigurationException(TradingSystemException):
    """Configuration is invalid."""
    pass


class DataException(TradingSystemException):
    """Data-related error."""
    pass


class APIException(TradingSystemException):
    """API-related error."""
    pass


class Trading212Exception(APIException):
    """Trading 212 API error."""
    pass


class AuthenticationException(TradingSystemException):
    """Authentication failed."""
    pass


class ValidationException(TradingSystemException):
    """Data validation failed."""
    pass


class InsufficientFundsException(TradingSystemException):
    """Not enough capital for trade."""
    pass


class PositionException(TradingSystemException):
    """Position management error."""
    pass


class RiskException(TradingSystemException):
    """Risk management constraint violated."""
    pass


class ExecutionException(TradingSystemException):
    """Order execution failed."""
    pass


class BacktestException(TradingSystemException):
    """Backtest execution error."""
    pass


class ModelException(TradingSystemException):
    """Model training or inference error."""
    pass


class RateLimitException(APIException):
    """API rate limit exceeded."""
    pass
