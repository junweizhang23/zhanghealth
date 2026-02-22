"""
SMS sender module using Twilio.
Handles sending messages and logging delivery status.
"""

import logging
import os
from datetime import datetime, date
from typing import Optional

import pytz

from config import Config
from models import User, UserStore
from messages import (
    get_exercise_message,
    get_opt_out_confirmation,
    get_opt_in_confirmation,
    get_ok_acknowledgment,
)

logger = logging.getLogger(__name__)


class SMSSender:
    """Handles sending SMS messages via Twilio."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize the SMS sender.

        Args:
            dry_run: If True, messages are logged but not actually sent.
                     Useful for testing without Twilio credentials.
        """
        self.dry_run = dry_run
        self.client = None
        self.from_number = Config.TWILIO_PHONE_NUMBER

        if not dry_run:
            try:
                from twilio.rest import Client

                self.client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
                logger.info("Twilio client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
                logger.warning("Falling back to dry-run mode.")
                self.dry_run = True

    def send_message(self, to_number: str, body: str) -> Optional[str]:
        """
        Send an SMS message.

        Args:
            to_number: Recipient phone number in E.164 format.
            body: Message content.

        Returns:
            Message SID if sent successfully, None otherwise.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would send to {to_number}:\n{body}\n")
            return "dry_run_sid"

        try:
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number,
            )
            logger.info(f"Message sent to {to_number}, SID: {message.sid}, Status: {message.status}")
            return message.sid
        except Exception as e:
            logger.error(f"Failed to send message to {to_number}: {e}")
            return None

    def send_exercise_reminder(self, user: User) -> bool:
        """
        Send an exercise reminder to a specific user.

        Args:
            user: The User object to send the reminder to.

        Returns:
            True if the message was sent successfully.
        """
        # Calculate which routine to send (rotates through the plan)
        if user.last_sent_date:
            last = date.fromisoformat(user.last_sent_date)
            days_since_start = (date.today() - last).days
            message_index = days_since_start // user.cadence_days
        else:
            message_index = 0

        body = get_exercise_message(user.name, user.exercise_plan, message_index)
        sid = self.send_message(user.phone, body)
        return sid is not None


class ReminderScheduler:
    """
    Orchestrates the sending of reminders based on user schedules.
    This is the main entry point called by the scheduler.
    """

    def __init__(self, dry_run: bool = False):
        self.sender = SMSSender(dry_run=dry_run)
        self.store = UserStore()

    def check_and_send_reminders(self):
        """
        Check all users and send reminders to those who are due.
        This method is called by the scheduler (e.g., every hour).
        """
        logger.info("=== Running reminder check ===")
        users = self.store.load_users()

        if not users:
            logger.warning("No users found. Skipping reminder check.")
            return

        today = date.today()
        sent_count = 0

        for user in users:
            if not user.active:
                logger.debug(f"Skipping inactive user: {user.name}")
                continue

            if not user.should_send_today(today):
                logger.debug(f"Not time to send to {user.name} yet.")
                continue

            # Check if it's the right hour in the user's timezone
            try:
                user_tz = pytz.timezone(user.timezone)
                user_now = datetime.now(user_tz)
                current_hour = user_now.hour

                if current_hour != user.preferred_hour:
                    logger.debug(
                        f"Not the right hour for {user.name} "
                        f"(current: {current_hour}, preferred: {user.preferred_hour})"
                    )
                    continue
            except pytz.exceptions.UnknownTimeZoneError:
                logger.error(f"Unknown timezone for {user.name}: {user.timezone}")
                continue

            # Send the reminder
            logger.info(f"Sending reminder to {user.name} ({user.phone})")
            success = self.sender.send_exercise_reminder(user)

            if success:
                self.store.update_user(
                    user.phone,
                    last_sent_date=today.isoformat(),
                )
                sent_count += 1

        logger.info(f"=== Reminder check complete. Sent {sent_count} messages. ===")

    def handle_reply(self, from_number: str, body: str) -> Optional[str]:
        """
        Process an incoming reply from a user.

        Args:
            from_number: The phone number that sent the reply.
            body: The content of the reply.

        Returns:
            A response message to send back, or None if no response is needed.
        """
        user = self.store.get_user_by_phone(from_number)
        if not user:
            logger.warning(f"Received reply from unknown number: {from_number}")
            return None

        body_lower = body.strip().lower()
        now_str = datetime.utcnow().isoformat()

        # Update last reply info regardless of content
        self.store.update_user(
            from_number,
            last_reply=body.strip(),
            last_reply_date=now_str,
        )

        # Handle opt-out
        if body_lower in ("no", "stop", "unsubscribe", "quit", "cancel"):
            self.store.update_user(from_number, active=False)
            logger.info(f"User {user.name} ({from_number}) opted out.")
            return get_opt_out_confirmation(user.name)

        # Handle opt-in
        if body_lower in ("start", "yes", "resume", "subscribe"):
            self.store.update_user(from_number, active=True)
            logger.info(f"User {user.name} ({from_number}) opted back in.")
            return get_opt_in_confirmation(user.name)

        # Handle OK confirmation
        if body_lower in ("ok", "done", "完成", "做了", "好"):
            logger.info(f"User {user.name} ({from_number}) confirmed exercise completion.")
            return get_ok_acknowledgment(user.name)

        # For any other reply, just acknowledge
        logger.info(f"Received message from {user.name}: {body}")
        return f"收到您的消息：\"{body.strip()}\"\n如有需要，回复 OK 确认完成锻炼，或回复 NO 暂停提醒。"
