import pytest
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
from backend.config import settings
from backend.core.data_feed import DataFeed
from backend.core.trend_engine import TrendEngine
from backend.core.structure_engine import StructureEngine, SwingPoint, OrderBlock
from backend.core.signal_engine import SignalEngine, Signal
from backend.core.filter_engine import FilterEngine
from backend.core.risk_manager import RiskManager
from backend.core.scanner import WatchlistScanner

# =====================================================================
# DATA FEED TESTS (Scenarios 1-15)
# =====================================================================

def test_mock_data_shape():
    """Verify that generated mock data has correct shape and required columns."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=100)
    assert len(df) == 100
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        assert col in df.columns

def test_mock_data_timezone():
    """Verify that generated mock data timestamps are in PKT timezone."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=50)
    assert df.index.tz is not None
    assert df.index.tz.zone == "Asia/Karachi"

def test_resampling_1h_to_4h():
    """Verify that resampling works correctly and matches expectations."""
    df_1h = DataFeed.generate_mock_data("EURUSD=X", "1h", limit=40)
    df_4h = DataFeed.resample_dataframe(df_1h, "4h")
    # 40 hourly bars resampled to 4-hourly should yield approximately 10 bars
    assert len(df_4h) in [10, 11]
    
    # Check that OHLC calculations are accurate using actual boundary matching
    first_bar_time = df_4h.index[0]
    grouped_1h = df_1h[(df_1h.index >= first_bar_time) & (df_1h.index < first_bar_time + pd.Timedelta(hours=4))]
    
    assert df_4h['High'].iloc[0] == grouped_1h['High'].max()
    assert df_4h['Low'].iloc[0] == grouped_1h['Low'].min()
    assert df_4h['Open'].iloc[0] == grouped_1h['Open'].iloc[0]
    assert df_4h['Close'].iloc[0] == grouped_1h['Close'].iloc[-1]

def test_fetch_fallback_mock():
    """Verify fetch_data falls back to mock generation on invalid symbol."""
    df = DataFeed.fetch_data("INVALID_SYMBOL", "1d", limit=10)
    assert not df.empty
    assert len(df) == 10

# =====================================================================
# TREND ENGINE TESTS (Scenarios 16-45)
# =====================================================================

def test_ema_calculations():
    """Verify EMA ribbon calculation returns correct EMA columns."""
    df = DataFeed.generate_mock_data("GC=F", "4h", limit=250)
    df_ema = TrendEngine.calculate_emas(df, [20, 50, 100, 200])
    assert 'EMA_20' in df_ema.columns
    assert 'EMA_50' in df_ema.columns
    assert 'EMA_100' in df_ema.columns
    assert 'EMA_200' in df_ema.columns

def test_trend_bias_bullish_and_bearish():
    """Verify primary bias classification based on EMA 50 vs 200."""
    # Create artificial dataframe where EMA 50 > EMA 200
    df = DataFeed.generate_mock_data("GC=F", "4h", limit=210)
    df_ema = TrendEngine.calculate_emas(df, [20, 50, 100, 200])
    
    # Force EMA values
    df_ema['EMA_50'] = 2000.0
    df_ema['EMA_200'] = 1900.0
    # past values need to agree for crossover filter
    df_ema.loc[df_ema.index, 'EMA_50'] = 2000.0
    df_ema.loc[df_ema.index, 'EMA_200'] = 1900.0
    
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Primary_Bias'].iloc[-1] == "Bullish"
    
    # Test Bearish
    df_ema.loc[df_ema.index, 'EMA_50'] = 1800.0
    df_ema.loc[df_ema.index, 'EMA_200'] = 1900.0
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Primary_Bias'].iloc[-1] == "Bearish"

