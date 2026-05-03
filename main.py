"""
Job Hunter - główny skrypt
python main.py         # normalny run
python main.py --test  # test WhatsApp
python main.py --dry   # podgląd bez wysyłki
"""

import sys
import os
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database.db import init_db, is_seen, save_job, get_unsent_jobs, mark_as_sent
from scrapers.justjoin import fetch_justjoin
from scrapers.pracuj import fetch_pracuj
from scoring.scorer import score_job
from notifications.whatsapp import send_digest, send_test_message

MIN_SCORE   = int(os.getenv("MIN_SCORE", "30"))
MAX_OFFERS  = int(os.getenv("MAX_OFFERS_PER_DIGEST", "5"))
MIN_SALARY  = int(os.getenv("MIN_SALARY_B2B", "26000"))

# Tytuły które wykluczamy
EXCLUDED_TITLE_WORDS = ["lead", "manager", "head of", "director", "vp ", "principal"]

# Słowa sugerujące wysoki angielski
HIGH_ENG_WORDS   = ["c1", "c2", "fluent english", "advanced english", "native english", "excellent english", "excellent in english"]
MEDIUM_ENG_WORDS = ["b2", "good english", "strong english", "upper intermediate"]

def _check_english(job: dict) -> str:
    """Zwraca poziom angielskiego jeśli wykryty w opisie."""
    text = f"{job.get('title','')} {job.get('description','')}".lower()
    for kw in HIGH_ENG_WORDS:
        if kw in text:
            return f"UWAGA - wymagany wysoki poziom ({kw.upper()})"
    for kw in MEDIUM_ENG_WORDS:
        if kw in text:
            return f"Wymaga B2"
    return ""

def _parse_salary_min(salary_str: str) -> int:
    """Wyciąga minimalną kwotę z widełek. Zwraca 0 jeśli brak."""
    if not salary_str:
        return 0
    numbers = re.findall(r'[\d\s]+', salary_str.replace('\xa0', ' '))
    nums = []
    for n in numbers:
        clean = n.replace(' ', '').strip()
        if clean and len(clean) >= 4:
            try:
                nums.append(int(clean))
            except:
                pass
    return min(nums) if nums else 0

def _should_include(job: dict) -> tuple[bool, str]:
    """Zwraca (True/False, powód wykluczenia)."""
    title_lower = job.get("title", "").lower()

    # Wyklucz stanowiska lead/manager
    for word in EXCLUDED_TITLE_WORDS:
        if word in title_lower:
            return False, f"wykluczone stanowisko ({word})"

    # Sprawdź wynagrodzenie
    salary_str = job.get("salary", "")
    if salary_str:
        min_sal = _parse_salary_min(salary_str)
        if min_sal > 0 and min_sal < MIN_SALARY:
            return False, f"za niskie wynagrodzenie ({min_sal} < {MIN_SALARY})"

    return True, ""

def _dedup_and_score(all_jobs: list, save: bool = True) -> list:
    result = []
    seen_titles = set()

    for job in all_jobs:
        if is_seen(job["id"]):
            continue

        title_key = job["title"].replace(" NOWA", "").strip().lower()
        dedup_key = f"{title_key}|{job.get('company', '').lower()}"
        if dedup_key in seen_titles:
            continue
        seen_titles.add(dedup_key)

        include, reason = _should_include(job)
        if not include:
            print(f"   Pomijam: {job['title'][:40]} — {reason}")
            continue

        job["score"] = score_job(job)
        job["english_level"] = _check_english(job)

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
    print(f"   Lacznie: {len(all_jobs)}")

    new_jobs = _dedup_and_score(all_jobs, save=True)
    print(f"   Po filtrach: {len(new_jobs)}")

    top_jobs = get_unsent_jobs(min_score=MIN_SCORE, limit=MAX_OFFERS)

    if not top_jobs:
        print("\nBrak ofert spelniajacych kryteria.")
        return

    print(f"\nTop oferty ({len(top_jobs)}):")
    for job in top_jobs:
        eng = f" ⚠ {job.get('english_level','')}" if job.get('english_level') else ""
        print(f"   [{job['score']}%] {job['title'][:40]} – {job['company']}{eng}")

    success = send_digest(top_jobs)
    if success:
        mark_as_sent([job["id"] for job in top_jobs])
        print(f"\nWyslano {len(top_jobs)} ofert.")
    else:
        print("\nBlad wysylki.")

def dry_run():
    print("DRY RUN - scraping bez wysylki\n")
    init_db()

    all_jobs = []
    all_jobs.extend(fetch_justjoin())
    all_jobs.extend(fetch_pracuj())

    new_jobs = _dedup_and_score(all_jobs, save=False)
    new_jobs.sort(key=lambda x: x["score"], reverse=True)

    print(f"\nZnaleziono {len(new_jobs)} ofert po filtrach:\n")
    for job in new_jobs[:20]:
        eng = " [!ENG]" if job.get("english_level") else ""
        sal = f" | {job['salary']}" if job.get("salary") else ""
        print(f"  [{job['score']:3d}%] {job['title'][:40]:<40} | {job['company'][:20]:<20}{sal}{eng}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--test" in args:
        send_test_message()
    elif "--dry" in args:
        dry_run()
    else:
        run()
