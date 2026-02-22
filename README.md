# Zhang Health - Family Health Reminder System

A lightweight, automated system that sends periodic exercise reminders to family members via SMS. Built with Python, Flask, Twilio, and APScheduler.

## Features

- **Scheduled Exercise Reminders**: Sends age-appropriate exercise instructions (planks, light weight training) on an every-other-day cadence
- **Timezone-Aware Scheduling**: Supports family members in different timezones (e.g., Seattle PST, New York EST)
- **Two-Way Communication**: Handles replies via Twilio webhooks
  - Reply **OK** to confirm exercise completion
  - Reply **NO** to opt out of reminders
  - Reply **START** to re-subscribe
- **Bilingual Messages**: Exercise instructions in Chinese with English exercise names
- **Age-Appropriate Plans**: Different exercise routines for seniors (60+) and adults (40s)
- **Docker Support**: Easy deployment with Docker and docker-compose

## Architecture

```
zhanghealth/
├── app.py              # Flask web server + APScheduler
├── config.py           # Configuration from environment variables
├── models.py           # User data model and JSON store
├── messages.py         # Exercise message templates
├── sender.py           # Twilio SMS sender + reminder logic
├── cli.py              # Command-line management tool
├── data/
│   └── users.json      # User profiles (phone, timezone, plan)
├── logs/
│   └── zhanghealth.log # Application logs
├── tests/
│   └── test_core.py    # Unit tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                # Twilio credentials (not committed)
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A [Twilio account](https://www.twilio.com/try-twilio) (free trial available)
- A Twilio phone number capable of sending SMS

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/junweizhang23/zhanghealth.git
cd zhanghealth

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your Twilio credentials

# Initialize sample user data
python cli.py init-sample
# Edit data/users.json with real phone numbers
```

### 3. Configure Twilio

1. Sign up at [twilio.com](https://www.twilio.com/try-twilio)
2. Get your Account SID and Auth Token from the [Twilio Console](https://console.twilio.com/)
3. Buy a phone number (or use the trial number)
4. Add credentials to your `.env` file:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
```

### 4. Configure Users

Edit `data/users.json` with your family members' information:

```json
{
  "users": [
    {
      "name": "妈妈",
      "phone": "+12065551234",
      "timezone": "America/Los_Angeles",
      "age": 63,
      "preferred_hour": 9,
      "active": true,
      "cadence_days": 2,
      "exercise_plan": "senior_beginner"
    }
  ]
}
```

### 5. Set Up Twilio Webhook (for receiving replies)

To receive SMS replies, you need a public URL for Twilio to send webhooks to:

**Option A: Using ngrok (for development)**
```bash
# Install ngrok
brew install ngrok  # or download from ngrok.com

# Start ngrok tunnel
ngrok http 5000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Set it in Twilio Console > Phone Numbers > Your Number > Messaging Webhook
# URL: https://abc123.ngrok.io/webhook/twilio
```

**Option B: Deploy to a cloud server (for production)**
```bash
# Using Docker
docker-compose up -d

# Set the webhook URL in Twilio Console
# URL: https://your-server.com/webhook/twilio
```

### 6. Run

```bash
# Development mode
python app.py

# Production mode (with Docker)
docker-compose up -d
```

## CLI Commands

```bash
python cli.py test-message    # Preview sample exercise messages
python cli.py send-now        # Trigger immediate reminder check (dry run)
python cli.py list-users      # List all registered users
python cli.py add-user        # Interactively add a new user
python cli.py init-sample     # Create sample users.json
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Health check and system status |
| `/webhook/twilio` | POST | Twilio webhook for incoming SMS |
| `/api/send-now` | POST | Manually trigger reminder check (requires auth) |
| `/api/users` | GET | List all users (requires auth) |
| `/api/users/<phone>/toggle` | POST | Toggle user active status (requires auth) |

Admin endpoints require the `X-Admin-Token` header matching `FLASK_SECRET_KEY`.

## How It Works

1. **APScheduler** runs a check every hour
2. For each active user, it checks:
   - Is the user active (not opted out)?
   - Has enough time passed since the last message (cadence_days)?
   - Is it the right hour in the user's local timezone?
3. If all conditions are met, it sends a personalized exercise reminder via Twilio SMS
4. When a user replies, Twilio forwards the message to the `/webhook/twilio` endpoint
5. The system processes the reply (OK, NO, START) and responds accordingly

## Exercise Plans

| Plan | Target | Exercises |
|---|---|---|
| `senior_beginner` | Age 60+ | Modified planks, wall push-ups, chair squats, light dumbbells (2-3 lbs) |
| `adult_intermediate` | Age 30-50 | Standard planks, push-ups, squats, deadlifts, pull-ups |

## Testing

```bash
python -m pytest tests/ -v
```

## Security Notes

- Twilio credentials are stored in `.env` (never committed to git)
- `data/users.json` contains phone numbers and is in `.gitignore`
- Admin API endpoints require authentication token
- Twilio webhook validation should be enabled in production

## License

Private - Zhang Family Use Only
