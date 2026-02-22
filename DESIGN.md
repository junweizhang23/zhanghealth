# Zhang Health - System Design

**Author:** Manus AI
**Date:** 2026-02-22

## 1. Overview

This document outlines the system architecture and implementation plan for the **Zhang Health** project. The goal is to create a reliable, automated system for sending periodic health-related reminders to family members via SMS, with capabilities for handling user replies and managing schedules across different timezones.

## 2. Core Requirements

- **Automated Reminders:** Send SMS messages to family members with exercise instructions (e.g., planking, light weight training).
- **Flexible Scheduling:** Messages should be sent every other day, at a time appropriate for the recipient's local timezone (e.g., Seattle and New York).
- **Two-Way Communication:** The system must be able to receive and process replies. Specifically, it needs to handle "OK" for confirmation and "no" for opting out of future messages.
- **User Management:** A simple system to manage family members' contact information and preferences.
- **Scalability & Maintainability:** The architecture should be modular, allowing for future enhancements, such as changing the messaging provider or adding new types of reminders.

## 3. Technology Stack & Architecture

Based on the initial research, a cloud-based solution using Python and the Twilio API is the most robust and cost-effective approach. This architecture avoids reliance on personal hardware (like an always-on Mac) and provides a scalable platform.

| Component | Technology | Rationale (Confidence: 95%) |
| :--- | :--- | :--- |
| **Core Application** | Python 3.11 | A versatile and widely-supported language with excellent libraries for web development, scheduling, and API integration. |
| **Messaging Service** | Twilio SMS API | Highly reliable, cost-effective (~$0.0079/message), with a powerful Python SDK, and built-in features for scheduling and receiving messages via webhooks. This is a more practical choice than iMessage-specific APIs which are more expensive and less transparent in their pricing. [1] |
| **Web Framework** | Flask | A lightweight and simple web framework, perfect for creating the webhook endpoint needed to receive replies from Twilio. |
| **Scheduling** | APScheduler (Python library) | A powerful, in-process scheduler that can handle the timezone-aware, every-other-day logic required for sending the reminders. |
| **Data Storage** | JSON file | For the current scale of the project (a few family members), a simple JSON file is sufficient to store user profiles (name, phone, timezone, opt-in status). This simplifies the setup and avoids the overhead of a full database. |
| **Deployment** | Docker | Containerizing the application with Docker will ensure a consistent environment and simplify deployment to any cloud provider or a local server. |

### System Flow Diagram

```mermaid
graph TD
    A[Scheduler (APScheduler)] -- triggers every hour --> B{Check for pending messages};
    B -- Yes --> C[Prepare Message Content];
    C --> D[Send SMS via Twilio API];
    D -- message sent --> E[Log Sent Message];

    subgraph User Interaction
        F[Family Member] -- receives SMS --> G{Replies "OK" or "no"};
    end

    G -- reply sent --> H[Twilio];
    H -- POST request --> I[Flask Webhook Endpoint];
    I --> J{Parse Reply};
    J -- "OK" --> K[Log Confirmation];
    J -- "no" --> L[Update User Profile to Opt-Out];

    M[User Profiles (JSON)] <--> B;
    M <--> L;
```

## 4. Implementation Plan

### Step 1: Project Setup
- Initialize a Python project with a `requirements.txt` file (Flask, Twilio, APScheduler).
- Create a `config.py` to store Twilio credentials and other configuration variables.
- Create a `users.json` file with the initial data for the family members.

### Step 2: Core Messaging Logic
- Implement a Python script (`sender.py`) that:
    - Reads user data from `users.json`.
    - For each user, checks if a message should be sent based on the schedule and their timezone.
    - Constructs the message content.
    - Uses the Twilio client to send the SMS.

### Step 3: Scheduling
- In the main application file (`app.py`), configure APScheduler to run the `sender.py` script at a regular interval (e.g., every hour).

### Step 4: Reply Handling (Webhook)
- In `app.py`, create a Flask route (`/webhook/twilio`) that will listen for incoming POST requests from Twilio.
- The webhook will:
    - Parse the incoming message content and sender's number.
    - Implement the logic to handle "OK" and "no".
    - Update the `users.json` file accordingly.

### Step 5: Dockerization & Deployment
- Write a `Dockerfile` to containerize the Flask application.
- Provide instructions in the `README.md` on how to build and run the Docker container.

## 5. Risks and Mitigation

- **Risk:** Twilio account suspension for sending unsolicited messages.
  - **Mitigation:** Implement a clear opt-in/opt-out mechanism. The first message sent to a new user should include instructions on how to stop receiving messages (e.g., "Reply NO to unsubscribe").
- **Risk:** Timezone conversion errors.
  - **Mitigation:** Use a robust library like `pytz` for all timezone-related calculations. Thoroughly test the scheduling logic with different timezones.
- **Risk:** Security of Twilio credentials.
  - **Mitigation:** Store credentials in environment variables, not directly in the code. The `.gitignore` file will be configured to ignore `config.py` and any other files containing sensitive information.

## 6. References

[1] Twilio Pricing. [https://www.twilio.com/en-us/pricing](https://www.twilio.com/en-us/pricing)
