import pandas as pd
import numpy as np
from typing import Dict, Any, List
from backend.config import settings

class TrendEngine:
    """
    Computes higher timeframe (HTF) trend classification, EMA Ribbon status,
    and dynamic trend behavior (expansion, compression, acceleration, exhaustion).
    """

    @staticmethod
    def calculate_emas(df: pd.DataFrame, lengths: List[int]) -> pd.DataFrame:
        """
        Calculates EMA columns on the dataframe.
        """
        df_out = df.copy()
        for length in lengths:
            df_out[f'EMA_{length}'] = df_out['Close'].ewm(span=length, adjust=False).mean()
        return df_out

    @staticmethod
    def analyze_trend(df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyzes trend context bar-by-bar on a confirmed dataframe.
        Applies non-repainting rules (each row i depends only on data <= i).
        """
        lengths = settings.ema.lengths
        has_all_emas = all(f'EMA_{l}' in df.columns for l in lengths)
        df_ema = df.copy() if has_all_emas else TrendEngine.calculate_emas(df, lengths)
        
        # Initialize trend analysis columns
        df_ema['Primary_Bias'] = 'Neutral'
        df_ema['Ribbon_Shape'] = 'Tangled'
        df_ema['Trend_Strength'] = 'Weak'
        df_ema['Ribbon_Expansion'] = False
        df_ema['Ribbon_Compression'] = False
        df_ema['Trend_Acceleration'] = False
        df_ema['Trend_Deceleration'] = False
        df_ema['Pullback_Active'] = False
        df_ema['EMA_Rejection'] = False
        df_ema['Trend_Exhaustion'] = False
        df_ema['Trend_Failure'] = False
        df_ema['Trend_Confidence'] = 'Neutral'
        
        # Skip if there's not enough data
        max_len = max(lengths)
        if len(df_ema) < max_len + 10:
            return df_ema

        # Calculate standard helper columns for cleaner lookups
        ema_cols = [f'EMA_{l}' for l in lengths]
        close = df_ema['Close']
        high = df_ema['High']
        low = df_ema['Low']
        
        # Calculate ATR for volatility/distance normalized analysis
        high_low = high - low
        high_cp = (high - close.shift(1)).abs()
        low_cp = (low - close.shift(1)).abs()
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        atr = tr.ewm(span=14, adjust=False).mean()
        df_ema['ATR'] = atr

        # We evaluate row by row to prevent future leaks (strict backtest consistency)
        for i in range(max_len, len(df_ema)):
            row_close = close.iloc[i]
            row_high = high.iloc[i]
            row_low = low.iloc[i]
            row_atr = atr.iloc[i] if not pd.isna(atr.iloc[i]) else (row_high - row_low)
            
            e20 = df_ema['EMA_20'].iloc[i]
            e50 = df_ema['EMA_50'].iloc[i]
            e100 = df_ema['EMA_100'].iloc[i]
            e200 = df_ema['EMA_200'].iloc[i]
            
            prev_e20 = df_ema['EMA_20'].iloc[i-1]
            prev_e50 = df_ema['EMA_50'].iloc[i-1]
            
            # 1. Primary Bias (EMA 50 vs EMA 200) with 3-bar crossover filter
            bias = 'Neutral'
            if e50 > e200:
                # Check if it was also true for past 3 bars to filter false crosses
                if (df_ema['EMA_50'].iloc[i-1] > df_ema['EMA_200'].iloc[i-1] and 
                    df_ema['EMA_50'].iloc[i-2] > df_ema['EMA_200'].iloc[i-2]):
                    bias = 'Bullish'
            elif e50 < e200:
                if (df_ema['EMA_50'].iloc[i-1] < df_ema['EMA_200'].iloc[i-1] and 
                    df_ema['EMA_50'].iloc[i-2] < df_ema['EMA_200'].iloc[i-2]):
                    bias = 'Bearish'
            
            df_ema.loc[df_ema.index[i], 'Primary_Bias'] = bias

            # 2. Ribbon Shape (Ordering)
            shape = 'Tangled'
            if e20 > e50 > e100 > e200:
                shape = 'Fanned_Bullish'
            elif e20 < e50 < e100 < e200:
                shape = 'Fanned_Bearish'
            elif e20 > e50 and e50 > e100 and bias == 'Bullish':
                shape = 'Loose_Bullish'
            elif e20 < e50 and e50 < e100 and bias == 'Bearish':
                shape = 'Loose_Bearish'
                
            df_ema.loc[df_ema.index[i], 'Ribbon_Shape'] = shape

            # 3. Ribbon Expansion & Compression (using distance over last 3 bars)
            dist_curr = abs(e20 - e50) + abs(e50 - e100) + abs(e100 - e200)
            
            e20_prev1 = df_ema['EMA_20'].iloc[i-1]
            e50_prev1 = df_ema['EMA_50'].iloc[i-1]
            e100_prev1 = df_ema['EMA_100'].iloc[i-1]
            e200_prev1 = df_ema['EMA_200'].iloc[i-1]
            dist_prev1 = abs(e20_prev1 - e50_prev1) + abs(e50_prev1 - e100_prev1) + abs(e100_prev1 - e200_prev1)
            
            e20_prev2 = df_ema['EMA_20'].iloc[i-2]
            e50_prev2 = df_ema['EMA_50'].iloc[i-2]
            e100_prev2 = df_ema['EMA_100'].iloc[i-2]
            e200_prev2 = df_ema['EMA_200'].iloc[i-2]
            dist_prev2 = abs(e20_prev2 - e50_prev2) + abs(e50_prev2 - e100_prev2) + abs(e100_prev2 - e200_prev2)
            
            expansion = dist_curr > dist_prev1 > dist_prev2
            compression = dist_curr < dist_prev1 < dist_prev2
            
            df_ema.loc[df_ema.index[i], 'Ribbon_Expansion'] = expansion
            df_ema.loc[df_ema.index[i], 'Ribbon_Compression'] = compression

            # 4. Trend Acceleration & Deceleration (rate of change of fastest EMA)
            slope_curr = e20 - prev_e20
            slope_prev = prev_e20 - df_ema['EMA_20'].iloc[i-2]
            
            acceleration = False
            deceleration = False
            
            if bias == 'Bullish':
                acceleration = slope_curr > slope_prev > 0
                deceleration = (slope_curr < slope_prev) and (slope_curr > 0)
            elif bias == 'Bearish':
                acceleration = slope_curr < slope_prev < 0
                deceleration = (slope_curr > slope_prev) and (slope_curr < 0)
                
            df_ema.loc[df_ema.index[i], 'Trend_Acceleration'] = acceleration
            df_ema.loc[df_ema.index[i], 'Trend_Deceleration'] = deceleration

            # 5. Pullback Active
            pullback = False
            if bias == 'Bullish':
                # Price drops below EMA 20 but remains above EMA 200
                pullback = row_close < e20 and row_close > e200
            elif bias == 'Bearish':
                # Price rises above EMA 20 but remains below EMA 200
                pullback = row_close > e20 and row_close < e200
            df_ema.loc[df_ema.index[i], 'Pullback_Active'] = pullback

            # 6. EMA Rejection Detection (touching EMA 50 or 100 and bouncing back)
            rejection = False
            if bias == 'Bullish' and pullback:
                # Low touches EMA 50 or 100, close is well above it
                touches_ema = (row_low <= e50 * 1.002 and row_low >= e50 * 0.998) or \
                              (row_low <= e100 * 1.002 and row_low >= e100 * 0.998)
                rejection = touches_ema and (row_close > row_low + 0.3 * (row_high - row_low))
            elif bias == 'Bearish' and pullback:
                # High touches EMA 50 or 100, close is well below it
                touches_ema = (row_high >= e50 * 0.998 and row_high <= e50 * 1.002) or \
                              (row_high >= e100 * 0.998 and row_high <= e100 * 1.002)
                rejection = touches_ema and (row_close < row_high - 0.3 * (row_high - row_low))
            df_ema.loc[df_ema.index[i], 'EMA_Rejection'] = rejection

            # 7. Trend Exhaustion & Failure
            # Exhaustion: trend is long-lived, compression active, deceleration active, price extended
            exhaustion = False
            failure = False
            
            # Simple age/duration tracker of current bias
            bias_duration = 0
            for j in range(i, max_len, -1):
                if df_ema['Primary_Bias'].iloc[j] == bias:
                    bias_duration += 1
                else:
                    break
            
            if bias_duration > 50 and compression and deceleration:
                # Dynamic check: price extension relative to EMA 200
                dist_200 = abs(row_close - e200)
                mean_dist = df_ema['Close'].iloc[max(0, i-50):i].sub(df_ema['EMA_200'].iloc[max(0, i-50):i]).abs().mean()
                if dist_200 > mean_dist * 1.5:
                    exhaustion = True
            
            # Failure: close crosses EMA 200 in opposite direction
            if bias == 'Bullish' and row_close < e200:
                failure = True
            elif bias == 'Bearish' and row_close > e200:
                failure = True

            df_ema.loc[df_ema.index[i], 'Trend_Exhaustion'] = exhaustion
            df_ema.loc[df_ema.index[i], 'Trend_Failure'] = failure

            # 8. Dynamic Strength and Confidence Scoring
            strength = 'Weak'
            confidence = 'Neutral'
            
            if bias == 'Bullish':
                if shape == 'Fanned_Bullish':
                    if expansion:
                        strength = 'Strong'
                        confidence = 'Strong Bullish'
                    else:
                        strength = 'Moderate'
                        confidence = 'Moderate Bullish'
                elif shape == 'Loose_Bullish':
                    strength = 'Moderate'
                    confidence = 'Moderate Bullish'
                else:
                    strength = 'Weak'
                    confidence = 'Weak Bullish'
                    
                if exhaustion:
                    confidence = 'Bullish Exhaustion'
                elif failure:
                    confidence = 'Trend Failed'
                elif compression or deceleration:
                    confidence = 'Early Bullish Weakness'
                    
            elif bias == 'Bearish':
                if shape == 'Fanned_Bearish':
                    if expansion:
                        strength = 'Strong'
                        confidence = 'Strong Bearish'
                    else:
                        strength = 'Moderate'
                        confidence = 'Moderate Bearish'
                elif shape == 'Loose_Bearish':
                    strength = 'Moderate'
                    confidence = 'Moderate Bearish'
                else:
                    strength = 'Weak'
                    confidence = 'Weak Bearish'
                    
                if exhaustion:
                    confidence = 'Bearish Exhaustion'
                elif failure:
                    confidence = 'Trend Failed'
                elif compression or deceleration:
                    confidence = 'Early Bearish Weakness'
            else:
                strength = 'Weak'
                confidence = 'Neutral'
                
            df_ema.loc[df_ema.index[i], 'Trend_Strength'] = strength
            df_ema.loc[df_ema.index[i], 'Trend_Confidence'] = confidence

        return df_ema

    @staticmethod
    def check_mtf_alignment(df_h4: pd.DataFrame, df_d1: pd.DataFrame) -> str:
        """
        Compares Trend Confidence between H4 and D1.
        Returns: 'Full Alignment', 'Partial Alignment', or 'Conflict'.
        """
        if df_h4.empty or df_d1.empty:
            return 'Undetermined'
            
        h4_bias = df_h4['Primary_Bias'].iloc[-1]
        d1_bias = df_d1['Primary_Bias'].iloc[-1]
        
        h4_conf = df_h4['Trend_Confidence'].iloc[-1]
        d1_conf = df_d1['Trend_Confidence'].iloc[-1]
        
        if h4_bias == d1_bias and h4_bias != 'Neutral':
            if 'Strong' in h4_conf and 'Strong' in d1_conf:
                return 'Full Alignment'
            return 'Partial Alignment'
        elif h4_bias == 'Neutral' or d1_bias == 'Neutral':
            return 'Partial Alignment'
        else:
            return 'Conflict'
