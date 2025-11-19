"""Utility functions for retrieving travel-time estimates and sending alerts."""
from __future__ import annotations

import os
import smtplib
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


def send_email_alert(
    *,
    email_from: str,
    email_password: str,
    email_to: str,
    subject: str,
    body: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
) -> None:
    """Send an email alert describing the current commute time."""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_from, email_password)
            server.send_message(msg)
    except Exception as exc:  # pragma: no cover - network failure is unrecoverable in tests
        raise EmailDeliveryError("Failed to send email alert") from exc


def resolve_env(name: str) -> Optional[str]:
    """Fetch an environment variable and return ``None`` when missing or empty."""
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None

