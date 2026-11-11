from typing import List, Dict, Tuple
from datetime import datetime, timezone

class WhipsawProtectionEngine:
    """
    Vantage-Point 2.0: Anti-Whipsaw Signal Quality and Hysteresis Engine.
    
    This engine filters high-frequency market noise and prevents rapid alternating trades 
    (whipsaw effect) by checking:
    1. Kaufman's Efficiency Ratio (ER): Measures trend directionality vs. market noise.
    2. Volatility-Adjusted Thresholds (ATR): Dynamically scales price breakout bands.
    3. Directional Hysteresis: Locks out rapid opposite trades unless signal quality is extreme.
    4. Signal Quality Index (SQI): Synthesizes these factors into a single confidence rating (0-100%).
    """

    def __init__(self, er_period: int = 10, atr_period: int = 10, cooldown_ticks: int = 3):
        self.er_period = er_period
        self.atr_period = atr_period
        self.cooldown_ticks = cooldown_ticks

    def calculate_efficiency_ratio(self, ohlc: List[Dict]) -> Tuple[float, str]:
        """
        Calculates Kaufman's Efficiency Ratio (ER).
        ER = Directional Move / Total Path Volatility
        
        Range: 0.0 to 1.0
        - ER > 0.6: Smooth directional trend (high signal quality)
        - 0.3 <= ER <= 0.6: Moderate noise
        - ER < 0.3: High market noise, random walk, extreme whipsaw risk
        """
        if len(ohlc) < self.er_period + 1:
            return 0.0, "INSUFFICIENT_DATA" # Missing history must never be treated as a strong trend
            
        # Candle providers return chronological data; use the newest window,
        # not the oldest candles in a long history.
        close_prices = [float(candle.get("close", 0)) for candle in ohlc[-(self.er_period + 1):]]

        # Net direction move over the latest period.
        net_change = abs(close_prices[-1] - close_prices[0])

        # Sum of absolute price changes over the same latest window.
        sum_of_changes = 0.0
        for i in range(self.er_period):
            sum_of_changes += abs(close_prices[i + 1] - close_prices[i])
            
        if sum_of_changes == 0.0:
            er = 0.0
        else:
            er = net_change / sum_of_changes
            
        # Classify regime
        if er >= 0.6:
            regime = "STRONG_TREND (Safe)"
        elif er >= 0.3:
            regime = "MODERATE_NOISE (Caution)"
        else:
            regime = "HIGH_NOISE (Whipsaw Zone)"
            
        return round(er, 4), regime

    def calculate_atr(self, ohlc: List[Dict]) -> float:
        """
        Calculates the Average True Range (ATR) over the last N candles.
        Measures the absolute price volatility.
        """
        if len(ohlc) < self.atr_period + 1:
            # Fallback to standard price standard deviation if insufficient data using pure python
            closes = [float(c.get("close", 0)) for c in ohlc]
            if not closes:
                return 1.0
            mean = sum(closes) / len(closes)
            variance = sum((x - mean) ** 2 for x in closes) / len(closes)
            std = variance ** 0.5
            return float(std)

        true_ranges = []
        latest = ohlc[-(self.atr_period + 1):]
        for i in range(1, len(latest)):
            curr = latest[i]
            prev = latest[i - 1]

            high = float(curr.get("high", 0))
            low = float(curr.get("low", 0))
            prev_close = float(prev.get("close", 0))
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_ranges.append(max(tr1, tr2, tr3))
            
        return sum(true_ranges) / len(true_ranges)


    def evaluate_signal_quality(self, ohlc: List[Dict], trades_history: List[Dict], target_action: str) -> Dict:
        """
        Synthesizes indicators into a Signal Quality Report.
        
        Calculates:
        - efficiency_ratio: Signal directionality.
        - atr: Absolute volatility.
        - dynamic_buffer: Price distance buffer required before rebalancing.
        - whipsaw_risk: Probability of a whipsaw (High, Medium, Low).
        - cooldown_lock: True if opposite trade occurred too recently.
        - signal_quality_index (SQI): Final trade-safety metric (0% to 100%).
        """
        if not ohlc:
            return {
                "efficiency_ratio": 0.0,
                "regime": "NO_DATA",
                "atr": 0.0,
                "whipsaw_risk": "HIGH",
                "cooldown_lock": True,
                "signal_quality_index": 0.0,
                "action_recommendation": "FORCE_HOLD",
                "reason": "No market data available; fail-closed filter requires HOLD."
            }

        # 1. Kaufman ER
        er, regime = self.calculate_efficiency_ratio(ohlc)
        
        # 2. Volatility Analysis
        atr = self.calculate_atr(ohlc)
        last_price = float(ohlc[0].get("close", 1.0))
        pct_volatility = (atr / last_price) * 100 if last_price > 0 else 0.0

        # 3. Directional Cooldown & Hysteresis Lockout
        cooldown_lock = False
        lock_reason = ""
        
        if trades_history and target_action != "HOLD":
            # Search for the most recent valid trade
            recent_trades = [
                t for t in trades_history
                if str(t.get("side", "")).lower() in ["buy", "sell", "expense"]
            ]
            if recent_trades:
                last_trade = recent_trades[-1]
                last_side = str(last_trade.get("side", "")).lower()
                
                # Check if it was an opposite trade
                if (target_action.lower() == "buy" and last_side == "sell") or \
                   (target_action.lower() == "sell" and last_side == "buy"):
                    
                    # Compute temporal tick difference or time diff
                    try:
                        t_now = datetime.now(timezone.utc)
                        t_last = datetime.fromisoformat(last_trade.get("timestamp").replace("Z", "+00:00"))
                        time_diff_sec = (t_now - t_last).total_seconds()
                        
                        # Lockout if less than 5 minutes (300s) and Efficiency Ratio is low
                        if time_diff_sec < 300 and er < 0.5:
                            cooldown_lock = True
                            lock_reason = f"Directional reversal blocked. Last trade ({last_side.upper()}) was only {int(time_diff_sec)}s ago and Efficiency Ratio ({er}) is too low to confirm regime shift."
                    except Exception as e:
                        # Fallback count check if date parsing fails
                        if len(trades_history) < self.cooldown_ticks and er < 0.4:
                            cooldown_lock = True
                            lock_reason = "Recent rapid trade detected in opposite direction. Safe-cooldown lock active."

        # 4. Whipsaw Risk Classification
        if er < 0.3:
            whipsaw_risk = "HIGH"
            sqi = er * 100 * 0.8 # Penalize heavily for low ER (choppy)
        elif er < 0.6:
            whipsaw_risk = "MEDIUM"
            sqi = er * 100 * 1.2
        else:
            whipsaw_risk = "LOW"
            sqi = min(100.0, er * 100 * 1.4)
            
        # Volatility adjustments to SQI
        if pct_volatility > 2.0: # High intraday volatility spikes increase whipsaw probability
            sqi *= 0.85
            regime += " + HIGH_VOLATILITY"
            if whipsaw_risk == "LOW":
                whipsaw_risk = "MEDIUM"

        sqi = max(5.0, min(100.0, sqi)) # Bound between 5% and 100%

        # Determine Recommendation
        if cooldown_lock:
            recommendation = "FORCE_HOLD"
            reason = lock_reason
        elif sqi < 30.0 and target_action != "HOLD":
            recommendation = "ADVISE_HOLD"
            reason = f"Market is in a highly choppy 'random walk' state (ER: {er}, Whipsaw Risk: HIGH). Signal quality is too poor ({sqi:.1f}%) to trade."
        elif sqi < 50.0 and target_action != "HOLD":
            recommendation = "CAUTION"
            reason = f"Moderate choppiness detected (ER: {er}). Recommending smaller trade size or higher boardroom consensus."
        else:
            recommendation = "PROCEED"
            reason = f"Strong signal quality ({sqi:.1f}%) supported by smooth trend directionality (ER: {er})."

        return {
            "efficiency_ratio": er,
            "regime": regime,
            "atr": round(atr, 4),
            "pct_volatility": round(pct_volatility, 2),
            "whipsaw_risk": whipsaw_risk,
            "cooldown_lock": cooldown_lock,
            "signal_quality_index": round(sqi, 1),
            "action_recommendation": recommendation,
            "reason": reason
        }

whipsaw_protection = WhipsawProtectionEngine()