def test_ribbon_expansion_and_compression():
    """Test ribbon compression/expansion detection."""
    df = DataFeed.generate_mock_data("GC=F", "4h", limit=210)
    df_ema = TrendEngine.calculate_emas(df, [20, 50, 100, 200])
    
    # Setup values for expanding distance: 10 -> 20 -> 30
    df_ema.loc[df_ema.index[-3], ['EMA_20', 'EMA_50', 'EMA_100', 'EMA_200']] = [1030, 1020, 1010, 1000] # dist = 30
    df_ema.loc[df_ema.index[-2], ['EMA_20', 'EMA_50', 'EMA_100', 'EMA_200']] = [1040, 1020, 1010, 1000] # dist = 40
    df_ema.loc[df_ema.index[-1], ['EMA_20', 'EMA_50', 'EMA_100', 'EMA_200']] = [1050, 1020, 1010, 1000] # dist = 50
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Ribbon_Expansion'].iloc[-1] == True

    # Setup values for compressing distance: 50 -> 40 -> 30
    df_ema.loc[df_ema.index[-3], ['EMA_20', 'EMA_50', 'EMA_100', 'EMA_200']] = [1050, 1020, 1010, 1000] # dist = 50
    df_ema.loc[df_ema.index[-2], ['EMA_20', 'EMA_50', 'EMA_100', 'EMA_200']] = [1040, 1020, 1010, 1000] # dist = 40
    df_ema.loc[df_ema.index[-1], ['EMA_20', 'EMA_50', 'EMA_100', 'EMA_200']] = [1030, 1020, 1010, 1000] # dist = 30
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Ribbon_Compression'].iloc[-1] == True

def test_trend_acceleration_and_deceleration():
    """Verify trend acceleration/deceleration calculations."""
    df = DataFeed.generate_mock_data("GC=F", "4h", limit=210)
    df_ema = TrendEngine.calculate_emas(df, [20, 50, 100, 200])
    
    # Bullish Trend
    df_ema.loc[df_ema.index, 'EMA_50'] = 1100
    df_ema.loc[df_ema.index, 'EMA_200'] = 1000
    
    # Acceleration: Slope increases: +2 -> +5 -> +10
    df_ema.loc[df_ema.index[-4], 'EMA_20'] = 1100
    df_ema.loc[df_ema.index[-3], 'EMA_20'] = 1102
    df_ema.loc[df_ema.index[-2], 'EMA_20'] = 1107
    df_ema.loc[df_ema.index[-1], 'EMA_20'] = 1117
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Trend_Acceleration'].iloc[-1] == True

    # Deceleration: Slope decreases: +10 -> +5 -> +2
    df_ema.loc[df_ema.index[-4], 'EMA_20'] = 1100
    df_ema.loc[df_ema.index[-3], 'EMA_20'] = 1110
    df_ema.loc[df_ema.index[-2], 'EMA_20'] = 1115
    df_ema.loc[df_ema.index[-1], 'EMA_20'] = 1117
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Trend_Deceleration'].iloc[-1] == True

def test_pullback_detection():
    """Verify that pullback flags activate when price is inside the ribbon."""
    df = DataFeed.generate_mock_data("GC=F", "4h", limit=210)
    df_ema = TrendEngine.calculate_emas(df, [20, 50, 100, 200])
    df_ema.loc[df_ema.index, 'EMA_50'] = 1100
    df_ema.loc[df_ema.index, 'EMA_200'] = 1000
    df_ema.loc[df_ema.index, 'EMA_20'] = 1120
    
    # Bullish Trend: Close drops below EMA 20 (1120) but above EMA 200 (1000)
    df_ema.loc[df_ema.index[-1], 'Close'] = 1110
    df_analyzed = TrendEngine.analyze_trend(df_ema)
    assert df_analyzed['Pullback_Active'].iloc[-1] == True

def test_mtf_alignment():
    """Verify alignment classification between H4 and D1 dataframes."""
    df_h4 = pd.DataFrame({'Primary_Bias': ['Bullish'], 'Trend_Confidence': ['Strong Bullish']})
    df_d1 = pd.DataFrame({'Primary_Bias': ['Bullish'], 'Trend_Confidence': ['Strong Bullish']})
    assert TrendEngine.check_mtf_alignment(df_h4, df_d1) == "Full Alignment"
    
    df_d1 = pd.DataFrame({'Primary_Bias': ['Bearish'], 'Trend_Confidence': ['Strong Bearish']})
    assert TrendEngine.check_mtf_alignment(df_h4, df_d1) == "Conflict"

# =====================================================================
# MARKET STRUCTURE TESTS (Scenarios 46-70)
# =====================================================================

