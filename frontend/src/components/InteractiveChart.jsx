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
          background: { color: 'rgba(5, 5, 8, 0.85)' }, // Deep luxury black
          textColor: '#a3a3a3', // Cool grey text
        },
        grid: {
          vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
          horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
        },
        crosshair: {
          mode: 1, // Magnet
          vertLine: { color: '#ffffff', width: 1, style: 2 }, // Dashed white line
          horzLine: { color: '#ffffff', width: 1, style: 2 },
        },
        rightPriceScale: {
          borderColor: 'rgba(255, 255, 255, 0.08)',
        },
        timeScale: {
          borderColor: 'rgba(255, 255, 255, 0.08)',
          timeVisible: true,
          secondsVisible: false,
        },
      });

      chartRef.current = chart;

      // Add Candlestick Series in Luxury Monochrome
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#ffffff', // Bulish - White
        downColor: '#26262b', // Bearish - Charcoal
        borderUpColor: '#ffffff',
        borderDownColor: '#26262b',
        wickUpColor: '#ffffff',
        wickDownColor: '#26262b',
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

      // Add EMA Ribbons (White/Silver/Grey gradients)
      const colors = ['#ffffff', '#e5e5e5', '#a3a3a3', '#525252'];
      const lengths = [20, 50, 100, 200];

      lengths.forEach((len, idx) => {
        const candleKey = `ema${len}`;
        if (sortedData[0] && sortedData[0][candleKey] !== undefined) {
          const emaSeries = chart.addSeries(LineSeries, {
            color: colors[idx],
            lineWidth: len === 20 ? 1.8 : 1.0,
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

      // Add OB Horizontal Price Lines in Monochrome shades
      if (orderBlocks) {
        orderBlocks.forEach((ob) => {
          // High Boundary Line
          candleSeries.createPriceLine({
            price: ob.high,
            color: ob.is_bullish ? 'rgba(255, 255, 255, 0.4)' : 'rgba(115, 115, 115, 0.4)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `${ob.is_bullish ? 'Bull OB' : 'Bear OB'} High`,
          });

          // Low Boundary Line
          candleSeries.createPriceLine({
            price: ob.low,
            color: ob.is_bullish ? 'rgba(255, 255, 255, 0.4)' : 'rgba(115, 115, 115, 0.4)',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `${ob.is_bullish ? 'Bull OB' : 'Bear OB'} Low`,
          });
        });
      }

      // Set Signal Markers in Monochrome
      if (signals && signals.length > 0) {
        const markers = signals
          .map((sig) => {
            const timeVal = new Date(sig.timestamp).getTime() / 1000;
            if (isNaN(timeVal)) return null;
            return {
              time: timeVal,
              position: sig.direction === 'BUY' ? 'belowBar' : 'aboveBar',
              color: '#ffffff', // All signals are clean white markers
              shape: sig.direction === 'BUY' ? 'arrowUp' : 'arrowDown',
              text: `${sig.direction} (${sig.quality})`,
              size: 2.2,
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
    <div className="relative w-full rounded-2xl border border-[#26262b] overflow-hidden bg-cyber-bg/70 backdrop-blur shadow-glow-cyan/5">
      {/* Legend overlays */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap gap-3 bg-[#0d0d11]/90 p-3 rounded-lg border border-[#26262b] text-xs backdrop-blur-md">
        <span className="flex items-center gap-1.5 text-white">
          <span className="w-2.5 h-2.5 rounded-full bg-white shadow-glow-cyan" /> EMA 20
        </span>
        <span className="flex items-center gap-1.5 text-[#e5e5e5]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#e5e5e5]" /> EMA 50
        </span>
        <span className="flex items-center gap-1.5 text-[#a3a3a3]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#a3a3a3]" /> EMA 100
        </span>
        <span className="flex items-center gap-1.5 text-[#525252]">
          <span className="w-2.5 h-2.5 rounded-full bg-[#525252]" /> EMA 200
        </span>
      </div>
      <div ref={chartContainerRef} className="w-full h-[480px]" />
    </div>
  );
};

export default InteractiveChart;
