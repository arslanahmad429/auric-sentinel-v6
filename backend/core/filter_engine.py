import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, Any, Tuple
from backend.config import settings

class FilterEngine:
    """
    Gates candidate signals based on trading session timing (in PKT)
    and ATR-based volatility conditions.
    """

    @staticmethod
    def evaluate_filters(signal_dir: str, timestamp: Any, df_etf: pd.DataFrame) -> Tuple[bool, str]:
        """
        Evaluates session and volatility filters.
        Returns: (approved: bool, reason_code: str)
        """
        # --- 1. Session Filter Check ---
        if settings.filter.enable_session_filter:
            in_session, session_name = FilterEngine.check_session(timestamp)
            if not in_session:
                reason = "Session Filter Blocked (Outside trading hours)"
                if settings.filter.filter_action == "warning":
                    return True, f"Soft Warning: {reason}"
                return False, reason

        # --- 2. Volatility Filter Check ---
        if settings.filter.enable_volatility_filter:
            vol_status, ratio = FilterEngine.check_volatility(df_etf)
            if vol_status != "normal":
                reason = f"Volatility Filter Blocked ({vol_status.upper()} Volatility: ratio {ratio:.2f})"
                if settings.filter.filter_action == "warning":
                    return True, f"Soft Warning: {reason}"
                return False, reason

        return True, "Approved"

    @staticmethod
    def check_session(timestamp: Any) -> Tuple[bool, str]:
        """
        Checks if the localized PKT timestamp is within one of the approved session windows.
        Handles sessions crossing midnight correctly.
        """
        bar_time = timestamp.time()
        
        for sess in settings.filter.approved_sessions_pkt:
            start_str = sess["start"]
            end_str = sess["end"]
            
            # Parse start and end times
            start_parts = list(map(int, start_str.split(":")))
            end_parts = list(map(int, end_str.split(":")))
            
            start_t = time(start_parts[0], start_parts[1])
            end_t = time(end_parts[0], end_parts[1])
            
            if start_t <= end_t:
                # Same day session (e.g. 13:00 to 22:00)
                if start_t <= bar_time <= end_t:
                    return True, sess["name"]
            else:
                # Overnight session (e.g. 18:00 to 03:00)
                if bar_time >= start_t or bar_time <= end_t:
                    return True, sess["name"]
                    
        return False, "None"

    @staticmethod
    def check_volatility(df_etf: pd.DataFrame) -> Tuple[str, float]:
        """
        Checks if the current market volatility is within acceptable bounds
        relative to the historical ATR baseline.
        Returns: ('low' / 'normal' / 'extreme', ATR_ratio)
        """
        lookback = settings.filter.volatility_lookback
        if len(df_etf) < lookback + 10:
            return "normal", 1.0
            
        # Calculate ATR
        high = df_etf['High']
        low = df_etf['Low']
        close = df_etf['Close']
        
        high_low = high - low
        high_cp = (high - close.shift(1)).abs()
        low_cp = (low - close.shift(1)).abs()
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        
        # Current ATR (short lookback)
        atr_curr = tr.ewm(span=14, adjust=False).mean().iloc[-1]
        
        # Baseline ATR (longer lookback)
        atr_baseline = tr.ewm(span=lookback * 5, adjust=False).mean().iloc[-1]
        
        if atr_baseline <= 0:
            return "normal", 1.0
            
        ratio = atr_curr / atr_baseline
        
        if ratio < settings.filter.min_volatility_pct:
            return "low", ratio
        elif ratio > settings.filter.max_volatility_pct:
            return "extreme", ratio
            
        return "normal", ratio
