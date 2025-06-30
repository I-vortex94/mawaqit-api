import requests
from bs4 import BeautifulSoup
from fastapi import HTTPException
from config.redisClient import redisClient
from redis.exceptions import RedisError
from datetime import datetime, timedelta
import os
import imaplib
import email
import re
import json
import models.models as models


EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")


def fetch_mawaqit(masjid_id: str):
    WEEK_IN_SECONDS = 604800

    if redisClient:
        try:
            cached = redisClient.get(masjid_id)
            if cached:
                return json.loads(cached)
        except RedisError:
            print("Redis read error")

    r = requests.get(f"https://mawaqit.net/fr/{masjid_id}")
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        script_tag = soup.find('script', string=re.compile(r'var confData = (.*?);', re.DOTALL))
        if script_tag:
            match = re.search(r'var confData = (.*?);', script_tag.string, re.DOTALL)
            if match:
                conf_data = json.loads(match.group(1))
                if redisClient:
                    redisClient.set(masjid_id, json.dumps(conf_data), ex=WEEK_IN_SECONDS)
                return conf_data
        raise HTTPException(500, f"confData not found for {masjid_id}")
    raise HTTPException(r.status_code, f"HTTP error {r.status_code} for {masjid_id}")


def clean_text(text):
    text = text.replace('*', '')
    text = re.sub(r'(\n){1,5}$', '', text.strip(), flags=re.MULTILINE)
    return text

def normalize_linebreaks(text):
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return re.sub(r' {2,}', ' ', text)

def extract_parts(text):
    text = text.strip().replace('\r', '')
    lines = text.split('\n')
    lines = [line for line in lines if not re.fullmatch(r'[*\s\-_=~#]+', line.strip())]
    title = lines[0].strip() if len(lines) > 0 else ""
    basmala = lines[2].strip() if len(lines) > 2 else ""
    content = normalize_linebreaks("\n".join(lines[3:]))

    for kw in [
        "Retrouvez le hadith du jour", "www.hadithdujour.com",
        "officielhadithdujour@gmail.com", "désinscription",
        "Afficher l'intégralité", "Message tronqué",
    ]:
        content = content.split(kw)[0]

    lines = content.split('\n')
    arabic_index = next((i for i, l in enumerate(lines) if re.search(r'[\u0600-\u06FF]', l)), None)
    if arabic_index is not None:
        hadith_fr = "\n".join(lines[:arabic_index]).strip()
        hadith_ar = "\n".join(lines[arabic_index:]).strip()
    else:
        hadith_fr = content.strip()
        hadith_ar = ""

    return {
        "title": clean_text(title),
        "basmala": clean_text(basmala),
        "hadith_fr": clean_text(hadith_fr),
        "hadith_ar": clean_text(hadith_ar)
    }

def get_latest_email_hadith():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        _, messages = mail.search(None, "ALL")
        latest = messages[0].split()[-1]
        _, msg_data = mail.fetch(latest, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return extract_parts(part.get_payload(decode=True).decode())
        return extract_parts(msg.get_payload(decode=True).decode())
    except Exception as e:
        return {
            "title": "",
            "basmala": "",
            "hadith_fr": "",
            "hadith_ar": "",
            "error": str(e)
        }

def get_trmnl_data(masjid_id: str):
    conf = fetch_mawaqit(masjid_id)
    now = datetime.now()
    today_str = str(now.day)
    tomorrow_str = str((now + timedelta(days=1)).day)
    month = conf["calendar"][now.month - 1]

    def clean(prayers): return [x for x in prayers if ":" in x]
    today = dict(zip(
        ["fajr", "shuruk", "dohr", "asr", "maghreb", "isha"],
        clean(month.get(today_str, []))
    ))
    tomorrow = dict(zip(
        ["fajr", "shuruk", "dohr", "asr", "maghreb", "isha"],
        clean(month.get(tomorrow_str, []))
    ))

    hadith = get_latest_email_hadith()

    return {
        "today": {k: today.get(k, "") for k in ["fajr", "dohr", "asr", "maghreb", "isha"]},
        "tomorrow": {k: tomorrow.get(k, "") for k in ["fajr", "dohr", "asr", "maghreb", "isha"]},
        "shuruk": today.get("shuruk", ""),
        "jumua": conf.get("jumua", ""),
        "basmala": hadith.get("basmala", ""),
        "title": hadith.get("title", ""),
        "hadith_fr": hadith.get("hadith_fr", ""),
        "hadith_ar": hadith.get("hadith_ar", "")
    }
