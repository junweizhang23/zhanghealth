"""
Zhang Health - Main Application
Flask web server with:
  - Twilio webhook for receiving SMS replies
  - APScheduler for periodic reminder checks
  - Health check endpoint
  - Admin API with HMAC-based token authentication
"""

import logging
import os
import sys
from datetime import datetime, timezone

from flask import Flask, request, jsonify, abort
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from sender import ReminderScheduler
from models import UserStore
from admin_auth import require_admin

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

os.makedirs(Config.LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(Config.LOG_DIR, "zhanghealth.log")),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY

# Determine if we're in dry-run mode (no Twilio credentials)
DRY_RUN = not (Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN)
if DRY_RUN:
    logger.warning(
        "Twilio credentials not configured. Running in DRY RUN mode. "
        "Messages will be logged but not sent."
    )

reminder_scheduler = ReminderScheduler(dry_run=DRY_RUN)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/", methods=["GET"])
def index():
    """Health check and status page."""
    store = UserStore()
    users = store.load_users()
    active_count = sum(1 for u in users if u.active)
    return jsonify(
        {
            "service": "Zhang Health Reminder System",
            "status": "running",
            "mode": "dry_run" if DRY_RUN else "live",
            "total_users": len(users),
            "active_users": active_count,
            "server_time_utc": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.route("/webhook/twilio", methods=["POST"])
def twilio_webhook():
    """
    Webhook endpoint for incoming SMS from Twilio.
    Twilio sends a POST request with the message details.
    Validates Twilio request signature to prevent spoofing.
    """
    # Validate Twilio request signature (if auth token available)
    if not DRY_RUN:
        try:
            from twilio.request_validator import RequestValidator
            validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
            url = request.url
            signature = request.headers.get("X-Twilio-Signature", "")
            if not validator.validate(url, request.form, signature):
                logger.warning(f"Invalid Twilio signature from {request.remote_addr}")
                abort(403)
        except ImportError:
            pass  # Twilio not installed, skip validation

    from_number = request.values.get("From", "")
    body = request.values.get("Body", "")

    logger.info(f"Received SMS from {from_number}: {body}")

    # Process the reply and get a response
    response_text = reminder_scheduler.handle_reply(from_number, body)

    if response_text:
        # Send the response back via Twilio TwiML
        from twilio.twiml.messaging_response import MessagingResponse

        resp = MessagingResponse()
        resp.message(response_text)
        return str(resp), 200, {"Content-Type": "text/xml"}

    # No response needed
    return "", 204


@app.route("/api/send-now", methods=["POST"])
@require_admin
def send_now():
    """
    Admin endpoint to manually trigger a reminder check.
    Requires a valid HMAC-signed admin token in the X-Admin-Token header.
    Generate a token with: python admin_auth.py generate
    """
    reminder_scheduler.check_and_send_reminders()
    return jsonify({"status": "ok", "message": "Reminder check triggered."})


@app.route("/api/users", methods=["GET"])
@require_admin
def list_users():
    """List all users (admin endpoint). Requires valid admin token."""
    store = UserStore()
    users = store.load_users()
    return jsonify({"users": [u.to_dict() for u in users]})


@app.route("/api/users/<phone>/toggle", methods=["POST"])
@require_admin
def toggle_user(phone):
    """Toggle a user's active status (admin endpoint). Requires valid admin token."""
    store = UserStore()
    user = store.get_user_by_phone(phone)
    if not user:
        return jsonify({"error": "User not found"}), 404

    new_status = not user.active
    store.update_user(phone, active=new_status)
    return jsonify({"phone": phone, "active": new_status})


# ---------------------------------------------------------------------------
# Scheduler setup
# ---------------------------------------------------------------------------


def start_scheduler():
    """Start the background scheduler for periodic reminder checks."""
    scheduler = BackgroundScheduler()
    # Check every hour if any reminders need to be sent
    scheduler.add_job(
        reminder_scheduler.check_and_send_reminders,
        trigger=IntervalTrigger(hours=1),
        id="reminder_check",
        name="Check and send exercise reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Background scheduler started. Checking for reminders every hour.")
    return scheduler


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  Zhang Health Reminder System Starting")
    logger.info("=" * 60)

    # Start the background scheduler
    bg_scheduler = start_scheduler()

    # Run the Flask app
    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,  # Don't use debug mode with APScheduler
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
        bg_scheduler.shutdown()
