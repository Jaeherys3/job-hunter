import json
import time
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark"]

def fetch_justjoin() -> list:
    """Pobiera oferty z JustJoin.it przez przeglądarkę (Playwright)."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()

            # Przechwytuj odpowiedzi API
            captured = []

            def handle_response(response):
                if "api.justjoin.it/v1/offers" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            captured.extend(data)
                    except:
                        pass

            page.on("response", handle_response)

            page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=30000, wait_until="networkidle")
            time.sleep(3)

            browser.close()

            if not captured:
                print("[JustJoin] Brak danych z API — spróbuj uruchomić ponownie")
                return []

            parsed = [_parse_offer(o) for o in captured]
            filtered = [j for j in parsed if _matches_keywords(j)]
            print(f"[JustJoin] Pobrano {len(captured)} ofert, po filtrze: {len(filtered)}")
            return filtered

    except Exception as e:
        print(f"[JustJoin] Błąd: {e}")
        return []

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_offer(offer: dict) -> dict:
    salary = ""
    employment_types = offer.get("employment_types", [])
    if employment_types:
        sal = employment_types[0].get("salary")
        if sal and isinstance(sal, dict):
            frm = sal.get("from", "")
            to = sal.get("to", "")
            currency = sal.get("currency", "PLN")
            if frm and to:
                salary = f"{frm} - {to} {currency}"

    remote = offer.get("remote", False)
    city = offer.get("city", "")
    location = "Remote" if remote else city

    skills = offer.get("skills", [])
    skill_names = [s.get("name", "") for s in skills if s.get("name")]
    description = " ".join(skill_names)

    job_id = offer.get("id", "")

    return {
        "id": f"jj_{job_id}",
        "title": offer.get("title", ""),
        "company": offer.get("company_name", ""),
        "location": location,
        "salary": salary,
        "url": f"https://justjoin.it/offers/{job_id}",
        "source": "JustJoin.it",
        "description": description,
    }
