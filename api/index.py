import os
import json

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

import requests

from api.db import (
    init_db,
    create_user,
    verify_user,
    save_location,
    get_active_locations,
    was_alert_sent_recently,
    log_alert,
    enable_email_alerts,
    disable_email_alerts,
    get_user_by_email
)

from api.email_service import send_climate_alert_email

app = Flask(
    __name__,
    template_folder="../templates",
    static_folder="../static"
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "temporary-student-secret-key-change-this"
)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

RISK_PRIORITY = {
    "Low": 1,
    "Moderate": 2,
    "High": 3,
    "Severe": 4
}

try:
    init_db()
except Exception as error:
    print("Database initialization skipped:", error)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="All fields are required."
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match."
            )

        if len(password) < 6:
            return render_template(
                "register.html",
                error="Password must be at least 6 characters."
            )

        created = create_user(name, email, password)

        if not created:
            return render_template(
                "register.html",
                error="This email is already registered."
            )

        session["user_email"] = email
        session["user_name"] = name

        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = verify_user(email, password)

        if not user:
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        session["user_email"] = user["email"]
        session["user_name"] = user["name"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    email = session.get("user_email")

    if not email:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name"),
        user_email=email
    )


@app.route("/enable-alerts", methods=["POST"])
def enable_alerts():
    email = session.get("user_email")

    if not email:
        return jsonify({"error": "Login required."}), 401

    enable_email_alerts(email)

    return jsonify({"message": "Email alerts enabled."})


@app.route("/disable-alerts", methods=["POST"])
def disable_alerts():
    email = session.get("user_email")

    if not email:
        return jsonify({"error": "Login required."}), 401

    disable_email_alerts(email)

    return jsonify({"message": "Email alerts disabled."})


@app.route("/save-location", methods=["POST"])
def save_user_location():
    email = session.get("user_email")

    if not email:
        return jsonify({"error": "Login required."}), 401

    data = request.get_json()

    location_name = data.get("location_name")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    if not location_name or latitude is None or longitude is None:
        return jsonify({"error": "Invalid location data."}), 400

    user = get_user_by_email(email)

    if not user:
        return jsonify({"error": "User not found."}), 404

    save_location(
        user["id"],
        location_name,
        float(latitude),
        float(longitude)
    )

    return jsonify({"message": "Location saved successfully."})


@app.route("/api/location")
def find_location():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"error": "Please enter a location."}), 400

    headers = {
        "User-Agent": os.environ.get(
            "NOMINATIM_USER_AGENT",
            "ClimateShieldStudentProject/1.0 "
            "(replace-with-your-email@example.com)"
        )
    }

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1
    }

    try:
        response = requests.get(
            NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        results = response.json()

    except requests.RequestException as error:
        print("Nominatim error:", error)
        return jsonify({"error": "Location service is unavailable."}), 502

    if not results:
        return jsonify({"error": "Location not found."}), 404

    location = results[0]

    return jsonify({
        "name": location["display_name"],
        "latitude": float(location["lat"]),
        "longitude": float(location["lon"])
    })


@app.route("/api/risk")
def get_risk():
    try:
        latitude = float(request.args["latitude"])
        longitude = float(request.args["longitude"])
    except (KeyError, ValueError):
        return jsonify({
            "error": "Valid latitude and longitude are required."
        }), 400

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "rain,wind_speed_10m,weather_code"
        ),
        "hourly": (
            "temperature_2m,precipitation_probability,"
            "rain,wind_speed_10m"
        ),
        "forecast_days": 3,
        "timezone": "auto"
    }

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        weather_data = response.json()

    except requests.RequestException as error:
        print("Open-Meteo error:", error)
        return jsonify({"error": "Weather service is unavailable."}), 502

    risk_result = classify_risk(weather_data)

    risk_result.update({
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "current": weather_data.get("current", {}),
        "hourly": weather_data.get("hourly", {}),
        "timezone": weather_data.get("timezone", "")
    })

    risk_result["guidance"] = generate_guidance(
        risk_result["risks"]
    )

    return jsonify(risk_result)


