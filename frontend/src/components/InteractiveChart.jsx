import React, { useEffect, useRef } from 'react';
import { createChart, LineStyle } from 'lightweight-charts';

const InteractiveChart = ({ data, orderBlocks, signals }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return;

    // Create Chart
    const chart = createChart(chartContainerRef.current, {
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
        mode: 1, // Magnet mode
        vertLine: {
          color: '#00f0ff',
          width: 1,
          style: 0,
        },
        horzLine: {
          color: '#00f0ff',
          width: 1,
          style: 0,
        },
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
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#39ff14',
      downColor: '#ff007f',
      borderUpColor: '#39ff14',
      borderDownColor: '#ff007f',
      wickUpColor: '#39ff14',
      wickDownColor: '#ff007f',
    });

    // Format candle data
    const formattedCandles = data.map((d) => ({
      time: new Date(d.Timestamp).getTime() / 1000,
      open: d.Open,
      high: d.High,
      low: d.Low,
      close: d.Close,
    }));
    candleSeries.setData(formattedCandles);

    // Add EMA Ribbons
    const colors = ['#00f0ff', '#39ff14', '#ffd700', '#ff007f'];
    const lengths = [20, 50, 100, 200];
    const emaSeriesList = [];

    lengths.forEach((len, idx) => {
      const emaKey = `EMA_${len}`;
      if (data[0] && data[0][emaKey] !== undefined) {
        const emaSeries = chart.addLineSeries({
          color: colors[idx],
          lineWidth: len === 20 ? 2 : 1.2,
          lineStyle: len === 200 ? LineStyle.Dotted : LineStyle.Solid,
          title: `EMA ${len}`,
        });

        const formattedEma = data
          .filter((d) => d[emaKey] !== null)
          .map((d) => ({
            time: new Date(d.Timestamp).getTime() / 1000,
            value: d[emaKey],
          }));

        emaSeries.setData(formattedEma);
        emaSeriesList.push(emaSeries);
      }
    });

    // Add OB Horizontal Price Lines
    const priceLines = [];
    if (orderBlocks) {
      orderBlocks.forEach((ob, idx) => {
        // High Boundary Line
        const highLine = candleSeries.createPriceLine({
          price: ob.high,
          color: ob.is_bullish ? 'rgba(57, 255, 20, 0.45)' : 'rgba(255, 0, 127, 0.45)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `${ob.is_bullish ? 'Bull OB' : 'Bear OB'} High`,
        });

        // Low Boundary Line
        const lowLine = candleSeries.createPriceLine({
          price: ob.low,
          color: ob.is_bullish ? 'rgba(57, 255, 20, 0.45)' : 'rgba(255, 0, 127, 0.45)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: `${ob.is_bullish ? 'Bull OB' : 'Bear OB'} Low`,
        });

        priceLines.push(highLine, lowLine);
      });
    }

    // Set Signal Markers
    if (signals && signals.length > 0) {
      const markers = signals.map((sig) => ({
        time: new Date(sig.timestamp).getTime() / 1000,
        position: sig.direction === 'BUY' ? 'belowBar' : 'aboveBar',
        color: sig.direction === 'BUY' ? '#39ff14' : '#ff007f',
        shape: sig.direction === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: `${sig.direction} (${sig.quality})`,
        size: 2,
      }));
      candleSeries.setMarkers(markers);
    }

    // Fit content
    chart.timeScale().fitContent();

    // Resize Handler
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.resize(chartContainerRef.current.clientWidth, 480);
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove(candleSeries);
      emaSeriesList.forEach((s) => chart.remove(s));
      chart.destroy();
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
