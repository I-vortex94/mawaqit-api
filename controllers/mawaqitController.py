from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from typing import List

import scraping.script as script
import models.models as models

from datetime import datetime
import pytz

router = APIRouter(prefix="/api/v1")


@router.get("/", summary="Greetings")
def read_root():
    return {
        "Greetings": "Hello and Welcome to this Api, this api use the mawaqit.net as data source of prayers time."
    }


@router.get("/{masjid_id}/", status_code=200, summary="get raw data")
def get_raw_data(masjid_id: str):
    try:
        r = script.fetch_mawaqit(masjid_id)
        paris_time = datetime.now(pytz.timezone("Europe/Paris")).strftime("%H:%M")

        return {
            "rawdata": r,
            "time": paris_time
        }

    except Exception as e:
        return {"error": str(e)}


@router.get("/{masjid_id}/prayer-times", response_model=models.PrayerTimes)
def get_prayer_times(masjid_id: str):
    try:
        return script.get_prayer_times_of_the_day(masjid_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/{masjid_id}/calendar")
def get_year_calendar(masjid_id: str):
    try:
        r = script.get_calendar(masjid_id)
        return {"calendar": r}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{masjid_id}/calendar/{month_number}", response_model=List[models.PrayerTimes])
def get_month_calendar(masjid_id: str, month_number: int):
    try:
        month_dict = script.get_month(masjid_id, month_number)
        return jsonable_encoder(month_dict)
    except Exception as e:
        return {"error": str(e)}


@router.get("/{masjid_id}/trmnl")
def get_trmnl_format(masjid_id: str):
    try:
        return script.get_trmnl_data(masjid_id)
    except Exception as e:
        return {"error": str(e)}
