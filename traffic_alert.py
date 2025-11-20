"""Utility functions for retrieving travel-time estimates and sending alerts."""
from __future__ import annotations

import base64
import os
from email.mime.text import MIMEText
from typing import Optional

import requests


class TrafficAlertError(Exception):
    """Base exception for traffic alert operations."""


class TravelTimeError(TrafficAlertError):
    """Raised when the travel time API cannot provide a result."""


class EmailDeliveryError(TrafficAlertError):
    """Raised when an email alert cannot be delivered."""


def get_travel_time(api_key: str, origin: str, destination: str) -> float:
    """Return the estimated travel time in minutes between two addresses.

    Raises
    ------
    TravelTimeError
        If the API response cannot be parsed or does not contain a travel time.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": api_key,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException as exc:
        raise TravelTimeError("Unable to contact the Google Directions API") from exc

    if response.status_code != 200:
        raise TravelTimeError(
            f"Directions API request failed with HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise TravelTimeError("Directions API returned an unreadable response") from exc

    status = data.get("status", "UNKNOWN")
    if status != "OK":
        if status == "ZERO_RESULTS":
            raise TravelTimeError("No route found between the selected locations.")
        message = data.get("error_message") or f"Directions API error: {status}"
        raise TravelTimeError(message)

    try:
        leg = data["routes"][0]["legs"][0]
    except (KeyError, IndexError) as exc:
        raise TravelTimeError("Directions API response was missing route data") from exc

    duration_block = leg.get("duration_in_traffic") or leg.get("duration")
    if not duration_block or "value" not in duration_block:
        raise TravelTimeError("Directions API did not include a travel time.")

    return duration_block["value"] / 60.0


def format_eta(minutes: float) -> str:
    """Return a user-friendly ETA string from minutes."""
    total_minutes = int(round(minutes))
    hours, mins = divmod(total_minutes, 60)

    if hours and mins:
        return f"{hours} hr {mins} min"
    if hours:
        return f"{hours} hr"
    return f"{mins} min"


def refresh_access_token(
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str,
    token_url: str = "https://oauth2.googleapis.com/token",
) -> str:
    """Exchange a refresh token for a short-lived access token."""

    if not token_url.lower().startswith("https://"):
        raise EmailDeliveryError("OAuth token URL must use HTTPS")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        response = requests.post(token_url, data=payload, timeout=10)
    except requests.RequestException as exc:
        raise EmailDeliveryError("Failed to refresh email access token") from exc

    if response.status_code != 200:
        try:
            data = response.json()
            error_detail = data.get("error_description") or data.get("error")
        except ValueError:
            error_detail = response.text.strip()

        message = "Unable to refresh email access token"
        if error_detail:
            message = f"{message}: {error_detail}"
        raise EmailDeliveryError(message)

    try:
        data = response.json()
    except ValueError as exc:
        raise EmailDeliveryError("Token endpoint returned invalid JSON") from exc

    access_token = data.get("access_token")
    if not access_token:
        raise EmailDeliveryError("Token endpoint response was missing an access_token")

    return access_token


def send_email_alert(
    *,
    email_from: str,
    email_api_key: Optional[str],
    email_api_url: str,
    email_to: str,
    subject: str,
    body: str,
    email_refresh_token: Optional[str] = None,
    oauth_client_id: Optional[str] = None,
    oauth_client_secret: Optional[str] = None,
    oauth_token_url: str = "https://oauth2.googleapis.com/token",
) -> None:
    """Send an email alert describing the current commute time via HTTPS."""

    if not email_api_url.lower().startswith("https://"):
        raise EmailDeliveryError("Email API URL must use HTTPS")

    refresh_available = all([email_refresh_token, oauth_client_id, oauth_client_secret])
    token_used = email_api_key

    if not token_used and refresh_available:
        token_used = refresh_access_token(
            refresh_token=email_refresh_token or "",
            client_id=oauth_client_id or "",
            client_secret=oauth_client_secret or "",
            token_url=oauth_token_url,
        )
    elif not token_used:
        raise EmailDeliveryError("Email API key missing and no refresh token available")

    if "gmail.googleapis.com" in email_api_url:
        message = MIMEText(body)
        message["to"] = email_to
        message["from"] = email_from
        message["subject"] = subject

        payload = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
    else:
        payload = {
            "from": email_from,
            "to": email_to,
            "subject": subject,
            "text": body,
        }

    def _deliver(access_token: str) -> requests.Response:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        return requests.post(email_api_url, json=payload, headers=headers, timeout=10)

    try:
        response = _deliver(token_used)
    except requests.RequestException as exc:  # pragma: no cover - network failure is unrecoverable in tests
        raise EmailDeliveryError("Failed to reach the email API") from exc

    if response.status_code == 401 and refresh_available:
        try:
            refreshed_token = refresh_access_token(
                refresh_token=email_refresh_token or "",
                client_id=oauth_client_id or "",
                client_secret=oauth_client_secret or "",
                token_url=oauth_token_url,
            )
        except EmailDeliveryError:
            pass
        else:
            try:
                response = _deliver(refreshed_token)
            except requests.RequestException as exc:  # pragma: no cover
                raise EmailDeliveryError("Failed to reach the email API") from exc

    if response.status_code >= 400:
        try:
            data = response.json()
            error_detail = data.get("error") or data.get("message")
        except ValueError:
            error_detail = response.text.strip()

        message = "Email API rejected the request"
        if error_detail:
            message = f"{message}: {error_detail}"
        raise EmailDeliveryError(message)


def resolve_env(name: str) -> Optional[str]:
    """Fetch an environment variable and return ``None`` when missing or empty."""
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None

