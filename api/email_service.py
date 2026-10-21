import os
import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_climate_alert_email(
    receiver_email,
    receiver_name,
    location_name,
    risk_type,
    risk_level,
    weather_snapshot
):
    api_key = os.environ.get("BREVO_API_KEY")

    if not api_key:
        return False, "BREVO_API_KEY is not configured."

    temperature = weather_snapshot.get("temperature_2m", "Not available")
    rainfall = weather_snapshot.get("rain", "Not available")
    wind_speed = weather_snapshot.get("wind_speed_10m", "Not available")
    humidity = weather_snapshot.get("relative_humidity_2m", "Not available")

    subject = (
        f"ClimateShield Alert: {risk_level} {risk_type} "
        f"Risk in {location_name}"
    )

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #172033;">
            <h2 style="color: #0f766e;">ClimateShield Climate Alert</h2>

            <p>Hello {receiver_name},</p>

            <p>
                ClimateShield has detected a
                <strong>{risk_level} {risk_type} Risk</strong>
                for your saved location:
                <strong>{location_name}</strong>.
            </p>

            <h3>Current Conditions</h3>
            <ul>
                <li>Temperature: {temperature} °C</li>
                <li>Rainfall: {rainfall} mm</li>
                <li>Wind Speed: {wind_speed} km/h</li>
                <li>Humidity: {humidity}%</li>
            </ul>

            <h3>Safety Guidance</h3>

            <p>
                {get_safety_message(risk_type)}
            </p>

            <p>
                This is an educational climate-awareness alert.
                It is not an official emergency warning.
                Always follow local government and emergency-service advisories.
            </p>

            <p>— ClimateShield</p>
        </body>
    </html>
    """

    payload = {
        "sender": {
            "name": "ClimateShield",
            "email": os.environ.get("BREVO_SENDER_EMAIL")
        },
        "to": [
            {
                "email": receiver_email,
                "name": receiver_name
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()
        return True, "Email sent successfully."

    except requests.RequestException as error:
        return False, str(error)


def get_safety_message(risk_type):
    risk_type = risk_type.lower()

    if "heat" in risk_type:
        return (
            "Drink water regularly, avoid unnecessary outdoor activity, "
            "and stay in a cool or shaded place."
        )

    if "rain" in risk_type or "flood" in risk_type:
        return (
            "Avoid low-lying and flood-prone areas. "
            "Do not cross flowing water on foot or by vehicle. "
            "Keep emergency items ready and follow official advisories."
        )

    if "wind" in risk_type:
        return (
            "Stay indoors where possible. "
            "Keep away from windows, trees, and unstable structures."
        )

    return "Stay alert and follow official local weather advisories."
