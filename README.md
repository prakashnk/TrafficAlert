# TrafficAlert

A minimal Flask application that checks the current travel time between two addresses using the Google Maps Directions API and optionally sends an email notification when the ETA is below a configurable threshold.

## Prerequisites

- Python 3.10+
- Google Maps Directions API key (the Places API is recommended for richer autocomplete suggestions, but the app now falls back to the Geocoding API when Places isn't enabled)
- HTTPS-capable email API endpoint and API key (required only if you enable email notifications)

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

### Configuring the email API

Set `EMAIL_API_URL` to the HTTPS endpoint used for sending messages and `EMAIL_API_KEY` to the Bearer token used to authorize requests. The `EMAIL_FROM` value populates the sender field.

#### Using Gmail

If you want to send alerts through Gmail:

- Set `EMAIL_API_URL` to `https://gmail.googleapis.com/gmail/v1/users/me/messages/send`.
- Use an OAuth 2.0 access token with Gmail send scope as `EMAIL_API_KEY`.
- Provide your refresh token and OAuth client credentials to keep the access token fresh:
  - `EMAIL_OAUTH_REFRESH_TOKEN`
  - `EMAIL_OAUTH_CLIENT_ID`
  - `EMAIL_OAUTH_CLIENT_SECRET`
- Optionally override `EMAIL_OAUTH_TOKEN_URL` if you are using a non-Google OAuth provider (defaults to `https://oauth2.googleapis.com/token`).
- Set `EMAIL_FROM` to the Gmail address associated with the token.

When the Gmail endpoint is detected, the app automatically builds the raw MIME payload that the Gmail API expects and sends it over HTTPS. If a refresh token and client credentials are provided, the app will exchange them for a new access token when needed. For other providers, it falls back to the generic JSON payload with `from`, `to`, `subject`, and `text` fields.

### Refreshing the Modern theme

The UI ships with a custom Modern skin that lives in `static/css/modern.css`. Browsers can occasionally cache that file aggressively. If you pull the latest code but still see the older styling, edit your `.env` file and set `ASSET_VERSION` to any unique value. Restart the Flask server and reload the page—the query parameter automatically appended to the stylesheet URL will force the browser to fetch the updated CSS.

## How it works

- The form submits the origin and destination addresses.
- The application queries the Google Maps Directions API for real-time traffic information and displays the ETA in a friendly format.
- Address suggestions come from the Google Places Autocomplete API when available, and automatically fall back to the Geocoding API when Places access is not configured for your key.
- If notifications are enabled and the travel time is below the configured threshold, an email alert is sent through the configured HTTPS email API endpoint.

## Development notes

- The application avoids storing secrets in the repository. Use environment variables for API keys and passwords.
- Email sending is optional; you can leave the notification switch disabled to simply inspect travel times without triggering alerts.

