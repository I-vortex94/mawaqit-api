# email_utils.py

import os
import imaplib
import email
from email.header import decode_header
import re

EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

def normalize_linebreaks(text):
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text

def clean_text(text):
    text = text.replace('*', '')
    text = re.sub(r'(\n){1,5}$', '', text.strip(), flags=re.MULTILINE)
    return text

def extract_parts(text):
    text = text.strip().replace('\r', '')
    lines = text.split('\n')
    lines = [line for line in lines if not re.fullmatch(r'[*\s\-_=~#]+', line.strip())]

    title = lines[0].strip() if len(lines) > 0 else ""
    basmala = lines[2].strip() if len(lines) > 2 else ""

    content_lines = lines[3:]
    content = "\n".join(content_lines)
    content = normalize_linebreaks(content)

    truncation_keywords = [
        "Retrouvez le hadith du jour", "www.hadithdujour.com", "officielhadithdujour@gmail.com",
        "désinscription", "Afficher l'intégralité", "Message tronqué",
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

    return {
        "title": clean_text(title),
        "basmala": clean_text(basmala),
        "hadith_fr": clean_text(hadith_fr),
        "hadith_ar": clean_text(hadith_ar)
    }

def get_latest_email_parts():
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

        return extract_parts(body)

    except Exception as e:
        return {"error": str(e)}