@app.route("/api/check-alerts")
def check_alerts():
    active_locations = get_active_locations()

    sent_count = 0

    for location in active_locations:
        weather_data = get_weather_data(
            location["latitude"],
            location["longitude"]
        )

        if not weather_data:
            continue

        risk_result = classify_risk(weather_data)

        if risk_result["level"] not in ["High", "Severe"]:
            continue

        for risk in risk_result["risks"]:
            if risk["level"] not in ["High", "Severe"]:
                continue

            already_sent = was_alert_sent_recently(
                location["user_id"],
                location["location_id"],
                risk["type"],
                risk["level"]
            )

            if already_sent:
                continue

            success = send_climate_alert_email(
                location["user_email"],
                location["user_name"],
                location["location_name"],
                risk["type"],
                risk["level"],
                weather_data.get("current", {})
            )

            if success:
                log_alert(
                    location["user_id"],
                    location["location_id"],
                    risk["type"],
                    risk["level"],
                    json.dumps(weather_data.get("current", {}))
                )

                sent_count += 1

    return jsonify({
        "message": f"{sent_count} alert email(s) processed.",
        "checked_locations": len(active_locations)
    })


def get_weather_data(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "rain,wind_speed_10m,weather_code"
        ),
        "timezone": "auto"
    }

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        print("Weather data error:", error)
        return None


def classify_risk(weather_data):
    current = weather_data.get("current", {})

    temperature = current.get("temperature_2m")
    rainfall = current.get("rain", 0) or 0
    wind_speed = current.get("wind_speed_10m", 0) or 0

    risks = []

    if temperature is not None:
        if temperature >= 45:
            risks.append({
                "type": "Extreme Heat",
                "level": "Severe",
                "detail": f"Temperature is {temperature}°C."
            })

        elif temperature >= 40:
            risks.append({
                "type": "Extreme Heat",
                "level": "High",
                "detail": f"Temperature is {temperature}°C."
            })

        elif temperature >= 35:
            risks.append({
                "type": "Heat Risk",
                "level": "Moderate",
                "detail": f"Temperature is {temperature}°C."
            })

    if rainfall >= 20:
        risks.append({
            "type": "Heavy Rainfall",
            "level": "High",
            "detail": (
                f"Rainfall is {rainfall} mm. "
                "Low-lying areas may face increased flood "
                "or waterlogging risk."
            )
        })

    elif rainfall >= 5:
        risks.append({
            "type": "Rainfall",
            "level": "Moderate",
            "detail": f"Rainfall is {rainfall} mm."
        })

    if wind_speed >= 60:
        risks.append({
            "type": "Strong Wind",
            "level": "High",
            "detail": f"Wind speed is {wind_speed} km/h."
        })

    elif wind_speed >= 35:
        risks.append({
            "type": "Wind Risk",
            "level": "Moderate",
            "detail": f"Wind speed is {wind_speed} km/h."
        })

    if not risks:
        overall_level = "Low"

    else:
        overall_level = max(
            [risk["level"] for risk in risks],
            key=lambda level: RISK_PRIORITY[level]
        )

    return {
        "level": overall_level,
        "risks": risks
    }


def generate_guidance(risks):
    instructions = []

    for risk in risks:
        risk_type = risk["type"].lower()

        if "heat" in risk_type:
            instructions.append(
                "Drink water, avoid unnecessary outdoor activity, "
                "and stay in a cool place."
            )

        elif "rain" in risk_type or "flood" in risk_type:
            instructions.append(
                "Avoid low-lying and flood-prone areas. "
                "Do not cross flowing water on foot or by vehicle. "
                "Follow official local advisories."
            )

        elif "wind" in risk_type:
            instructions.append(
                "Stay indoors where possible. "
                "Keep away from windows, trees, "
                "and unstable structures."
            )

    if not instructions:
        instructions.append(
            "No immediate project-defined hazard was detected. "
            "Continue following official local advisories."
        )

    return list(dict.fromkeys(instructions))


@app.errorhandler(Exception)
def handle_error(error):
    print("Unhandled application error:", error)
    return jsonify({
        "error": "Unable to process request. Please try again later."
    }), 502
