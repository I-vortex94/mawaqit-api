import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException
from config.redisClient import redisClient
from redis.exceptions import RedisError
from datetime import datetime, timedelta

import json
import re
import models.models as models

def fetch_mawaqit(masjid_id: str):
    WEEK_IN_SECONDS = 604800
    retrieved_data = None

    # Check if Redis client is initialized
    if redisClient is not None:
        try:
            retrieved_data = redisClient.get(masjid_id)
        except RedisError:
            print("Error when reading from cache")

        if retrieved_data:
            return json.loads(retrieved_data)

    r = requests.get(f"https://mawaqit.net/fr/{masjid_id}")
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        script = soup.find('script', string=re.compile(r'var confData = (.*?);', re.DOTALL))
        if script:
            mawaqit = re.search(r'var confData = (.*?);', script.string, re.DOTALL)
            if mawaqit:
                conf_data_json = mawaqit.group(1)
                conf_data = json.loads(conf_data_json)
                # Store data in Redis if client is initialized
                if redisClient is not None:
                    redisClient.set(masjid_id, json.dumps(conf_data), ex=WEEK_IN_SECONDS)
                return conf_data
            else:
                raise HTTPException(status_code=500, detail=f"Failed to extract confData JSON for {masjid_id}")
        else:
            print("Script containing confData not found.")
            raise HTTPException(status_code=500, detail=f"Script containing confData not found for {masjid_id}")
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail=f"{masjid_id} not found")


# Ajout : Heure actuelle (HH:MM)
time = datetime.now().strftime("%H:%M")


def get_prayer_times_of_the_day(masjid_id):
    confData = fetch_mawaqit(masjid_id)
    times = confData["times"]
    sunset = confData["shuruq"]
    prayer_time = models.PrayerTimes(fajr=times[0], sunset=sunset, dohr=times[1], asr=times[2], maghreb=times[3], icha=times[4])
    prayer_dict = prayer_time.dict()
    return prayer_dict

def get_calendar(masjid_id):
    confData = fetch_mawaqit(masjid_id)
    return confData["calendar"]

def get_month(masjid_id, month_number):
    if month_number < 1 or month_number > 12:
        raise HTTPException(status_code=400, detail=f"Month number should be between 1 and 12")
    confData = fetch_mawaqit(masjid_id)
    month = confData["calendar"][month_number - 1]
    prayer_times_list = [
        models.PrayerTimes( 
            fajr=prayer[0],
            sunset=prayer[1],
            dohr=prayer[2],
            asr=prayer[3],
            maghreb=prayer[4],
            icha=prayer[5]
        )
        for prayer in month.values()
    ]
    return prayer_times_list

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

    # === utilitaire : nettoyer les listes ===
    def clean(prayer_list):
        return [h for h in prayer_list if ":" in h]

    raw_today = clean(calendar.get(today_day, []))
    raw_tomorrow = clean(calendar.get(tomorrow_day, []))

    if len(raw_today) < 6 or len(iqama_times) < 5:
        raise HTTPException(status_code=500, detail="Données de prière insuffisantes ou mal formées.")

    prayers = ["fajr", "shuruk", "dohr", "asr", "maghreb", "isha"]
    iqama_labels = ["fajr", "dohr", "asr", "maghreb", "isha"]

    # assignation correcte
    today = dict(zip(prayers, raw_today))
    tomorrow = dict(zip(prayers, raw_tomorrow))


    return {
        "today": {k: today[k] for k in iqama_labels},
        "tomorrow": {k: tomorrow.get(k, "") for k in iqama_labels},
        "shuruk": today.get("shuruk", ""),
        "jumua": jumua,
    }