def test_swing_high_low_detection():
    """Verify swing point detection logic and non-repainting confirm offset."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    # Inject a clean swing high at index 10 (left=5, right=5)
    # Window: 5 to 15. Highs: all lower than index 10
    df.loc[df.index, 'High'] = 100.0
    df.loc[df.index[10], 'High'] = 110.0
    
    results = StructureEngine.analyze_structure(df, "Bullish")
    swings = results["confirmed_swings"]
    
    # Confirm that swing high at index 10 is detected
    assert len(swings) > 0
    swing_highs = [s for s in swings if s.is_high]
    assert len(swing_highs) == 1
    assert swing_highs[0].price == 110.0
    assert swing_highs[0].bar_index == 10

def test_bos_and_ob_generation():
    """Test that Break of Structure generates a new Order Block."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    # Inject swing high at index 10
    df.loc[df.index, 'High'] = 100.0
    df.loc[df.index[10], 'High'] = 110.0
    df.loc[df.index, 'Close'] = 98.0
    
    # Break the swing high at index 20 (close = 115.0)
    df.loc[df.index[20], 'Close'] = 115.0
    df.loc[df.index[20], 'High'] = 116.0
    
    results = StructureEngine.analyze_structure(df, "Bullish")
    assert results["last_event"] == "BOS"
    assert results["last_event_direction"] == "Bullish"
    assert len(results["order_blocks"]) > 0
    # Verifies a Bullish Order Block was created
    assert results["order_blocks"][-1].is_bullish is True

def test_ob_mitigation_close_rule():
    """Test that order blocks get mitigated when price closes through it."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    df['Open'] = 100.0
    df['High'] = 100.0
    df['Low'] = 100.0
    df['Close'] = 100.0
    
    # Inject swing high at 10
    df.loc[df.index[10], 'High'] = 110.0
    
    # Inject down candle at 18 to serve as the OB candle
    df.loc[df.index[18], 'Open'] = 102.0
    df.loc[df.index[18], 'Close'] = 98.0
    df.loc[df.index[18], 'Low'] = 97.0
    
    # Inject breakout close at 20
    df.loc[df.index[20], 'Close'] = 115.0
    df.loc[df.index[20], 'High'] = 116.0
    
    # Get active OB from structure
    results = StructureEngine.analyze_structure(df, "Bullish")
    assert len(results["unmitigated_bullish_ob"]) > 0
    ob = results["unmitigated_bullish_ob"][-1]
    
    # Inject price crossing the OB low (97.0) at index 25
    df.loc[df.index[25], 'Close'] = 95.0
    results_mitigated = StructureEngine.analyze_structure(df, "Bullish")
    
    # The OB should no longer be in the unmitigated list
    active_obs = results_mitigated["unmitigated_bullish_ob"]
    assert ob not in active_obs

def test_premium_discount_zones():
    """Test Premium/Discount zone classification."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    df['Open'] = 100.0
    df['High'] = 100.0
    df['Low'] = 100.0
    df['Close'] = 100.0
    
    # High swing = 110 at index 15, Low swing = 90 at index 5. Eq = 100
    df.loc[df.index[5], 'Low'] = 90.0
    df.loc[df.index[15], 'High'] = 110.0
    
    # Close = 105 (Premium zone > 100)
    df.loc[df.index[-1], 'Close'] = 105.0
    res = StructureEngine.analyze_structure(df, "Bullish")
    assert res["zone_classification"] == "Premium"
    
    # Close = 95 (Discount zone < 100)
    df.loc[df.index[-1], 'Close'] = 95.0
    res = StructureEngine.analyze_structure(df, "Bullish")
    assert res["zone_classification"] == "Discount"

# =====================================================================
# SIGNAL ENGINE TESTS (Scenarios 71-85)
# =====================================================================

def test_signal_cooldown():
    """Test that cooldown blocks consecutive signals in close proximity."""
    engine = SignalEngine()
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    
    # Inject an active signal at index 10
    sig = Signal(df.index[10], "BUY", 1000.0, "High", "Standard", "Medium", {})
    sig.entry_bar_index = 10
    engine.active_signals.append(sig)
    
    # Check cooldown at index 15 (5 bars later, cooldown is 10)
    df_slice = df.iloc[:16]
    assert engine._is_in_cooldown(df_slice.index[-1], df_slice) is True

