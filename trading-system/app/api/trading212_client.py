"""Trading 212 API client with robust error handling."""

import asyncio
import logging
from typing import Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.core.exceptions import (
    Trading212Exception,
    RateLimitException,
    AuthenticationException,
)


logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Trading position."""
    instrument_id: str
    quantity: float
    buy_price: float
    current_price: float
    pl: float
    pl_pct: float


@dataclass
class Quote:
    """Market quote."""
    instrument_id: str
    bid: float
    ask: float
    last: float
    timestamp: datetime


class Trading212Client:
    """Async client for Trading 212 API."""
    
    def __init__(self, api_key: str = "", demo: bool = True):
        """
        Initialize Trading 212 client.
        
        Args:
            api_key: API key for authentication
            demo: Use demo/paper trading if True
        """
        self.api_key = api_key or settings.trading212.api_key
        self.demo = demo
        self.base_url = settings.trading212.base_url
        self.timeout = settings.trading212.request_timeout
        self.session: Optional[httpx.AsyncClient] = None
        self._rate_limit_reset: Optional[datetime] = None
        self._request_count = 0
        self._window_start = datetime.utcnow()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Establish HTTP session."""
        if not self.session:
            headers = self._build_headers()
            self.session = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
            logger.info("Connected to Trading 212 API")
    
    async def disconnect(self):
        """Close HTTP session."""
        if self.session:
            await self.session.aclose()
            self.session = None
            logger.info("Disconnected from Trading 212 API")
    
    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"{settings.app_name}/{settings.app_version}",
        }
        if self.demo:
            headers["X-Demo"] = "true"
        return headers
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.utcnow()
        
        # Reset counter if window has passed
        if (now - self._window_start).total_seconds() >= 60:
            self._request_count = 0
            self._window_start = now
        
        if self._request_count >= settings.trading212.rate_limit:
            wait_time = 60 - (now - self._window_start).total_seconds()
            logger.warning(f"Rate limit reached. Waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time + 0.1)
            self._request_count = 0
            self._window_start = datetime.utcnow()
        
        self._request_count += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data
            
        Raises:
            Trading212Exception: API error
            RateLimitException: Rate limit exceeded
            AuthenticationException: Authentication failed
        """
        if not self.session:
            await self.connect()
        
        await self._check_rate_limit()
        
        try:
            response = await self.session.request(
                method,
                endpoint,
                **kwargs,
            )
            
            # Handle specific status codes
            if response.status_code == 401:
                raise AuthenticationException("Invalid API key")
            elif response.status_code == 429:
                raise RateLimitException("Rate limit exceeded")
            elif response.status_code >= 400:
                raise Trading212Exception(
                    f"API error {response.status_code}: {response.text}"
                )
            
            return response.json()
        
        except httpx.TimeoutException:
            logger.error(f"Request timeout for {endpoint}")
            raise Trading212Exception(f"Request timeout for {endpoint}")
        except httpx.NetworkError as e:
            logger.error(f"Network error: {e}")
            raise Trading212Exception(f"Network error: {e}")
    
    async def get_account(self) -> dict[str, Any]:
        """Get account information."""
        return await self._request("GET", "/accounts/me")
    
    async def get_balance(self) -> float:
        """Get account balance."""
        account = await self.get_account()
        return account.get("balance", 0.0)
    
    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        data = await self._request("GET", "/positions")
        
        positions = []
        for item in data.get("positions", []):
            positions.append(Position(
                instrument_id=item["instrumentId"],
                quantity=item["quantity"],
                buy_price=item["buyPrice"],
                current_price=item["currentPrice"],
                pl=item["pl"],
                pl_pct=item["plPercent"],
            ))
        
        return positions
    
    async def get_quote(self, instrument_id: str) -> Quote:
        """Get current quote for instrument."""
        data = await self._request(
            "GET",
            f"/instruments/{instrument_id}/quote"
        )
        
        return Quote(
            instrument_id=instrument_id,
            bid=data["bid"],
            ask=data["ask"],
            last=data.get("last", (data["bid"] + data["ask"]) / 2),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
    
    async def place_order(
        self,
        instrument_id: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        order_type: str = "MARKET",  # "MARKET" or "LIMIT"
        limit_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Place an order.
        
        Args:
            instrument_id: Instrument ID
            side: BUY or SELL
            quantity: Quantity to trade
            order_type: MARKET or LIMIT
            limit_price: Price for LIMIT orders
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order response
        """
        payload = {
            "instrumentId": instrument_id,
            "side": side,
            "quantity": quantity,
            "orderType": order_type,
            "demo": self.demo,
        }
        
        if order_type == "LIMIT" and limit_price:
            payload["limitPrice"] = limit_price
        
        if stop_loss:
            payload["stopLoss"] = stop_loss
        
        if take_profit:
            payload["takeProfit"] = take_profit
        
        return await self._request("POST", "/orders", json=payload)
    
    async def close_position(self, position_id: str) -> dict[str, Any]:
        """Close a position."""
        return await self._request("POST", f"/positions/{position_id}/close")
    
    async def get_historical_data(
        self,
        instrument_id: str,
        timeframe: str = "1d",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get historical OHLCV data.
        
        Args:
            instrument_id: Instrument ID
            timeframe: 1m, 5m, 15m, 1h, 4h, 1d
            limit: Number of candles
            
        Returns:
            List of OHLCV candles
        """
        params = {
            "timeframe": timeframe,
            "limit": limit,
        }
        
        data = await self._request(
            "GET",
            f"/instruments/{instrument_id}/candles",
            params=params,
        )
        
        return data.get("candles", [])
    
    async def health_check(self) -> bool:
        """Check API connectivity."""
        try:
            await self.get_account()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class PaperTradingClient:
    """Simulated trading client for paper trading."""
    
    def __init__(self, initial_balance: float = 100000.0):
        """Initialize paper trading client."""
        self.balance = initial_balance
        self.positions: dict[str, Position] = {}
        self.orders: list[dict[str, Any]] = []
        self.trade_log: list[dict[str, Any]] = []
    
    async def get_balance(self) -> float:
        """Get current balance."""
        return self.balance
    
    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        return list(self.positions.values())
    
    async def place_order(
        self,
        instrument_id: str,
        side: str,
        quantity: float,
        limit_price: Optional[float] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Simulate order placement."""
        # In paper trading, we simulate immediate fill
        cost = quantity * (limit_price or 100.0)  # Mock price
        
        if side == "BUY":
            if cost > self.balance:
                raise Exception("Insufficient funds")
            self.balance -= cost
        else:
            self.balance += cost
        
        order = {
            "id": f"SIM_{len(self.orders) + 1}",
            "instrument_id": instrument_id,
            "side": side,
            "quantity": quantity,
            "price": limit_price or 100.0,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "FILLED",
        }
        
        self.orders.append(order)
        self.trade_log.append(order)
        
        return order
    
    async def health_check(self) -> bool:
        """Always healthy for paper trading."""
        return True
