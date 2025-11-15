from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from flask import Flask, flash, redirect, render_template, request, url_for

from dotenv import load_dotenv

from traffic_alert import EmailDeliveryError, TravelTimeError, format_eta, get_travel_time, send_email_alert


@dataclass
class AppConfig:
    google_maps_api_key: Optional[str]
    email_from: Optional[str]
    email_password: Optional[str]
    email_subject: str
    alert_threshold_minutes: int


def load_config() -> AppConfig:
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    email_from = os.getenv("EMAIL_FROM")
    email_password = os.getenv("EMAIL_APP_PASSWORD")
    email_subject = os.getenv("EMAIL_SUBJECT", "🚦 Traffic Alert")

    try:
        threshold = int(os.getenv("ALERT_THRESHOLD_MINUTES", "120"))
    except ValueError:
        threshold = 120

    return AppConfig(
        google_maps_api_key=api_key,
        email_from=email_from,
        email_password=email_password,
        email_subject=email_subject,
        alert_threshold_minutes=threshold,
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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)

