import time
import re
import hashlib
from playwright.sync_api import sync_playwright

SEARCHES = [
    "data engineer databricks",
    "senior data engineer azure",
    "data engineer airflow python",
]

def fetch_pracuj() -> list:
    """Pobiera oferty z NoFluffJobs przez przeglądarkę (Playwright)."""
    all_jobs = []
    seen_ids = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()

            for query in SEARCHES:
                try:
                    jobs = _scrape_nofluff(page, query)
                    for job in jobs:
                        if job["id"] not in seen_ids:
                            seen_ids.add(job["id"])
                            all_jobs.append(job)
                    time.sleep(2)
                except Exception as e:
                    print(f"[NoFluffJobs] Błąd dla '{query}': {e}")

            browser.close()

    except Exception as e:
        print(f"[NoFluffJobs] Błąd ogólny: {e}")

    print(f"[NoFluffJobs] Pobrano {len(all_jobs)} ofert")
    return all_jobs

def _scrape_nofluff(page, query: str) -> list:
    captured = []

    def handle_response(response):
        if "nofluffjobs.com/api/search/posting" in response.url and response.status == 200:
            try:
                data = response.json()
                postings = data.get("postings", [])
                captured.extend(postings)
            except:
                pass

    page.on("response", handle_response)

    encoded = query.replace(" ", "%20")
    page.goto(f"https://nofluffjobs.com/pl?criteria=requirement%3D{encoded}", timeout=30000, wait_until="networkidle")
    time.sleep(2)

    page.remove_listener("response", handle_response)
    return [_parse_posting(p) for p in captured]

def _parse_posting(posting: dict) -> dict:
    salary = ""
    sal = posting.get("salary")
    if sal:
        frm = sal.get("from", "")
        to = sal.get("to", "")
        currency = sal.get("currency", "PLN")
        if frm and to:
            salary = f"{frm} - {to} {currency}"

    location_data = posting.get("location", {})
    remote = location_data.get("fullyRemote", False)
    places = location_data.get("places", [])

    if remote:
        location = "Remote"
    elif places:
        city = places[0].get("city", {})
        location = city.get("name", "Polska") if isinstance(city, dict) else str(city)
    else:
        location = "Polska"

    skills = posting.get("technology", []) or []
    description = " ".join(str(s) for s in skills if s)
    description += f" {posting.get('title', '')} {posting.get('category', '')}"

    post_id = posting.get("id") or posting.get("slug", "")
    post_url = posting.get("url", post_id)

    return {
        "id": f"nfj_{post_id}",
        "title": posting.get("title", ""),
        "company": posting.get("name", ""),
        "location": location,
        "salary": salary,
        "url": f"https://nofluffjobs.com/pl/job/{post_url}",
        "source": "NoFluffJobs",
        "description": description,
    }
