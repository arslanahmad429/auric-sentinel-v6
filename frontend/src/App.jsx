import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ShieldAlert, Cpu, Layers, Activity, ChevronRight, BookOpen, AlertCircle } from 'lucide-react';
import ThreeBackground from './components/ThreeBackground';
import InteractiveChart from './components/InteractiveChart';
import ScannerTable from './components/ScannerTable';
import ControlPanel from './components/ControlPanel';

const API_BASE = 'http://localhost:8000/api';

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
      const res = await fetch(`${API_BASE}/scan`);
      if (!res.ok) throw new Error('Failed to run scanner re-sync');
      const data = await res.json();
      setScanResults(data);

      if (data.length > 0) {
        // If active symbol is not in results, select the first one
        const exists = data.some((r) => r.symbol === activeSymbol);
        if (!exists) {
          setActiveSymbol(data[0].symbol);
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
      const res = await fetch(`${API_BASE}/symbol/${symbol}?timeframe=${timeframe}`);
      if (!res.ok) throw new Error(`Failed to load data for ${symbol}`);
      const data = await res.json();
      setChartData(data.candles || []);
      setOrderBlocks(data.order_blocks || []);
      setSignals(data.signals || []);
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

  // Periodic polling for live data simulation (every 12 seconds)
  useEffect(() => {
    const timer = setInterval(() => {
      if (activeSymbol) {
        fetchSymbolDetails(activeSymbol, settings.timeframe);
      }
    }, 12000);
    return () => clearInterval(timer);
  }, [activeSymbol, settings.timeframe]);

  const handleUpdateSettings = (newSettings) => {
    setSettings(newSettings);
    handleScan(newSettings);
  };

  return (
    <div className="relative min-h-screen text-white pb-16 font-sans">
      {/* 3D Canvas Background */}
      <ThreeBackground />

      {/* Top Header / Navigation Bar */}
      <header className="w-full border-b border-cyber-border/40 bg-cyber-bg/70 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyber-cyan/15 rounded-lg border border-cyber-cyan/30 shadow-glow-cyan animate-pulse">
            <Cpu className="text-cyber-cyan w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-widest text-white font-orbitron glow-text-cyan">
                AURIC SENTINEL
              </h1>
              <span className="text-[10px] bg-cyber-cyan/20 border border-cyber-cyan/40 text-cyber-cyan px-2 py-0.5 rounded font-mono font-bold tracking-widest uppercase">
                v6.0
              </span>
            </div>
            <p className="text-[10px] text-cyber-gray tracking-wider uppercase font-mono mt-0.5">
              Flow-Based Market Alignment Engine
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="w-2.5 h-2.5 rounded-full bg-cyber-green animate-ping" />
            <span className="text-cyber-gray">PKT TIMESTAMPS: LOCALIZED</span>
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <main className="max-w-7xl mx-auto px-6 mt-8 grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* Left column: Controls */}
        <motion.div 
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="lg:col-span-1 space-y-8"
        >
          <ControlPanel 
            settings={settings}
            onChangeSettings={handleUpdateSettings}
            onTriggerScan={() => handleScan()}
            loading={loading}
          />
          
          {/* Quick Stats Widget */}
          <div className="glass-panel rounded-2xl p-5 border border-cyber-border/30 text-xs font-mono space-y-4">
            <h3 className="text-white font-bold tracking-wider text-xs uppercase flex items-center gap-1.5 border-b border-cyber-border/20 pb-2">
              <Activity className="w-4 h-4 text-cyber-cyan" /> Engine Health Indices
            </h3>
            <div className="flex justify-between items-center">
              <span className="text-cyber-gray">Timeframe Offset</span>
              <span className="text-cyber-cyan font-bold">15m / 4h / 1d PKT</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-cyber-gray">Primary Risk Gate</span>
              <span className="text-cyber-green font-bold flex items-center gap-1">
                <Shield className="w-3.5 h-3.5" /> ACTIVE
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-cyber-gray">Signals Cached</span>
              <span className="text-white font-bold">{signals.length} Signals</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-cyber-gray">Unmitigated OBs</span>
              <span className="text-cyber-magenta font-bold">{orderBlocks.length} Zones</span>
            </div>
          </div>
        </motion.div>

        {/* Right Columns: Chart & Watchlist */}
        <div className="lg:col-span-3 space-y-8">
          
          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="bg-cyber-magenta/15 border border-cyber-magenta/40 rounded-xl p-4 flex items-center gap-3 text-sm text-white"
              >
                <AlertCircle className="text-cyber-magenta w-5 h-5 flex-shrink-0 animate-bounce" />
                <div>
                  <span className="font-bold font-mono">CONNECTION ALERT:</span> {error}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Interactive Chart Container */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="w-full relative"
          >
            {chartLoading && (
              <div className="absolute inset-0 bg-cyber-bg/85 backdrop-blur-sm z-30 flex flex-col justify-center items-center rounded-2xl gap-3">
                <RefreshCw className="w-8 h-8 text-cyber-cyan animate-spin" />
                <span className="font-mono text-xs text-cyber-cyan tracking-widest animate-pulse">
                  DECRYPTING CANDLE DATASTREAM...
                </span>
              </div>
            )}
            
            <div className="flex justify-between items-center mb-2 px-1">
              <div className="flex items-center gap-2">
                <h3 className="font-mono text-xs uppercase text-cyber-gray tracking-widest">
                  Symbol Viewport:
                </h3>
                <span className="font-mono text-sm font-bold text-white tracking-wider bg-cyber-cyan/15 px-2.5 py-1 rounded border border-cyber-cyan/30 shadow-glow-cyan">
                  {activeSymbol}
                </span>
              </div>
              <span className="text-xs text-cyber-gray/70 font-mono">
                Powered by TradingView API & Lightweight Charts
              </span>
            </div>

            <InteractiveChart 
              data={chartData}
              orderBlocks={orderBlocks}
              signals={signals}
            />
          </motion.div>

          {/* Watchlist Scanner Table */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <ScannerTable 
              scanResults={scanResults}
              activeSymbol={activeSymbol}
              onSelectSymbol={setActiveSymbol}
            />
          </motion.div>

          {/* Documentation / Bible Section */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="glass-panel rounded-2xl p-6 border border-cyber-border/40"
          >
            <h3 className="text-white font-bold tracking-wider text-sm uppercase flex items-center gap-2 border-b border-cyber-border/20 pb-3 mb-4">
              <BookOpen className="w-5 h-5 text-cyber-cyan" /> INDICATOR ALIGNMENT PROTOCOLS (V6 BIBLE)
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-cyber-gray leading-relaxed font-mono">
              <div className="space-y-4">
                <div>
                  <h4 className="text-white font-bold mb-1 flex items-center gap-1.5">
                    <ChevronRight className="w-3.5 h-3.5 text-cyber-cyan" /> 1. MTF EMA RIBBON CONFIRMATION
                  </h4>
                  <p>
                    Ensures execution is supported by the macro trend. We calculate EMA crossovers (20, 50, 100, 200) on both execution (e.g. 15m) and higher timeframes (e.g. H4, D1). Entry requires bias alignment, checking for compression (ribbons tightening) to catch explosive expansions.
                  </p>
                </div>
                <div>
                  <h4 className="text-white font-bold mb-1 flex items-center gap-1.5">
                    <ChevronRight className="w-3.5 h-3.5 text-cyber-cyan" /> 2. ORDER BLOCKS & REAL-TIME MITIGATION
                  </h4>
                  <p>
                    High-volume breakout candles create order blocks. A bullish order block represents the last down-candle before an upward break of structure (BOS). These zones remain active until a subsequent candle closes through the block's boundaries (Mitigation Close Rule).
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-white font-bold mb-1 flex items-center gap-1.5">
                    <ChevronRight className="w-3.5 h-3.5 text-cyber-cyan" /> 3. DECISION GATE REDUCTION
                  </h4>
                  <p>
                    Signals undergo dynamic quality score reductions (capped at 6). Reductions are triggered by counter-optimal setups, such as buying in the Premium zone, weak HTF confidence, lack of structural support touch, or unaligned momentum. Strictness level gates entries accordingly.
                  </p>
                </div>
                <div>
                  <h4 className="text-white font-bold mb-1 flex items-center gap-1.5">
                    <ChevronRight className="w-3.5 h-3.5 text-cyber-cyan" /> 4. RISK MANAGED SAFEGUARDS
                  </h4>
                  <p>
                    Protects capital in real-time. Entries automatically calculate dynamic ATR-based stop losses. Once price moves in-favor to the first milestone (e.g. 1.0 ATR), the Risk Manager shifts the Stop Loss to the Breakeven entry price, securing a zero-risk trade.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

        </div>
      </main>
    </div>
  );
}

export default App;
