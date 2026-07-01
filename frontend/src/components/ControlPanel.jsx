import React from 'react';
import { Settings, Sliders, PlayCircle, RefreshCw } from 'lucide-react';

const ControlPanel = ({ settings, onChangeSettings, onTriggerScan, loading }) => {
  const handleModeChange = (e) => {
    onChangeSettings({
      ...settings,
      signal: {
        ...settings.signal,
        entry_mode: e.target.value,
      },
    });
  };

  const handleTimeframeChange = (e) => {
    onChangeSettings({
      ...settings,
      timeframe: e.target.value,
    });
  };

  const handleWatchlistChange = (e) => {
    const list = e.target.value.split(',').map((s) => s.trim().toUpperCase());
    onChangeSettings({
      ...settings,
      scanner: {
        ...settings.scanner,
        watchlist: list,
      },
    });
  };

  return (
    <div className="glass-panel rounded-2xl p-6 shadow-2xl border border-cyber-border/40">
      <h2 className="text-lg font-semibold tracking-wider text-white glow-text-cyan flex items-center gap-2 mb-6 border-b border-cyber-border/20 pb-3">
        <Settings className="text-cyber-cyan w-5 h-5" /> SYSTEM CONTROL CENTER
      </h2>

      <div className="space-y-6">
        {/* Entry Strictness Mode */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-cyber-gray mb-2">
            Signal Strictness Mode
          </label>
          <div className="grid grid-cols-3 gap-3">
            {['conservative', 'default', 'aggressive'].map((mode) => (
              <button
                key={mode}
                onClick={() => handleModeChange({ target: { value: mode } })}
                className={`py-2 px-3 rounded-lg border font-mono text-xs uppercase tracking-wide transition-all ${
                  settings.signal?.entry_mode === mode
                    ? 'bg-cyber-cyan text-cyber-bg border-cyber-cyan font-bold shadow-glow-cyan'
                    : 'bg-cyber-bg/40 border-cyber-border/60 text-cyber-gray hover:border-cyber-cyan/50 hover:text-white'
                }`}
              >
                {mode}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-cyber-gray/70 mt-2 font-mono leading-relaxed">
            {settings.signal?.entry_mode === 'conservative' && 'Conservative: Requires 0 score reductions (no weak trends or premium zone buys).'}
            {settings.signal?.entry_mode === 'default' && 'Default: Allows up to 3 score reductions.'}
            {settings.signal?.entry_mode === 'aggressive' && 'Aggressive: Allows up to 5 score reductions (highly reactive entry signals).'}
          </p>
        </div>

        {/* Timeframe selector */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-cyber-gray mb-2">
            Execution Timeframe
          </label>
          <select
            value={settings.timeframe || '15m'}
            onChange={handleTimeframeChange}
            className="w-full bg-cyber-bg/85 border border-cyber-border/65 rounded-lg py-2.5 px-3 text-white text-xs font-mono focus:border-cyber-cyan outline-none"
          >
            <option value="5m">5 Minute (Scalp)</option>
            <option value="15m">15 Minute (Intraday)</option>
            <option value="1h">1 Hour (Swing)</option>
            <option value="4h">4 Hour (Position)</option>
          </select>
        </div>

        {/* Watchlist inputs */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-cyber-gray mb-2">
            Scanner Watchlist (comma separated)
          </label>
          <input
            type="text"
            defaultValue={settings.scanner?.watchlist?.join(', ') || 'GC=F, EURUSD=X'}
            onBlur={handleWatchlistChange}
            placeholder="GC=F, EURUSD=X, BTC-USD"
            className="w-full bg-cyber-bg/85 border border-cyber-border/65 rounded-lg py-2.5 px-3 text-white text-xs font-mono focus:border-cyber-cyan outline-none"
          />
        </div>

        {/* Run Manual scan */}
        <button
          onClick={onTriggerScan}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-cyber-cyan text-cyber-bg hover:bg-cyber-cyan/90 font-mono text-xs font-bold uppercase tracking-widest transition-all shadow-glow-cyan disabled:opacity-50"
        >
          {loading ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <PlayCircle className="w-4 h-4" />
          )}
          {loading ? 'PROCESSING...' : 'TRIGGER FORCE SCAN'}
        </button>
      </div>
    </div>
  );
};

export default ControlPanel;
