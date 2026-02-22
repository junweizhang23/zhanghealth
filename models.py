"""
Data models for Zhang Health user management.
Uses a JSON file as a lightweight data store.
"""

import json
import os
import logging
from datetime import datetime, date
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)


class User:
    """Represents a family member in the health reminder system."""

    def __init__(
        self,
        name: str,
        phone: str,
        timezone: str,
        age: int,
        preferred_hour: int = 9,
        active: bool = True,
        cadence_days: int = 2,
        last_sent_date: Optional[str] = None,
        last_reply: Optional[str] = None,
        last_reply_date: Optional[str] = None,
        exercise_plan: Optional[str] = None,
        notes: str = "",
    ):
        self.name = name
        self.phone = phone  # E.164 format, e.g. "+12065551234"
        self.timezone = timezone  # e.g. "America/Los_Angeles"
        self.age = age
        self.preferred_hour = preferred_hour  # Hour in local time (0-23)
        self.active = active
        self.cadence_days = cadence_days  # Send every N days
        self.last_sent_date = last_sent_date  # ISO date string
        self.last_reply = last_reply
        self.last_reply_date = last_reply_date
        self.exercise_plan = exercise_plan or "default"
        self.notes = notes

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "phone": self.phone,
            "timezone": self.timezone,
            "age": self.age,
            "preferred_hour": self.preferred_hour,
            "active": self.active,
            "cadence_days": self.cadence_days,
            "last_sent_date": self.last_sent_date,
            "last_reply": self.last_reply,
            "last_reply_date": self.last_reply_date,
            "exercise_plan": self.exercise_plan,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(**data)

    def should_send_today(self, today: date) -> bool:
        """Determine if a message should be sent to this user today."""
        if not self.active:
            return False
        if self.last_sent_date is None:
            return True
        last_sent = date.fromisoformat(self.last_sent_date)
        days_since = (today - last_sent).days
        return days_since >= self.cadence_days


class UserStore:
    """Manages reading/writing user data to/from a JSON file."""

    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or Config.USERS_FILE
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create the data directory if it doesn't exist."""
        data_dir = os.path.dirname(self.filepath)
        os.makedirs(data_dir, exist_ok=True)

    def load_users(self) -> list[User]:
        """Load all users from the JSON file."""
        if not os.path.exists(self.filepath):
            logger.warning(f"Users file not found at {self.filepath}. Returning empty list.")
            return []
        try:
            with open(self.filepath, "r") as f:
                data = json.load(f)
            return [User.from_dict(u) for u in data.get("users", [])]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading users file: {e}")
            return []

    def save_users(self, users: list[User]):
        """Save all users to the JSON file."""
        data = {"users": [u.to_dict() for u in users], "updated_at": datetime.utcnow().isoformat()}
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(users)} users to {self.filepath}")

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """Find a user by their phone number."""
        users = self.load_users()
        for user in users:
            if user.phone == phone:
                return user
        return None

    def update_user(self, phone: str, **kwargs):
        """Update a user's fields by phone number."""
        users = self.load_users()
        for user in users:
            if user.phone == phone:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                self.save_users(users)
                logger.info(f"Updated user {user.name} ({phone}): {kwargs}")
                return True
        logger.warning(f"User with phone {phone} not found for update.")
        return False
