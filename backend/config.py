from pydantic import BaseModel, Field
from typing import List, Dict

class EMASettings(BaseModel):
    lengths: List[int] = Field(default=[20, 50, 100, 200], description="EMA lengths for ribbon stack")
    trend_timeframe: str = Field(default="4h", description="Higher timeframe for trend context (e.g., '1d', '4h')")
    execution_timeframe: str = Field(default="15m", description="Execution timeframe for signal triggers (e.g., '15m', '5m')")
    sensitivity_threshold_pct: float = Field(default=0.05, description="Min percentage separation between EMAs for strong trend rating")
    fast_reference: int = Field(default=50, description="Fast reference average for primary bias")
    slow_reference: int = Field(default=200, description="Slow reference average for primary bias")

class MarketStructureSettings(BaseModel):
    swing_left_bars: int = Field(default=5, description="Bars to the left to confirm a swing point")
    swing_right_bars: int = Field(default=5, description="Bars to the right to confirm a swing point")
    show_order_blocks: bool = Field(default=True, description="Show/hide order blocks on chart")
    max_order_blocks: int = Field(default=5, description="Max active order blocks to track per direction")
    ob_invalidation_rule: str = Field(default="close", description="OB invalidation rule: 'close' (candle close through OB) or 'wick' (wick through OB)")
    show_premium_discount: bool = Field(default=True, description="Show premium, discount, equilibrium zones")

class SignalSettings(BaseModel):
    allow_longs: bool = Field(default=True, description="Enable buy signals")
    allow_shorts: bool = Field(default=True, description="Enable sell signals")
    alignment_strictness: str = Field(default="all", description="Strictness: 'all' (trend & structure agree) or 'trend_only'")
    cooldown_bars: int = Field(default=10, description="Minimum bars between identical signals in the same zone")
    allow_counter_trend: bool = Field(default=False, description="Allow counter-trend reversal setups")
    entry_mode: str = Field(default="default", description="Entry mode: 'conservative', 'default', or 'aggressive'")

class FilterSettings(BaseModel):
    enable_session_filter: bool = Field(default=True, description="Filter signals by trading sessions")
    approved_sessions_pkt: List[Dict[str, str]] = Field(
        default=[
            {"name": "London", "start": "13:00", "end": "22:00"},
            {"name": "New York", "start": "18:00", "end": "03:00"}
        ],
        description="Session times in Pakistan Standard Time (UTC+5)"
    )
    enable_volatility_filter: bool = Field(default=True, description="Filter signals by volatility baseline")
    volatility_lookback: int = Field(default=20, description="Lookback period for ATR volatility calculation")
    min_volatility_pct: float = Field(default=0.2, description="ATR multiplier below which market is low volatility")
    max_volatility_pct: float = Field(default=2.5, description="ATR multiplier above which market is extreme volatility")
    filter_action: str = Field(default="warning", description="Action when filter fails: 'reject' or 'warning'")

class RiskSettings(BaseModel):
    stop_loss_method: str = Field(default="structure", description="Stop loss method: 'structure' (swing point / OB) or 'volatility' (ATR based)")
    take_profit_method: str = Field(default="fixed_r", description="Take profit method: 'fixed_r' or 'structure'")
    tp_targets_r: List[float] = Field(default=[1.5, 3.0, 5.0], description="Take profit multiples of initial risk")
    breakeven_milestone_r: float = Field(default=1.5, description="Breakeven trigger milestone (TP1 multiple)")
    account_size: float = Field(default=10000.0, description="Account size in USD for position sizing")
    risk_percentage: float = Field(default=1.0, description="Percentage of account risked per trade")
    min_stop_atr_multiplier: float = Field(default=0.5, description="Minimum stop loss size as multiple of ATR")
    max_stop_atr_multiplier: float = Field(default=4.0, description="Maximum stop loss size as multiple of ATR")

class ScannerSettings(BaseModel):
    enable_scanner: bool = Field(default=True, description="Enable multi-symbol scan")
    watchlist: List[str] = Field(
        default=["GC=F", "SI=F", "EURUSD=X", "GBPUSD=X", "USDJPY=X"],
        description="Watchlist symbols for scanner (Gold, Silver, FX)"
    )
    filter_active_only: bool = Field(default=False, description="Show only symbols with active signals in scan table")

class SystemSettings(BaseModel):
    theme: str = Field(default="dark", description="Dashboard theme: 'dark' or 'light'")
    debug_mode: bool = Field(default=False, description="Enable debug rows and logging")
    ema: EMASettings = EMASettings()
    structure: MarketStructureSettings = MarketStructureSettings()
    signal: SignalSettings = SignalSettings()
    filter: FilterSettings = FilterSettings()
    risk: RiskSettings = RiskSettings()
    scanner: ScannerSettings = ScannerSettings()

# Global default settings
settings = SystemSettings()
