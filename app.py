import os
from flask import Flask, render_template, request, jsonify
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from waitress import serve

app = Flask(__name__)

API_KEY = os.getenv("WEATHER_API_KEY")

if not API_KEY:
    raise ValueError("WEATHER_API_KEY belum diatur. Masukkan API key lewat environment variable.")

BASE_URL = "https://api.weatherapi.com/v1/current.json"

# Session agar request ke API lebih stabil
session = requests.Session()

retry = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)

adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Menyimpan data terakhir sebagai cadangan kalau API sedang error
last_good_data = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/weather")
def weather_api():
    city = request.args.get("city", "").strip()

    if not city:
        return jsonify({
            "success": False,
            "error": "Nama kota tidak boleh kosong."
        })

    result = get_realtime_weather(city)
    return jsonify(result)


def get_realtime_weather(city):
    params = {
        "key": API_KEY,
        "q": city,
        "aqi": "yes",
        "lang": "id"
    }

    try:
        response = session.get(BASE_URL, params=params, timeout=5)
        data = response.json()

        if response.status_code == 200:
            weather = {
                "city": data["location"]["name"],
                "region": data["location"]["region"],
                "country": data["location"]["country"],
                "localtime": data["location"]["localtime"],

                "temperature": data["current"]["temp_c"],
                "feels_like": data["current"]["feelslike_c"],
                "humidity": data["current"]["humidity"],
                "pressure": data["current"]["pressure_mb"],
                "wind_speed": data["current"]["wind_kph"],
                "wind_direction": data["current"]["wind_dir"],

                "condition": data["current"]["condition"]["text"],
                "icon": data["current"]["condition"]["icon"],

                "uv": data["current"]["uv"],
                "visibility": data["current"]["vis_km"],
                "cloud": data["current"].get("cloud", 0),
                "gust": data["current"].get("gust_kph", 0),
                "precip": data["current"].get("precip_mm", 0),
                "air_quality_pm25": round(data["current"].get("air_quality", {}).get("pm2_5", 0), 1),
                "air_quality_pm10": round(data["current"].get("air_quality", {}).get("pm10", 0), 1),
                "last_updated": data["current"]["last_updated"],
                "request_time": datetime.now().strftime("%H:%M:%S"),

                "source": "WeatherAPI.com Realtime API",
                "status": "Data realtime berhasil diperbarui"
            }

            last_good_data[city.lower()] = weather

            return {
                "success": True,
                "weather": weather
            }

        else:
            error_message = data.get("error", {}).get("message", "Data cuaca tidak ditemukan.")

            if city.lower() in last_good_data:
                backup = last_good_data[city.lower()].copy()
                backup["status"] = "API bermasalah, menampilkan data terakhir"

                return {
                    "success": True,
                    "weather": backup
                }

            return {
                "success": False,
                "error": error_message
            }

    except requests.exceptions.Timeout:
        if city.lower() in last_good_data:
            backup = last_good_data[city.lower()].copy()
            backup["status"] = "Koneksi lambat, menampilkan data terakhir"

            return {
                "success": True,
                "weather": backup
            }

        return {
            "success": False,
            "error": "Request terlalu lama. Coba lagi."
        }

    except requests.exceptions.ConnectionError:
        if city.lower() in last_good_data:
            backup = last_good_data[city.lower()].copy()
            backup["status"] = "Koneksi internet bermasalah, menampilkan data terakhir"

            return {
                "success": True,
                "weather": backup
            }

        return {
            "success": False,
            "error": "Tidak ada koneksi internet."
        }

    except Exception as e:
        print("Error:", e)

        return {
            "success": False,
            "error": "Terjadi kesalahan saat mengambil data cuaca."
        }


if __name__ == "__main__":
    print("Server berjalan di semua device jaringan.")
    print("Buka di laptop: http://127.0.0.1:5000")
    print("Buka di HP/device lain: http://IP-LAPTOP-KAMU:5000")
    serve(app, host="0.0.0.0", port=5000)
