import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Cpu, Activity, ChevronRight, BookOpen, AlertCircle, RefreshCw, Layers, TrendingUp, TrendingDown, HelpCircle } from 'lucide-react';
import Lightfall from './components/Lightfall';
import InteractiveChart from './components/InteractiveChart';
import ScannerTable from './components/ScannerTable';
import ControlPanel from './components/ControlPanel';
import ErrorBoundary from './components/ErrorBoundary';

const API_BASE = 'http://localhost:8000/api';
const LIGHTFALL_COLORS = ['#ffffff', '#a3a3a3', '#e5e5e5'];

function App() {
  const [settings, setSettings] = useState({
    timeframe: '15m',
    scanner: { watchlist: ['GC=F', 'EURUSD=X'] },
    signal: { entry_mode: 'default' },
  });
  const [scanResults, setScanResults] = useState([]);
  const [activeSymbol, setActiveSymbol] = useState('GC=F');
  const [chartData, setChartData] = useState([]);
  const [orderBlocks, setOrderBlocks] = useState([]);
  const [signals, setSignals] = useState([]);
  
  const [loading, setLoading] = useState(false);
  const [chartLoading, setChartLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('chart'); // 'chart' or 'docs'

  // Fetch settings on mount
  useEffect(() => {
    fetch(`${API_BASE}/settings`)
      .then((res) => res.json())
      .then((data) => setSettings(data))
      .catch((err) => console.error('Error fetching settings:', err));
  }, []);

  // Scan watchlist
  const handleScan = async (currentSettings = settings) => {
    setLoading(true);
    setError(null);
    try {
      // First update backend settings
      await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(currentSettings),
      });

      // Then trigger scan
      const res = await fetch(`${API_BASE}/scanner`);
      if (!res.ok) throw new Error('Failed to run scanner re-sync');
      const data = await res.json();
      const results = data.results || [];
      setScanResults(results);

      if (results.length > 0) {
        const exists = results.some((r) => r.symbol === activeSymbol);
        if (!exists) {
          setActiveSymbol(results[0].symbol);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch symbol details (candlesticks + OBs + signals)
  const fetchSymbolDetails = async (symbol, timeframe = settings.timeframe) => {
    setChartLoading(true);
    try {
      const res = await fetch(`${API_BASE}/chart/${symbol}?timeframe=${timeframe}`);
      if (!res.ok) throw new Error(`Failed to load data for ${symbol}`);
      const data = await res.json();
      setChartData(data.candles || []);
      
      const bull = (data.bullish_order_blocks || []).map((ob) => ({ ...ob, is_bullish: true }));
      const bear = (data.bearish_order_blocks || []).map((ob) => ({ ...ob, is_bullish: false }));
      setOrderBlocks([...bull, ...bear]);
      
      setSignals(data.active_signal ? [data.active_signal] : []);
    } catch (err) {
      console.error(err);
    } finally {
      setChartLoading(false);
    }
  };

  // Run initial scan
  useEffect(() => {
    handleScan();
  }, []);

  // Update symbol details when active symbol or timeframe changes
  useEffect(() => {
    if (activeSymbol) {
      fetchSymbolDetails(activeSymbol, settings.timeframe);
    }
  }, [activeSymbol, settings.timeframe]);

  // Periodic polling for live data simulation (every 15 seconds)
  useEffect(() => {
    const timer = setInterval(() => {
      if (activeSymbol) {
        fetchSymbolDetails(activeSymbol, settings.timeframe);
      }
    }, 15000);
    return () => clearInterval(timer);
  }, [activeSymbol, settings.timeframe]);

  const handleUpdateSettings = (newSettings) => {
    setSettings(newSettings);
    handleScan(newSettings);
  };

  const activeResult = scanResults.find(r => r.symbol === activeSymbol);
  const activeSignal = activeResult?.signal;

  return (
    <div className="relative min-h-screen text-white pb-16 font-sans bg-[#050508]">
      {/* Lightfall Animated Background Container */}
      <div style={{ width: '100%', height: '600px', position: 'absolute', top: 0, left: 0, zIndex: 0, overflow: 'hidden', pointerEvents: 'none' }}>
        <Lightfall
          colors={LIGHTFALL_COLORS}
          backgroundColor="#050508"
          speed={0.5}
          streakCount={3}
          streakWidth={1.2}
          streakLength={1.2}
          glow={1.5}
          density={0.7}
          twinkle={1.2}
          zoom={3}
          backgroundGlow={0.6}
          opacity={1}
          mouseInteraction
          mouseStrength={0.5}
          mouseRadius={1.2}
          color1="#ffffff"
          color2="#a3a3a3"
          color3="#e5e5e5"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#050508]/80 to-[#050508]" />
      </div>

      {/* Top Header / Navigation Bar */}
      <header className="w-full border-b border-white/5 bg-[#050508]/60 backdrop-blur-lg sticky top-0 z-50 px-8 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-white/5 rounded-lg border border-white/10 shadow-glow-cyan animate-pulse">
            <Cpu className="text-white w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-widest text-white font-syne uppercase">
                AURIC SENTINEL
              </h1>
              <span className="text-[9px] bg-white/15 border border-white/20 text-white px-2 py-0.5 rounded font-mono font-bold tracking-widest uppercase">
                v6.0
              </span>
            </div>
            <p className="text-[10px] text-neutral-400 tracking-wider uppercase font-mono mt-0.5">
              Flow-Based Market Alignment Engine
            </p>
          </div>
        </div>

        <nav className="flex items-center gap-6">
          <button
            onClick={() => setActiveTab('chart')}
            className={`font-outfit text-xs font-semibold tracking-wider uppercase transition-colors ${
              activeTab === 'chart' ? 'text-white border-b-2 border-white pb-1' : 'text-neutral-400 hover:text-white'
            }`}
          >
            Terminal View
          </button>
          <button
            onClick={() => setActiveTab('docs')}
            className={`font-outfit text-xs font-semibold tracking-wider uppercase transition-colors ${
              activeTab === 'docs' ? 'text-white border-b-2 border-white pb-1' : 'text-neutral-400 hover:text-white'
            }`}
          >
            Protocols & Bible
          </button>
        </nav>
      </header>

      {/* Main Grid Layout */}
      <main className="max-w-7xl mx-auto px-6 mt-8 grid grid-cols-1 lg:grid-cols-4 gap-8 relative z-10">
        
        {/* Left column: Controls */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="lg:col-span-1 space-y-6"
        >
          <ControlPanel 
            settings={settings}
            onChangeSettings={handleUpdateSettings}
            onTriggerScan={() => handleScan()}
            loading={loading}
          />
          
          {/* Real-time metrics overview */}
          <div className="glass-panel rounded-2xl p-5 border border-white/5 bg-[#0e0e12]/45 space-y-4">
            <h3 className="text-white font-outfit font-bold tracking-wider text-xs uppercase flex items-center gap-1.5 border-b border-white/5 pb-2">
              <Activity className="w-4 h-4 text-white" /> ENGINE METRICS
            </h3>
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-neutral-400">Timeframe Offset</span>
              <span className="text-white font-bold">15m / 4h / 1d</span>
            </div>
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-neutral-400">Risk Gate</span>
              <span className="text-white font-bold flex items-center gap-1">
                <Shield className="w-3.5 h-3.5" /> ACTIVE
              </span>
            </div>
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-neutral-400">Active Signals</span>
              <span className="text-white font-bold">{scanResults.filter(r => r.signal).length} Active</span>
            </div>
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-neutral-400">Scanner Status</span>
              <span className="text-white font-bold animate-pulse">MONITORING</span>
            </div>
          </div>
        </motion.div>

        {/* Right Columns: Dynamic Viewport */}
        <div className="lg:col-span-3 space-y-8">
          
          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3 text-sm text-white bg-[#050508]/85 backdrop-blur"
              >
                <AlertCircle className="text-red-500 w-5 h-5 flex-shrink-0" />
                <div>
                  <span className="font-bold font-mono">ERROR:</span> {error}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {activeTab === 'chart' ? (
              <motion.div
                key="chart-view"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.4 }}
                className="space-y-8"
              >
                {/* Premium Banner Graphic */}
                <div className="relative rounded-2xl h-36 overflow-hidden border border-white/5 shadow-2xl flex items-center px-8 bg-[#0a0a0d]">
                  <img 
                    src="/abstract_trading.png" 
                    alt="Trading background" 
                    className="absolute inset-0 w-full h-full object-cover opacity-15 mix-blend-luminosity hover:opacity-25 transition-opacity duration-700 pointer-events-none" 
                  />
                  <div className="absolute inset-0 bg-gradient-to-r from-[#050508] via-[#050508]/75 to-transparent" />
                  <div className="relative z-10 space-y-1">
                    <span className="text-[10px] font-mono tracking-widest text-[#a3a3a3] uppercase">
                      ACTIVE VIEWPORT NODE
                    </span>
                    <h2 className="text-2xl font-black font-syne tracking-wider text-white uppercase">
                      {activeSymbol} MARKET METRICS
                    </h2>
                    <p className="text-xs text-neutral-400 font-outfit font-light">
                      Real-time analysis overlay with non-repainting order blocks
                    </p>
                  </div>
                </div>

                {/* Chart Box wrapped in Error Boundary */}
                <div className="relative w-full">
                  {chartLoading && (
                    <div className="absolute inset-0 bg-[#050508]/85 backdrop-blur-sm z-30 flex flex-col justify-center items-center rounded-2xl gap-3">
                      <RefreshCw className="w-8 h-8 text-white animate-spin" />
                      <span className="font-mono text-xs text-white tracking-widest animate-pulse">
                        PARSING FINANCIAL DATASTREAM...
                      </span>
                    </div>
                  )}

                  <ErrorBoundary onReset={() => fetchSymbolDetails(activeSymbol, settings.timeframe)}>
                    <InteractiveChart 
                      data={chartData}
                      orderBlocks={orderBlocks}
                      signals={signals}
                    />
                  </ErrorBoundary>
                </div>

                {/* Collapsible Signal Detail Display */}
                {activeSignal && (
                  <motion.div
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="glass-panel rounded-2xl p-6 border border-white/5 bg-[#0e0e12]/45 flex flex-col md:flex-row md:items-center justify-between gap-6"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-3 py-1 text-xs font-bold font-mono rounded ${
                          activeSignal.direction === 'BUY' 
                            ? 'bg-white/10 text-white border border-white/20' 
                            : 'bg-neutral-800 text-neutral-400 border border-neutral-700'
                        }`}>
                          {activeSignal.direction} SIGNAL DETECTED
                        </span>
                        <span className="text-xs font-mono text-neutral-400">
                          at ${activeSignal.price?.toFixed(2)}
                        </span>
                      </div>
                      <p className="text-sm font-outfit text-white font-medium mt-2">
                        {activeSignal.justification?.reason || "Condition matches structural support bounce."}
                      </p>
                    </div>

                    <div className="flex gap-6 font-mono text-xs border-t md:border-t-0 md:border-l border-white/10 pt-4 md:pt-0 md:pl-6">
                      <div className="space-y-1">
                        <span className="text-neutral-400 block">Stop Loss</span>
                        <span className="text-neutral-300 font-bold font-mono">${activeSignal.risk_framing?.stop_loss?.toFixed(2) || '0.00'}</span>
                      </div>
                      <div className="space-y-1">
                        <span className="text-neutral-400 block">Target Price</span>
                        <span className="text-white font-bold font-mono">${activeSignal.risk_framing?.target_price?.toFixed(2) || '0.00'}</span>
                      </div>
                      <div className="space-y-1">
                        <span className="text-neutral-400 block">Risk:Reward</span>
                        <span className="text-white font-bold font-mono">1:{activeSignal.risk_framing?.risk_reward_ratio?.toFixed(1) || '2.0'}</span>
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* Scanner Grid Table */}
                <ScannerTable 
                  scanResults={scanResults}
                  activeSymbol={activeSymbol}
                  onSelectSymbol={setActiveSymbol}
                />
              </motion.div>
            ) : (
              <motion.div
                key="docs-view"
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.98 }}
                transition={{ duration: 0.4 }}
              >
                {/* Full Documentation Viewport */}
                <div className="glass-panel rounded-2xl p-8 border border-white/5 bg-[#0e0e12]/45 space-y-8">
                  <div className="border-b border-white/5 pb-4">
                    <h2 className="text-xl font-bold font-syne text-white uppercase flex items-center gap-2">
                      <BookOpen className="text-white w-6 h-6" /> ENGINE DECISION PROTOCOLS
                    </h2>
                    <p className="text-xs text-neutral-400 mt-1">Detailed documentation of the Auric Sentinel logic system</p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-sm text-neutral-400 leading-relaxed font-outfit">
                    <div className="space-y-4">
                      <h3 className="text-white font-bold tracking-wide uppercase font-syne border-l-2 border-l-white pl-3">
                        Multi-Timeframe Ribbon Crossovers
                      </h3>
                      <p className="font-light">
                        Auric Sentinel v6 utilizes dynamic Exponential Moving Average (EMA) ribbons (20, 50, 100, and 200 lengths) to coordinate direction. Crossovers are calculated both locally (e.g. 15m) and on higher context timeframes (e.g. H4, D1). Reversals are filtered through crossover delays to avoid false breaks.
                      </p>
                      
                      <h3 className="text-white font-bold tracking-wide uppercase font-syne border-l-2 border-l-white pl-3">
                        Market Structure Breakouts
                      </h3>
                      <p className="font-light">
                        Swing high/low points are established based on localized peak/valley windows. When price closes past the most recent confirmed swing level, a **Break of Structure (BOS)** or **Change of Character (CHoCH)** is registered. The originating bar of the impulse leg creates an Order Block (OB).
                      </p>
                    </div>

                    <div className="space-y-4">
                      <h3 className="text-white font-bold tracking-wide uppercase font-syne border-l-2 border-l-white pl-3">
                        Dynamic Score Reduction Gating
                      </h3>
                      <p className="font-light">
                        Every trade candidate starts with a potential Quality Score. Reductions are applied chronologically: buying in premium zones, lack of support touches, ribbon expansion distance, or unaligned momentum. Depending on settings (Conservative, Default, Aggressive), entries are filtered and logged.
                      </p>

                      <h3 className="text-white font-bold tracking-wide uppercase font-syne border-l-2 border-l-white pl-3">
                        Real-Time Risk Management
                      </h3>
                      <p className="font-light">
                        Stop Losses are computed dynamically using a multiple of the Average True Range (ATR). A **Breakeven Milestone** rule tracks price progress; once it reaches a 1x ATR profit target, the Stop Loss is automatically adjusted to the entry price, securing a risk-free position.
                      </p>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </main>
    </div>
  );
}

export default App;
