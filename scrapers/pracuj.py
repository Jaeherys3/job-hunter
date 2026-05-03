import time
from playwright.sync_api import sync_playwright

# Jedno zapytanie — NoFluffJobs zwraca wszystkie oferty z Data kategorii
# Filtrowanie robimy lokalnie żeby uniknąć duplikatów z wielu zapytań
KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark", "azure data"]

def fetch_pracuj() -> list:
    """Pobiera oferty z NoFluffJobs przez przeglądarkę (Playwright)."""
    all_jobs = {}  # słownik id -> job, automatycznie deduplikuje

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()

            def handle_response(response):
                if "nofluffjobs.com/api/search/posting" in response.url and response.status == 200:
                    try:
                        data = response.json()
                        for posting in data.get("postings", []):
                            job = _parse_posting(posting)
                            if job and _matches_keywords(job):
                                all_jobs[job["id"]] = job  # deduplikacja przez słownik
                    except:
                        pass

            page.on("response", handle_response)

            # Jedno szerokie zapytanie po kategorii Data — brak duplikatów
            page.goto(
                "https://nofluffjobs.com/pl/data-engineering",
                timeout=45000,
                wait_until="networkidle"
            )
            time.sleep(3)
            browser.close()

    except Exception as e:
        print(f"[NoFluffJobs] Błąd: {e}")

    result = list(all_jobs.values())
    print(f"[NoFluffJobs] Pobrano {len(result)} unikalnych ofert")
    return result

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_posting(posting: dict) -> dict:
    if not posting:
        return None

    # Wynagrodzenie
    salary = ""
    sal = posting.get("salary")
    if sal:
        frm = sal.get("from", "")
        to = sal.get("to", "")
        currency = sal.get("currency", "PLN")
        if frm and to:
            salary = f"{frm} - {to} {currency}"

    # Lokalizacja
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

    # Opis — sklejamy tytuł + technologie + kategorię żeby scorer miał co analizować
    skills = posting.get("technology", []) or []
    skill_names = [str(s) for s in skills if s]
    title = posting.get("title", "")
    category = posting.get("category", "")
    seniority = " ".join(posting.get("seniority", []) or [])
    description = " ".join(filter(None, [title, category, seniority] + skill_names))

    post_id = posting.get("id") or posting.get("slug", "")
    post_url = posting.get("url", post_id)

    return {
        "id": f"nfj_{post_id}",
        "title": title,
        "company": posting.get("name", ""),
        "location": location,
        "salary": salary,
        "url": f"https://nofluffjobs.com/pl/job/{post_url}",
        "source": "NoFluffJobs",
        "description": description,
    }
