# Auric Sentinel v6: System Documentation & Feature Guide

This document provides a comprehensive guide to what Auric Sentinel v6 does, where it is useful, its primary use cases, and detailed operational rules for each algorithmic engine.

---

## 📖 What This Project Does

Auric Sentinel v6 is a **Flow-Based Market Alignment Engine** designed to automate quantitative market analysis. It scans financial watchlists, measures trend directions across multiple timeframes, maps market structure boundaries (BOS/CHoCH), registers buying/selling zones, and evaluates trade entries using a systematic scoring matrix.

The system ensures that entry signals are only generated when **higher timeframe trend bias** agrees with **lower timeframe market structure breakouts**, and filters the setups through session time blocks, volatility bounds, and ATR-based risk management rules.

---

## 💡 Where It Is Useful & Primary Use Cases

### 1. Proprietary Trading Desks & Fund Risk Controls
Proprietary trading firms use the engine to establish rule-based entry guidelines for their funded traders, preventing them from taking low-probability counter-trend setups or trading during low-volatility dead hours.

### 2. Retail Swing & Day Trading
Retail traders use the dashboard as a centralized scanner terminal, enabling them to monitor multiple assets (indices, metals, FX pairs) in real-time, removing emotional biases by executing only high-quality setups.

### 3. Quantitative Algorithmic Hedging
Treasury desks and corporate hedgers use the scanner to track structural trend shifts on commodity assets (e.g. Gold `GC=F`, Silver `SI=F`) and foreign currency pairs, timing their hedges based on macro breakouts.

---

## 🔍 Detailed Component Guide

### 1. Stacked Moving Average Ribbons (Trend Engine)
* **Calculations**: Computes 20, 50, 100, and 200 EMA ribbons.
* **Sensitivity Gating**: Checks if the EMA lines are stacked in alignment (20 > 50 > 100 > 200 for Bullish; 20 < 50 < 100 < 200 for Bearish) and calculates the percentage distance between them to filter out sideways consolidation (Ribbon Compression).
* **High Timeframe Context**: Signals are disabled if the execution timeframe direction opposes the Higher Timeframe (HTF) trend bias.

### 2. Market Structure Breakouts (Structure Engine)
* **Swing Identification**: Detects swing highs/lows using a symmetric lookback/lookahead window (e.g. 5 bars to the left, 5 bars to the right).
* **Break of Structure (BOS)**: Triggered when price closes past a confirmed swing high/low in the direction of the dominant trend.
* **Change of Character (CHoCH)**: Triggered when price closes past the opposite swing level, signaling a trend reversal.
* **Order Block (OB) Mapping**: The bar that initiated the breakout leg is mapped as an Order Block. Bullish OBs act as demand support; Bearish OBs act as supply resistance.
* **Non-Repainting Invalidation**: OB zones are invalidated immediately when a subsequent candle closes through the OB zone boundary.

### 3. Entry Quality Scoring (Signal Engine)
Every setup candidate starts with a score of 6 points. Reductions are applied systematically for structural flaws:
1. **Premium/Discount Zone Penalty (-1.5 pts)**: Buying in the premium zone or selling in the discount zone.
2. **Support/Resistance Touch Absence (-1.0 pts)**: Price triggering a buy signal without touching the EMA 20 support bounds.
3. **Exhaustion Distance Penalty (-1.0 pts)**: Price triggering an entry when the EMA 20 is too far from the EMA 50 (overextended trend).
4. **Momentum Divergence Penalty (-1.0 pts)**: Crossover slope decelerating compared to the previous bar.

Entry rules dictate:
* **Conservative Mode**: Requires a minimum quality score of `5.0`.
* **Default Mode**: Requires a minimum quality score of `3.5`.
* **Aggressive Mode**: Requires a minimum quality score of `2.0`.

### 4. Dynamic Risk Gating (Risk Manager)
* **Position Sizing**: Automatically adjusts contract sizes based on a fixed risk percentage of the account balance (e.g. risking 1% of a $10,000 account = $100 risk).
* **Stop Loss Sizing**: Placed just below the confirmed swing low (for long entries) or using an ATR volatility multiple, bounded between `0.5x` and `4.0x` ATR.
* **Milestone Breakeven Trail**: Once price gains a profit equal to 1.5x ATR, the Stop Loss is automatically adjusted to the entry price (Breakeven), securing a risk-free position.
