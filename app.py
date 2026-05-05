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

# Data terakhir disimpan sebagai cadangan kalau API/koneksi bermasalah
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

//smart recomendation
def generate_recommendation(weather):
    recommendations = []

    condition = str(weather.get("condition", "")).lower()
    temperature = float(weather.get("temperature", 0))
    feels_like = float(weather.get("feels_like", 0))
    humidity = float(weather.get("humidity", 0))
    wind_speed = float(weather.get("wind_speed", 0))
    uv = float(weather.get("uv", 0))
    precip = float(weather.get("precip", 0))
    pm25 = float(weather.get("air_quality_pm25", 0))

    if "hujan" in condition or "rain" in condition or precip > 0:
        recommendations.append("Bawa payung atau jas hujan karena ada indikasi hujan di lokasi ini.")

    if uv >= 8:
        recommendations.append("UV Index sangat tinggi. Gunakan sunscreen, topi, atau hindari terlalu lama di luar ruangan.")
    elif uv >= 6:
        recommendations.append("UV Index cukup tinggi. Gunakan pelindung kulit jika beraktivitas di luar.")
    elif uv >= 3:
        recommendations.append("UV Index sedang. Aktivitas luar masih aman, tetapi tetap disarankan memakai pelindung jika lama di bawah matahari.")

    if feels_like >= 33:
        recommendations.append("Suhu terasa cukup panas. Perbanyak minum air dan hindari aktivitas berat terlalu lama.")
    elif temperature <= 22:
        recommendations.append("Udara cukup sejuk. Gunakan pakaian yang nyaman agar tubuh tetap hangat.")

    if humidity >= 80:
        recommendations.append("Kelembapan tinggi, udara bisa terasa lebih gerah dan kurang nyaman.")
    elif humidity <= 35:
        recommendations.append("Udara cukup kering. Jaga hidrasi tubuh dan kelembapan kulit.")

    if wind_speed >= 30:
        recommendations.append("Angin cukup kencang. Hati-hati saat berkendara atau berada di luar ruangan.")

    if pm25 >= 55:
        recommendations.append("Kualitas udara kurang baik. Gunakan masker jika beraktivitas di luar.")
    elif pm25 >= 35:
        recommendations.append("Kualitas udara sedang. Orang sensitif sebaiknya membatasi aktivitas luar ruangan.")

    if not recommendations:
        recommendations.append("Kondisi cuaca cukup aman untuk aktivitas harian.")

    return recommendations

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
            current = data["current"]
            location = data["location"]
            condition = current["condition"]
            air_quality = current.get("air_quality", {})

            weather = {
                "city": location.get("name", "-"),
                "region": location.get("region", "-"),
                "country": location.get("country", "-"),
                "localtime": location.get("localtime", "-"),
                "timezone": location.get("tz_id", "-"),

                "temperature": current.get("temp_c", 0),
                "feels_like": current.get("feelslike_c", 0),
                "humidity": current.get("humidity", 0),
                "pressure": current.get("pressure_mb", 0),

                "wind_speed": current.get("wind_kph", 0),
                "wind_direction": current.get("wind_dir", "-"),
                "wind_degree": current.get("wind_degree", 0),
                "gust": current.get("gust_kph", 0),

                "condition": condition.get("text", "-"),
                "icon": condition.get("icon", ""),
                "is_day": current.get("is_day", 1),

                "uv": current.get("uv", 0),
                "visibility": current.get("vis_km", 0),
                "cloud": current.get("cloud", 0),
                "precip": current.get("precip_mm", 0),

                "air_quality_pm25": round(air_quality.get("pm2_5", 0), 1),
                "air_quality_pm10": round(air_quality.get("pm10", 0), 1),

                "last_updated": current.get("last_updated", "-"),
                "request_time": datetime.now().strftime("%H:%M:%S"),

                "source": "WeatherAPI.com Realtime API",
                "status": "Data realtime berhasil diperbarui"
            }

            //hasil rekomendasi
            weather["recommendations"] = generate_recommendation(weather)
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
    port = int(os.environ.get("PORT", 5000))

    print("Server berjalan.")
    print("Buka di laptop: http://127.0.0.1:5000")
    print("Buka di HP/device lain satu jaringan: http://IP-LAPTOP-KAMU:5000")

    serve(app, host="0.0.0.0", port=port)
