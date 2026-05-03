import time
import json
import re
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark"]

def fetch_justjoin() -> list:
    """Pobiera oferty z JustJoin — przechwytuje requesty sieciowe podczas ładowania strony."""
    all_jobs = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()

            captured_responses = []

            # Przechwytuj WSZYSTKIE odpowiedzi JSON z justjoin API
            def on_response(response):
                url = response.url
                if "justjoin.it" in url and response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type:
                        try:
                            data = response.json()
                            captured_responses.append({"url": url, "data": data})
                        except:
                            pass

            page.on("response", on_response)

            # Załaduj stronę z ofertami data
            page.goto(
                "https://justjoin.it/job-offers/all-locations/data",
                timeout=45000,
                wait_until="networkidle"
            )
            time.sleep(4)

            browser.close()

            # Szukaj ofert w przechwyconych odpowiedziach
            for item in captured_responses:
                data = item["data"]
                offers = None

                if isinstance(data, list):
                    offers = data
                elif isinstance(data, dict):
                    # Różne struktury odpowiedzi
                    for key in ["data", "offers", "postings", "items", "results", "jobs"]:
                        if key in data and isinstance(data[key], list):
                            offers = data[key]
                            break

                if offers:
                    for offer in offers:
                        if isinstance(offer, dict) and offer.get("title"):
                            job = _parse_offer(offer)
                            if job and _matches_keywords(job):
                                all_jobs[job["id"]] = job

            if not all_jobs:
                print(f"[JustJoin] Nie znaleziono ofert. Przechwycono {len(captured_responses)} odpowiedzi JSON.")
                for item in captured_responses[:5]:
                    print(f"  URL: {item['url'][:80]}")

    except Exception as e:
        print(f"[JustJoin] Błąd: {e}")

    result_list = list(all_jobs.values())
    print(f"[JustJoin] Pobrano {len(result_list)} unikalnych ofert")
    return result_list

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_offer(offer: dict) -> dict:
    if not offer:
        return None

    salary = ""
    for key in ["employment_types", "employmentTypes"]:
        employment_types = offer.get(key, [])
        if employment_types:
            sal = employment_types[0].get("salary")
            if sal and isinstance(sal, dict):
                frm = sal.get("from", "")
                to = sal.get("to", "")
                currency = sal.get("currency", "PLN")
                if frm and to:
                    salary = f"{frm} - {to} {currency}"
            break

    remote = offer.get("remote", False) or offer.get("workplaceType") == "remote"
    city = offer.get("city", "") or offer.get("cityName", "")
    location = "Remote" if remote else city

    skills = offer.get("skills", []) or offer.get("requiredSkills", []) or []
    skill_names = []
    for s in skills:
        if isinstance(s, dict):
            skill_names.append(s.get("name", "") or s.get("value", ""))
        elif isinstance(s, str):
            skill_names.append(s)

    description = " ".join(filter(None, skill_names))

    job_id = offer.get("id") or offer.get("slug", "")
    slug = offer.get("slug") or job_id

    return {
        "id": f"jj_{job_id}",
        "title": offer.get("title", ""),
        "company": offer.get("company_name", "") or offer.get("companyName", "") or offer.get("company", {}).get("name", ""),
        "location": location,
        "salary": salary,
        "url": f"https://justjoin.it/job-offer/{slug}",
        "source": "JustJoin.it",
        "description": description,
    }
