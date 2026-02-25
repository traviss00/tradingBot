"""Complete end-to-end example script."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from app.core.logging_config import setup_logging, get_logger
from app.core.config import settings
from app.data.ingestion import DataProvider, DataCleaner
from app.features.technical_indicators import FeatureEngineer
from app.training.training_pipeline import TrainingPipeline
from app.backtest.engine import BacktestEngine
from app.models.prediction_models import create_model
from app.execution.strategy import TradingStrategy, Signal
from app.api.trading212_client import Trading212Client, PaperTradingClient

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def main():
    """Run complete trading system example."""
    
    logger.info("=" * 80)
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info("=" * 80)
    
    # Configuration
    symbol = "AAPL"
    start_date = "2023-01-01"
    end_date = "2024-01-01"
    initial_capital = 100000.0
    
    try:
        # 1. DATA INGESTION
        logger.info("\n1️⃣ FETCHING HISTORICAL DATA")
        logger.info("-" * 80)
        
        provider = DataProvider()
        df = provider.get_historical_data(
            symbol=symbol,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date),
            interval="1d",
        )
        
        logger.info(f"✅ Downloaded {len(df)} candles for {symbol}")
        logger.info(f"Date range: {df.index[0].date()} to {df.index[-1].date()}")
        
        # 2. DATA CLEANING
        logger.info("\n2️⃣ CLEANING DATA")
        logger.info("-" * 80)
        
        cleaner = DataCleaner()
        df = cleaner.remove_gaps(df, threshold=0.05)
        df = cleaner.handle_outliers(df, column="close")
        
        logger.info("✅ Data cleaned and validated")
        
        # 3. FEATURE ENGINEERING
        logger.info("\n3️⃣ ENGINEERING FEATURES")
        logger.info("-" * 80)
        
        engineer = FeatureEngineer(feature_set="standard")
        features_df = engineer.engineer_features(df)
        
        logger.info(f"✅ Generated {len(engineer.features_added)} features")
        logger.info(f"Total columns: {len(features_df.columns)}")
        
        # 4. CREATE TARGET
        logger.info("\n4️⃣ CREATING TARGET VARIABLE")
        logger.info("-" * 80)
        
        # Simple target: 1 if price goes up next day, 0 otherwise
        features_df["target"] = (
            features_df["close"].shift(-1) > features_df["close"]
        ).astype(int)
        features_df = features_df.dropna()
        
        target_dist = features_df["target"].value_counts()
        logger.info(f"Target distribution: {dict(target_dist)}")
        
        # 5. MODEL TRAINING
        logger.info("\n5️⃣ TRAINING MODEL")
        logger.info("-" * 80)
        
        pipeline = TrainingPipeline(model_type="xgboost")
        model, report = pipeline.run(
            df=features_df,
            target_col="target",
            tune_hyperparams=True,
            n_trials=30,
        )
        
        logger.info(f"✅ Model trained")
        logger.info(f"Test Accuracy: {report['test_metrics']['accuracy']:.4f}")
        logger.info(f"Test F1-Score: {report['test_metrics']['f1']:.4f}")
        logger.info(f"Test ROC-AUC: {report['test_metrics']['roc_auc']:.4f}")
        
        # Save model
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        model.save(str(models_dir / f"{symbol}_model.pkl"))
        logger.info(f"✅ Model saved to models/{symbol}_model.pkl")
        
        # 6. STRATEGY GENERATION
        logger.info("\n6️⃣ GENERATING TRADING SIGNALS")
        logger.info("-" * 80)
        
        strategy = TradingStrategy(model=model)
        
        # Get features for signal generation (recent data)
        recent_df = features_df.tail(20)
        signals = []
        
        for idx, row in recent_df.iterrows():
            signal, confidence = strategy.generate_signal(
                df=recent_df.loc[:idx],
                symbol=symbol,
                confidence_threshold=0.55,
            )
            signals.append({
                "date": idx,
                "signal": signal.name,
                "confidence": confidence,
            })
        
        logger.info(f"✅ Generated {len(signals)} signals")
        for s in signals[-5:]:
            logger.info(f"  {s['date'].date()}: {s['signal']} (confidence: {s['confidence']:.2%})")
        
        # 7. BACKTESTING
        logger.info("\n7️⃣ BACKTESTING STRATEGY")
        logger.info("-" * 80)
        
        # Add signals to dataframe
        test_df = features_df.copy()
        test_df["proba"] = model.predict_proba(
            test_df[[c for c in test_df.columns if c not in ['open', 'high', 'low', 'close', 'volume', 'target']]]
        )[:, 1]
        test_df["signal"] = test_df["proba"].apply(
            lambda x: "BUY" if x > 0.6 else ("SELL" if x < 0.4 else "HOLD")
        )
        
        # Run backtest
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission=0.001,
            slippage=0.0005,
        )
        result = engine.backtest(test_df, signal_col="signal", price_col="close", symbol=symbol)
        
        logger.info("✅ Backtest completed!")
        logger.info("\n" + "=" * 80)
        logger.info("BACKTEST RESULTS")
        logger.info("=" * 80)
        logger.info(f"Total Trades: {result.total_trades}")
        logger.info(f"Winning Trades: {result.winning_trades}")
        logger.info(f"Losing Trades: {result.losing_trades}")
        logger.info(f"Win Rate: {result.win_rate:.2f}%")
        logger.info(f"Profit Factor: {result.profit_factor:.2f}")
        logger.info(f"\nTotal P&L: ${result.total_pnl:,.2f} ({result.total_pnl_pct:.2f}%)")
        logger.info(f"Avg Win: ${result.avg_win:,.2f}")
        logger.info(f"Avg Loss: ${result.avg_loss:,.2f}")
        logger.info(f"Largest Win: ${result.largest_win:,.2f}")
        logger.info(f"Largest Loss: ${result.largest_loss:,.2f}")
        logger.info(f"\nMax Consecutive Wins: {result.max_consecutive_wins}")
        logger.info(f"Max Consecutive Losses: {result.max_consecutive_losses}")
        logger.info(f"\nSharpe Ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"Sortino Ratio: {result.sortino_ratio:.2f}")
        logger.info(f"Max Drawdown: {result.max_drawdown:.2%}")
        logger.info(f"CAGR: {result.cagr:.2f}%")
        logger.info(f"\nFinal Equity: ${result.equity_curve[-1]:,.2f}")
        
        # Export results
        export_path = f"backtest_results_{symbol}.json"
        engine.export_results(export_path)
        logger.info(f"\n✅ Results exported to {export_path}")
        
        # 8. EVALUATION
        logger.info("\n8️⃣ PERFORMANCE EVALUATION")
        logger.info("-" * 80)
        
        # Check against targets
        targets = {
            "Sharpe Ratio > 1.2": result.sharpe_ratio > 1.2,
            "Max Drawdown < 20%": result.max_drawdown > -0.20,
            "Win Rate > 55%": result.win_rate > 55,
            "Profit Factor > 1.5": result.profit_factor > 1.5,
        }
        
        for target, met in targets.items():
            status = "✅" if met else "❌"
            logger.info(f"{status} {target}")
        
        # 9. SIMULATION (Paper Trading)
        logger.info("\n9️⃣ PAPER TRADING SIMULATION")
        logger.info("-" * 80)
        
        paper_client = PaperTradingClient(initial_balance=initial_capital)
        logger.info(f"Starting balance: ${initial_capital:,.2f}")
        
        # Simulate a few trades
        await paper_client.place_order(
            instrument_id="AAPL",
            side="BUY",
            quantity=10,
            limit_price=150.0,
        )
        
        await paper_client.place_order(
            instrument_id="AAPL",
            side="SELL",
            quantity=10,
            limit_price=155.0,
        )
        
        final_balance = await paper_client.get_balance()
        logger.info(f"Final balance: ${final_balance:,.2f}")
        logger.info(f"P&L: ${final_balance - initial_capital:,.2f}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ COMPLETE TRADING SYSTEM EXAMPLE FINISHED")
        logger.info("=" * 80)
        logger.info("\nNext Steps:")
        logger.info("1. Review backtest results and metrics")
        logger.info("2. Adjust strategy parameters if needed")
        logger.info("3. Test with paper trading for 2-4 weeks")
        logger.info("4. Deploy with real capital (if confident)")
        logger.info("\n⚠️  Remember: Past performance ≠ Future results")
        
    except Exception as e:
        logger.error(f"❌ Error in trading system: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
