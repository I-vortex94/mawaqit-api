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

    # 🔁 Cache Redis
    if redisClient is not None:
        try:
            retrieved_data = redisClient.get(masjid_id)
        except RedisError:
            print("Error when reading from cache")

        if retrieved_data:
            return json.loads(retrieved_data)

    url = f"https://mawaqit.net/fr/{masjid_id}"
    r = requests.get(url)

    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')

        # 🔥 FIX IMPORTANT
        searchString = r'(?:var|let)\s+confData\s*=\s*(.*?);'
        script_tag = soup.find('script', string=re.compile(searchString, re.DOTALL))

        if not script_tag:
            raise HTTPException(status_code=500, detail="confData script not found")

        match = re.search(searchString, script_tag.string, re.DOTALL)

        if not match:
            raise HTTPException(status_code=500, detail="confData not extracted")

        conf_data = json.loads(match.group(1))

        if redisClient is not None:
            try:
                redisClient.set(masjid_id, json.dumps(conf_data), ex=WEEK_IN_SECONDS)
            except RedisError:
                print("Redis write error")

        return conf_data

    elif r.status_code == 404:
        raise HTTPException(status_code=404, detail=f"{masjid_id} not found")

    else:
        raise HTTPException(status_code=502, detail="Mawaqit request failed")


# ✅ PRAYER TIMES SAFE
def get_prayer_times_of_the_day(masjid_id):
    confData = fetch_mawaqit(masjid_id)

    if not confData:
        raise HTTPException(status_code=500, detail="No data")

    times = confData.get("times", [])
    shuruq = confData.get("shuruq")

    if len(times) < 5:
        raise HTTPException(status_code=500, detail="Invalid prayer data")

    prayer_time = models.PrayerTimes(
        fajr=times[0],
        sunrise=shuruq,
        dohr=times[1],
        asr=times[2],
        maghreb=times[3],
        icha=times[4]
    )

    return prayer_time.dict()


def get_calendar(masjid_id):
    confData = fetch_mawaqit(masjid_id)
    return confData.get("calendar", [])


def get_month(masjid_id, month_number):
    if month_number < 1 or month_number > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

    confData = fetch_mawaqit(masjid_id)
    calendar = confData.get("calendar", [])

    if not calendar:
        raise HTTPException(status_code=500, detail="Calendar missing")

    month = calendar[month_number - 1]

    return [
        models.PrayerTimes(
            fajr=p[0],
            sunrise=p[1],
            dohr=p[2],
            asr=p[3],
            maghreb=p[4],
            icha=p[5]
        )
        for p in month.values()
    ]


def get_trmnl_data(masjid_id):
    confData = fetch_mawaqit(masjid_id)

    now = datetime.now()
    today_day = str(now.day)
    tomorrow_day = str((now + timedelta(days=1)).day)
    month_index = now.month - 1

    calendar = confData.get("calendar", [])
    iqama_times = confData.get("times", [])
    jumua = confData.get("jumua", "")

    if not calendar:
        raise HTTPException(status_code=500, detail="Calendar missing")

    calendar = calendar[month_index]

    def clean(lst):
        return [h for h in lst if ":" in h]

    raw_today = clean(calendar.get(today_day, []))
    raw_tomorrow = clean(calendar.get(tomorrow_day, []))

    if len(raw_today) < 6 or len(iqama_times) < 5:
        raise HTTPException(status_code=500, detail="Invalid prayer data")

    prayers = ["fajr", "shuruk", "dohr", "asr", "maghreb", "isha"]
    iqama_labels = ["fajr", "dohr", "asr", "maghreb", "isha"]

    today = dict(zip(prayers, raw_today))
    tomorrow = dict(zip(prayers, raw_tomorrow))

    return {
        "today": {k: today.get(k, "") for k in iqama_labels},
        "tomorrow": {k: tomorrow.get(k, "") for k in iqama_labels},
        "shuruk": today.get("shuruk", ""),
        "jumua": jumua,
    }
