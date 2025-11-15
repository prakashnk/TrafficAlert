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

3. Copy the sample environment file and fill in your own values:

   ```bash
   cp .env.example .env
   ```

   Update `.env` with your Google Maps API key. You only need to provide the email-related settings if you want the application to send alerts.

## Running the server

Start the Flask development server (the `python-dotenv` package automatically loads the `.env` file):

```bash
flask --app app run --debug
```

Alternatively, you can launch the app directly with Python:

```bash
python app.py
```

Open a browser and navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000). Fill in the origin, destination, and (optionally) enable email notifications to receive alerts when the travel time drops below the specified threshold.

## How it works

- The form submits the origin and destination addresses.
- The application queries the Google Maps Directions API for real-time traffic information and displays the ETA in a friendly format.
- If notifications are enabled and the travel time is below the configured threshold, an email alert is sent using the Gmail SMTP server.

## Development notes

- The application avoids storing secrets in the repository. Use environment variables for API keys and passwords.
- Email sending is optional; you can leave the notification switch disabled to simply inspect travel times without triggering alerts.

