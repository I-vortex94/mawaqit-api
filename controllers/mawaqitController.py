from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from typing import List
import scraping.script as script
import models.models as models

router = APIRouter(prefix="/api/v1")

@router.get("/")
def read_root():
    return {
        "Greetings": "This API uses mawaqit.net as a data source for prayer times. See /docs for usage."
    }

@router.get("/{masjid_id}/")
def get_raw_data(masjid_id: str):
    return {"rawdata": script.fetch_mawaqit(masjid_id)}

@router.get("/{masjid_id}/prayer-times", response_model=models.PrayerTimes)
def get_prayer_times(masjid_id: str):
    return script.get_prayer_times_of_the_day(masjid_id)

@router.get("/{masjid_id}/calendar")
def get_year_calendar(masjid_id: str):
    return {"calendar": script.get_calendar(masjid_id)}

@router.get("/{masjid_id}/calendar/{month_number}", response_model=List[models.PrayerTimes])
def get_month_calendar(masjid_id: str, month_number: int):
    return jsonable_encoder(script.get_month(masjid_id, month_number))

@router.get("/{masjid_id}/trmnl")
def get_trmnl_format(masjid_id: str):
    return script.get_trmnl_data(masjid_id)
