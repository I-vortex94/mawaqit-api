from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from typing import List

from flask import Flask, jsonify
import os
import imaplib
import email
from email.header import decode_header
import re

import scraping.script as script
import models.models as models

router = APIRouter(prefix="/api/v1")

@router.get("/", summary="Greetings",)
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
def get_trmnl_format(masjid_id: str):
    app = Flask(__name__)
    
    EMAIL_USER = os.environ.get("EMAIL_USER")
    EMAIL_PASS = os.environ.get("EMAIL_PASS")
    
    def normalize_linebreaks(text):
        # Fusionne les sauts de ligne isolés (paragraphes artificiels)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        text = re.sub(r' {2,}', ' ', text)
        return text
    
    def clean_text(text):
        # Supprimer les étoiles
        text = text.replace('*', '')
        # Supprimer les 5 derniers \n (retours à la ligne)
        text = re.sub(r'(\n){1,5}$', '', text.strip(), flags=re.MULTILINE)
        return text
    
    def extract_parts(text):
        text = text.strip().replace('\r', '')
        lines = text.split('\n')
    
        # Supprime les lignes décoratives (ex : "**********")
        lines = [line for line in lines if not re.fullmatch(r'[*\s\-_=~#]+', line.strip())]
    
        title = lines[0].strip() if len(lines) > 0 else ""
        basmala = lines[2].strip() if len(lines) > 2 else ""
    
        content_lines = lines[3:]
        content = "\n".join(content_lines)
        content = normalize_linebreaks(content)
    
        # Supprime tout ce qui vient après certaines expressions
        truncation_keywords = [
            "Retrouvez le hadith du jour",
            "www.hadithdujour.com",
            "officielhadithdujour@gmail.com",
            "désinscription",
            "Afficher l'intégralité",
            "Message tronqué",
        ]
        for kw in truncation_keywords:
            content = content.split(kw)[0]
    
        arabic_pattern = re.compile(r'[\u0600-\u06FF]')
        content_lines = content.split('\n')
    
        arabic_start_index = None
        for i, line in enumerate(content_lines):
            if arabic_pattern.search(line):
                arabic_start_index = i
                break
    
        if arabic_start_index is not None:
            hadith_fr = "\n".join(content_lines[:arabic_start_index]).strip()
            hadith_ar = "\n".join(content_lines[arabic_start_index:]).strip()
        else:
            hadith_fr = content.strip()
            hadith_ar = ""
    
        # Nettoyage final : astérisques et fins vides
        return {
            "title": clean_text(title),
            "basmala": clean_text(basmala),
            "hadith_fr": clean_text(hadith_fr),
            "hadith_ar": clean_text(hadith_ar)
        }
    
    @app.route("/email", methods=["GET"])
    def get_latest_email():
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("inbox")
    
            status, messages = mail.search(None, "ALL")
            email_ids = messages[0].split()
            latest_email_id = email_ids[-1]
    
            status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
    
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()
    
            result = extract_parts(body)
            return jsonify(result)
    
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port)
    return script.get_trmnl_data(masjid_id)
