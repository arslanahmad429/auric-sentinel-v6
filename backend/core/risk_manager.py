import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from backend.config import settings

class RiskManager:
    """
    Frames trades with SL, TP targets, position sizing, 
    and handles dynamic adjustments like breakeven triggers.
    """

    @staticmethod
    def frame_trade(signal: Any, df_etf: pd.DataFrame, struct_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates SL, TPs, position size, and initial risk framing for an approved signal.
        Modifies the signal's initial_risk_framing directly.
        """
        entry_price = signal.price
        direction = signal.direction
        
        # Calculate ATR on ETF for safeguards
        high = df_etf['High']
        low = df_etf['Low']
        close = df_etf['Close']
        high_low = high - low
        tr = pd.concat([high_low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
        atr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
        
        # --- 1. Stop Loss Calculation ---
        sl_price = 0.0
        
        if settings.risk.stop_loss_method == "structure":
            # Structure-based: place below recent swing point or OB
            if direction == "BUY":
                # Find recent confirmed swing low
                recent_sws = [s.price for s in struct_data.get('confirmed_swings', []) if not s.is_high]
                sl_base = recent_sws[-1] if recent_sws else entry_price * 0.99
                
                # Check if we have active order blocks for extra cushion
                bullish_obs = struct_data.get('unmitigated_bullish_ob', [])
                if bullish_obs:
                    sl_base = min(sl_base, bullish_obs[-1].low)
                    
                # Add tiny buffer (e.g. 5% of ATR)
                sl_price = sl_base - (0.05 * atr)
            else: # SELL
                recent_sws = [s.price for s in struct_data.get('confirmed_swings', []) if s.is_high]
                sl_base = recent_sws[-1] if recent_sws else entry_price * 1.01
                
                bearish_obs = struct_data.get('unmitigated_bearish_ob', [])
                if bearish_obs:
                    sl_base = max(sl_base, bearish_obs[-1].high)
                    
                sl_price = sl_base + (0.05 * atr)
        else:
            # Volatility-based stop loss (ATR buffer)
            sl_distance = atr * 1.5
            sl_price = entry_price - sl_distance if direction == "BUY" else entry_price + sl_distance
            
        # Apply safeguards (Min/Max stop distance in ATR units)
        actual_stop_dist = abs(entry_price - sl_price)
        min_stop_allowed = atr * settings.risk.min_stop_atr_multiplier
        max_stop_allowed = atr * settings.risk.max_stop_atr_multiplier
        
        if actual_stop_dist < min_stop_allowed:
            sl_price = entry_price - min_stop_allowed if direction == "BUY" else entry_price + min_stop_allowed
        elif actual_stop_dist > max_stop_allowed:
            sl_price = entry_price - max_stop_allowed if direction == "BUY" else entry_price + max_stop_allowed
            
        stop_distance = abs(entry_price - sl_price)

        # --- 2. Take Profit Targets ---
        tp_targets: List[float] = []
        
        if settings.risk.take_profit_method == "fixed_r":
            # Target multiples of R
            for multiple in settings.risk.tp_targets_r:
                tp = entry_price + (stop_distance * multiple) if direction == "BUY" else entry_price - (stop_distance * multiple)
                tp_targets.append(tp)
        else:
            # Structure-based targets (recent opposite swing highs/lows)
            if direction == "BUY":
                recent_highs = [s.price for s in struct_data.get('confirmed_swings', []) if s.is_high]
                tp_base = recent_highs[-1] if recent_highs else entry_price + (stop_distance * 3.0)
                tp_targets = [tp_base * 0.995, tp_base, tp_base * 1.01] # 3 splits near resistance
            else:
                recent_lows = [s.price for s in struct_data.get('confirmed_swings', []) if not s.is_high]
                tp_base = recent_lows[-1] if recent_lows else entry_price - (stop_distance * 3.0)
                tp_targets = [tp_base * 1.005, tp_base, tp_base * 0.99]
                
        # --- 3. Position Sizing ---
        suggested_units = 0.0
        suggested_lots = 0.0
        
        account_size = settings.risk.account_size
        risk_pct = settings.risk.risk_percentage
        risk_usd = account_size * (risk_pct / 100.0)
        
        if stop_distance > 0:
            suggested_units = risk_usd / stop_distance
            # Assuming standard Gold contract size: 1 lot = 100 units (ounces)
            # FX contract size: 1 lot = 100,000 units (base currency)
            # We provide a general lot guide:
            suggested_lots = suggested_units / 100.0
            
        risk_framing = {
            "entry": entry_price,
            "stop_loss": sl_price,
            "original_stop_loss": sl_price,
            "take_profits": tp_targets,
            "stop_distance": stop_distance,
            "risk_usd": risk_usd,
            "suggested_units": round(suggested_units, 2),
            "suggested_lots": round(suggested_lots, 2),
            "breakeven_triggered": False,
            "live_unrealized_r": 0.0
        }
        
        signal.initial_risk_framing = risk_framing
        return risk_framing

    @staticmethod
    def update_live_risk(signal: Any, current_close: float) -> Dict[str, Any]:
        """
        Updates the live unrealized R-multiple and monitors breakeven milestones.
        """
        framing = signal.initial_risk_framing
        if not framing:
            return {}
            
        entry = framing["entry"]
        orig_sl = framing["original_stop_loss"]
        stop_dist = framing["stop_distance"]
        direction = signal.direction
        
        if stop_dist <= 0:
            return framing
            
        # Calculate live R-multiple
        if direction == "BUY":
            live_r = (current_close - entry) / stop_dist
        else:
            live_r = (entry - current_close) / stop_dist
            
        framing["live_unrealized_r"] = round(live_r, 2)
        
        # Check Breakeven trigger condition
        if not framing["breakeven_triggered"]:
            breakeven_milestone = settings.risk.breakeven_milestone_r
            if live_r >= breakeven_milestone:
                framing["breakeven_triggered"] = True
                framing["stop_loss"] = entry # Move SL to Entry
                signal.status = "Protected"
                if settings.debug_mode:
                    print(f"[RISK] {signal.timestamp} - Trade moved to Breakeven (TP1 milestone reached)")
                    
        # Check final resolution (take profit 3 hit or stop hit)
        if direction == "BUY":
            # Hit target 3
            if current_close >= framing["take_profits"][-1]:
                signal.status = "Completed"
            # Hit stop loss
            elif current_close <= framing["stop_loss"]:
                signal.status = "Completed"
        else:
            if current_close <= framing["take_profits"][-1]:
                signal.status = "Completed"
            elif current_close >= framing["stop_loss"]:
                signal.status = "Completed"
                
        return framing
