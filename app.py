from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import requests
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from dotenv import load_dotenv

from traffic_alert import EmailDeliveryError, TravelTimeError, format_eta, get_travel_time, send_email_alert


@dataclass
class AppConfig:
    google_maps_api_key: Optional[str]
    email_from: Optional[str]
    email_password: Optional[str]
    email_subject: str
    alert_threshold_minutes: int
    refresh_interval_seconds: int
    asset_version: str


def load_config() -> AppConfig:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    email_password = os.getenv("EMAIL_APP_PASSWORD")
    email_subject = os.getenv("EMAIL_SUBJECT", "🚦 Traffic Alert")

    try:
        threshold = int(os.getenv("ALERT_THRESHOLD_MINUTES", "120"))
    except ValueError:
        threshold = 120

    try:
        refresh_seconds = int(os.getenv("CHECK_INTERVAL_SECONDS", "120"))
    except ValueError:
        refresh_seconds = 120

    asset_version = os.getenv("ASSET_VERSION")
    if not asset_version:
        from datetime import datetime

        asset_version = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    return AppConfig(
        google_maps_api_key=api_key,
        email_from=email_from,
        email_password=email_password,
        email_subject=email_subject,
        alert_threshold_minutes=threshold,
        refresh_interval_seconds=refresh_seconds,
        asset_version=asset_version,
    )


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    app.config_obj = load_config()

    @app.route("/", methods=["GET", "POST"])
    def index():
        config: AppConfig = app.config_obj
        result = None

        if request.method == "POST" and request.is_json:
            data = request.get_json(force=True) or {}

            origin = (data.get("origin") or "").strip()
            destination = (data.get("destination") or "").strip()
            email_to = (data.get("email") or "").strip()
            notify = bool(data.get("notify"))
            notification_sent = bool(data.get("notificationSent"))
            threshold_str = data.get("threshold", str(config.alert_threshold_minutes))

            if not origin or not destination:
                return (
                    jsonify({"ok": False, "error": "Provide both origin and destination."}),
                    400,
                )

            if notify and not email_to:
                return (
                    jsonify({"ok": False, "error": "Enter an email address to notify."}),
                    400,
                )

            try:
                threshold = int(threshold_str)
            except ValueError:
                threshold = config.alert_threshold_minutes

            api_key = config.google_maps_api_key
            if not api_key:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "Google Maps API key missing. Set GOOGLE_MAPS_API_KEY.",
                        }
                    ),
                    400,
                )

            try:
                travel_minutes = get_travel_time(api_key, origin, destination)
            except TravelTimeError as exc:
                return jsonify({"ok": False, "error": str(exc)}), 502

            eta_display = format_eta(travel_minutes)
            should_alert = travel_minutes <= threshold
            alert_sent = False

            if notify and should_alert and not notification_sent:
                email_from = config.email_from
                email_password = config.email_password

                if not email_from or not email_password:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "Email credentials missing. Set EMAIL_FROM and EMAIL_APP_PASSWORD.",
                            }
                        ),
                        400,
                    )

                body = (
                    f"🚗 Traffic Alert: Travel time from {origin} to {destination} is now "
                    f"{eta_display}."
                )

                try:
                    send_email_alert(
                        email_from=email_from,
                        email_password=email_password,
                        email_to=email_to,
                        subject=config.email_subject,
                        body=body,
                    )
                except EmailDeliveryError as exc:
                    return jsonify({"ok": False, "error": str(exc)}), 502

                alert_sent = True

            payload = {
                "ok": True,
                "result": {
                    "origin": origin,
                    "destination": destination,
                    "minutes": travel_minutes,
                    "eta_display": eta_display,
                    "threshold": threshold,
                },
                "should_alert": should_alert,
                "alert_sent": alert_sent,
            }

            return jsonify(payload)

        if request.method == "POST":
            origin = request.form.get("origin", "").strip()
            destination = request.form.get("destination", "").strip()
            email_to = request.form.get("email", "").strip()
            notify = bool(request.form.get("notify"))
            threshold_str = request.form.get("threshold", str(config.alert_threshold_minutes))

            if not origin or not destination:
                flash("Please provide both origin and destination addresses.", "error")
                return redirect(url_for("index"))

            if notify and not email_to:
                flash("Enter an email address to receive notifications.", "error")
                return redirect(url_for("index"))

            try:
                threshold = int(threshold_str)
            except ValueError:
                threshold = config.alert_threshold_minutes

            api_key = config.google_maps_api_key
            if not api_key:
                flash(
                    "Google Maps API key missing. Set the GOOGLE_MAPS_API_KEY environment variable.",
                    "error",
                )
                return redirect(url_for("index"))

            try:
                travel_minutes = get_travel_time(api_key, origin, destination)
                eta_display = format_eta(travel_minutes)
                result = {
                    "origin": origin,
                    "destination": destination,
                    "minutes": travel_minutes,
                    "eta_display": eta_display,
                    "threshold": threshold,
                }
            except TravelTimeError as exc:
                flash(str(exc), "error")
                return redirect(url_for("index"))

            should_alert = travel_minutes <= threshold

            if notify and should_alert:
                email_from = config.email_from
                email_password = config.email_password

                if not email_from or not email_password:
                    flash(
                        "Email credentials are missing. Set EMAIL_FROM and EMAIL_APP_PASSWORD in the environment.",
                        "error",
                    )
                else:
                    body = (
                        f"🚗 Traffic Alert: Travel time from {origin} to {destination} is now "
                        f"{eta_display}."
                    )
                    try:
                        send_email_alert(
                            email_from=email_from,
                            email_password=email_password,
                            email_to=email_to,
                            subject=config.email_subject,
                            body=body,
                        )
                        flash(f"Email alert sent to {email_to}.", "success")
                    except EmailDeliveryError as exc:
                        flash(str(exc), "error")
            elif notify and not should_alert:
                flash(
                    "No alert sent because the travel time is above the configured threshold.",
                    "info",
                )

        return render_template("index.html", result=result, config=app.config_obj)

    @app.route("/autocomplete")
    def autocomplete():
        config: AppConfig = app.config_obj
        query = (request.args.get("q") or "").strip()

        if not query:
            return jsonify({"ok": True, "predictions": []})

        api_key = config.google_maps_api_key
        if not api_key:
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "Google Maps API key missing. Set GOOGLE_MAPS_API_KEY.",
                    }
                ),
                400,
            )

        params = {
            "input": query,
            "types": "geocode",
            "key": api_key,
        }

        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/place/autocomplete/json",
                params=params,
                timeout=5,
            )
            data = response.json()
        except Exception:
            return (
                jsonify({"ok": False, "error": "Failed to fetch address suggestions."}),
                502,
            )

        status = data.get("status", "UNKNOWN")
        if status not in {"OK", "ZERO_RESULTS"}:
            message = data.get("error_message") or f"Places API error: {status}"
            return jsonify({"ok": False, "error": message}), 502

        predictions = [
            prediction.get("description", "")
            for prediction in data.get("predictions", [])
            if prediction.get("description")
        ]

        return jsonify({"ok": True, "predictions": predictions})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

