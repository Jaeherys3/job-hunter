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

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database.db import init_db, is_seen, save_job, get_unsent_jobs, mark_as_sent
from scrapers.justjoin import fetch_justjoin
from scrapers.pracuj import fetch_pracuj
from scoring.scorer import score_job
from notifications.whatsapp import send_digest, send_test_message

MIN_SCORE = int(os.getenv("MIN_SCORE", "30"))
MAX_OFFERS = int(os.getenv("MAX_OFFERS_PER_DIGEST", "5"))

def _dedup_and_score(all_jobs: list, save: bool = True) -> list:
    """Deduplikuje oferty i oblicza score. Opcjonalnie zapisuje do DB."""
    result = []
    seen_db = set()
    seen_titles = set()

    for job in all_jobs:
        if is_seen(job["id"]):
            continue
        # Deduplikacja po tytule+firma (usuwa warianty "NOWA")
        title_key = job["title"].replace(" NOWA", "").strip().lower()
        dedup_key = f"{title_key}|{job.get('company', '').lower()}"
        if dedup_key in seen_titles:
            continue
        seen_titles.add(dedup_key)

        job["score"] = score_job(job)
        if save:
            save_job(job)
        result.append(job)

    return result

def run():
    print("=" * 50)
    print("Job Hunter startuje...")
    print("=" * 50)

    init_db()

    print("\nScrapuje oferty...")
    all_jobs = []
    all_jobs.extend(fetch_justjoin())
    all_jobs.extend(fetch_pracuj())
    print(f"   Lacznie pobrano: {len(all_jobs)} ofert")

    new_jobs = _dedup_and_score(all_jobs, save=True)
    print(f"   Nowych ofert: {len(new_jobs)}")

    top_jobs = get_unsent_jobs(min_score=MIN_SCORE, limit=MAX_OFFERS)

    if not top_jobs:
        print("\nBrak nowych ofert spelniajacych kryteria. Digest nie zostanie wyslany.")
        return

    print(f"\nTop oferty do wyslania ({len(top_jobs)}):")
    for job in top_jobs:
        print(f"   [{job['score']}%] {job['title']} - {job['company']} ({job['source']})")

    print("\nWysylam digest na WhatsApp...")
    success = send_digest(top_jobs)

    if success:
        mark_as_sent([job["id"] for job in top_jobs])
        print(f"\nGotowe! Wyslano {len(top_jobs)} ofert.")
    else:
        print("\nBlad wysylki. Oferty NIE zostaly oznaczone jako wyslane.")

def dry_run():
    print("DRY RUN - scraping bez wysylki\n")
    init_db()

    all_jobs = []
    all_jobs.extend(fetch_justjoin())
    all_jobs.extend(fetch_pracuj())

    new_jobs = _dedup_and_score(all_jobs, save=False)
    new_jobs.sort(key=lambda x: x["score"], reverse=True)

    print(f"\nZnaleziono {len(new_jobs)} nowych ofert:\n")
    for job in new_jobs[:20]:
        print(f"  [{job['score']:3d}%] {job['title'][:45]:<45} | {job['company'][:25]:<25} | {job['source']}")

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        print("Wysylam wiadomosc testowa...")
        send_test_message()
    elif "--dry" in args:
        dry_run()
    else:
        run()
