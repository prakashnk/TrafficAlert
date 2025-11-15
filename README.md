# TrafficAlert

A minimal Flask application that checks the current travel time between two addresses using the Google Maps Directions API and optionally sends an email notification when the ETA is below a configurable threshold.

## Prerequisites

- Python 3.10+
- Google Maps Directions API key
- Gmail account with an [App Password](https://support.google.com/accounts/answer/185833) (required only if you enable email notifications)

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the environment variables. Create a `.env` file or export them in your shell before running the server.

   ```bash
   export GOOGLE_MAPS_API_KEY="your-google-maps-api-key"
   export EMAIL_FROM="your-gmail-address"           # optional, required for email alerts
   export EMAIL_APP_PASSWORD="your-gmail-app-password"  # optional, required for email alerts
   export EMAIL_SUBJECT="🚦 Traffic Alert"          # optional
   export ALERT_THRESHOLD_MINUTES=120               # optional
   export FLASK_SECRET_KEY="change-me"             # optional
   ```

## Running the server

Start the Flask development server:

```bash
flask --app app run --debug
```

Open a browser and navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000). Fill in the origin, destination, and (optionally) enable email notifications to receive alerts when the travel time drops below the specified threshold.

## How it works

- The form submits the origin and destination addresses.
- The application queries the Google Maps Directions API for real-time traffic information and displays the ETA in a friendly format.
- If notifications are enabled and the travel time is below the configured threshold, an email alert is sent using the Gmail SMTP server.

## Development notes

- The application avoids storing secrets in the repository. Use environment variables for API keys and passwords.
- Email sending is optional; you can leave the notification switch disabled to simply inspect travel times without triggering alerts.

