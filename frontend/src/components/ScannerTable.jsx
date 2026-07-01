import React from 'react';
import { Eye, TrendingUp, TrendingDown, ShieldAlert, Award, Zap } from 'lucide-react';

const ScannerTable = ({ scanResults, activeSymbol, onSelectSymbol }) => {
  return (
    <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl border border-cyber-border/40">
      <div className="px-6 py-5 border-b border-cyber-border/30 flex justify-between items-center bg-cyber-bg/40">
        <div>
          <h2 className="text-lg font-semibold tracking-wider text-white glow-text-cyan flex items-center gap-2">
            <Zap className="text-cyber-cyan w-5 h-5 animate-pulse" /> AURIC SENTINEL ACTIVE SCANNER
          </h2>
          <p className="text-xs text-cyber-gray mt-1">Real-time market scanning and signal matching metrics</p>
        </div>
        <span className="px-3 py-1 bg-cyber-cyan/10 border border-cyber-cyan/35 rounded-full text-cyber-cyan text-xs font-mono font-semibold animate-pulse">
          LIVE STATUS: OK
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-cyber-border/20 text-cyber-gray text-xs tracking-widest font-mono uppercase bg-cyber-bg/25">
              <th className="py-4 px-6">Symbol</th>
              <th className="py-4 px-6">Last Price</th>
              <th className="py-4 px-6">MTF Trend Alignment</th>
              <th className="py-4 px-6">Score Reductions</th>
              <th className="py-4 px-6">Confidence</th>
              <th className="py-4 px-6">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-cyber-border/10 font-mono text-sm">
            {scanResults && scanResults.length > 0 ? (
              scanResults.map((result) => {
                const isSelected = activeSymbol === result.symbol;
                const trend = result.htf_trend || {};
                const bias = trend.Primary_Bias || 'Neutral';
                const conf = trend.Trend_Confidence || 'Neutral';
                const reductions = result.signal ? result.signal.justification?.reductions_count || 0 : 4;
                
                return (
                  <tr
                    key={result.symbol}
                    className={`transition-colors hover:bg-cyber-cyan/5 ${
                      isSelected ? 'bg-cyber-cyan/10 border-l-4 border-l-cyber-cyan' : ''
                    }`}
                  >
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white tracking-wider">{result.symbol}</span>
                        {result.signal && (
                          <span className={`px-2 py-0.5 text-[10px] rounded font-semibold border ${
                            result.signal.direction === 'BUY' 
                              ? 'bg-cyber-green/10 border-cyber-green text-cyber-green shadow-glow-green/10' 
                              : 'bg-cyber-magenta/10 border-cyber-magenta text-cyber-magenta shadow-glow-magenta/10'
                          }`}>
                            {result.signal.direction}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-6 text-white font-bold">
                      ${result.current_price?.toFixed(2) || '0.00'}
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        {bias === 'Bullish' && <TrendingUp className="text-cyber-green w-4 h-4" />}
                        {bias === 'Bearish' && <TrendingDown className="text-cyber-magenta w-4 h-4" />}
                        {bias === 'Neutral' && <ShieldAlert className="text-cyber-yellow w-4 h-4" />}
                        <span className={`text-xs px-2 py-1 rounded border ${
                          bias === 'Bullish'
                            ? 'bg-cyber-green/10 border-cyber-green/20 text-cyber-green'
                            : bias === 'Bearish'
                            ? 'bg-cyber-magenta/10 border-cyber-magenta/20 text-cyber-magenta'
                            : 'bg-cyber-yellow/10 border-cyber-yellow/20 text-cyber-yellow'
                        }`}>
                          {bias} ({conf})
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-cyber-border/30 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              reductions <= 2 
                                ? 'bg-cyber-green shadow-glow-green' 
                                : reductions <= 4 
                                ? 'bg-cyber-yellow' 
                                : 'bg-cyber-magenta shadow-glow-magenta'
                            }`}
                            style={{ width: `${Math.min(100, (reductions / 6) * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs text-white">{reductions} / 6</span>
                      </div>
                    </td>
                    <td className="py-4 px-6">
                      <span className="text-xs flex items-center gap-1 text-cyber-yellow">
                        <Award className="w-4 h-4 text-cyber-yellow animate-bounce" />
                        {result.signal?.quality || 'Medium'} Quality
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <button
                        onClick={() => onSelectSymbol(result.symbol)}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border font-semibold text-xs transition-all ${
                          isSelected
                            ? 'bg-cyber-cyan text-cyber-bg border-cyber-cyan shadow-glow-cyan'
                            : 'bg-transparent border-cyber-cyan/40 text-cyber-cyan hover:border-cyber-cyan hover:bg-cyber-cyan/10'
                        }`}
                      >
                        <Eye className="w-3.5 h-3.5" />
                        {isSelected ? 'ACTIVE VIEW' : 'LOAD DATA'}
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="6" className="py-8 px-6 text-center text-cyber-gray text-sm">
                  Scanning market nodes for active connections...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ScannerTable;
