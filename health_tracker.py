"""
Health Data Tracker

Parses health data from SMS replies and stores them for trend analysis.
Supports:
- Blood pressure readings (e.g., "BP 120/80" or "血压 130/85")
- Blood sugar readings (e.g., "BS 95" or "血糖 5.6")
- Weight readings (e.g., "W 165" or "体重 75")
- Exercise completion confirmations

Integrates with foundation MemoryStore for cross-agent access.
"""
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
HEALTH_LOG_FILE = DATA_DIR / "health_log.jsonl"

# Foundation MemoryStore integration
try:
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from foundation_bridge import get_memory_store
    _memory = get_memory_store()
    HAS_MEMORY = True
except (ImportError, Exception):
    _memory = None
    HAS_MEMORY = False


# ─── Parsing Patterns ────────────────────────────────────────────────────────

# Blood pressure: "BP 120/80", "bp120/80", "血压 130/85", "130/80"
BP_PATTERNS = [
    re.compile(r"(?:bp|血压|blood\s*pressure)\s*(\d{2,3})\s*/\s*(\d{2,3})", re.IGNORECASE),
    re.compile(r"^(\d{2,3})\s*/\s*(\d{2,3})$"),  # Just numbers like "120/80"
]

# Blood sugar: "BS 95", "血糖 5.6", "sugar 100"
BS_PATTERNS = [
    re.compile(r"(?:bs|血糖|blood\s*sugar|sugar|glucose)\s*(\d+\.?\d*)", re.IGNORECASE),
]

# Weight: "W 165", "体重 75", "weight 165"
WEIGHT_PATTERNS = [
    re.compile(r"(?:w|体重|weight)\s*(\d+\.?\d*)", re.IGNORECASE),
]

# Heart rate: "HR 72", "心率 80"
HR_PATTERNS = [
    re.compile(r"(?:hr|心率|heart\s*rate|pulse)\s*(\d{2,3})", re.IGNORECASE),
]


def parse_health_data(text: str) -> Optional[dict]:
    """
    Parse health data from an SMS text message.

    Returns a dict with the parsed data type and values, or None if
    no health data pattern is found.
    """
    text = text.strip()

    # Blood pressure
    for pattern in BP_PATTERNS:
        match = pattern.search(text)
        if match:
            systolic = int(match.group(1))
            diastolic = int(match.group(2))
            # Validate ranges
            if 60 <= systolic <= 250 and 30 <= diastolic <= 150:
                return {
                    "type": "blood_pressure",
                    "systolic": systolic,
                    "diastolic": diastolic,
                    "category": _classify_bp(systolic, diastolic),
                }

    # Blood sugar
    for pattern in BS_PATTERNS:
        match = pattern.search(text)
        if match:
            value = float(match.group(1))
            # Detect unit: mg/dL (US) vs mmol/L (international)
            if value < 30:  # mmol/L
                unit = "mmol/L"
                mg_dl = value * 18  # Convert for classification
            else:
                unit = "mg/dL"
                mg_dl = value
            if 20 <= mg_dl <= 600:
                return {
                    "type": "blood_sugar",
                    "value": value,
                    "unit": unit,
                    "category": _classify_bs(mg_dl),
                }

    # Weight
    for pattern in WEIGHT_PATTERNS:
        match = pattern.search(text)
        if match:
            value = float(match.group(1))
            # Detect unit: if Chinese text present, assume kg; otherwise lbs if >100
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
            if has_chinese:
                unit = "kg"
            elif value > 100:
                unit = "lbs"
            else:
                unit = "kg"  # Ambiguous, default kg
            return {
                "type": "weight",
                "value": value,
                "unit": unit,
            }

    # Heart rate
    for pattern in HR_PATTERNS:
        match = pattern.search(text)
        if match:
            value = int(match.group(1))
            if 30 <= value <= 220:
                return {
                    "type": "heart_rate",
                    "value": value,
                    "category": _classify_hr(value),
                }

    return None


def _classify_bp(systolic: int, diastolic: int) -> str:
    """Classify blood pressure according to AHA guidelines."""
    if systolic < 120 and diastolic < 80:
        return "normal"
    elif systolic < 130 and diastolic < 80:
        return "elevated"
    elif systolic < 140 or diastolic < 90:
        return "high_stage1"
    elif systolic >= 140 or diastolic >= 90:
        return "high_stage2"
    if systolic >= 180 or diastolic >= 120:
        return "crisis"
    return "unknown"


def _classify_bs(mg_dl: float) -> str:
    """Classify fasting blood sugar."""
    if mg_dl < 70:
        return "low"
    elif mg_dl < 100:
        return "normal"
    elif mg_dl < 126:
        return "prediabetic"
    else:
        return "diabetic"


def _classify_hr(bpm: int) -> str:
    """Classify resting heart rate."""
    if bpm < 60:
        return "low"
    elif bpm <= 100:
        return "normal"
    else:
        return "high"


