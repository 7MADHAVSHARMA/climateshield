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
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

RISK_PRIORITY = {
    "Minimal": 1,
    "Low": 2,
    "Moderate": 3,
    "High": 4,
    "Severe": 5
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
            "(4madhavs1@gmail.com)"
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


@app.route("/api/suggestions")
def get_location_suggestions():
    query = request.args.get("q", "").strip()

    if len(query) < 3:
        return jsonify({"suggestions": []})

    headers = {
        "User-Agent": os.environ.get(
            "NOMINATIM_USER_AGENT",
            "ClimateShieldStudentProject/1.0 "
            "(4madhavs1@gmail.com)"
        )
    }

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 5,
        "addressdetails": 1
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
        print("Nominatim suggestions error:", error)
        return jsonify({"suggestions": []})

    suggestions = []

    for location in results:
        suggestions.append({
            "name": location.get("display_name", ""),
            "latitude": float(location.get("lat", 0)),
            "longitude": float(location.get("lon", 0))
        })

    return jsonify({"suggestions": suggestions})


@app.route("/api/risk")
def get_risk():
    try:
        latitude = float(request.args["latitude"])
        longitude = float(request.args["longitude"])
    except (KeyError, ValueError):
        return jsonify({
            "error": "Valid latitude and longitude are required."
        }), 400

    try:
        weather_data = get_weather_data(latitude, longitude)

        if not weather_data:
            return jsonify({
                "error": "Weather service is unavailable."
            }), 502

        air_quality_data = get_air_quality_data(latitude, longitude)

        current_weather = weather_data.get("current", {})
        daily_weather = weather_data.get("daily", {})
        current_air = air_quality_data.get("current", {})

        rainfall = float(current_weather.get("rain", 0) or 0)
        wind_speed = float(current_weather.get("wind_speed_10m", 0) or 0)
        humidity = float(current_weather.get("relative_humidity_2m", 0) or 0)
        temperature = float(current_weather.get("temperature_2m", 0) or 0)
        weather_code = int(current_weather.get("weather_code", 0) or 0)

        daily_rain = daily_weather.get("precipitation_sum", [0, 0, 0])
        daily_gusts = daily_weather.get("wind_gusts_10m_max", [0, 0, 0])

        max_rain = max(
            float(value or 0) for value in daily_rain
        )

        max_gust = max(
            float(value or 0) for value in daily_gusts
        )

        pm25 = float(current_air.get("pm2_5", 0) or 0)
        pm10 = float(current_air.get("pm10", 0) or 0)
        no2 = float(current_air.get("nitrogen_dioxide", 0) or 0)
        so2 = float(current_air.get("sulphur_dioxide", 0) or 0)
        ozone = float(current_air.get("ozone", 0) or 0)
        carbon_monoxide = float(current_air.get("carbon_monoxide", 0) or 0)
        european_aqi = float(current_air.get("european_aqi", 0) or 0)

        flood_risk = calculate_flood_risk(
            max_rain,
            rainfall,
            humidity
        )

        thunderstorm_risk = calculate_thunderstorm_risk(
            max_gust,
            max_rain,
            humidity,
            weather_code
        )

        dust_risk = calculate_dust_risk(
            wind_speed,
            max_gust,
            rainfall,
            humidity,
            temperature
        )

        pollution_risk = calculate_pollution_risk(
            pm25,
            pm10,
            no2,
            so2,
            ozone,
            carbon_monoxide,
            european_aqi
        )

        overall_risk = calculate_overall_risk(
            flood_risk,
            thunderstorm_risk,
            dust_risk,
            pollution_risk
        )

        risks = {
            "flood": {
                "score": round(flood_risk * 100, 1),
                "level": get_risk_level(flood_risk)
            },
            "thunderstorm": {
                "score": round(thunderstorm_risk * 100, 1),
                "level": get_risk_level(thunderstorm_risk)
            },
            "sandstorm": {
                "score": round(dust_risk * 100, 1),
                "level": get_risk_level(dust_risk)
            },
            "air_pollution": {
                "score": round(pollution_risk * 100, 1),
                "level": get_risk_level(pollution_risk),
                "pm2_5": pm25,
                "pm10": pm10,
                "european_aqi": european_aqi
            },
            "overall": {
                "score": round(overall_risk * 100, 1),
                "level": get_risk_level(overall_risk)
            }
        }

        return jsonify({
            "latitude": latitude,
            "longitude": longitude,
            "current": {
                "temperature_2m": temperature,
                "relative_humidity_2m": humidity,
                "precipitation": rainfall,
                "weather_code": weather_code,
                "wind_speed_10m": wind_speed,
                "pm2_5": pm25,
                "pm10": pm10,
                "nitrogen_dioxide": no2,
                "sulphur_dioxide": so2,
                "ozone": ozone,
                "carbon_monoxide": carbon_monoxide,
                "european_aqi": european_aqi
            },
            "risks": risks,
            "guidance": generate_guidance(risks)
        })

    except Exception as error:
        print("Risk calculation error:", error)
        return jsonify({
            "error": "Unable to calculate climate risk."
        }), 500


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

        current = weather_data.get("current", {})

        rainfall = float(current.get("rain", 0) or 0)
        wind_speed = float(current.get("wind_speed_10m", 0) or 0)

        risks = []

        if rainfall >= 20:
            risks.append({
                "type": "Heavy Rainfall",
                "level": "High"
            })

        if wind_speed >= 60:
            risks.append({
                "type": "Strong Wind",
                "level": "High"
            })

        for risk in risks:
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
                current
            )

            if success:
                log_alert(
                    location["user_id"],
                    location["location_id"],
                    risk["type"],
                    risk["level"],
                    json.dumps(current)
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
        "daily": (
            "precipitation_sum,wind_gusts_10m_max"
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
        return response.json()

    except requests.RequestException as error:
        print("Weather data error:", error)
        return None


def get_air_quality_data(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,"
            "sulphur_dioxide,ozone,european_aqi"
        ),
        "timezone": "auto"
    }

    try:
        response = requests.get(
            AIR_QUALITY_URL,
            params=params,
            timeout=10
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        print("Air quality error:", error)
        return {}


def calculate_flood_risk(
    max_daily_rain,
    current_rain,
    humidity
):
    flood_risk = (
        (max_daily_rain / 100) * 0.60 +
        (current_rain / 50) * 0.25 +
        (humidity / 100) * 0.15
    )

    return min(1.0, max(0.0, flood_risk))


def calculate_thunderstorm_risk(
    max_gust,
    max_rain,
    humidity,
    weather_code
):
    thunderstorm_risk = (
        (max_gust / 100) * 0.40 +
        (max_rain / 100) * 0.35 +
        (humidity / 100) * 0.25
    )

    if weather_code in [95, 96, 99]:
        thunderstorm_risk = max(thunderstorm_risk, 0.80)

    return min(1.0, max(0.0, thunderstorm_risk))


def calculate_dust_risk(
    wind_speed,
    max_gust,
    rainfall,
    humidity,
    temperature
):
    dust_risk = (
        (wind_speed / 80) * 0.35 +
        (max_gust / 100) * 0.30 +
        (1 - min(1.0, rainfall / 10)) * 0.15 +
        (1 - humidity / 100) * 0.10 +
        (max(0, temperature - 30) / 25) * 0.10
    )

    return min(1.0, max(0.0, dust_risk))


def calculate_pollution_risk(
    pm25,
    pm10,
    no2,
    so2,
    ozone,
    carbon_monoxide,
    european_aqi
):
    pollution_risk = (
        (pm25 / 150) * 0.35 +
        (pm10 / 250) * 0.20 +
        (no2 / 200) * 0.10 +
        (so2 / 200) * 0.10 +
        (ozone / 240) * 0.10 +
        (carbon_monoxide / 10000) * 0.05 +
        (european_aqi / 200) * 0.10
    )

    return min(1.0, max(0.0, pollution_risk))


def calculate_overall_risk(
    flood_risk,
    thunderstorm_risk,
    dust_risk,
    pollution_risk
):
    overall_risk = (
        flood_risk * 0.30 +
        thunderstorm_risk * 0.25 +
        dust_risk * 0.20 +
        pollution_risk * 0.25
    )

    return min(1.0, max(0.0, overall_risk))


def get_risk_level(score):
    if score >= 0.80:
        return "Severe"
    elif score >= 0.60:
        return "High"
    elif score >= 0.40:
        return "Moderate"
    elif score >= 0.20:
        return "Low"
    else:
        return "Minimal"


def generate_guidance(risks):
    guidance = []

    if risks["flood"]["score"] >= 60:
        guidance.append(
            "Avoid low-lying areas, drains, and flooded roads. "
            "Move to higher ground if flooding begins."
        )

    if risks["thunderstorm"]["score"] >= 60:
        guidance.append(
            "Stay indoors during thunderstorms. Avoid open fields, "
            "tall trees, and metal objects."
        )

    if risks["sandstorm"]["score"] >= 60:
        guidance.append(
            "Cover your nose and mouth, wear protective eyewear, "
            "and avoid outdoor travel during dust storms."
        )

    if risks["air_pollution"]["score"] >= 60:
        guidance.append(
            "Limit outdoor activity, especially for children, older adults, "
            "and people with breathing problems."
        )

    if risks["overall"]["score"] >= 80:
        guidance.append(
            "Severe conditions detected. Follow official local emergency advisories."
        )

    if not guidance:
        guidance.append(
            "No major climate risks detected at this time. "
            "Continue normal activities with general weather awareness."
        )

    return list(dict.fromkeys(guidance))


@app.errorhandler(Exception)
def handle_error(error):
    print("Unhandled application error:", error)
    return jsonify({
        "error": "Unable to process request. Please try again later."
    }), 502
