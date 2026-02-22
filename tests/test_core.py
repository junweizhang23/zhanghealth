"""
Unit tests for Zhang Health core logic.
Run with: python -m pytest tests/ -v
"""

import json
import os
import sys
import tempfile
from datetime import date, timedelta

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User, UserStore
from messages import get_exercise_message, get_opt_out_confirmation, EXERCISE_PLANS


class TestUser:
    """Tests for the User model."""

    def test_user_creation(self):
        user = User(
            name="Test",
            phone="+12065551234",
            timezone="America/Los_Angeles",
            age=63,
        )
        assert user.name == "Test"
        assert user.active is True
        assert user.cadence_days == 2

    def test_should_send_today_never_sent(self):
        user = User(name="Test", phone="+1", timezone="UTC", age=63)
        assert user.should_send_today(date.today()) is True

    def test_should_send_today_sent_yesterday(self):
        user = User(
            name="Test",
            phone="+1",
            timezone="UTC",
            age=63,
            cadence_days=2,
            last_sent_date=(date.today() - timedelta(days=1)).isoformat(),
        )
        assert user.should_send_today(date.today()) is False

    def test_should_send_today_sent_two_days_ago(self):
        user = User(
            name="Test",
            phone="+1",
            timezone="UTC",
            age=63,
            cadence_days=2,
            last_sent_date=(date.today() - timedelta(days=2)).isoformat(),
        )
        assert user.should_send_today(date.today()) is True

    def test_inactive_user_should_not_send(self):
        user = User(name="Test", phone="+1", timezone="UTC", age=63, active=False)
        assert user.should_send_today(date.today()) is False

    def test_to_dict_and_from_dict(self):
        user = User(name="Test", phone="+12065551234", timezone="UTC", age=40)
        d = user.to_dict()
        user2 = User.from_dict(d)
        assert user2.name == user.name
        assert user2.phone == user.phone
        assert user2.age == user.age


class TestUserStore:
    """Tests for the UserStore."""

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            store = UserStore(filepath=filepath)
            users = [
                User(name="Alice", phone="+1111", timezone="UTC", age=63),
                User(name="Bob", phone="+2222", timezone="UTC", age=40),
            ]
            store.save_users(users)
            loaded = store.load_users()
            assert len(loaded) == 2
            assert loaded[0].name == "Alice"
            assert loaded[1].name == "Bob"
        finally:
            os.unlink(filepath)

    def test_get_user_by_phone(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            store = UserStore(filepath=filepath)
            users = [
                User(name="Alice", phone="+1111", timezone="UTC", age=63),
            ]
            store.save_users(users)
            user = store.get_user_by_phone("+1111")
            assert user is not None
            assert user.name == "Alice"

            user = store.get_user_by_phone("+9999")
            assert user is None
        finally:
            os.unlink(filepath)

    def test_update_user(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            store = UserStore(filepath=filepath)
            users = [
                User(name="Alice", phone="+1111", timezone="UTC", age=63, active=True),
            ]
            store.save_users(users)
            store.update_user("+1111", active=False)
            user = store.get_user_by_phone("+1111")
            assert user.active is False
        finally:
            os.unlink(filepath)


class TestMessages:
    """Tests for message generation."""

    def test_exercise_message_contains_exercises(self):
        msg = get_exercise_message("妈妈", "senior_beginner", 0)
        assert "平板支撑" in msg
        assert "妈妈" in msg
        assert "OK" in msg

    def test_exercise_message_rotation(self):
        msg_a = get_exercise_message("妈妈", "senior_beginner", 0)
        msg_b = get_exercise_message("妈妈", "senior_beginner", 1)
        # Different days should have different routines
        assert "Day A" in msg_a
        assert "Day B" in msg_b

    def test_opt_out_message(self):
        msg = get_opt_out_confirmation("妈妈")
        assert "妈妈" in msg
        assert "暂停" in msg
        assert "START" in msg

    def test_all_plans_exist(self):
        assert "senior_beginner" in EXERCISE_PLANS
        assert "adult_intermediate" in EXERCISE_PLANS

    def test_all_plans_have_exercises(self):
        for plan_name, routines in EXERCISE_PLANS.items():
            assert len(routines) > 0, f"Plan '{plan_name}' has no routines"
            for routine in routines:
                assert "title" in routine
                assert "exercises" in routine
                assert len(routine["exercises"]) > 0
