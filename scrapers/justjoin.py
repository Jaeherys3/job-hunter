import time
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark"]

def fetch_justjoin() -> list:
    """Pobiera oferty z JustJoin.it — wywołuje API z kontekstu przeglądarki."""
    all_jobs = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()

            # Odwiedź stronę żeby dostać ciasteczka
            page.goto("https://justjoin.it", timeout=45000, wait_until="domcontentloaded")
            time.sleep(2)

            # Wywołaj API z kontekstu przeglądarki
            result = page.evaluate("""
                async () => {
                    const response = await fetch('https://api.justjoin.it/v1/offers', {
                        headers: {
                            'Accept': 'application/json',
                            'Referer': 'https://justjoin.it/',
                        }
                    });
                    if (!response.ok) return null;
                    return await response.json();
                }
            """)

            browser.close()

            if not result or not isinstance(result, list):
                print("[JustJoin] Brak odpowiedzi z API")
                return []

            for offer in result:
                job = _parse_offer(offer)
                if job and _matches_keywords(job):
                    all_jobs[job["id"]] = job

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
