import requests
import urllib.parse
import os
from datetime import datetime

WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "48725405574")
WHATSAPP_APIKEY = os.getenv("WHATSAPP_APIKEY", "8153909")
CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"

def send_digest(jobs: list) -> bool:
    """Wysyła dzienny digest ofert pracy na WhatsApp."""
    if not jobs:
        print("[WhatsApp] Brak nowych ofert do wysłania.")
        return True

    message = _build_message(jobs)
    return _send_whatsapp(message)

def send_test_message() -> bool:
    """Wysyła wiadomość testową."""
    message = "✅ Job Hunter działa poprawnie! Będziesz otrzymywać codzienne podsumowania ofert pracy."
    return _send_whatsapp(message)

def _build_message(jobs: list) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    lines = [f"🔍 *Nowe oferty dla Ciebie* ({today})\n"]

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    for i, job in enumerate(jobs):
        emoji = emojis[i] if i < len(emojis) else f"{i+1}."
        score = job.get("score", 0)
        score_bar = _score_bar(score)

        lines.append(f"{emoji} *{job['title']}*")
        lines.append(f"🏢 {job['company']}")

        if job.get("salary"):
            lines.append(f"💰 {job['salary']}")

        lines.append(f"📍 {job.get('location', 'Polska')}")
        lines.append(f"⭐ Dopasowanie: {score}% {score_bar}")
        lines.append(f"🔗 {job['url']}")
        lines.append("")  # pusta linia między ofertami

    lines.append(f"📊 Źródło: {_sources_summary(jobs)}")
    lines.append("_Job Hunter 🤖_")

    return "\n".join(lines)

def _score_bar(score: int) -> str:
    filled = round(score / 20)  # 0-5 filled blocks
    return "🟩" * filled + "⬜" * (5 - filled)

def _sources_summary(jobs: list) -> str:
    sources = {}
    for job in jobs:
        src = job.get("source", "?")
        sources[src] = sources.get(src, 0) + 1
    return ", ".join(f"{src} ({count})" for src, count in sources.items())

def _send_whatsapp(message: str) -> bool:
    """Wysyła wiadomość przez CallMeBot API."""
    try:
        encoded = urllib.parse.quote(message)
        url = f"{CALLMEBOT_URL}?phone={WHATSAPP_PHONE}&text={encoded}&apikey={WHATSAPP_APIKEY}"
        response = requests.get(url, timeout=15)

        if response.status_code == 200:
            print(f"[WhatsApp] ✅ Wiadomość wysłana pomyślnie")
            return True
        else:
            print(f"[WhatsApp] ❌ Błąd: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[WhatsApp] ❌ Wyjątek: {e}")
        return False
