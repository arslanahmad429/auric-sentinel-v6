import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.config import settings

class Signal:
    def __init__(self, 
                 timestamp: Any,
                 direction: str, # 'BUY' or 'SELL'
                 price: float,
                 confidence: str, # 'Very High', 'High', 'Medium', 'Low'
                 quality: str, # 'Institutional', 'Standard', 'Aggressive'
                 priority: str, # 'High', 'Medium', 'Low'
                 justification: Dict[str, Any],
                 status: str = "Active"):
        self.timestamp = timestamp
        self.direction = direction
        self.price = price
        self.confidence = confidence
        self.quality = quality
        self.priority = priority
        self.justification = justification
        self.status = status  # 'Active', 'Protected', 'Aging', 'Completed', 'Invalidated', 'Cancelled'
        self.age_bars = 0
        self.entry_bar_index = -1
        self.initial_risk_framing: Dict[str, float] = {}

class SignalEngine:
    """
    Evaluates candidate setups against the 8-stage decision hierarchy.
    Tracks active signals, handles signal memory/cooldown, and evaluates entry modes.
    """

    def __init__(self):
        self.active_signals: List[Signal] = []
        self.historical_signals: List[Signal] = []

    def evaluate_signals(self, 
                        df_etf: pd.DataFrame, 
                        htf_trend_data: Dict[str, Any],
                        struct_data: Dict[str, Any],
                        mtf_alignment: str) -> Optional[Signal]:
        """
        Runs the 8-stage decision pipeline on the latest confirmed bar of the execution timeframe.
        Returns a new Signal object if approved, else None.
        """
        if df_etf.empty or not htf_trend_data or not struct_data:
            return None

        # Check signal cooldown/memory to prevent spam
        if self._is_in_cooldown(df_etf.index[-1], df_etf):
            return None

        # Gather inputs from latest bars
        last_idx = df_etf.index[-1]
        last_close = df_etf['Close'].iloc[-1]
        last_open = df_etf['Open'].iloc[-1]
        last_high = df_etf['High'].iloc[-1]
        last_low = df_etf['Low'].iloc[-1]
        
        # Pullback & EMAs from ETF
        # Note: We calculate ETF EMAs for immediate rejection analysis
        e20 = df_etf['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
        e50 = df_etf['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
        e200 = df_etf['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
        
        # Calculate ATR on ETF for price action checks
        high_low = df_etf['High'] - df_etf['Low']
        tr = pd.concat([high_low, (df_etf['High'] - df_etf['Close'].shift(1)).abs(), (df_etf['Low'] - df_etf['Close'].shift(1)).abs()], axis=1).max(axis=1)
        atr_etf = tr.ewm(span=14, adjust=False).mean().iloc[-1]
        
        # Determine candidate direction
        cand_dir = "None"
        if last_close > last_open:
            cand_dir = "BUY"
        elif last_close < last_open:
            cand_dir = "SELL"
            
        if cand_dir == "None":
            return None

        # Toggles check
        if cand_dir == "BUY" and not settings.signal.allow_longs:
            return None
        if cand_dir == "SELL" and not settings.signal.allow_shorts:
            return None

        # ----------------------------------------------------
        # 8-STAGE DECISION HIERARCHY
        # ----------------------------------------------------
        justification: Dict[str, Any] = {}
        score_reductions = 0
        rejection_reason = ""

        # --- STAGE 1: TREND CONTEXT ---
        htf_bias = htf_trend_data.get('Primary_Bias', 'Neutral')
        htf_conf = htf_trend_data.get('Trend_Confidence', 'Neutral')
        
        # Hard conflict check
        if htf_bias == 'Bullish' and cand_dir == 'SELL' and not settings.signal.allow_counter_trend:
            rejection_reason = "Stage 1: Direct trend conflict (Bullish bias vs SELL signal)"
        elif htf_bias == 'Bearish' and cand_dir == 'BUY' and not settings.signal.allow_counter_trend:
            rejection_reason = "Stage 1: Direct trend conflict (Bearish bias vs BUY signal)"
            
        if rejection_reason:
            return self._record_rejection(last_idx, cand_dir, rejection_reason)
            
        # Soft warnings
        if htf_bias == 'Neutral':
            score_reductions += 1
            justification["Trend"] = "Neutral HTF Trend Context (+1 caution)"
        else:
            justification["Trend"] = f"HTF Trend: {htf_conf}"
            if "Weak" in htf_conf or "Transitional" in htf_conf:
                score_reductions += 1
                justification["Trend"] += " (+1 caution)"

        # --- STAGE 2: MARKET STRUCTURE ---
        struct_align = struct_data.get('structural_alignment', 'Neutral')
        market_phase = struct_data.get('market_phase', 'Transitional')
        zone_class = struct_data.get('zone_classification', 'Equilibrium')
        
        # Hard conflict check (under default/strict settings)
        if settings.signal.alignment_strictness == 'all' and struct_align == 'Conflict':
            rejection_reason = f"Stage 2: Structural alignment conflict (Trend vs Structure)"
            return self._record_rejection(last_idx, cand_dir, rejection_reason)
            
        # Soft warnings
        if struct_align == 'Conflict':
            score_reductions += 2
            justification["Structure"] = "Structure conflict (+2 caution)"
        elif struct_align == 'Neutral':
            score_reductions += 1
            justification["Structure"] = "Neutral structure alignment (+1 caution)"
        else:
            justification["Structure"] = f"Structure Aligned, Phase: {market_phase}"
            
        # Premium/Discount check (Buy in Discount, Sell in Premium preferred)
        if cand_dir == "BUY" and zone_class == "Premium":
            score_reductions += 1
            justification["Zone"] = "Buying in Premium zone (+1 caution)"
        elif cand_dir == "SELL" and zone_class == "Discount":
            score_reductions += 1
            justification["Zone"] = "Selling in Discount zone (+1 caution)"
        else:
            justification["Zone"] = f"Price in {zone_class} zone (Favorable)"

        # --- STAGE 3: EMA CONFIRMATION ---
        # Ribbon compression, trend exhaustion check
        exhaustion = htf_trend_data.get('Trend_Exhaustion', False)
        compression = htf_trend_data.get('Ribbon_Compression', False)
        
        if exhaustion:
            score_reductions += 2
            justification["EMA_Ribbon"] = "HTF Ribbon Exhaustion active (+2 caution)"
        elif compression:
            score_reductions += 1
            justification["EMA_Ribbon"] = "HTF Ribbon Compression active (+1 caution)"
        else:
            justification["EMA_Ribbon"] = "HTF Ribbon Healthy"

        # --- STAGE 4: PRICE ACTION (Pullback & Rejection) ---
        # Verify if a pullback was active and if we have a rejection candlestick
        # Rejection candle = candle wick in direction of trend is significant (lower wick for BUY, upper wick for SELL)
        range_candle = last_high - last_low
        if range_candle <= 0:
            return None
            
        rejection_detected = False
        wick_pct = 0.0
        
        if cand_dir == "BUY":
            lower_wick = min(last_open, last_close) - last_low
            wick_pct = lower_wick / range_candle
            # Requires lower wick to be >= 35% of candle range to indicate rejection of lower prices
            if wick_pct >= 0.35:
                rejection_detected = True
        else:
            upper_wick = last_high - max(last_open, last_close)
            wick_pct = upper_wick / range_candle
            if wick_pct >= 0.35:
                rejection_detected = True
                
        # Also check dynamic touch on Order Blocks or dynamic EMA Support (EMA 50 or 200)
        touches_support = False
        
        # Check if low (buy) or high (sell) touches active order block zones
        if cand_dir == "BUY":
            for ob in struct_data.get('unmitigated_bullish_ob', []):
                if last_low <= ob.high and last_high >= ob.low:
                    touches_support = True
                    justification["PA_Confirmation"] = "Order Block Touch"
                    break
            # Or touch EMA 50/200
            if not touches_support and (last_low <= e50 * 1.002 and last_low >= e50 * 0.998):
                touches_support = True
                justification["PA_Confirmation"] = "EMA 50 Bounce"
        else:
            for ob in struct_data.get('unmitigated_bearish_ob', []):
                if last_high >= ob.low and last_low <= ob.high:
                    touches_support = True
                    justification["PA_Confirmation"] = "Order Block Touch"
                    break
            if not touches_support and (last_high >= e50 * 0.998 and last_high <= e50 * 1.002):
                touches_support = True
                justification["PA_Confirmation"] = "EMA 50 Bounce"
                
        if not rejection_detected:
            score_reductions += 1
            justification["PriceAction"] = f"No clean rejection wick (Wick: {wick_pct:.1%}) (+1 caution)"
        else:
            justification["PriceAction"] = f"Clean Rejection Wick ({wick_pct:.1%})"
            
        if not touches_support:
            score_reductions += 1
            justification["PA_Confirmation"] = "No structural support touch (+1 caution)"

        # --- STAGE 5: MOMENTUM ---
        # Compute dynamic momentum on execution timeframe (e.g. rate of change of Close)
        roc = (last_close - df_etf['Close'].iloc[-3]) / df_etf['Close'].iloc[-3]
        momentum_aligned = False
        if cand_dir == "BUY" and roc > 0:
            momentum_aligned = True
        elif cand_dir == "SELL" and roc < 0:
            momentum_aligned = True
            
        if not momentum_aligned:
            score_reductions += 1
            justification["Momentum"] = f"Momentum not aligned (ROC: {roc:.3%}) (+1 caution)"
        else:
            justification["Momentum"] = f"Momentum Aligned (ROC: {roc:.3%})"

        # --- ENTRY MODE FILTERING (Stages 1-5 evaluation) ---
        mode = settings.signal.entry_mode
        
        # Conservative Mode: 0 tolerance for score reductions in stages 1-5
        if mode == "conservative" and score_reductions > 0:
            rejection_reason = f"Stage 8: Rejected due to Conservative Mode restrictions (Reductions: {score_reductions})"
            return self._record_rejection(last_idx, cand_dir, rejection_reason)
            
        # Default Mode: allows up to 3 reductions
        if mode == "default" and score_reductions > 3:
            rejection_reason = f"Stage 8: Rejected due to Default Mode limit (Reductions: {score_reductions} > 3)"
            return self._record_rejection(last_idx, cand_dir, rejection_reason)
            
        # Aggressive Mode: allows up to 5 reductions
        if mode == "aggressive" and score_reductions > 5:
            rejection_reason = f"Stage 8: Rejected due to Aggressive Mode limit (Reductions: {score_reductions} > 5)"
            return self._record_rejection(last_idx, cand_dir, rejection_reason)

        # ----------------------------------------------------
        # STAGE CONFIDENCE & QUALITY CLASSIFICATION
        # ----------------------------------------------------
        confidence = "High"
        if score_reductions == 0:
            confidence = "Very High"
        elif score_reductions in [1, 2]:
            confidence = "High"
        elif score_reductions in [3, 4]:
            confidence = "Medium"
        else:
            confidence = "Low"

        # Determine Quality
        # High Probability Entry: passes all stages at full standing AND MTF alignment is Full AND Trending phase
        quality = "Standard"
        if score_reductions == 0 and mtf_alignment == "Full Alignment" and market_phase == "Trending":
            quality = "Institutional"
        elif score_reductions > 3:
            quality = "Aggressive"

        # Determine Priority
        priority = "Medium"
        if quality == "Institutional" or (confidence == "Very High" and market_phase == "Trending"):
            priority = "High"
        elif confidence == "Low":
            priority = "Low"

        # Construct new approved Signal
        new_signal = Signal(
            timestamp=last_idx,
            direction=cand_dir,
            price=last_close,
            confidence=confidence,
            quality=quality,
            priority=priority,
            justification=justification
        )
        new_signal.entry_bar_index = len(df_etf) - 1
        
        self.active_signals.append(new_signal)
        return new_signal

    def update_active_signals(self, df_etf: pd.DataFrame, trend_data: Dict[str, Any], struct_data: Dict[str, Any]):
        """
        Tracks active signals and updates their age, breakeven status, and check for completions.
        Called on every new bar confirmation.
        """
        last_close = df_etf['Close'].iloc[-1]
        last_high = df_etf['High'].iloc[-1]
        last_low = df_etf['Low'].iloc[-1]
        
        still_active = []
        
        for sig in self.active_signals:
            sig.age_bars += 1
            
            # Check for invalidation based on Structure or Trend failure
            # Invalidation: price closes past structural zone or trend failure confirmed
            # Note: exact stop loss hits are managed by Risk Manager, this is thematic invalidation
            invalidated = False
            
            # If trend failure is active on HTF
            if trend_data.get('Trend_Failure', False):
                sig.status = "Invalidated"
                sig.justification["Exit_Reason"] = "Trend Exit (HTF Trend Failed)"
                invalidated = True
                
            # If structure failure or character change in opposite direction
            elif struct_data.get('structure_strength') == "Structure Failure":
                sig.status = "Invalidated"
                sig.justification["Exit_Reason"] = "Structure Exit (Structure Failure)"
                invalidated = True
                
            # Check aging status (over 40 bars without reaching target/stop)
            if not invalidated and sig.age_bars > 40:
                sig.status = "Aging"
                sig.justification["Status_Warning"] = "Signal Aged (Freshness reduced)"
                
            if invalidated:
                self.historical_signals.append(sig)
            else:
                still_active.append(sig)
                
        self.active_signals = still_active

    def _is_in_cooldown(self, timestamp: Any, df_etf: pd.DataFrame) -> bool:
        """
        Checks if the system is in signal cooldown.
        """
        if not self.active_signals and not self.historical_signals:
            return False
            
        all_sig = self.active_signals + self.historical_signals
        if not all_sig:
            return False
            
        last_sig = all_sig[-1]
        
        # Check bar cooldown
        cooldown_threshold = settings.signal.cooldown_bars
        current_bar_idx = len(df_etf) - 1
        
        if current_bar_idx - last_sig.entry_bar_index < cooldown_threshold:
            return True
            
        return False

    def _record_rejection(self, timestamp: Any, direction: str, reason: str) -> None:
        """
        Internal utility to log a signal rejection event if debug is active.
        """
        if settings.debug_mode:
            print(f"[REJECTION] {timestamp} - {direction} setup rejected. Reason: {reason}")
        return None
