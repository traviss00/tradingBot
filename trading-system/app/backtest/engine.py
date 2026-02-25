"""Backtesting engine for strategy validation."""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path

from app.core.config import settings
from app.core.utils import calculate_sharpe_ratio, calculate_max_drawdown, calculate_sortino_ratio, calculate_cagr


logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    symbol: str = ""
    side: str = "BUY"  # BUY or SELL
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    duration: Optional[int] = None  # bars
    
    def close(self, exit_price: float, exit_time: datetime, commission: float = 0.0):
        """Close the trade."""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.commission = commission
        
        # Calculate P&L
        if self.side == "BUY":
            gross_pnl = (exit_price - self.entry_price) * self.quantity
        else:
            gross_pnl = (self.entry_price - exit_price) * self.quantity
        
        self.pnl = gross_pnl - commission
        self.pnl_pct = (self.pnl / (self.entry_price * self.quantity)) * 100 if self.entry_price > 0 else 0.0
        
        if exit_time and self.entry_time:
            self.duration = (exit_time - self.entry_time).days + 1


@dataclass
class BacktestResult:
    """Results of backtesting."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    
    # Risk metrics
    max_drawdown: float = 0.0
    avg_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    cagr: float = 0.0
    
    # Equity curve
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    
    # Details
    trades: List[Trade] = field(default_factory=list)


class BacktestEngine:
    """Backtesting engine for algorithmic strategies."""
    
    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        """
        Initialize backtesting engine.
        
        Args:
            initial_capital: Starting capital
            commission: Commission per trade (as % of trade value)
            slippage: Slippage per trade (as % of price)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission_pct = commission
        self.slippage_pct = slippage
        
        self.positions: Dict[str, Trade] = {}
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.timestamps: List[datetime] = []
    
    def add_signal(
        self,
        timestamp: datetime,
        symbol: str,
        signal: str,  # BUY, SELL, HOLD
        price: float,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> bool:
        """
        Process a trading signal.
        
        Args:
            timestamp: Signal time
            symbol: Asset symbol
            signal: BUY, SELL, or HOLD
            price: Current price
            quantity: Quantity to trade
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if trade was executed
        """
        if signal == "HOLD":
            return False
        
        # Apply slippage
        slippage = price * self.slippage_pct
        execution_price = price + slippage if signal == "BUY" else price - slippage
        
        # Commission
        commission = execution_price * quantity * self.commission_pct
        
        # Check funds
        cost = execution_price * quantity
        if signal == "BUY" and cost > self.capital:
            logger.warning(f"Insufficient capital for BUY {symbol}: {cost} > {self.capital}")
            return False
        
        # Execute trade
        if signal == "BUY":
            self.capital -= cost + commission
            
            trade = Trade(
                entry_time=timestamp,
                symbol=symbol,
                side="BUY",
                entry_price=execution_price,
                quantity=quantity,
                commission=commission,
            )
            self.positions[symbol] = trade
            
            logger.info(f"BUY {quantity} {symbol} @ {execution_price:.2f}")
            return True
        
        elif signal == "SELL":
            if symbol not in self.positions:
                logger.warning(f"No position to SELL for {symbol}")
                return False
            
            trade = self.positions.pop(symbol)
            proceeds = execution_price * quantity - commission
            self.capital += proceeds
            
            trade.close(execution_price, timestamp, commission)
            self.closed_trades.append(trade)
            
            logger.info(f"SELL {quantity} {symbol} @ {execution_price:.2f} | P&L: ${trade.pnl:.2f}")
            return True
        
        return False
    
    def update_position_prices(self, prices: Dict[str, float]) -> float:
        """
        Update open positions with current prices.
        
        Args:
            prices: Dictionary of symbol -> price
            
        Returns:
            Current equity
        """
        position_value = 0.0
        
        for symbol, trade in self.positions.items():
            if symbol in prices:
                current_price = prices[symbol]
                position_value += current_price * trade.quantity
        
        current_equity = self.capital + position_value
        self.equity_curve.append(current_equity)
        
        return current_equity
    
    def backtest(
        self,
        df: pd.DataFrame,
        signal_col: str = "signal",
        price_col: str = "close",
        symbol: str = "STOCK",
    ) -> BacktestResult:
        """
        Run backtest on data.
        
        Args:
            df: DataFrame with signals and prices
            signal_col: Column name with signals (BUY/SELL/HOLD)
            price_col: Column name with prices
            symbol: Asset symbol
            
        Returns:
            BacktestResult with detailed metrics
        """
        logger.info(f"Starting backtest for {symbol}")
        
        self.capital = self.initial_capital
        self.positions = {}
        self.closed_trades = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = [df.index[0]]
        
        for idx, row in df.iterrows():
            signal = row.get(signal_col, "HOLD")
            price = row[price_col]
            
            # Simple fixed quantity for now
            quantity = 1.0
            
            # Process signal
            self.add_signal(idx, symbol, signal, price, quantity)
            
            # Update equity
            current_equity = self.update_position_prices({symbol: price})
            self.timestamps.append(idx)
        
        # Close remaining positions at last price
        last_price = df[price_col].iloc[-1]
        last_time = df.index[-1]
        
        for symbol, trade in list(self.positions.items()):
            trade.close(last_price, last_time)
            self.closed_trades.append(trade)
        
        # Calculate metrics
        result = self._calculate_metrics()
        result.equity_curve = self.equity_curve
        result.timestamps = self.timestamps
        result.trades = self.closed_trades
        
        return result
    
    def _calculate_metrics(self) -> BacktestResult:
        """Calculate performance metrics."""
        result = BacktestResult()
        
        if not self.closed_trades:
            logger.warning("No closed trades to analyze")
            return result
        
        trades = self.closed_trades
        result.total_trades = len(trades)
        
        # Wins/losses
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        result.winning_trades = len(winning_trades)
        result.losing_trades = len(losing_trades)
        result.win_rate = (result.winning_trades / result.total_trades * 100) if result.total_trades > 0 else 0.0
        
        # P&L
        result.total_pnl = sum(t.pnl for t in trades)
        result.total_pnl_pct = (result.total_pnl / self.initial_capital * 100)
        
        result.avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0.0
        result.avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0.0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Expectancy
        result.expectancy = result.avg_win * result.win_rate + result.avg_loss * (1 - result.win_rate)
        
        # Extremes
        result.largest_win = max([t.pnl for t in winning_trades]) if winning_trades else 0.0
        result.largest_loss = min([t.pnl for t in losing_trades]) if losing_trades else 0.0
        
        # Consecutive wins/losses
        result.max_consecutive_wins = self._max_consecutive_wins()
        result.max_consecutive_losses = self._max_consecutive_losses()
        
        # Risk metrics
        if self.equity_curve:
            result.max_drawdown = calculate_max_drawdown(self.equity_curve)
            result.sharpe_ratio = calculate_sharpe_ratio([
                (self.equity_curve[i+1] - self.equity_curve[i]) / self.equity_curve[i]
                for i in range(len(self.equity_curve) - 1)
            ])
            
            result.sortino_ratio = calculate_sortino_ratio([
                (self.equity_curve[i+1] - self.equity_curve[i]) / self.equity_curve[i]
                for i in range(len(self.equity_curve) - 1)
            ])
            
            years = len(self.equity_curve) / 252  # Approximate
            if years > 0:
                result.cagr = calculate_cagr(
                    self.initial_capital,
                    self.equity_curve[-1],
                    years
                )
        
        logger.info(f"Total Trades: {result.total_trades}")
        logger.info(f"Win Rate: {result.win_rate:.2f}%")
        logger.info(f"Total P&L: ${result.total_pnl:.2f}")
        logger.info(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"Max Drawdown: {result.max_drawdown:.2f}%")
        
        return result
    
    def _max_consecutive_wins(self) -> int:
        """Calculate max consecutive wins."""
        max_streak = 0
        current_streak = 0
        
        for trade in self.closed_trades:
            if trade.pnl > 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _max_consecutive_losses(self) -> int:
        """Calculate max consecutive losses."""
        max_streak = 0
        current_streak = 0
        
        for trade in self.closed_trades:
            if trade.pnl <= 0:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def export_results(self, path: str = "backtest_results.json"):
        """Export results to JSON."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "summary": {
                "total_trades": len(self.closed_trades),
                "winning_trades": sum(1 for t in self.closed_trades if t.pnl > 0),
                "total_pnl": sum(t.pnl for t in self.closed_trades),
                "equity_final": self.equity_curve[-1] if self.equity_curve else 0,
            },
            "trades": [
                {
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "symbol": t.symbol,
                    "side": t.side,
                    "entry_price": float(t.entry_price),
                    "exit_price": float(t.exit_price) if t.exit_price else None,
                    "quantity": float(t.quantity),
                    "pnl": float(t.pnl),
                    "pnl_pct": float(t.pnl_pct),
                }
                for t in self.closed_trades
            ],
        }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Exported backtest results to {path}")
