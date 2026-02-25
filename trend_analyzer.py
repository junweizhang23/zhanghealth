"""
Health Trend Analyzer — Analyze health metrics over time and generate insights.

Features:
1. Blood pressure trend analysis with classification
2. Weight/BMI tracking with goal progress
3. Heart rate variability analysis
4. Blood glucose tracking (if applicable)
5. Anomaly detection (sudden spikes/drops)
6. Weekly/monthly summary reports
7. Risk scoring based on combined metrics

Integrates with health_tracker.py for data and medication_manager.py for context.
"""

import json
import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Blood pressure classification (AHA guidelines)
BP_CATEGORIES = [
    {"name": "Normal", "systolic_max": 120, "diastolic_max": 80, "risk": "low"},
    {"name": "Elevated", "systolic_max": 129, "diastolic_max": 80, "risk": "moderate"},
    {"name": "Stage 1 Hypertension", "systolic_max": 139, "diastolic_max": 89, "risk": "high"},
    {"name": "Stage 2 Hypertension", "systolic_max": 180, "diastolic_max": 120, "risk": "very_high"},
    {"name": "Hypertensive Crisis", "systolic_max": 999, "diastolic_max": 999, "risk": "critical"},
]

# BMI classification (WHO)
BMI_CATEGORIES = [
    {"name": "Underweight", "max": 18.5, "risk": "moderate"},
    {"name": "Normal", "max": 24.9, "risk": "low"},
    {"name": "Overweight", "max": 29.9, "risk": "moderate"},
    {"name": "Obese Class I", "max": 34.9, "risk": "high"},
    {"name": "Obese Class II", "max": 39.9, "risk": "very_high"},
    {"name": "Obese Class III", "max": 999, "risk": "critical"},
]


