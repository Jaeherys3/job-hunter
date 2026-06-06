import requests
import urllib.parse
import os
import time
from datetime import datetime

WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "48725405574")
WHATSAPP_APIKEY = os.getenv("WHATSAPP_APIKEY", "8153909")
CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"

# CallMeBot ma limit ~1600 znakow na wiadomosc
MAX_MSG_LEN = 1550

# CallMeBot throttluje zbyt szybkie zadania (stad 403 przy wysylce seriami).
# Odstep miedzy wiadomosciami i pauza przed ponowieniem - konfigurowalne w .env.
SEND_DELAY = float(os.getenv("WHATSAPP_SEND_DELAY", "5"))
RETRY_DELAY = float(os.getenv("WHATSAPP_RETRY_DELAY", "8"))
MAX_RETRIES = int(os.getenv("WHATSAPP_MAX_RETRIES", "2"))


def send_digest(jobs: list) -> list:
    """
    Wysyla naglowek + po jednej ofercie. Zwraca liste ID ofert, ktore
    FAKTYCZNIE sie wyslaly (tylko te oznaczamy potem jako wyslane).
    """
    if not jobs:
        print("[WhatsApp] Brak nowych ofert do wyslania.")
        return []

    today = datetime.now().strftime("%d.%m.%Y")
    header = f"Nowe oferty ({today}) - {len(jobs)} dopasowanych:"
    _send_whatsapp(header)

    sent_ids = []
    for i, job in enumerate(jobs):
        time.sleep(SEND_DELAY)  # odstep zeby nie wpasc w limit CallMeBot
        msg = _build_single(job, i + 1)
        if _send_whatsapp(msg):
            sent_ids.append(job["id"])

    return sent_ids


def send_test_message() -> bool:
    return _send_whatsapp("Job Hunter dziala! Bedziesz dostawac codzienne oferty pracy.")


def _build_single(job: dict, num: int) -> str:
    score = job.get("score", 0)
    lines = []
    lines.append(f"{num}. {job['title']}")
    lines.append(f"Firma: {job.get('company', '?')}")
    lines.append(f"Miejsce: {job.get('location', 'Polska')}")

    if job.get("salary"):
        lines.append(f"Kasa: {job['salary']}")

    lines.append(f"Dopasowanie: {score}%")

    eng = job.get("english_level", "")
    if eng:
        lines.append(f"Angielski: {eng}")

    lines.append(job.get("url", ""))
    return "\n".join(lines)


def _send_whatsapp(message: str) -> bool:
    encoded = urllib.parse.quote(message)
    url = f"{CALLMEBOT_URL}?phone={WHATSAPP_PHONE}&text={encoded}&apikey={WHATSAPP_APIKEY}"

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                print(f"[WhatsApp] Wyslano: {message[:50]}...")
                return True
            print(f"[WhatsApp] Blad: {response.status_code} "
                  f"(proba {attempt + 1}/{MAX_RETRIES + 1})")
        except Exception as e:
            print(f"[WhatsApp] Wyjatek: {e} (proba {attempt + 1}/{MAX_RETRIES + 1})")

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)  # odczekaj i sprobuj ponownie (throttle 403)

    return False
