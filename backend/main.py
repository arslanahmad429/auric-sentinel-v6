import re
import time
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any, List
from collections import defaultdict
import pandas as pd
from backend.config import settings, SystemSettings
from backend.core.data_feed import DataFeed
from backend.core.trend_engine import TrendEngine
from backend.core.structure_engine import StructureEngine
from backend.core.scanner import WatchlistScanner

app = FastAPI(title="AURIC SENTINEL Intelligence System Backend", version="1.0.0")

# 1. Simple In-Memory Token-Bucket Rate Limiter Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.visitor_records = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Allow Swagger docs to bypass rate limit
        if request.url.path in ["/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean up old timestamps (older than 60 seconds)
        self.visitor_records[client_ip] = [
            t for t in self.visitor_records[client_ip] if current_time - t < 60
        ]
        
        if len(self.visitor_records[client_ip]) >= self.requests_per_minute:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit exceeded."}
            )
            
        self.visitor_records[client_ip].append(current_time)
        return await call_next(request)

# 2. OWASP Secure Headers Injection Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"  # Clickjacking mitigation
        response.headers["X-Content-Type-Options"] = "nosniff"  # MIME-sniffing prevention
        response.headers["X-XSS-Protection"] = "1; mode=block"  # Cross-Site Scripting block
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self' http://localhost:8000 http://localhost:5173 http://127.0.0.1:8000 http://127.0.0.1:5173; "
            "img-src 'self' data: http://localhost:5173 http://localhost:8000 http://127.0.0.1:5173 http://127.0.0.1:8000;"
        )
        return response

# Register Custom Security Middlewares
app.add_middleware(RateLimitMiddleware, requests_per_minute=45)
app.add_middleware(SecurityHeadersMiddleware)

# Restrict CORS to trusted local web domains rather than wildcards
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Initialize instances
scanner = WatchlistScanner()

# Helper for strict ticker symbol sanitization to prevent injection
TICKER_REGEX = re.compile(r"^[A-Za-z0-9=\-\.\^\$]{1,16}$")

@app.get("/api/status")
def get_system_status():
    """
    Returns the overall status of the trading intelligence system.
    """
    watchlist_len = len(settings.scanner.watchlist)
    return {
        "status": "Scanning" if settings.scanner.enable_scanner else "Idle",
        "watchlist_count": watchlist_len,
        "entry_mode": settings.signal.entry_mode,
        "primary_timeframe": settings.ema.execution_timeframe,
        "context_timeframe": settings.ema.trend_timeframe,
        "debug_mode": settings.debug_mode
    }

@app.get("/api/settings")
def get_settings():
    """
    Returns current configuration settings.
    """
    return settings

@app.post("/api/settings")
def update_settings(new_settings: SystemSettings = Body(...)):
    """
    Updates system settings dynamically at runtime using Pydantic model validation.
    Protects against property/prototype injection.
    """
    global settings
    try:
        # Pydantic handles full schema type validation automatically
        settings.ema = new_settings.ema
        settings.structure = new_settings.structure
        settings.signal = new_settings.signal
        settings.filter = new_settings.filter
        settings.risk = new_settings.risk
        settings.scanner = new_settings.scanner
        settings.theme = new_settings.theme
        settings.debug_mode = new_settings.debug_mode
        return {"status": "success", "message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update settings: {str(e)}")

