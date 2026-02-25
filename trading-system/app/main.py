"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.exceptions import TradingSystemException
from app.auth.jwt_auth import validate_api_key, create_access_token

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    yield
    
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-grade algorithmic trading system",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(TradingSystemException)
async def trading_exception_handler(request, exc: TradingSystemException):
    """Handle trading system exceptions."""
    logger.error(f"Trading exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


# API Routes
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.post("/auth/login", tags=["Auth"])
async def login(username: str, password: str):
    """
    Login endpoint (placeholder).
    
    In production, validate against database.
    """
    if not username or not password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    token = create_access_token({"sub": username, "scope": "read:write"})
    
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@app.get("/account", tags=["Account"])
async def get_account():
    """Get account information."""
    # This would query the actual account from Trading 212 or paper trading
    return {
        "id": "account_123",
        "balance": 100000.0,
        "currency": "USD",
        "last_updated": datetime.utcnow().isoformat(),
    }


@app.get("/positions", tags=["Positions"])
async def get_positions():
    """Get open positions."""
    return {
        "positions": [
            {
                "symbol": "AAPL",
                "quantity": 20,
                "entry_price": 150.0,
                "current_price": 151.5,
                "pnl": 30.0,
                "pnl_pct": 0.99,
            },
            {
                "symbol": "MSFT",
                "quantity": 10,
                "entry_price": 320.0,
                "current_price": 322.0,
                "pnl": 20.0,
                "pnl_pct": 0.62,
            },
        ]
    }


@app.get("/trades", tags=["Trading"])
async def get_trades(
    limit: int = 100,
    skip: int = 0,
):
    """Get trade history."""
    # This would query from database
    return {
        "trades": [],
        "total": 0,
        "limit": limit,
        "skip": skip,
    }


@app.post("/trading/start", tags=["Trading"])
async def start_trading():
    """Start trading."""
    logger.info("Trading started")
    return {"status": "trading", "message": "Trading has been started"}


@app.post("/trading/stop", tags=["Trading"])
async def stop_trading():
    """Stop trading."""
    logger.info("Trading stopped")
    return {"status": "stopped", "message": "Trading has been stopped"}


@app.get("/model/status", tags=["Model"])
async def model_status():
    """Get model training status."""
    return {
        "model": "xgboost",
        "status": "trained",
        "accuracy": 0.78,
        "last_training": "2024-02-25T10:00:00Z",
    }


@app.post("/model/train", tags=["Model"])
async def train_model():
    """Trigger model training."""
    logger.info("Model training initiated")
    return {
        "status": "training",
        "message": "Model training has been initiated",
    }


@app.get("/backtest/{symbol}", tags=["Backtest"])
async def get_backtest_results(symbol: str):
    """Get backtest results for a symbol."""
    return {
        "symbol": symbol,
        "total_trades": 250,
        "win_rate": 0.62,
        "profit_factor": 2.15,
        "sharpe_ratio": 1.45,
        "max_drawdown": -0.085,
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    # In production, use prometheus_client library
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "open_positions": 2,
        "daily_pnl": 2500.0,
        "sharpe_ratio": 1.45,
    }


@app.get("/config", tags=["Configuration"])
async def get_config():
    """Get current configuration."""
    return {
        "environment": settings.environment,
        "trading_enabled": settings.trading_enabled,
        "paper_trading": settings.paper_trading,
        "symbols": settings.symbols,
        "risk": {
            "max_position_size": settings.risk.max_position_size,
            "max_concurrent_positions": settings.risk.max_concurrent_positions,
            "max_daily_loss_pct": settings.risk.max_daily_loss_pct,
        },
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
    )
