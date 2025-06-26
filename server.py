from flask import Flask, jsonify, request
import asyncio
from mawaqit import AsyncMawaqitClient
from datetime import datetime, timedelta

app = Flask(__name__)
client = AsyncMawaqitClient()

async def fetch_prayer_data():
    mosque = await client.get_mosque(mosquee-sahaba-creteil)
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    def format_day(day):
        prayers = mosque.calendar.get(day.isoformat())
        iqamas = mosque.iqama_calendar.get(day.isoformat())

        return {
            "Fajr": {
                "time": prayers.fajr.strftime("%H:%M"),
                "iqama": iqamas.fajr.strftime("%H:%M") if iqamas.fajr else ""
            },
            "Shuruk": {
                "time": prayers.sunrise.strftime("%H:%M")
            },
            "Dhuhr": {
                "time": prayers.dhuhr.strftime("%H:%M"),
                "iqama": iqamas.dhuhr.strftime("%H:%M") if iqamas.dhuhr else ""
            },
            "Asr": {
                "time": prayers.asr.strftime("%H:%M"),
                "iqama": iqamas.asr.strftime("%H:%M") if iqamas.asr else ""
            },
            "Maghrib": {
                "time": prayers.maghrib.strftime("%H:%M"),
                "iqama": iqamas.maghrib.strftime("%H:%M") if iqamas.maghrib else ""
            },
            "Isha": {
                "time": prayers.isha.strftime("%H:%M"),
                "iqama": iqamas.isha.strftime("%H:%M") if iqamas.isha else ""
            }
        }

    return {
        "today": {
            **format_day(today),
            "hijriDate": mosque.hijri_date
        },
        "tomorrow": format_day(tomorrow),
        "jumua": mosque.jumua.strftime("%H:%M") if mosque.jumua else ""
    }

@app.route("/mawaqit-today")
def prayer_times():
    slug = request.args.get("slug", "mosquee-sahaba-creteil")
    data = asyncio.run(fetch_prayer_data(slug))
    return jsonify(data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