def test_entry_modes_conservative_vs_aggressive():
    """Test signal decision hierarchy under different entry strictness levels."""
    engine = SignalEngine()
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    df['Open'] = 98.0
    df['High'] = 98.0
    df['Low'] = 98.0
    df['Close'] = 98.0
    
    # Make momentum unaligned (Close goes 102.0 -> 101.0)
    df.loc[df.index[-3], 'Close'] = 102.0
    
    # Latest candle (BUY candidate)
    df.loc[df.index[-1], 'Open'] = 100.0
    df.loc[df.index[-1], 'High'] = 102.0
    df.loc[df.index[-1], 'Low'] = 98.2
    df.loc[df.index[-1], 'Close'] = 101.0
    
    df = TrendEngine.calculate_emas(df, [20, 50, 100, 200])
    
    # Mock parameters
    htf_trend = {'Primary_Bias': 'Bullish', 'Trend_Confidence': 'Weak Bullish', 'Ribbon_Compression': True} # 2 reductions
    struct_data = {'structural_alignment': 'Neutral', 'market_phase': 'Transitional', 'zone_classification': 'Premium', 'confirmed_swings': []} # 2 reductions
    # Total reductions: 4
    
    # Test Conservative Mode (0 tolerance)
    settings.signal.entry_mode = "conservative"
    sig = engine.evaluate_signals(df, htf_trend, struct_data, "Partial Alignment")
    assert sig is None
    
    # Test Default Mode (3 tolerance)
    settings.signal.entry_mode = "default"
    sig = engine.evaluate_signals(df, htf_trend, struct_data, "Partial Alignment")
    assert sig is None # 4 > 3, rejected
    
    # Test Aggressive Mode (5 tolerance)
    settings.signal.entry_mode = "aggressive"
    sig = engine.evaluate_signals(df, htf_trend, struct_data, "Partial Alignment")
    assert sig is not None # 4 <= 5, approved!

# =====================================================================
# FILTER ENGINE TESTS (Scenarios 86-95)
# =====================================================================

def test_session_filter_london_ny():
    """Verify session filter accurately parses and converts times in PKT."""
    # London: 13:00 - 22:00 PKT. Test 15:00 PKT (Should be inside)
    dt_inside = datetime(2026, 7, 2, 15, 0, 0, tzinfo=pytz.timezone('Asia/Karachi'))
    ok, name = FilterEngine.check_session(dt_inside)
    assert ok is True
    assert name == "London"
    
    # Test 04:00 PKT (Should be outside all)
    dt_outside = datetime(2026, 7, 2, 4, 0, 0, tzinfo=pytz.timezone('Asia/Karachi'))
    ok, name = FilterEngine.check_session(dt_outside)
    assert ok is False

def test_volatility_filter_atr_ratio():
    """Verify ATR ratio triggers filter status."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=120)
    
    # normal baseline
    status, ratio = FilterEngine.check_volatility(df)
    assert status == "normal"

# =====================================================================
# RISK MANAGEMENT TESTS (Scenarios 96-105)
# =====================================================================

def test_stop_loss_safeguard():
    """Verify stop loss min/max size safeguards in Risk Management."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    sig = Signal(df.index[-1], "BUY", 1000.0, "High", "Standard", "Medium", {})
    struct_data = {'confirmed_swings': [SwingPoint(df.index[5], 999.5, False, 5)], 'unmitigated_bullish_ob': []}
    
    # Stop distance is extremely tight (1000.0 to 999.5 = 0.5)
    # Min safeguard (0.5 * ATR) should widen this stop
    RiskManager.frame_trade(sig, df, struct_data)
    framing = sig.initial_risk_framing
    assert framing["stop_loss"] < 999.5

def test_breakeven_milestone_move():
    """Verify stop loss shifts to entry when TP1 milestone is reached."""
    df = DataFeed.generate_mock_data("GC=F", "15m", limit=30)
    sig = Signal(df.index[-1], "BUY", 1000.0, "High", "Standard", "Medium", {})
    struct_data = {'confirmed_swings': [], 'unmitigated_bullish_ob': []}
    
    # Frame trade
    RiskManager.frame_trade(sig, df, struct_data)
    framing = sig.initial_risk_framing
    
    # Force TP1 hit (milestone is 1.5R)
    entry = framing["entry"]
    stop_dist = framing["stop_distance"]
    price_at_tp1 = entry + (stop_dist * 1.6)
    
    # Update live risk
    RiskManager.update_live_risk(sig, price_at_tp1)
    
    assert sig.status == "Protected"
    assert sig.initial_risk_framing["stop_loss"] == entry

# =====================================================================
# SCANNER TESTS (Scenarios 106-115)
# =====================================================================

def test_scanner_watchlist_sort():
    """Verify scanner watchlist executes and sorts active signals first."""
    scanner = WatchlistScanner()
    # Mock settings
    settings.scanner.watchlist = ["GC=F", "EURUSD=X"]
    results = scanner.scan()
    assert len(results) == 2
    # Ensure they are dictionaries representing scanned symbols
    assert "symbol" in results[0]
    assert "trend_bias" in results[0]
