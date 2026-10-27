import os
import re
from datetime import datetime

from flask import Flask, make_response, redirect, render_template, request, url_for
import requests

app = Flask(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ZIP_URL = "https://api.zippopotam.us/us/{}"
SAN_JOSE = {"latitude": 37.3382, "longitude": -121.8863}
ZIP_PATTERN = re.compile(r"\d{5}")
REPORTS_FILE = os.path.join(app.root_path, "reports.txt")
MAX_REPORT_LENGTH = 500
LAST_ZIP_COOKIE = "last_zip"
LAST_ZIP_MAX_AGE = 60 * 60 * 24 * 365  # one year

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


class ZipNotFound(Exception):
    pass


def get_current_weather(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,weather_code",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
    }
    response = requests.get(FORECAST_URL, params=params, timeout=10)
    response.raise_for_status()
    current = response.json()["current"]
    return {
        "temperature": round(current["temperature_2m"]),
        "description": WEATHER_CODES.get(current["weather_code"], "Unknown"),
    }


def lookup_zip(zip_code):
    response = requests.get(ZIP_URL.format(zip_code), timeout=10)
    if response.status_code == 404:
        raise ZipNotFound(zip_code)
    response.raise_for_status()
    place = response.json()["places"][0]
    return {
        "name": f"{place['place name']}, {place['state']}",
        "latitude": float(place["latitude"]),
        "longitude": float(place["longitude"]),
    }


@app.route("/")
def index():
    try:
        weather = get_current_weather(**SAN_JOSE)
        error = None
    except (requests.RequestException, KeyError, ValueError):
        weather = None
        error = "Couldn't load the weather right now. Please try again later."
    reported = request.args.get("reported") == "1"
    return render_template(
        "index.html", weather=weather, error=error, reported=reported
    )


@app.route("/report", methods=["POST"])
def report():
    # Collapse whitespace so each report stays on a single line
    message = " ".join(request.form.get("message", "").split())
    message = message[:MAX_REPORT_LENGTH]
    if not message:
        return redirect(url_for("index"))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(REPORTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")
    return redirect(url_for("index", reported=1, _anchor="report"))


@app.route("/zip")
def zip_weather():
    zip_code = request.args.get("zip", "").strip()
    place = weather = error = None
    remember_zip = False
    if not zip_code:
        # Pre-fill the box with the visitor's last lookup, without searching
        last_zip = request.cookies.get(LAST_ZIP_COOKIE, "")
        if ZIP_PATTERN.fullmatch(last_zip):
            zip_code = last_zip
    else:
        if not ZIP_PATTERN.fullmatch(zip_code):
            error = "Please enter a 5-digit US zip code."
        else:
            try:
                place = lookup_zip(zip_code)
                remember_zip = True
                weather = get_current_weather(place["latitude"], place["longitude"])
            except ZipNotFound:
                place = None
                error = f"Zip code {zip_code} does not exist."
            except (requests.RequestException, KeyError, IndexError, ValueError):
                place = None
                error = "Couldn't load the weather right now. Please try again later."
    response = make_response(render_template(
        "zip.html", zip_code=zip_code, place=place, weather=weather, error=error
    ))
    if remember_zip:
        response.set_cookie(LAST_ZIP_COOKIE, zip_code, max_age=LAST_ZIP_MAX_AGE,
                            httponly=True, samesite="Lax")
    return response


if __name__ == "__main__":
    app.run(debug=True)
