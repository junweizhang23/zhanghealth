#!/usr/bin/env python3
"""
Zhang Health CLI - Command-line tool for managing the health reminder system.

Usage:
    python cli.py test-message          # Preview a sample message (no SMS sent)
    python cli.py send-now              # Trigger an immediate reminder check (dry run)
    python cli.py list-users            # List all registered users
    python cli.py add-user              # Interactively add a new user
    python cli.py init-sample           # Create sample users.json from template
"""

import argparse
import json
import os
import shutil
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import User, UserStore
from messages import get_exercise_message, EXERCISE_PLANS
from sender import ReminderScheduler


def cmd_test_message(args):
    """Preview a sample exercise message without sending."""
    print("\n" + "=" * 60)
    print("  SAMPLE MESSAGE PREVIEW (senior_beginner, Day A)")
    print("=" * 60)
    msg = get_exercise_message("妈妈", "senior_beginner", 0)
    print(msg)
    print("=" * 60)

    print("\n" + "=" * 60)
    print("  SAMPLE MESSAGE PREVIEW (senior_beginner, Day B)")
    print("=" * 60)
    msg = get_exercise_message("妈妈", "senior_beginner", 1)
    print(msg)
    print("=" * 60)

    print("\n" + "=" * 60)
    print("  SAMPLE MESSAGE PREVIEW (adult_intermediate, Day A)")
    print("=" * 60)
    msg = get_exercise_message("Alfred", "adult_intermediate", 0)
    print(msg)
    print("=" * 60)


def cmd_send_now(args):
    """Trigger an immediate reminder check in dry-run mode."""
    print("Running reminder check in DRY RUN mode...")
    scheduler = ReminderScheduler(dry_run=True)
    scheduler.check_and_send_reminders()
    print("Done.")


def cmd_list_users(args):
    """List all registered users."""
    store = UserStore()
    users = store.load_users()
    if not users:
        print("No users found. Run 'python cli.py init-sample' to create sample data.")
        return

    print(f"\n{'Name':<12} {'Phone':<16} {'Timezone':<24} {'Age':<5} {'Active':<8} {'Plan':<20} {'Last Sent'}")
    print("-" * 110)
    for u in users:
        print(
            f"{u.name:<12} {u.phone:<16} {u.timezone:<24} {u.age:<5} "
            f"{'✅' if u.active else '❌':<8} {u.exercise_plan:<20} {u.last_sent_date or 'Never'}"
        )
    print()


def cmd_add_user(args):
    """Interactively add a new user."""
    print("\n--- Add New User ---")
    name = input("Name: ").strip()
    phone = input("Phone (E.164, e.g. +12065551234): ").strip()
    timezone = input("Timezone (e.g. America/Los_Angeles): ").strip() or "America/Los_Angeles"
    age = int(input("Age: ").strip())
    preferred_hour = int(input("Preferred hour (0-23, local time): ").strip() or "9")
    cadence = int(input("Cadence in days (default 2): ").strip() or "2")

    # Auto-select plan based on age
    if age >= 55:
        plan = "senior_beginner"
    else:
        plan = "adult_intermediate"

    plan_input = input(f"Exercise plan [{plan}]: ").strip()
    if plan_input:
        plan = plan_input

    user = User(
        name=name,
        phone=phone,
        timezone=timezone,
        age=age,
        preferred_hour=preferred_hour,
        cadence_days=cadence,
        exercise_plan=plan,
    )

    store = UserStore()
    users = store.load_users()
    users.append(user)
    store.save_users(users)
    print(f"\n✅ User '{name}' added successfully!")


def cmd_init_sample(args):
    """Initialize sample users.json from the example template."""
    example_path = os.path.join(Config.DATA_DIR, "users.json.example")
    target_path = Config.USERS_FILE

    if os.path.exists(target_path):
        confirm = input(f"'{target_path}' already exists. Overwrite? (y/N): ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    os.makedirs(Config.DATA_DIR, exist_ok=True)
    shutil.copy2(example_path, target_path)
    print(f"✅ Sample users.json created at {target_path}")
    print("   Please edit it with real phone numbers before running the system.")


def main():
    parser = argparse.ArgumentParser(
        description="Zhang Health CLI - Manage the family health reminder system"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("test-message", help="Preview sample exercise messages")
    subparsers.add_parser("send-now", help="Trigger an immediate reminder check (dry run)")
    subparsers.add_parser("list-users", help="List all registered users")
    subparsers.add_parser("add-user", help="Interactively add a new user")
    subparsers.add_parser("init-sample", help="Initialize sample users.json")

    args = parser.parse_args()

    commands = {
        "test-message": cmd_test_message,
        "send-now": cmd_send_now,
        "list-users": cmd_list_users,
        "add-user": cmd_add_user,
        "init-sample": cmd_init_sample,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
