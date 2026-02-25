"""
Medication Manager — Track medications, dosages, and adherence for family members.

Features:
1. Medication schedule management (add/remove/update meds)
2. SMS-based reminders at scheduled times
3. Adherence tracking (did they take it? reply Y/N)
4. Refill reminders (based on supply count)
5. Drug interaction warnings (basic rule-based)
6. Monthly adherence reports

Integrates with zhanghealth SMS system for reminders and tracking.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta, time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Medication:
    name: str
    dosage: str  # e.g., "10mg", "500mg"
    frequency: str  # "daily", "twice_daily", "weekly", "as_needed"
    times: list = field(default_factory=list)  # ["08:00", "20:00"]
    member_id: str = ""
    prescriber: str = ""
    pharmacy: str = ""
    supply_remaining: int = 30  # Days of supply
    refill_threshold: int = 7  # Alert when X days remaining
    notes: str = ""
    active: bool = True
    created_at: str = ""
    interactions: list = field(default_factory=list)  # Known interactions


@dataclass
class AdherenceRecord:
    medication_name: str
    member_id: str
    scheduled_time: str
    taken: bool = False
    response_time: str = ""
    method: str = "sms"  # "sms", "manual", "auto"


# Basic drug interaction rules (simplified)
KNOWN_INTERACTIONS = {
    ("lisinopril", "potassium"): "HIGH: ACE inhibitors + potassium supplements can cause hyperkalemia",
    ("metformin", "alcohol"): "MODERATE: Alcohol increases risk of lactic acidosis with metformin",
    ("warfarin", "aspirin"): "HIGH: Increased bleeding risk",
    ("warfarin", "ibuprofen"): "HIGH: NSAIDs increase bleeding risk with warfarin",
    ("amlodipine", "simvastatin"): "MODERATE: May increase simvastatin levels",
    ("lisinopril", "ibuprofen"): "MODERATE: NSAIDs may reduce ACE inhibitor effectiveness",
    ("metoprolol", "verapamil"): "HIGH: Risk of severe bradycardia",
}


class MedicationManager:
    """Manage family medication schedules and adherence."""

    def __init__(self, data_dir: str = "data/medications"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.meds_file = self.data_dir / "medications.json"
        self.adherence_file = self.data_dir / "adherence.json"
        self.medications = self._load_medications()
        self.adherence = self._load_adherence()

    def add_medication(self, med: Medication) -> dict:
        """Add a medication to a family member's schedule."""
        if not med.created_at:
            med.created_at = datetime.now(timezone.utc).isoformat()

        # Check for interactions with existing meds
        interactions = self._check_interactions(med)

        key = f"{med.member_id}:{med.name}"
        self.medications[key] = asdict(med)
        self._save_medications()

        result = {
            "status": "added",
            "medication": med.name,
            "member": med.member_id,
            "schedule": f"{med.frequency} at {', '.join(med.times)}",
        }

        if interactions:
            result["warnings"] = interactions
            logger.warning(f"Drug interactions found for {med.name}: {interactions}")

        return result

    def remove_medication(self, member_id: str, med_name: str) -> dict:
        """Remove a medication from schedule."""
        key = f"{member_id}:{med_name}"
        if key in self.medications:
            self.medications[key]["active"] = False
            self._save_medications()
            return {"status": "removed", "medication": med_name}
        return {"status": "not_found", "medication": med_name}

    def get_due_reminders(self, current_time: Optional[datetime] = None) -> list:
        """Get medications due for reminder at current time."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        current_hour_min = current_time.strftime("%H:%M")
        due = []

        for key, med_data in self.medications.items():
            if not med_data.get("active", True):
                continue

            for scheduled_time in med_data.get("times", []):
                if scheduled_time == current_hour_min:
                    due.append({
                        "member_id": med_data["member_id"],
                        "medication": med_data["name"],
                        "dosage": med_data["dosage"],
                        "scheduled_time": scheduled_time,
                    })

        return due

    def record_adherence(
        self,
        member_id: str,
        med_name: str,
        taken: bool,
        scheduled_time: str = "",
    ) -> dict:
        """Record whether a medication was taken."""
        record = AdherenceRecord(
            medication_name=med_name,
            member_id=member_id,
            scheduled_time=scheduled_time or datetime.now(timezone.utc).strftime("%H:%M"),
            taken=taken,
            response_time=datetime.now(timezone.utc).isoformat(),
        )

        date_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if date_key not in self.adherence:
            self.adherence[date_key] = []
        self.adherence[date_key].append(asdict(record))
        self._save_adherence()

        return {
            "status": "recorded",
            "medication": med_name,
            "taken": taken,
            "date": date_key,
        }

    def get_refill_alerts(self) -> list:
        """Check which medications need refills soon."""
        alerts = []
        for key, med_data in self.medications.items():
            if not med_data.get("active", True):
                continue

            remaining = med_data.get("supply_remaining", 30)
            threshold = med_data.get("refill_threshold", 7)

            if remaining <= threshold:
                alerts.append({
                    "member_id": med_data["member_id"],
                    "medication": med_data["name"],
                    "supply_remaining": remaining,
                    "pharmacy": med_data.get("pharmacy", ""),
                    "urgency": "critical" if remaining <= 2 else "warning",
                })

        return alerts

    def get_adherence_report(
        self,
        member_id: str,
        days: int = 30,
    ) -> dict:
        """Generate adherence report for a family member."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        total_scheduled = 0
        total_taken = 0
        by_medication = {}

        for date_key, records in self.adherence.items():
            try:
                record_date = datetime.strptime(date_key, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue

            if record_date < start_date or record_date > end_date:
                continue

            for record in records:
                if record.get("member_id") != member_id:
                    continue

                med_name = record.get("medication_name", "")
                if med_name not in by_medication:
                    by_medication[med_name] = {"scheduled": 0, "taken": 0}

                by_medication[med_name]["scheduled"] += 1
                total_scheduled += 1

                if record.get("taken", False):
                    by_medication[med_name]["taken"] += 1
                    total_taken += 1

        overall_rate = (total_taken / total_scheduled * 100) if total_scheduled > 0 else 0

        med_rates = {}
        for med_name, counts in by_medication.items():
            rate = (counts["taken"] / counts["scheduled"] * 100) if counts["scheduled"] > 0 else 0
            med_rates[med_name] = {
                "adherence_rate": round(rate, 1),
                "taken": counts["taken"],
                "scheduled": counts["scheduled"],
                "status": "good" if rate >= 80 else "needs_improvement",
            }

        return {
            "member_id": member_id,
            "period_days": days,
            "overall_adherence_rate": round(overall_rate, 1),
            "total_scheduled": total_scheduled,
            "total_taken": total_taken,
            "by_medication": med_rates,
            "assessment": self._assess_adherence(overall_rate),
        }

    def parse_sms_medication_reply(self, text: str, member_id: str) -> dict:
        """Parse SMS replies related to medication tracking.

        Supported formats:
        - "MED Y" or "MED N" — took/didn't take medication
        - "MED LIST" — list current medications
        - "MED REFILL aspirin" — mark refill received
        - "TOOK aspirin" — mark specific medication as taken
        """
        text = text.strip().upper()

        if text in ("MED Y", "TOOK", "Y", "YES"):
            # Mark all due medications as taken
            due = self.get_due_reminders()
            results = []
            for item in due:
                if item["member_id"] == member_id:
                    r = self.record_adherence(member_id, item["medication"], True)
                    results.append(r)
            return {"action": "taken_all", "results": results}

        if text in ("MED N", "N", "NO"):
            due = self.get_due_reminders()
            results = []
            for item in due:
                if item["member_id"] == member_id:
                    r = self.record_adherence(member_id, item["medication"], False)
                    results.append(r)
            return {"action": "skipped_all", "results": results}

        if text.startswith("TOOK "):
            med_name = text[5:].strip().lower()
            r = self.record_adherence(member_id, med_name, True)
            return {"action": "taken_specific", "result": r}

        if text == "MED LIST":
            active_meds = [
                {
                    "name": m["name"],
                    "dosage": m["dosage"],
                    "times": m["times"],
                }
                for m in self.medications.values()
                if m.get("member_id") == member_id and m.get("active", True)
            ]
            return {"action": "list", "medications": active_meds}

        if text.startswith("MED REFILL "):
            med_name = text[11:].strip().lower()
            key = f"{member_id}:{med_name}"
            if key in self.medications:
                self.medications[key]["supply_remaining"] = 30
                self._save_medications()
                return {"action": "refill", "medication": med_name, "new_supply": 30}

        return {"action": "unknown", "raw": text}

    def _check_interactions(self, new_med: Medication) -> list:
        """Check for drug interactions with existing medications."""
        warnings = []
        new_name = new_med.name.lower()

        for key, existing in self.medications.items():
            if existing.get("member_id") != new_med.member_id:
                continue
            if not existing.get("active", True):
                continue

            existing_name = existing["name"].lower()
            pair1 = (new_name, existing_name)
            pair2 = (existing_name, new_name)

            if pair1 in KNOWN_INTERACTIONS:
                warnings.append(KNOWN_INTERACTIONS[pair1])
            elif pair2 in KNOWN_INTERACTIONS:
                warnings.append(KNOWN_INTERACTIONS[pair2])

        return warnings

    def _assess_adherence(self, rate: float) -> str:
        """Assess adherence rate."""
        if rate >= 90:
            return "Excellent adherence. Keep it up!"
        elif rate >= 80:
            return "Good adherence. Minor improvement possible."
        elif rate >= 60:
            return "Fair adherence. Consider setting additional reminders."
        else:
            return "Low adherence. Please discuss with healthcare provider."

    def _load_medications(self) -> dict:
        if self.meds_file.exists():
            with open(self.meds_file, "r") as f:
                return json.load(f)
        return {}

    def _save_medications(self):
        with open(self.meds_file, "w") as f:
            json.dump(self.medications, f, indent=2)

    def _load_adherence(self) -> dict:
        if self.adherence_file.exists():
            with open(self.adherence_file, "r") as f:
                return json.load(f)
        return {}

    def _save_adherence(self):
        with open(self.adherence_file, "w") as f:
            json.dump(self.adherence, f, indent=2)


if __name__ == "__main__":
    mgr = MedicationManager()

    # Add sample medications for testing
    mgr.add_medication(Medication(
        name="lisinopril",
        dosage="10mg",
        frequency="daily",
        times=["08:00"],
        member_id="parent_1",
        prescriber="Dr. Smith",
        supply_remaining=15,
    ))

    mgr.add_medication(Medication(
        name="metformin",
        dosage="500mg",
        frequency="twice_daily",
        times=["08:00", "20:00"],
        member_id="parent_1",
        prescriber="Dr. Smith",
        supply_remaining=5,
    ))

    # Check refill alerts
    alerts = mgr.get_refill_alerts()
    print(f"Refill alerts: {len(alerts)}")
    for a in alerts:
        print(f"  [{a['urgency']}] {a['medication']} — {a['supply_remaining']} days remaining")

    # Test SMS parsing
    result = mgr.parse_sms_medication_reply("MED LIST", "parent_1")
    print(f"\nMedication list: {len(result['medications'])} active")
    for m in result["medications"]:
        print(f"  {m['name']} {m['dosage']} at {', '.join(m['times'])}")

    print("\nMedication manager initialized successfully.")
