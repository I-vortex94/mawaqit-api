from fastapi import FastAPI, HTTPException
import asyncio
from mawaqit import AsyncMawaqitClient
from datetime import date, timedelta

app = FastAPI()

@app.get("/mawaqit-today")
async def mawaqit_today(slug: str = "mosquee-sahaba-creteil"):
    client = AsyncMawaqitClient()
    await client.get_api_token()
    mosques = await client.fetch_mosques_by_keyword(slug)
    if not mosques:
        raise HTTPException(status_code=404, detail="Mosquée introuvable")
    client.mosque = mosques[0]["uuid"]
    data = await client.fetch_prayer_times()
    await client.close()

    # Transforme le calendrier en structure souhaitée
    today = date.today()
    tomorrow = today + timedelta(days=1)
    def fmt(day):
        cal = data["calendar"].get(day.isoformat(), {})
        iq = data["iqama_calendar"].get(day.isoformat(), {})
        return {
            "time": cal.get("time", ""),
            "iqama": iq.get("time", "")
        }
    return {
        "today": {
            "hijriDate": data.get("hijriDate", ""),
            "Fajr": fmt(today).get("Fajr", {}),
            "Shuruk": fmt(today).get("Shuruk", {}),
            "Dhuhr": fmt(today).get("Dhuhr", {}),
            "Asr": fmt(today).get("Asr", {}),
            "Maghrib": fmt(today).get("Maghrib", {}),
            "Isha": fmt(today).get("Isha", {})
        },
        "tomorrow": {
            "Fajr": fmt(tomorrow).get("Fajr", {}),
            "Shuruk": fmt(tomorrow).get("Shuruk", {}),
            "Dhuhr": fmt(tomorrow).get("Dhuhr", {}),
            "Asr": fmt(tomorrow).get("Asr", {}),
            "Maghrib": fmt(tomorrow).get("Maghrib", {}),
            "Isha": fmt(tomorrow).get("Isha", {})
        },
        "jumua": data.get("jumua", "")
    }
