from flask import Flask, render_template
import requests

app = Flask(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
SAN_JOSE = {"latitude": 37.3382, "longitude": -121.8863}

# WMO weather interpretation codes used by Open-Meteo
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_current_weather():
    params = {
        **SAN_JOSE,
        "current": "temperature_2m,weather_code",
        "temperature_unit": "fahrenheit",
        "timezone": "America/Los_Angeles",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    current = response.json()["current"]
    return {
        "temperature": round(current["temperature_2m"]),
        "description": WEATHER_CODES.get(current["weather_code"], "Unknown"),
    }


@app.route("/")
def index():
    try:
        weather = get_current_weather()
        error = None
    except (requests.RequestException, KeyError, ValueError):
        weather = None
        error = "Couldn't load the weather right now. Please try again later."
    return render_template("index.html", weather=weather, error=error)


if __name__ == "__main__":
    app.run(debug=True)
