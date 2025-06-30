import os
import re
import json
import email
import imaplib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from fastapi import HTTPException
from redis.exceptions import RedisError

from config.redisClient import redisClient
import models.models as models

# === MAWAQIT UTIL ===
def fetch_mawaqit(masjid_id: str):
    WEEK_IN_SECONDS = 604800
    if redisClient:
        try:
            cached = redisClient.get(masjid_id)
            if cached:
                return json.loads(cached)
        except RedisError:
            pass

    r = requests.get(f"https://mawaqit.net/fr/{masjid_id}")
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        script = soup.find('script', string=re.compile(r'var confData = (.*?);', re.DOTALL))
        if script:
            match = re.search(r'var confData = (.*?);', script.string, re.DOTALL)
            if match:
                conf_data = json.loads(match.group(1))
                if redisClient:
                    redisClient.set(masjid_id, json.dumps(conf_data), ex=WEEK_IN_SECONDS)
                return conf_data
        raise HTTPException(status_code=500, detail=f"Données confData introuvables pour {masjid_id}")
    raise HTTPException(status_code=r.status_code, detail=f"Erreur HTTP {r.status_code} pour {masjid_id}")

# === EMAIL UTIL ===
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

def normalize_linebreaks(text):
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text

def clean_text(text):
    text = text.replace('*', '')
    return re.sub(r'(\n){1,5}$', '', text.strip(), flags=re.MULTILINE)

def extract_parts(text):
    lines = [line for line in text.strip().replace('\r', '').split('\n')
             if not re.fullmatch(r'[*\s\-_=~#]+', line.strip())]

    title = lines[0].strip() if lines else ""
    basmala = lines[2].strip() if len(lines) > 2 else ""
    content_lines = lines[3:]
    content = normalize_linebreaks("\n".join(content_lines))

    for kw in ["Retrouvez", "www.hadithdujour.com", "gmail.com", "désinscription"]:
        content = content.split(kw)[0]

    arabic_index = next((i for i, l in enumerate(content.split('\n'))
                         if re.search(r'[\u0600-\u06FF]', l)), None)

    if arabic_index is not None:
        lines = content.split('\n')
        hadith_fr = "\n".join(lines[:arabic_index]).strip()
        hadith_ar = "\n".join(lines[arabic_index:]).strip()
    else:
        hadith_fr, hadith_ar = content.strip(), ""

    return {
        "title": clean_text(title),
        "basmala": clean_text(basmala),
        "hadith_fr": clean_text(hadith_fr),
        "hadith_ar": clean_text(hadith_ar)
    }

def get_email_hadith():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        _, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()
        latest = email_ids[-1]
        _, data = mail.fetch(latest, "(RFC822)")
        raw = data[0][1]
        msg = email.message_from_bytes(raw)

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        return extract_parts(body)

    except Exception:
        return {"title": "", "basmala": "", "hadith_fr": "", "hadith_ar": ""}

def get_trmnl_data(masjid_id):
    confData = fetch_mawaqit(masjid_id)
    now = datetime.now()
    today = str(now.day)
    tomorrow = str((now + timedelta(days=1)).day)
    month_index = now.month - 1

    calendar = confData["calendar"][month_index]
    raw_today = [h for h in calendar.get(today, []) if ":" in h]
    raw_tomorrow = [h for h in calendar.get(tomorrow, []) if ":" in h]
    shuruk = confData.get("shuruq", "")
    jumua = confData.get("jumua", "")

    prayers = ["fajr", "shuruk", "dohr", "asr", "maghreb", "isha"]
    labels = ["fajr", "dohr", "asr", "maghreb", "isha"]
    today_dict = dict(zip(prayers, raw_today))
    tomorrow_dict = dict(zip(prayers, raw_tomorrow))

    hadith = get_email_hadith()

    return {
        "today": {k: today_dict.get(k, "") for k in labels},
        "tomorrow": {k: tomorrow_dict.get(k, "") for k in labels},
        "shuruk": today_dict.get("shuruk", shuruk),
        "jumua": jumua,
        "basmala": hadith.get("basmala", ""),
        "title": hadith.get("title", ""),
        "hadith_fr": hadith.get("hadith_fr", ""),
        "hadith_ar": hadith.get("hadith_ar", "")
    }