@app.get("/api/scanner")
def get_scanner_results():
    """
    Returns watchlist scan summary results.
    """
    try:
        results = scanner.scan()
        return {
            "timestamp": pd.Timestamp.now(tz='Asia/Karachi').strftime('%Y-%m-%d %H:%M:%S PKT'),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scanner execution failed: {str(e)}")

@app.get("/api/chart/{symbol}")
def get_chart_data(symbol: str, timeframe: str = "15m"):
    """
    Returns detailed candlestick data for the chart, combined with 
    computed indicators, swings, order blocks, and risk lines.
    """
    # Enforce strict regex validation on ticker input to prevent injection
    if not TICKER_REGEX.match(symbol):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol format")
    if timeframe not in ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]:
        raise HTTPException(status_code=400, detail="Invalid timeframe format")

    try:
        # Fetch execution timeframe data
        df_etf = DataFeed.fetch_data(symbol, timeframe, limit=300)
        
        # Fetch higher timeframe data for trend context
        htf = settings.ema.trend_timeframe
        df_htf = DataFeed.fetch_data(symbol, htf, limit=300)
        
        if df_etf.empty or df_htf.empty:
            raise HTTPException(status_code=404, detail=f"No data available for symbol {symbol}")
            
        # 1. Compute HTF Trend Calculations
        df_htf_analyzed = TrendEngine.analyze_trend(df_htf)
        latest_htf_trend = df_htf_analyzed.iloc[-1].to_dict()
        
        # 2. Compute ETF Market Structure
        trend_bias = latest_htf_trend.get("Primary_Bias", "Neutral")
        struct_results = StructureEngine.analyze_structure(df_etf, trend_bias)
        
        # 3. Compute local ETF EMAs for overlay
        df_etf = TrendEngine.calculate_emas(df_etf, settings.ema.lengths)
        
        # Format candle list for Lightweight Charts
        candles = []
        for idx, row in df_etf.iterrows():
            candles.append({
                "time": int(idx.timestamp()), # Epoch seconds
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"],
                "ema20": row.get("EMA_20"),
                "ema50": row.get("EMA_50"),
                "ema100": row.get("EMA_100"),
                "ema200": row.get("EMA_200"),
            })
            
        # Format Order Blocks for drawing
        bullish_obs = []
        for ob in struct_results["unmitigated_bullish_ob"]:
            bullish_obs.append({
                "low": ob.low,
                "high": ob.high,
                "time": int(ob.index.timestamp()) if hasattr(ob.index, 'timestamp') else ob.index
            })
            
        bearish_obs = []
        for ob in struct_results["unmitigated_bearish_ob"]:
            bearish_obs.append({
                "low": ob.low,
                "high": ob.high,
                "time": int(ob.index.timestamp()) if hasattr(ob.index, 'timestamp') else ob.index
            })
            
        # Format Swings
        swings = []
        for sw in struct_results["confirmed_swings"][-20:]: # Last 20 swings
            swings.append({
                "time": int(sw.index.timestamp()),
                "price": sw.price,
                "is_high": sw.is_high,
                "is_major": sw.is_major
            })

        # Fetch active signal for symbol from scanner's active state
        active_signal_data = None
        if symbol in scanner.signal_engines:
            sig_engine = scanner.signal_engines[symbol]
            if sig_engine.active_signals:
                active_sig = sig_engine.active_signals[-1]
                active_signal_data = {
                    "direction": active_sig.direction,
                    "price": active_sig.price,
                    "confidence": active_sig.confidence,
                    "priority": active_sig.priority,
                    "quality": active_sig.quality,
                    "justification": active_sig.justification,
                    "risk_framing": active_sig.initial_risk_framing,
                    "timestamp": active_sig.timestamp.isoformat() if hasattr(active_sig.timestamp, 'isoformat') else active_sig.timestamp
                }
                
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles,
            "trend_context": {
                "bias": trend_bias,
                "strength": latest_htf_trend.get("Trend_Strength", "Weak"),
                "confidence": latest_htf_trend.get("Trend_Confidence", "Neutral"),
                "expansion": latest_htf_trend.get("Ribbon_Expansion", False),
                "compression": latest_htf_trend.get("Ribbon_Compression", False),
            },
            "market_structure": {
                "alignment": struct_results["structural_alignment"],
                "phase": struct_results["market_phase"],
                "strength": struct_results["structure_strength"],
                "range_high": struct_results["range_high"],
                "range_low": struct_results["range_low"],
                "equilibrium": struct_results["equilibrium"],
                "zone": struct_results["zone_classification"],
                "last_event": struct_results["last_event"],
                "last_event_direction": struct_results["last_event_direction"]
            },
            "bullish_order_blocks": bullish_obs,
            "bearish_order_blocks": bearish_obs,
            "swings": swings,
            "active_signal": active_signal_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile chart data: {str(e)}")
