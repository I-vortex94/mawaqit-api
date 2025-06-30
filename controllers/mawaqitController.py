from datetime import datetime, timedelta
from fastapi import HTTPException

from scraping.script import fetch_mawaqit, get_email_hadith  # 🔁 bien importer

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
