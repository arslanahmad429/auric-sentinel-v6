import pandas as pd
from typing import Dict, Any, List
from backend.core.data_feed import DataFeed
from backend.core.trend_engine import TrendEngine
from backend.core.structure_engine import StructureEngine
from backend.core.signal_engine import SignalEngine, Signal
from backend.core.filter_engine import FilterEngine
from backend.core.risk_manager import RiskManager
from backend.config import settings

class WatchlistScanner:
    """
    Coordinates multi-symbol scanning across a watchlist, runs the core
    analysis pipeline, and surfaces ranked and sorted results.
    """

    def __init__(self):
        self.signal_engines: Dict[str, SignalEngine] = {}

    def scan(self) -> List[Dict[str, Any]]:
        """
        Executes a scan over all symbols in the watchlist.
        Returns a list of summaries for each symbol, sorted by priority.
        """
        results = []
        watchlist = settings.scanner.watchlist
        
        # Extract configurations
        htf = settings.ema.trend_timeframe
        etf = settings.ema.execution_timeframe
        
        for symbol in watchlist:
            # Check if yfinance limits or exceptions occur
            try:
                # 1. Fetch ETF & HTF data
                df_etf = DataFeed.fetch_data(symbol, etf, limit=300)
                df_htf = DataFeed.fetch_data(symbol, htf, limit=300)
                
                if df_etf.empty or df_htf.empty:
                    results.append(self._create_degraded_row(symbol, "No data available"))
                    continue
                    
                # 2. Analyze Trend Context (HTF)
                df_htf_analyzed = TrendEngine.analyze_trend(df_htf)
                latest_trend = df_htf_analyzed.iloc[-1].to_dict()
                
                # Check MTF alignment (H4 vs D1 if available, otherwise just relative comparison)
                mtf_alignment = "Full Alignment" if latest_trend.get("Trend_Strength") == "Strong" else "Partial Alignment"
                
                # 3. Analyze Market Structure (ETF)
                trend_bias = latest_trend.get("Primary_Bias", "Neutral")
                struct_results = StructureEngine.analyze_structure(df_etf, trend_bias)
                
                # Get or create signal engine for symbol
                if symbol not in self.signal_engines:
                    self.signal_engines[symbol] = SignalEngine()
                engine = self.signal_engines[symbol]
                
                # 4. Update existing signals
                engine.update_active_signals(df_etf, latest_trend, struct_results)
                
                # 5. Evaluate fresh signals
                new_sig = engine.evaluate_signals(df_etf, latest_trend, struct_results, mtf_alignment)
                
                # If approved, frame risk
                if new_sig:
                    # Filter check
                    approved, reason = FilterEngine.evaluate_filters(new_sig.direction, df_etf.index[-1], df_etf)
                    if approved:
                        RiskManager.frame_trade(new_sig, df_etf, struct_results)
                    else:
                        new_sig.status = "Rejected"
                        new_sig.justification["Rejection_Reason"] = reason
                        engine.active_signals.remove(new_sig)
                        engine.historical_signals.append(new_sig)
                        new_sig = None
                        
                # Update live risk for any active signals
                for sig in engine.active_signals:
                    RiskManager.update_live_risk(sig, df_etf['Close'].iloc[-1])
                    
                # 6. Build summary result row
                active_sig_desc = "None"
                active_sig_dir = "None"
                active_sig_price = 0.0
                live_r = 0.0
                confidence = "None"
                priority_val = 0 # for sorting: 3=High, 2=Medium, 1=Low, 0=None
                
                if engine.active_signals:
                    sig = engine.active_signals[-1]
                    active_sig_desc = f"{sig.direction} @ {sig.price:.2f}"
                    active_sig_dir = sig.direction
                    active_sig_price = sig.price
                    confidence = sig.confidence
                    live_r = sig.initial_risk_framing.get("live_unrealized_r", 0.0)
                    
                    priority_map = {"High": 3, "Medium": 2, "Low": 1}
                    priority_val = priority_map.get(sig.priority, 1)
                    
                summary = {
                    "symbol": symbol,
                    "status": "Monitored" if not engine.active_signals else "Signal Active",
                    "price": round(df_etf['Close'].iloc[-1], 2),
                    "trend_bias": trend_bias,
                    "trend_strength": latest_trend.get("Trend_Strength", "Weak"),
                    "trend_confidence": latest_trend.get("Trend_Confidence", "Neutral"),
                    "structural_alignment": struct_results["structural_alignment"],
                    "market_phase": struct_results["market_phase"],
                    "active_signal": active_sig_desc,
                    "active_signal_direction": active_sig_dir,
                    "active_signal_price": active_sig_price,
                    "signal_confidence": confidence,
                    "live_unrealized_r": live_r,
                    "volatility_status": FilterEngine.check_volatility(df_etf)[0],
                    "session_ok": FilterEngine.check_session(df_etf.index[-1])[0],
                    "priority_value": priority_val,
                    "degraded": False
                }
                results.append(summary)
                
            except Exception as e:
                print(f"Scanner error on {symbol}: {str(e)}")
                results.append(self._create_degraded_row(symbol, f"Error: {str(e)}"))
                
        # Sort results: Put active signals first, ordered by priority
        results.sort(key=lambda x: (x["degraded"], -x["priority_value"], x["symbol"]))
        
        # Apply active-only filter if set
        if settings.scanner.filter_active_only:
            results = [r for r in results if r["status"] == "Signal Active" or r["degraded"]]
            
        return results

    def _create_degraded_row(self, symbol: str, error_msg: str) -> Dict[str, Any]:
        """
        Helper to return a degraded row when evaluation fails.
        """
        return {
            "symbol": symbol,
            "status": "Degraded",
            "price": 0.0,
            "trend_bias": "Neutral",
            "trend_strength": "Weak",
            "trend_confidence": "Undetermined",
            "structural_alignment": "Neutral",
            "market_phase": "Transitional",
            "active_signal": "None",
            "active_signal_direction": "None",
            "active_signal_price": 0.0,
            "signal_confidence": "None",
            "live_unrealized_r": 0.0,
            "volatility_status": "normal",
            "session_ok": False,
            "priority_value": 0,
            "degraded": True,
            "error": error_msg
        }
