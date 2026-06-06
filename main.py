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
from scoring.english import assess_english, english_label, ENGLISH_HIGH, required_languages_outside
from scrapers.detail import enrich_jobs


FILTER_HIGH_ENGLISH = os.getenv("FILTER_HIGH_ENGLISH", "1") == "1"

# Twoje jezyki - oferta wymagajaca jezyka spoza tej listy zostanie odrzucona.
KNOWN_LANGUAGES = {
    c.strip().lower()
    for c in os.getenv("KNOWN_LANGUAGES", "pl,en,ru").split(",")
    if c.strip()
}
FILTER_FOREIGN_LANG = os.getenv("FILTER_FOREIGN_LANG", "1") == "1"

MIN_SCORE   = int(os.getenv("MIN_SCORE", "30"))
MAX_OFFERS  = int(os.getenv("MAX_OFFERS_PER_DIGEST", "5"))
MIN_SALARY_PLN = int(os.getenv("MIN_SALARY_B2B", "26000"))

EXCLUDED_TITLE_WORDS = ["manager", "head of", "director", "vp ", "team leader", "principal"]
EXCLUDED_EXACT = ["lead data engineer", "engineering lead", "tech lead", "data lead", "lead data scientist", "lead data analyst", "lead machine learning"]


def _parse_salary(salary_str: str) -> tuple:
    """Zwraca (min, max, currency). Obsługuje PLN/h, PLN/mies, USD."""
    if not salary_str:
        return 0, 0, ""
    text = salary_str.upper()
    currency = "USD" if "USD" in text else ("EUR" if "EUR" in text else "PLN")
    cleaned = salary_str.replace('\xa0', '').replace(' ', '').replace('\u00a0', '')
    numbers = re.findall(r'\d+', cleaned)
    nums = [int(n) for n in numbers if len(n) >= 2]
    if not nums:
        return 0, 0, currency
    is_hourly = "/h" in salary_str.lower() or "/godz" in salary_str.lower()
    if is_hourly:
        nums = [n * 168 for n in nums]
    return min(nums), max(nums), currency

def _should_include(job: dict) -> tuple:
    title_lower = job.get("title", "").lower()

    for word in EXCLUDED_TITLE_WORDS:
        if word in title_lower:
            return False, f"stanowisko zarzadcze ({word})"

    for exact in EXCLUDED_EXACT:
        if exact in title_lower:
            return False, f"stanowisko lead ({exact})"

    salary_str = job.get("salary", "")
    if salary_str:
        sal_min, sal_max, currency = _parse_salary(salary_str)
        if sal_max > 0:
            # Górne widełki muszą być >= MIN_SALARY_PLN
            if currency == "PLN" and sal_max < MIN_SALARY_PLN:
                return False, f"gorny prog za niski ({sal_max} PLN < {MIN_SALARY_PLN})"
            elif currency == "USD" and sal_max < 6500:
                return False, f"gorny prog za niski ({sal_max} USD)"

    return True, ""

def _dedup_and_score(all_jobs: list, save: bool = True, verbose: bool = False) -> list:
    seen_titles = set()
    candidates = []

    # Faza 1: tanie filtry (juz-widziane, dedup, tytul, widelki)
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
            if verbose:
                print(f"   [-] {job['title'][:40]:<40} | {job.get('salary',''):<20} | {reason}")
            continue

        candidates.append(job)

    # Faza 2: dociagniecie pelnego detalu TYLKO dla kandydatow (po taniejszych filtrach)
    if candidates:
        if verbose:
            print(f"   Dociagam detal dla {len(candidates)} ofert...")
        enrich_jobs(candidates, verbose=verbose)

    # Faza 3: scoring + filtr angielskiego na wzbogaconym tekscie
    result = []
    for job in candidates:
        # Filtr jezykow obcych (wymagany jezyk spoza Twojej listy znanych)
        if FILTER_FOREIGN_LANG:
            foreign = required_languages_outside(job.get("languages"), KNOWN_LANGUAGES)
            if foreign:
                if verbose:
                    print(f"   [-] {job['title'][:40]:<40} | wymaga jezyka: {','.join(c.upper() for c in foreign)}")
                continue

        job["score"] = score_job(job)
        eng_level, eng_match = assess_english(
            job.get("languages"),
            job.get("title", ""), job.get("description", ""), job.get("detail_text", "")
        )
        if FILTER_HIGH_ENGLISH and eng_level == ENGLISH_HIGH:
            if verbose:
                print(f"   [-] {job['title'][:40]:<40} | angielski {eng_match.upper()}")
            continue
        job["english_level"] = english_label(eng_level, eng_match)

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

    new_jobs = _dedup_and_score(all_jobs, save=True, verbose=True)
    print(f"   Po filtrach: {len(new_jobs)}")

    top_jobs = get_unsent_jobs(min_score=MIN_SCORE, limit=MAX_OFFERS)

    if not top_jobs:
        print("\nBrak ofert spelniajacych kryteria.")
        return

    print(f"\nTop oferty ({len(top_jobs)}):")
    for job in top_jobs:
        eng = f" !! {job.get('english_level','')}" if job.get('english_level') else ""
        print(f"   [{job['score']}%] {job['title'][:40]} - {job['company']}{eng}")

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

    print("\n--- Odrzucone ---")
    new_jobs = _dedup_and_score(all_jobs, save=False, verbose=True)
    new_jobs.sort(key=lambda x: x["score"], reverse=True)

    print(f"\n--- Przyjete: {len(new_jobs)} ofert ---\n")
    for job in new_jobs[:20]:
        eng = " [!ENG]" if job.get("english_level") else ""
        sal = f" | {job['salary']}" if job.get("salary") else " | brak widelek"
        print(f"  [{job['score']:3d}%] {job['title'][:40]:<40} | {job['company'][:20]:<20}{sal}{eng}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--test" in args:
        send_test_message()
    elif "--dry" in args:
        dry_run()
    else:
        run()
