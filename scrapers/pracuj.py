import time
import hashlib
import json
from playwright.sync_api import sync_playwright

SEARCHES = [
    "data engineer",
    "databricks",
    "airflow python",
    "pyspark azure",
]

def fetch_pracuj() -> list:
    all_jobs = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()
            page.goto("https://nofluffjobs.com/pl", timeout=90000, wait_until="domcontentloaded")
            time.sleep(2)

            for keyword in SEARCHES:
                # Sprawdź ile ofert jest łącznie
                count_result = page.evaluate(f"""
                    async () => {{
                        const r = await fetch('/api/search/posting?pageTo=1&pageSize=1&salaryCurrency=PLN&salaryPeriod=month', {{
                            method: 'POST',
                            headers: {{'Content-Type':'application/json','Accept':'application/json'}},
                            body: JSON.stringify({{"criteria":"","rawSearch":"{keyword}","pageSize":1}})
                        }});
                        const data = await r.json();
                        return data.totalCount || 0;
                    }}
                """)

                total = int(count_result) if count_result else 0
                page_size = 100
                pages_needed = min((total // page_size) + 2, 15)  # max 1500 ofert per keyword

                print(f"[NoFluffJobs] '{keyword}': {total} ofert, pobieranie {pages_needed} stron...")

                for page_to in range(1, pages_needed + 1):
                    result = page.evaluate(f"""
                        async () => {{
                            const r = await fetch('/api/search/posting?pageTo={page_to}&pageSize={page_size}&salaryCurrency=PLN&salaryPeriod=month', {{
                                method: 'POST',
                                headers: {{'Content-Type':'application/json','Accept':'application/json'}},
                                body: JSON.stringify({{"criteria":"","rawSearch":"{keyword}","pageSize":{page_size}}})
                            }});
                            if (!r.ok) return null;
                            return await r.json();
                        }}
                    """)

                    if not result:
                        break

                    postings = result.get("postings", [])
                    if not postings:
                        break

                    new_count = 0
                    for posting in postings:
                        job = _parse_posting(posting)
                        if job and job["id"] not in all_jobs:
                            all_jobs[job["id"]] = job
                            new_count += 1

                    if new_count == 0:
                        break

                    time.sleep(0.3)

            browser.close()

    except Exception as e:
        print(f"[NoFluffJobs] Blad: {e}")

    result_list = list(all_jobs.values())
    print(f"[NoFluffJobs] Lacznie pobrano {len(result_list)} unikalnych ofert")
    return result_list

def _parse_posting(posting: dict) -> dict:
    if not posting:
        return None

    salary = ""
    sal = posting.get("salary")
    if sal:
        frm = sal.get("from", "")
        to = sal.get("to", "")
        currency = sal.get("currency", "PLN")
        if frm and to:
            salary = f"{frm} - {to} {currency}"

    location_data = posting.get("location", {}) or {}
    remote = bool(location_data.get("fullyRemote", False))
    places = location_data.get("places", []) or []

    cities = []
    for pl in places:
        c = pl.get("city") if isinstance(pl, dict) else None
        name = c.get("name") if isinstance(c, dict) else c
        if name:
            cities.append(str(name))
    cities = [c.lower() for c in cities]

    if remote:
        location = "Remote"
    elif cities:
        location = cities[0].title()
    else:
        location = "Polska"

    skills = posting.get("technology", []) or []
    skill_names = [str(s) for s in skills if s]
    title = posting.get("title", "")
    description = f"{title} {' '.join(skill_names)}"

    post_id = posting.get("id") or posting.get("slug", "")
    post_url = posting.get("url", post_id)

    return {
        "id": f"nfj_{post_id}",
        "title": title,
        "company": posting.get("name", ""),
        "location": location,
        "remote": remote,
        "cities": cities,
        "salary": salary,
        "url": f"https://nofluffjobs.com/pl/job/{post_url}",
        "source": "NoFluffJobs",
        "description": description,
    }