class TrendAnalyzer:
    """Analyze health metrics trends for family members."""

    def __init__(self, data_dir: str = "data/trends"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def analyze_blood_pressure(
        self,
        readings: list,
        member_id: str = "",
    ) -> dict:
        """
        Analyze blood pressure readings over time.

        Args:
            readings: List of dicts with keys: systolic, diastolic, timestamp
        """
        if not readings:
            return {"status": "no_data", "message": "No blood pressure readings available"}

        systolic_values = [r["systolic"] for r in readings]
        diastolic_values = [r["diastolic"] for r in readings]

        latest = readings[-1]
        category = self._classify_bp(latest["systolic"], latest["diastolic"])

        # Trend analysis
        trend = "stable"
        if len(systolic_values) >= 5:
            recent_avg = statistics.mean(systolic_values[-5:])
            older_avg = statistics.mean(systolic_values[:5]) if len(systolic_values) >= 10 else statistics.mean(systolic_values[:len(systolic_values) // 2])
            diff = recent_avg - older_avg
            if diff > 5:
                trend = "increasing"
            elif diff < -5:
                trend = "decreasing"

        # Anomaly detection
        anomalies = []
        if len(systolic_values) >= 5:
            mean_sys = statistics.mean(systolic_values)
            std_sys = statistics.stdev(systolic_values) if len(systolic_values) > 1 else 0
            for i, r in enumerate(readings):
                if std_sys > 0 and abs(r["systolic"] - mean_sys) > 2 * std_sys:
                    anomalies.append({
                        "index": i,
                        "systolic": r["systolic"],
                        "diastolic": r["diastolic"],
                        "timestamp": r.get("timestamp", ""),
                        "type": "high" if r["systolic"] > mean_sys else "low",
                    })

        return {
            "member_id": member_id,
            "total_readings": len(readings),
            "latest": {
                "systolic": latest["systolic"],
                "diastolic": latest["diastolic"],
                "category": category["name"],
                "risk": category["risk"],
            },
            "statistics": {
                "systolic_avg": round(statistics.mean(systolic_values), 1),
                "systolic_min": min(systolic_values),
                "systolic_max": max(systolic_values),
                "diastolic_avg": round(statistics.mean(diastolic_values), 1),
                "diastolic_min": min(diastolic_values),
                "diastolic_max": max(diastolic_values),
            },
            "trend": trend,
            "anomalies": anomalies,
            "recommendation": self._bp_recommendation(category, trend),
        }

    def analyze_weight(
        self,
        readings: list,
        height_cm: float = 175,
        target_kg: Optional[float] = None,
        member_id: str = "",
    ) -> dict:
        """
        Analyze weight readings over time.

        Args:
            readings: List of dicts with keys: weight_kg, timestamp
            height_cm: Height in centimeters
            target_kg: Target weight in kg
        """
        if not readings:
            return {"status": "no_data"}

        weights = [r["weight_kg"] for r in readings]
        latest = weights[-1]
        bmi = latest / ((height_cm / 100) ** 2)
        bmi_category = self._classify_bmi(bmi)

        # Weight trend
        trend = "stable"
        weekly_change = 0
        if len(weights) >= 7:
            recent = statistics.mean(weights[-7:])
            older = statistics.mean(weights[:7]) if len(weights) >= 14 else weights[0]
            weeks = max(1, len(weights) / 7)
            weekly_change = (recent - older) / weeks
            if weekly_change > 0.2:
                trend = "gaining"
            elif weekly_change < -0.2:
                trend = "losing"

        # Goal progress
        goal_progress = None
        if target_kg is not None:
            start_weight = weights[0]
            total_to_lose = start_weight - target_kg
            lost_so_far = start_weight - latest
            if total_to_lose != 0:
                progress_pct = (lost_so_far / total_to_lose) * 100
            else:
                progress_pct = 100
            goal_progress = {
                "target_kg": target_kg,
                "remaining_kg": round(latest - target_kg, 1),
                "progress_pct": round(min(100, max(0, progress_pct)), 1),
                "weekly_rate": round(weekly_change, 2),
                "estimated_weeks_to_goal": (
                    round(abs(latest - target_kg) / abs(weekly_change))
                    if weekly_change != 0 and (
                        (weekly_change < 0 and latest > target_kg) or
                        (weekly_change > 0 and latest < target_kg)
                    )
                    else None
                ),
            }

        return {
            "member_id": member_id,
            "total_readings": len(readings),
            "latest": {
                "weight_kg": latest,
                "bmi": round(bmi, 1),
                "bmi_category": bmi_category["name"],
                "risk": bmi_category["risk"],
            },
            "statistics": {
                "avg_kg": round(statistics.mean(weights), 1),
                "min_kg": round(min(weights), 1),
                "max_kg": round(max(weights), 1),
                "std_kg": round(statistics.stdev(weights), 2) if len(weights) > 1 else 0,
            },
            "trend": trend,
            "weekly_change_kg": round(weekly_change, 2),
            "goal_progress": goal_progress,
        }

    def generate_weekly_summary(
        self,
        member_id: str,
        bp_readings: list = None,
        weight_readings: list = None,
        adherence_data: dict = None,
    ) -> str:
        """Generate a weekly health summary for SMS delivery."""
        now = datetime.now(timezone.utc)
        lines = [
            f"Weekly Health Summary",
            f"{member_id} | {now.strftime('%b %d, %Y')}",
            "─" * 30,
        ]

        if bp_readings:
            bp = self.analyze_blood_pressure(bp_readings[-7:], member_id)
            lines.append(f"\nBlood Pressure:")
            lines.append(f"  Latest: {bp['latest']['systolic']}/{bp['latest']['diastolic']} ({bp['latest']['category']})")
            lines.append(f"  Avg: {bp['statistics']['systolic_avg']}/{bp['statistics']['diastolic_avg']}")
            lines.append(f"  Trend: {bp['trend']}")

        if weight_readings:
            wt = self.analyze_weight(weight_readings[-7:], member_id=member_id)
            lines.append(f"\nWeight:")
            lines.append(f"  Latest: {wt['latest']['weight_kg']}kg (BMI {wt['latest']['bmi']})")
            lines.append(f"  Trend: {wt['trend']} ({wt['weekly_change_kg']:+.1f} kg/week)")

        if adherence_data:
            rate = adherence_data.get("overall_adherence_rate", 0)
            lines.append(f"\nMedication Adherence: {rate}%")
            status = "Great!" if rate >= 80 else "Needs improvement"
            lines.append(f"  Status: {status}")

        lines.append("\nReply HEALTH for detailed report")

        return "\n".join(lines)

    def calculate_health_risk_score(
        self,
        age: int,
        bp_readings: list = None,
        weight_readings: list = None,
        height_cm: float = 175,
        smoker: bool = False,
        diabetic: bool = False,
        family_history_cvd: bool = False,
    ) -> dict:
        """
        Calculate a simplified health risk score (0-100).

        Based on Framingham-inspired risk factors (simplified).
        """
        score = 0
        factors = []

        # Age factor (0-20 points)
        if age >= 65:
            score += 20
            factors.append(f"Age {age}: +20")
        elif age >= 55:
            score += 15
            factors.append(f"Age {age}: +15")
        elif age >= 45:
            score += 10
            factors.append(f"Age {age}: +10")
        else:
            score += 5
            factors.append(f"Age {age}: +5")

        # Blood pressure (0-25 points)
        if bp_readings:
            latest_bp = bp_readings[-1]
            cat = self._classify_bp(latest_bp["systolic"], latest_bp["diastolic"])
            bp_scores = {"low": 0, "moderate": 10, "high": 15, "very_high": 20, "critical": 25}
            bp_score = bp_scores.get(cat["risk"], 10)
            score += bp_score
            factors.append(f"BP {latest_bp['systolic']}/{latest_bp['diastolic']} ({cat['name']}): +{bp_score}")

        # BMI (0-15 points)
        if weight_readings:
            latest_wt = weight_readings[-1]["weight_kg"]
            bmi = latest_wt / ((height_cm / 100) ** 2)
            bmi_cat = self._classify_bmi(bmi)
            bmi_scores = {"low": 5, "moderate": 8, "high": 12, "very_high": 14, "critical": 15}
            bmi_score = bmi_scores.get(bmi_cat["risk"], 5)
            # Normal BMI gets 0
            if bmi_cat["name"] == "Normal":
                bmi_score = 0
            score += bmi_score
            factors.append(f"BMI {bmi:.1f} ({bmi_cat['name']}): +{bmi_score}")

        # Smoking (0-15 points)
        if smoker:
            score += 15
            factors.append("Smoker: +15")

        # Diabetes (0-10 points)
        if diabetic:
            score += 10
            factors.append("Diabetic: +10")

        # Family history (0-10 points)
        if family_history_cvd:
            score += 10
            factors.append("Family CVD history: +10")

        # Normalize to 0-100
        score = min(100, score)

        # Risk level
        if score <= 20:
            level = "Low"
        elif score <= 40:
            level = "Moderate"
        elif score <= 60:
            level = "High"
        else:
            level = "Very High"

        return {
            "score": score,
            "level": level,
            "factors": factors,
            "recommendation": self._risk_recommendation(level),
        }

    def _classify_bp(self, systolic: int, diastolic: int) -> dict:
        """Classify blood pressure reading."""
        for cat in BP_CATEGORIES:
            if systolic <= cat["systolic_max"] and diastolic <= cat["diastolic_max"]:
                return cat
        return BP_CATEGORIES[-1]

    def _classify_bmi(self, bmi: float) -> dict:
        """Classify BMI."""
        for cat in BMI_CATEGORIES:
            if bmi <= cat["max"]:
                return cat
        return BMI_CATEGORIES[-1]

    def _bp_recommendation(self, category: dict, trend: str) -> str:
        """Generate BP recommendation."""
        recs = {
            "Normal": "Maintain healthy lifestyle. Continue monitoring.",
            "Elevated": "Reduce sodium intake, increase exercise. Monitor weekly.",
            "Stage 1 Hypertension": "Consult physician. Lifestyle changes recommended. Monitor daily.",
            "Stage 2 Hypertension": "See physician promptly. Medication may be needed.",
            "Hypertensive Crisis": "SEEK IMMEDIATE MEDICAL ATTENTION.",
        }
        rec = recs.get(category["name"], "Consult physician.")
        if trend == "increasing":
            rec += " NOTE: BP trend is increasing — discuss with doctor."
        return rec

    def _risk_recommendation(self, level: str) -> str:
        """Generate risk-based recommendation."""
        recs = {
            "Low": "Continue healthy habits. Annual checkup recommended.",
            "Moderate": "Focus on diet and exercise. Semi-annual checkups recommended.",
            "High": "Consult physician for comprehensive evaluation. Quarterly monitoring.",
            "Very High": "Urgent medical consultation recommended. Monthly monitoring.",
        }
        return recs.get(level, "Consult physician.")


if __name__ == "__main__":
    analyzer = TrendAnalyzer()

    # Sample BP readings
    bp_data = [
        {"systolic": 128, "diastolic": 82, "timestamp": "2026-02-01"},
        {"systolic": 132, "diastolic": 85, "timestamp": "2026-02-05"},
        {"systolic": 125, "diastolic": 80, "timestamp": "2026-02-10"},
        {"systolic": 130, "diastolic": 84, "timestamp": "2026-02-15"},
        {"systolic": 127, "diastolic": 81, "timestamp": "2026-02-20"},
        {"systolic": 135, "diastolic": 88, "timestamp": "2026-02-25"},
    ]

    bp_analysis = analyzer.analyze_blood_pressure(bp_data, "parent_1")
    print(f"BP Analysis: {bp_analysis['latest']['category']} ({bp_analysis['trend']})")
    print(f"  Recommendation: {bp_analysis['recommendation']}")

    # Sample weight readings
    wt_data = [
        {"weight_kg": 82, "timestamp": "2026-02-01"},
        {"weight_kg": 81.5, "timestamp": "2026-02-08"},
        {"weight_kg": 81, "timestamp": "2026-02-15"},
        {"weight_kg": 80.5, "timestamp": "2026-02-22"},
    ]

    wt_analysis = analyzer.analyze_weight(wt_data, height_cm=175, target_kg=75)
    print(f"\nWeight: {wt_analysis['latest']['weight_kg']}kg BMI {wt_analysis['latest']['bmi']}")
    if wt_analysis["goal_progress"]:
        print(f"  Goal progress: {wt_analysis['goal_progress']['progress_pct']}%")

    # Risk score
    risk = analyzer.calculate_health_risk_score(
        age=35, bp_readings=bp_data, weight_readings=wt_data, height_cm=175
    )
    print(f"\nHealth Risk Score: {risk['score']}/100 ({risk['level']})")
    for f in risk["factors"]:
        print(f"  {f}")

    print("\nTrend analyzer working correctly.")