def log_health_data(
    member_id: str,
    phone: str,
    data: dict,
) -> str:
    """
    Log parsed health data to local file and MemoryStore.

    Returns a response message acknowledging the data.
    """
    now = datetime.now(timezone.utc)
    record = {
        "timestamp": now.isoformat(),
        "member_id": member_id,
        "phone": phone,
        **data,
    }

    # Append to local JSONL log
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HEALTH_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info(f"Health data logged: {record}")

    # Log to MemoryStore for cross-agent access
    if HAS_MEMORY and _memory:
        try:
            _memory.log_interaction(
                "health-agent", member_id,
                f"Recorded {data['type']} via SMS",
                data,
            )
            # Update member context with latest reading
            context_key = f"latest_{data['type']}"
            _memory.update_member_context(member_id, {
                context_key: {**data, "timestamp": now.isoformat()},
            })
        except Exception as e:
            logger.warning(f"MemoryStore logging failed: {e}")

    # Generate response message
    return _format_response(data)


def _format_response(data: dict) -> str:
    """Generate a bilingual response message for the health reading."""
    dtype = data["type"]

    if dtype == "blood_pressure":
        s, d = data["systolic"], data["diastolic"]
        cat = data["category"]
        cat_text = {
            "normal": "正常 ✅",
            "elevated": "偏高 ⚠️",
            "high_stage1": "高血压一期 ⚠️",
            "high_stage2": "高血压二期 🔴",
            "crisis": "危险！请立即就医 🚨",
        }.get(cat, cat)
        return (
            f"📊 血压记录成功！\n"
            f"收缩压/舒张压: {s}/{d} mmHg\n"
            f"分类: {cat_text}\n\n"
            f"Blood pressure recorded: {s}/{d}\n"
            f"Category: {cat}"
        )

    elif dtype == "blood_sugar":
        v = data["value"]
        u = data["unit"]
        cat = data["category"]
        cat_text = {
            "low": "偏低 ⚠️",
            "normal": "正常 ✅",
            "prediabetic": "糖尿病前期 ⚠️",
            "diabetic": "偏高 🔴",
        }.get(cat, cat)
        return (
            f"📊 血糖记录成功！\n"
            f"数值: {v} {u}\n"
            f"分类: {cat_text}"
        )

    elif dtype == "weight":
        v = data["value"]
        u = data["unit"]
        return f"📊 体重记录成功！\nWeight: {v} {u}"

    elif dtype == "heart_rate":
        v = data["value"]
        cat = data["category"]
        cat_text = {
            "low": "偏低",
            "normal": "正常 ✅",
            "high": "偏高 ⚠️",
        }.get(cat, cat)
        return (
            f"📊 心率记录成功！\n"
            f"Heart rate: {v} bpm\n"
            f"分类: {cat_text}"
        )

    return "📊 健康数据已记录！"


def get_health_summary(member_id: str, days: int = 30) -> str:
    """
    Generate a health summary for a family member over the past N days.
    Reads from the local JSONL log.
    """
    if not HEALTH_LOG_FILE.exists():
        return "暂无健康记录。"

    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = []

    with open(HEALTH_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("member_id") != member_id:
                    continue
                ts = datetime.fromisoformat(record["timestamp"])
                if ts >= cutoff:
                    records.append(record)
            except (json.JSONDecodeError, KeyError):
                continue

    if not records:
        return f"过去 {days} 天暂无健康记录。"

    # Group by type
    by_type = {}
    for r in records:
        t = r["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)

    lines = [f"📋 过去 {days} 天健康摘要：\n"]

    if "blood_pressure" in by_type:
        bps = by_type["blood_pressure"]
        avg_s = sum(r["systolic"] for r in bps) / len(bps)
        avg_d = sum(r["diastolic"] for r in bps) / len(bps)
        lines.append(f"🩸 血压: {len(bps)} 次记录")
        lines.append(f"   平均: {avg_s:.0f}/{avg_d:.0f} mmHg")
        latest = bps[-1]
        lines.append(f"   最近: {latest['systolic']}/{latest['diastolic']} ({latest['category']})")

    if "blood_sugar" in by_type:
        bss = by_type["blood_sugar"]
        avg = sum(r["value"] for r in bss) / len(bss)
        lines.append(f"🍬 血糖: {len(bss)} 次记录, 平均 {avg:.1f}")

    if "weight" in by_type:
        ws = by_type["weight"]
        latest = ws[-1]
        lines.append(f"⚖️ 体重: 最近 {latest['value']} {latest['unit']}")

    if "heart_rate" in by_type:
        hrs = by_type["heart_rate"]
        avg = sum(r["value"] for r in hrs) / len(hrs)
        lines.append(f"💓 心率: {len(hrs)} 次记录, 平均 {avg:.0f} bpm")

    return "\n".join(lines)
