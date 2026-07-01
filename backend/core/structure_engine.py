import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from backend.config import settings

class SwingPoint:
    def __init__(self, index: Any, price: float, is_high: bool, bar_index: int, is_major: bool = True):
        self.index = index
        self.price = price
        self.is_high = is_high
        self.bar_index = bar_index  # integer index of the bar
        self.is_major = is_major
        self.broken = False
        self.break_bar = -1

class OrderBlock:
    def __init__(self, low: float, high: float, is_bullish: bool, bar_index: int, index: Any):
        self.low = low
        self.high = high
        self.is_bullish = is_bullish
        self.bar_index = bar_index
        self.index = index
        self.mitigated = False
        self.mitigation_bar = -1

class StructureEngine:
    """
    Analyzes market structure: swings, BOS, CHoCH, Order Blocks, and Premium/Discount.
    Maintains 100% non-repainting behavior by confirming swing points only after close.
    """

    @staticmethod
    def analyze_structure(df_etf: pd.DataFrame, trend_bias: str) -> Dict[str, Any]:
        """
        Analyzes the execution timeframe structure.
        Returns active swing points, order blocks, premium/discount zones, and alignment status.
        """
        left = settings.structure.swing_left_bars
        right = settings.structure.swing_right_bars
        max_ob = settings.structure.max_order_blocks
        ob_rule = settings.structure.ob_invalidation_rule
        
        high = df_etf['High']
        low = df_etf['Low']
        close = df_etf['Close']
        
        confirmed_swings: List[SwingPoint] = []
        order_blocks: List[OrderBlock] = []
        
        last_event = "None"
        last_event_dir = "None"
        
        # 1. Swing Detection Loop (lagged confirmation)
        for i in range(left, len(df_etf) - right):
            is_high = True
            is_low = True
            
            for k in range(1, left + 1):
                if high.iloc[i] <= high.iloc[i - k]:
                    is_high = False
                    break
            for k in range(1, right + 1):
                if high.iloc[i] < high.iloc[i + k]:
                    is_high = False
                    break
                    
            for k in range(1, left + 1):
                if low.iloc[i] >= low.iloc[i - k]:
                    is_low = False
                    break
            for k in range(1, right + 1):
                if low.iloc[i] > low.iloc[i + k]:
                    is_low = False
                    break
            
            if is_high:
                is_major = True
                prev_highs = [s.price for s in confirmed_swings if s.is_high]
                if prev_highs and high.iloc[i] < max(prev_highs[-3:]):
                    is_major = False
                confirmed_swings.append(SwingPoint(df_etf.index[i], high.iloc[i], True, i, is_major))
                
            if is_low:
                is_major = True
                prev_lows = [s.price for s in confirmed_swings if not s.is_high]
                if prev_lows and low.iloc[i] > min(prev_lows[-3:]):
                    is_major = False
                confirmed_swings.append(SwingPoint(df_etf.index[i], low.iloc[i], False, i, is_major))

        # 2. Breakout and Mitigation Loop (real-time up to the last candle)
        for idx in range(left, len(df_etf)):
            row_close = close.iloc[idx]
            row_low = low.iloc[idx]
            row_high = high.iloc[idx]
            
            # Filter swings confirmed at or before current index 'idx'
            available_swings = [s for s in confirmed_swings if s.bar_index + right <= idx]
            active_highs = [s for s in available_swings if s.is_high and not s.broken]
            active_lows = [s for s in available_swings if not s.is_high and not s.broken]
            
            if active_highs and row_close > active_highs[-1].price:
                broken_swing = active_highs[-1]
                # Mark as broken in master list
                for s in confirmed_swings:
                    if s.bar_index == broken_swing.bar_index and s.is_high:
                        s.broken = True
                        s.break_bar = idx
                
                if trend_bias == 'Bullish' or trend_bias == 'Neutral':
                    last_event = "BOS"
                    last_event_dir = "Bullish"
                else:
                    last_event = "CHoCH"
                    last_event_dir = "Bullish"
                    
                # Create Bullish Order Block (last down candle before breaking move)
                ob_bar = idx - 1
                for b in range(idx - 1, max(0, broken_swing.bar_index - 2), -1):
                    if close.iloc[b] < df_etf['Open'].iloc[b]:
                        ob_bar = b
                        break
                order_blocks.append(OrderBlock(
                    low=low.iloc[ob_bar],
                    high=high.iloc[ob_bar],
                    is_bullish=True,
                    bar_index=ob_bar,
                    index=df_etf.index[ob_bar]
                ))
                
            elif active_lows and row_close < active_lows[-1].price:
                broken_swing = active_lows[-1]
                # Mark as broken in master list
                for s in confirmed_swings:
                    if s.bar_index == broken_swing.bar_index and not s.is_high:
                        s.broken = True
                        s.break_bar = idx
                
                if trend_bias == 'Bearish' or trend_bias == 'Neutral':
                    last_event = "BOS"
                    last_event_dir = "Bearish"
                else:
                    last_event = "CHoCH"
                    last_event_dir = "Bearish"
                    
                # Create Bearish Order Block (last up candle before breaking move)
                ob_bar = idx - 1
                for b in range(idx - 1, max(0, broken_swing.bar_index - 2), -1):
                    if close.iloc[b] > df_etf['Open'].iloc[b]:
                        ob_bar = b
                        break
                order_blocks.append(OrderBlock(
                    low=low.iloc[ob_bar],
                    high=high.iloc[ob_bar],
                    is_bullish=False,
                    bar_index=ob_bar,
                    index=df_etf.index[ob_bar]
                ))
                
            # OB mitigation checks
            for ob in order_blocks:
                if not ob.mitigated:
                    if ob.is_bullish:
                        val = row_close if ob_rule == "close" else row_low
                        if val < ob.low:
                            ob.mitigated = True
                            ob.mitigation_bar = idx
                    else:
                        val = row_close if ob_rule == "close" else row_high
                        if val > ob.high:
                            ob.mitigated = True
                            ob.mitigation_bar = idx

        # Calculate final state for the last confirmed bar in the dataset
        last_close = close.iloc[-1]
        active_sw_highs = [s for s in confirmed_swings if s.is_high]
        active_sw_lows = [s for s in confirmed_swings if not s.is_high]
        
        # Premium/Discount zones using major swing high/low of last 100 bars
        eq_zone = "Equilibrium"
        range_high = active_sw_highs[-1].price if active_sw_highs else last_close * 1.01
        range_low = active_sw_lows[-1].price if active_sw_lows else last_close * 0.99
        
        eq = (range_high + range_low) / 2.0
        
        if last_close > eq * 1.002:
            eq_zone = "Premium"
        elif last_close < eq * 0.998:
            eq_zone = "Discount"
            
        # Filter active unmitigated Order Blocks
        unmitigated_bullish_ob = [ob for ob in order_blocks if ob.is_bullish and not ob.mitigated][-max_ob:]
        unmitigated_bearish_ob = [ob for ob in order_blocks if not ob.is_bullish and not ob.mitigated][-max_ob:]
        
        # Structural Alignment Status
        struct_alignment = "Neutral"
        if last_event_dir == "Bullish" and trend_bias == "Bullish":
            struct_alignment = "Aligned"
        elif last_event_dir == "Bearish" and trend_bias == "Bearish":
            struct_alignment = "Aligned"
        elif last_event_dir != "None" and last_event_dir != trend_bias:
            struct_alignment = "Conflict"
            
        # Determine Market Phase
        market_phase = "Transitional"
        if last_event == "BOS":
            market_phase = "Trending"
        elif last_event == "None" and len(confirmed_swings) > 4:
            # Check if swings are alternating within a tight range
            recent_swings = confirmed_swings[-5:]
            prices = [s.price for s in recent_swings]
            if (max(prices) - min(prices)) / last_close < 0.02:
                market_phase = "Ranging"
                
        # Structure Strength Rating
        strength_rating = "Moderate Strength"
        if struct_alignment == "Aligned" and market_phase == "Trending":
            strength_rating = "High Strength"
        elif struct_alignment == "Conflict":
            strength_rating = "Structure Failure"
            
        return {
            "confirmed_swings": confirmed_swings,
            "order_blocks": order_blocks,
            "unmitigated_bullish_ob": unmitigated_bullish_ob,
            "unmitigated_bearish_ob": unmitigated_bearish_ob,
            "range_high": range_high,
            "range_low": range_low,
            "equilibrium": eq,
            "zone_classification": eq_zone,
            "last_event": last_event,
            "last_event_direction": last_event_dir,
            "structural_alignment": struct_alignment,
            "market_phase": market_phase,
            "structure_strength": strength_rating
        }
