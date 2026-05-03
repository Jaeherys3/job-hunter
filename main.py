"""
Job Hunter - główny skrypt
Uruchamiaj ręcznie lub przez Windows Task Scheduler.

Użycie:
    python main.py          # normalny run (scraping + digest)
    python main.py --test   # wyślij wiadomość testową na WhatsApp
    python main.py --dry    # scraping bez wysyłki (podgląd ofert)
"""

import sys
import os
from dotenv import load_dotenv

# Ładuj .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database.db import init_db, is_seen, save_job, get_unsent_jobs, mark_as_sent
from scrapers.justjoin import fetch_justjoin
from scrapers.pracuj import fetch_pracuj
from scoring.scorer import score_job
from notifications.whatsapp import send_digest, send_test_message

MIN_SCORE = int(os.getenv("MIN_SCORE", "50"))
MAX_OFFERS = int(os.getenv("MAX_OFFERS_PER_DIGEST", "5"))

def run():
    print("=" * 50)
    print("🚀 Job Hunter startuje...")
    print("=" * 50)

    # 1. Inicjalizacja bazy
    init_db()

    # 2. Scraping
    print("\n📡 Scrapuję oferty...")
    all_jobs = []
    all_jobs.extend(fetch_justjoin())
    all_jobs.extend(fetch_pracuj())
    print(f"   Łącznie pobrano: {len(all_jobs)} ofert")

    # 3. Filtruj już widziane + scoruj nowe
    new_jobs = []
    for job in all_jobs:
        if is_seen(job["id"]):
            continue
        job["score"] = score_job(job)
        save_job(job)
        new_jobs.append(job)

    print(f"   Nowych ofert: {len(new_jobs)}")

    # 4. Pobierz top oferty do wysłania
    top_jobs = get_unsent_jobs(min_score=MIN_SCORE, limit=MAX_OFFERS)

    if not top_jobs:
        print("\n📭 Brak nowych ofert spełniających kryteria. Digest nie zostanie wysłany.")
        return

    print(f"\n📋 Top oferty do wysłania ({len(top_jobs)}):")
    for job in top_jobs:
        print(f"   [{job['score']}%] {job['title']} – {job['company']} ({job['source']})")

    # 5. Wyślij digest
    print("\n📲 Wysyłam digest na WhatsApp...")
    success = send_digest(top_jobs)

    if success:
        mark_as_sent([job["id"] for job in top_jobs])
        print(f"\n✅ Gotowe! Wysłano {len(top_jobs)} ofert.")
    else:
        print("\n❌ Błąd wysyłki. Oferty NIE zostały oznaczone jako wysłane (spróbują jutro).")

def dry_run():
    print("🔍 DRY RUN - scraping bez wysyłki\n")
    init_db()

    all_jobs = []
    all_jobs.extend(fetch_justjoin())
    all_jobs.extend(fetch_pracuj())

    new_jobs = []
    for job in all_jobs:
        if not is_seen(job["id"]):
            job["score"] = score_job(job)
            new_jobs.append(job)

    new_jobs.sort(key=lambda x: x["score"], reverse=True)

    print(f"\nZnaleziono {len(new_jobs)} nowych ofert:\n")
    for job in new_jobs[:20]:
        print(f"  [{job['score']:3d}%] {job['title'][:45]:<45} | {job['company'][:25]:<25} | {job['source']}")

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        print("📲 Wysyłam wiadomość testową...")
        send_test_message()
    elif "--dry" in args:
        dry_run()
    else:
        run()
