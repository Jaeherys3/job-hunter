import requests
import urllib.parse
import os
from datetime import datetime

WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "48725405574")
WHATSAPP_APIKEY = os.getenv("WHATSAPP_APIKEY", "8153909")
CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"

# CallMeBot ma limit ~1600 znaków na wiadomość
MAX_MSG_LEN = 1550

def send_digest(jobs: list) -> bool:
    if not jobs:
        print("[WhatsApp] Brak nowych ofert do wysłania.")
        return True
    # Wysyłaj po jednej ofercie żeby uniknąć ucinania
    today = datetime.now().strftime("%d.%m.%Y")
    header = f"Nowe oferty ({today}) - {len(jobs)} dopasowanych:"
    _send_whatsapp(header)

    for i, job in enumerate(jobs):
        msg = _build_single(job, i + 1)
        _send_whatsapp(msg)

    return True

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

    # Ostrzeżenie o angielskim
    eng = job.get("english_level", "")
    if eng:
        lines.append(f"Angielski: {eng}")

    lines.append(job.get("url", ""))
    return "\n".join(lines)

def _send_whatsapp(message: str) -> bool:
    try:
        encoded = urllib.parse.quote(message)
        url = f"{CALLMEBOT_URL}?phone={WHATSAPP_PHONE}&text={encoded}&apikey={WHATSAPP_APIKEY}"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            print(f"[WhatsApp] Wyslano: {message[:50]}...")
            return True
        else:
            print(f"[WhatsApp] Blad: {response.status_code}")
            return False
    except Exception as e:
        print(f"[WhatsApp] Wyjatek: {e}")
        return False
