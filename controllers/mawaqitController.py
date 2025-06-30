# controllers/mawaqitController.py
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta
from typing import List

import scraping.script as script
from scraping.script import fetch_mawaqit, get_email_hadith
import models.models as models

router = APIRouter(prefix="/api/v1")

@router.get("/", summary="Greetings")
def read_root():
    return {"Greetings": "Hello and Welcome to this Api, this api use the mawaqit.net as data source of prayers time in more than 8000 masjid, this api can be used to fetch data in json, you can find our docs on /docs. "}

@router.get("/{masjid_id}/", status_code=200, summary="get the raw data from mawaqit website")
def get_raw_data(masjid_id: str):
    r = script.fetch_mawaqit(masjid_id)
    return {"rawdata": r}

@router.get("/{masjid_id}/prayer-times", status_code=200, summary="get the prayer times of the current day", response_model=models.PrayerTimes)
def get_prayer_times(masjid_id: str):
    prayer_times = script.get_prayer_times_of_the_day(masjid_id)
    return prayer_times

@router.get("/{masjid_id}/calendar", status_code=200, summary="get the year calendar of the prayer times")
def get_year_calendar(masjid_id: str):
    r = script.get_calendar(masjid_id)
    return {"calendar": r}

@router.get("/{masjid_id}/calendar/{month_number}", status_code=200, summary="get the month calendar of the prayer times", response_model=List[models.PrayerTimes])
def get_month_calendar(masjid_id: str, month_number: int):
    month_dict = script.get_month(masjid_id, month_number)
    return jsonable_encoder(month_dict)

@router.get("/{masjid_id}/trmnl", summary="Formatted data for TRMNL")
def get_trmnl_data(masjid_id):
    confData = fetch_mawaqit(masjid_id)

    now = datetime.now()
    today_day = str(now.day)
    tomorrow_day = str((now + timedelta(days=1)).day)
    month_index = now.month - 1

    calendar = confData["calendar"][month_index]
    iqama_times = confData["times"]
    shuruk = confData.get("shuruq", "")
    jumua = confData.get("jumua", "")

    def clean(prayer_list):
        return [h for h in prayer_list if ":" in h]

    raw_today = clean(calendar.get(today_day, []))
    raw_tomorrow = clean(calendar.get(tomorrow_day, []))

    if len(raw_today) < 6 or len(iqama_times) < 5:
        raise HTTPException(status_code=500, detail="Données de prière insuffisantes ou mal formées.")

    prayers = ["fajr", "shuruk", "dohr", "asr", "maghreb", "isha"]
    iqama_labels = ["fajr", "dohr", "asr", "maghreb", "isha"]

    today = dict(zip(prayers, raw_today))
    tomorrow = dict(zip(prayers, raw_tomorrow))

    hadith = get_email_hadith()

    return {
        "today": {k: today[k] for k in iqama_labels},
        "tomorrow": {k: tomorrow.get(k, "") for k in iqama_labels},
        "shuruk": today.get("shuruk", ""),
        "jumua": jumua,
        "basmala": hadith.get("basmala", ""),
        "title": hadith.get("title", ""),
        "hadith_fr": hadith.get("hadith_fr", ""),
        "hadith_ar": hadith.get("hadith_ar", "")
    }
