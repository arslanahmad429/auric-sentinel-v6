import React, { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, LineSeries, LineStyle } from 'lightweight-charts';

const InteractiveChart = ({ data, orderBlocks, signals }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;

    let chart;
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        try {
          chart.resize(chartContainerRef.current.clientWidth, 480);
        } catch (err) {
          console.error("Resize error:", err);
        }
      }
    };

    try {
      // Create Chart instance
      chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 480,
        layout: {
          background: { color: 'rgba(6, 9, 19, 0.85)' },
          textColor: '#8f9bb3',
        },
        grid: {
          vertLines: { color: 'rgba(32, 45, 83, 0.15)' },
          horzLines: { color: 'rgba(32, 45, 83, 0.15)' },
        },
        crosshair: {
          mode: 1, // Magnet
          vertLine: { color: '#00f0ff', width: 1, style: 0 },
          horzLine: { color: '#00f0ff', width: 1, style: 0 },
        },
        rightPriceScale: {
          borderColor: 'rgba(32, 45, 83, 0.3)',
        },
        timeScale: {
          borderColor: 'rgba(32, 45, 83, 0.3)',
          timeVisible: true,
          secondsVisible: false,
        },
      });

      chartRef.current = chart;

      // Add Candlestick Series
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#10b981', // Premium Emerald Green
        downColor: '#ef4444', // Premium Ruby Red
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
      });

      // Clean & sort candle data
      const seenTimes = new Set();
      const cleanCandles = [];
      const sortedData = [...data].sort((a, b) => a.time - b.time);

      sortedData.forEach((d) => {
        if (d.time && !isNaN(d.time) && !seenTimes.has(d.time)) {
          seenTimes.add(d.time);
          cleanCandles.push({
            time: d.time,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
          });
        }
      });

      if (cleanCandles.length > 0) {
        candleSeries.setData(cleanCandles);
      }

      // Add EMA Ribbons
      const colors = ['#00f0ff', '#10b981', '#ffd700', '#ff007f'];
      const lengths = [20, 50, 100, 200];

      lengths.forEach((len, idx) => {
        const candleKey = `ema${len}`;
        if (sortedData[0] && sortedData[0][candleKey] !== undefined) {
          const emaSeries = chart.addSeries(LineSeries, {
            color: colors[idx],
            lineWidth: len === 20 ? 2 : 1.2,
            lineStyle: len === 200 ? LineStyle.Dotted : LineStyle.Solid,
            title: `EMA ${len}`,
          });

          const seenEmaTimes = new Set();
          const formattedEma = [];
          sortedData.forEach((d) => {
            if (d[candleKey] !== null && d[candleKey] !== undefined && d.time && !seenEmaTimes.has(d.time)) {
              seenEmaTimes.add(d.time);
              formattedEma.push({
                time: d.time,
                value: d[candleKey],
              });
            }
          });

          if (formattedEma.length > 0) {
            emaSeries.setData(formattedEma);
          }
        }
      });

      // Add OB Horizontal Price Lines
      if (orderBlocks) {
        orderBlocks.forEach((ob) => {
          // High Boundary Line
          candleSeries.createPriceLine({
            price: ob.high,
            color: ob.is_bullish ? 'rgba(16, 185, 129, 0.45)' : 'rgba(239, 68, 68, 0.45)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `${ob.is_bullish ? 'Bull OB' : 'Bear OB'} High`,
          });

          // Low Boundary Line
          candleSeries.createPriceLine({
            price: ob.low,
            color: ob.is_bullish ? 'rgba(16, 185, 129, 0.45)' : 'rgba(239, 68, 68, 0.45)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `${ob.is_bullish ? 'Bull OB' : 'Bear OB'} Low`,
          });
        });
      }

      // Set Signal Markers
      if (signals && signals.length > 0) {
        const markers = signals
          .map((sig) => {
            const timeVal = new Date(sig.timestamp).getTime() / 1000;
            if (isNaN(timeVal)) return null;
            return {
              time: timeVal,
              position: sig.direction === 'BUY' ? 'belowBar' : 'aboveBar',
              color: sig.direction === 'BUY' ? '#10b981' : '#ef4444',
              shape: sig.direction === 'BUY' ? 'arrowUp' : 'arrowDown',
              text: `${sig.direction} (${sig.quality})`,
              size: 2,
            };
          })
          .filter(Boolean);
          
        if (markers.length > 0) {
          candleSeries.setMarkers(markers);
        }
      }

      // Fit content
      chart.timeScale().fitContent();

      // Attach Resize Listener
      window.addEventListener('resize', handleResize);
    } catch (err) {
      console.error("Failed to render chart:", err);
    }

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart) {
        try {
          chart.remove();
        } catch (err) {
          console.error("Error removing chart:", err);
        }
      }
    };
  }, [data, orderBlocks, signals]);

  return (
    <div className="relative w-full rounded-2xl border border-cyber-border overflow-hidden bg-cyber-bg/70 backdrop-blur shadow-glow-cyan/10">
      {/* Legend overlays */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap gap-3 bg-cyber-bg/90 p-3 rounded-lg border border-cyber-border/40 text-xs backdrop-blur-md">
        <span className="flex items-center gap-1.5 text-cyber-cyan">
          <span className="w-2.5 h-2.5 rounded-full bg-cyber-cyan shadow-glow-cyan" /> EMA 20
        </span>
        <span className="flex items-center gap-1.5 text-cyber-green">
          <span className="w-2.5 h-2.5 rounded-full bg-cyber-green shadow-glow-green" /> EMA 50
        </span>
        <span className="flex items-center gap-1.5 text-cyber-yellow">
          <span className="w-2.5 h-2.5 rounded-full bg-cyber-yellow" /> EMA 100
        </span>
        <span className="flex items-center gap-1.5 text-cyber-magenta">
          <span className="w-2.5 h-2.5 rounded-full bg-cyber-magenta shadow-glow-magenta" /> EMA 200
        </span>
      </div>
      <div ref={chartContainerRef} className="w-full h-[480px]" />
    </div>
  );
};

export default InteractiveChart;
