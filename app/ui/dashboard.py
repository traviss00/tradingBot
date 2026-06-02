"""Streamlit dashboard for trading system."""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Set page config
st.set_page_config(
    page_title="Trading System Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .positive {
        color: #09AB3B;
    }
    .negative {
        color: #FF2B2B;
    }
</style>
""", unsafe_allow_html=True)

logger = logging.getLogger(__name__)


class TradingDashboard:
    """Main dashboard class."""
    
    def __init__(self):
        """Initialize dashboard."""
        self.title = "🚀 Algorithmic Trading System"
        self.sidebar_title = "⚙️ Configuration"
    
    def render_header(self):
        """Render header section."""
        st.title(self.title)
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Account Balance", "$100,000.00", "+2.5%")
        with col2:
            st.metric("Open Positions", "2", "+1")
        with col3:
            st.metric("Today's P&L", "$2,500.00", "2.5%")
        with col4:
            st.metric("Sharpe Ratio", "1.45", "+0.15")
    
    def render_sidebar(self):
        """Render sidebar configuration."""
        with st.sidebar:
            st.header(self.sidebar_title)
            
            # Authentication (placeholder)
            st.subheader("🔐 Authentication")
            username = st.text_input("Username", value="demo", disabled=True)
            password = st.text_input("Password", type="password", disabled=True)
            
            st.divider()
            
            # Trading controls
            st.subheader("📊 Trading Controls")
            
            trading_enabled = st.toggle("Enable Trading", value=False)
            paper_trading = st.toggle("Paper Trading Mode", value=True)
            
            st.divider()
            
            # Strategy configuration
            st.subheader("⚙️ Strategy Settings")
            
            model_type = st.selectbox(
                "Model Type",
                ["XGBoost", "LightGBM", "Logistic Regression", "Ensemble"]
            )
            
            confidence_threshold = st.slider(
                "Confidence Threshold",
                min_value=0.50,
                max_value=0.95,
                value=0.65,
                step=0.05,
            )
            
            max_positions = st.slider(
                "Max Concurrent Positions",
                min_value=1,
                max_value=10,
                value=3,
            )
            
            risk_per_trade = st.slider(
                "Risk per Trade (%)",
                min_value=0.5,
                max_value=5.0,
                value=1.0,
                step=0.5,
            )
            
            st.divider()
            
            # Action buttons
            st.subheader("🎬 Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("▶️ Start Trading", use_container_width=True):
                    st.success("Trading started!")
            
            with col2:
                if st.button("⏸️ Stop Trading", use_container_width=True):
                    st.info("Trading stopped!")
            
            if st.button("🔄 Retrain Model", use_container_width=True):
                st.info("Model training started...")
            
            if st.button("💾 Save Settings", use_container_width=True):
                st.success("Settings saved!")
    
    def render_account_overview(self):
        """Render account overview section."""
        st.header("📊 Account Overview")
        
        tab1, tab2, tab3 = st.tabs(["Portfolio", "Positions", "Transactions"])
        
        with tab1:
            # Create sample data
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Capital", "$100,000.00")
                st.metric("Available Cash", "$95,000.00")
                st.metric("Invested", "$5,000.00")
            
            with col2:
                st.metric("Unrealized P&L", "$125.00", "+0.13%")
                st.metric("Realized P&L (Today)", "$2,500.00", "+2.5%")
                st.metric("Realized P&L (All Time)", "$12,500.00", "+12.5%")
            
            with col3:
                st.metric("Win Rate", "62%")
                st.metric("Profit Factor", "2.15")
                st.metric("Sharpe Ratio", "1.45")
            
            # Equity curve
            st.subheader("Equity Curve")
            
            dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
            equity = 100000 + np.cumsum(np.random.randn(100) * 100)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=equity,
                mode='lines',
                name='Equity',
                line=dict(color='#1f77b4', width=2),
                fill='tozeroy',
                fillcolor='rgba(31, 119, 180, 0.1)',
            ))
            
            fig.update_layout(
                title="Portfolio Equity Over Time",
                xaxis_title="Date",
                yaxis_title="Equity ($)",
                hovermode='x unified',
                height=400,
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            # Open positions table
            positions_data = {
                "Symbol": ["AAPL", "MSFT"],
                "Side": ["BUY", "BUY"],
                "Entry Price": ["$150.00", "$320.00"],
                "Current Price": ["$151.50", "$322.00"],
                "Quantity": ["20", "10"],
                "Value": ["$3,030.00", "$3,220.00"],
                "P&L": ["$30.00", "$20.00"],
                "P&L %": ["+0.99%", "+0.62%"],
            }
            
            st.dataframe(
                pd.DataFrame(positions_data),
                use_container_width=True,
                hide_index=True,
            )
        
        with tab3:
            # Transaction history
            transactions_data = {
                "Date": ["2024-02-25", "2024-02-24", "2024-02-23"],
                "Type": ["BUY", "SELL", "BUY"],
                "Symbol": ["AAPL", "GOOGL", "MSFT"],
                "Price": ["$150.00", "$125.00", "$320.00"],
                "Quantity": ["20", "30", "10"],
                "Commission": ["$30.00", "$37.50", "$32.00"],
            }
            
            st.dataframe(
                pd.DataFrame(transactions_data),
                use_container_width=True,
                hide_index=True,
            )
    
    def render_model_dashboard(self):
        """Render model performance dashboard."""
        st.header("🤖 Model Performance")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Training Metrics")
            
            metrics = {
                "Accuracy": 0.78,
                "Precision": 0.75,
                "Recall": 0.82,
                "F1 Score": 0.78,
                "ROC-AUC": 0.85,
            }
            
            for metric, value in metrics.items():
                st.metric(metric, f"{value:.2%}")
        
        with col2:
            st.subheader("Feature Importance (Top 10)")
            
            features = {
                "RSI_14": 0.15,
                "MACD_Signal": 0.12,
                "EMA_50": 0.11,
                "ATR_14": 0.10,
                "BB_Position": 0.09,
                "Volatility": 0.08,
                "Volume_Ratio": 0.07,
                "Returns_5": 0.06,
                "Close_Position": 0.05,
                "Momentum": 0.04,
            }
            
            fig = px.bar(
                x=list(features.values()),
                y=list(features.keys()),
                orientation='h',
                title="Feature Importance",
                labels={"x": "Importance", "y": "Feature"},
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def render_backtest_results(self):
        """Render backtest results."""
        st.header("📈 Backtest Results")
        
        # Sample backtest metrics
        metrics_cols = st.columns(5)
        
        metrics = [
            ("Total Trades", "250", "Metric"),
            ("Win Rate", "62%", "Success"),
            ("Profit Factor", "2.15", "Metric"),
            ("Max Drawdown", "-8.5%", "Risk"),
            ("Sharpe Ratio", "1.45", "Performance"),
        ]
        
        for col, (label, value, _type) in zip(metrics_cols, metrics):
            with col:
                st.metric(label, value)
        
        # Trade distribution
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Trade P&L Distribution")
            
            pnl_values = np.random.randn(250) * 100 + 20
            
            fig = px.histogram(
                x=pnl_values,
                nbins=50,
                title="P&L Distribution",
                labels={"x": "P&L ($)", "count": "Frequency"},
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Drawdown Analysis")
            
            dates = pd.date_range(start="2023-01-01", periods=250, freq="D")
            drawdown = np.concatenate([np.linspace(0, -0.08, 100), np.linspace(-0.08, -0.05, 150)])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=drawdown * 100,
                mode='lines',
                name='Drawdown',
                line=dict(color='#d62728'),
                fill='tozeroy',
            ))
            
            fig.update_layout(
                title="Drawdown Over Time",
                xaxis_title="Date",
                yaxis_title="Drawdown (%)",
                height=400,
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def render_logs(self):
        """Render system logs."""
        st.header("📋 System Logs")
        
        log_level = st.selectbox("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"])
        
        sample_logs = [
            "[2024-02-25 09:30:15] INFO: Market opened",
            "[2024-02-25 09:32:45] INFO: Generated BUY signal for AAPL (confidence: 0.78)",
            "[2024-02-25 09:33:00] INFO: Executed BUY order: 20 AAPL @ $150.00",
            "[2024-02-25 10:15:30] WARNING: High volatility detected for MSFT",
            "[2024-02-25 11:45:00] INFO: Closed position: GOOGL | P&L: $125.50",
        ]
        
        st.code("\n".join(sample_logs), language="text")
    
    def run(self):
        """Run the dashboard."""
        self.render_sidebar()
        self.render_header()
        
        # Main tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Account",
            "🤖 Model",
            "📈 Backtest",
            "📋 Logs",
            "⚙️ Settings"
        ])
        
        with tab1:
            self.render_account_overview()
        
        with tab2:
            self.render_model_dashboard()
        
        with tab3:
            self.render_backtest_results()
        
        with tab4:
            self.render_logs()
        
        with tab5:
            st.subheader("System Settings")
            st.info("Settings management coming soon...")


if __name__ == "__main__":
    dashboard = TradingDashboard()
    dashboard.run()
