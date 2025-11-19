# TrafficAlert

A minimal Flask application that checks the current travel time between two addresses using the Google Maps Directions API and optionally sends an email notification when the ETA is below a configurable threshold.

## Prerequisites

- Python 3.10+
- Google Maps Directions API key (the Places API is recommended for richer autocomplete suggestions, but the app now falls back to the Geocoding API when Places isn't enabled)
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

   Update `.env` with your Google Maps API key. You only need to provide the email-related settings if you want the application to send alerts. If your browser seems to cache an older stylesheet, set `ASSET_VERSION` in `.env` to any new value (for example, `ASSET_VERSION=20241118`) to force clients to download the refreshed Modern theme assets.

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

### Refreshing the Modern theme

The UI ships with a custom Modern skin that lives in `static/css/modern.css`. Browsers can occasionally cache that file aggressively. If you pull the latest code but still see the older styling, edit your `.env` file and set `ASSET_VERSION` to any unique value. Restart the Flask server and reload the page—the query parameter automatically appended to the stylesheet URL will force the browser to fetch the updated CSS.

## How it works

- The form submits the origin and destination addresses.
- The application queries the Google Maps Directions API for real-time traffic information and displays the ETA in a friendly format.
- Address suggestions come from the Google Places Autocomplete API when available, and automatically fall back to the Geocoding API when Places access is not configured for your key.
- If notifications are enabled and the travel time is below the configured threshold, an email alert is sent using the Gmail SMTP server.

## Development notes

- The application avoids storing secrets in the repository. Use environment variables for API keys and passwords.
- Email sending is optional; you can leave the notification switch disabled to simply inspect travel times without triggering alerts.

