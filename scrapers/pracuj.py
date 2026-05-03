import time
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark", "azure data"]

NFJ_API = "https://nofluffjobs.com/api/search/posting"

def fetch_pracuj() -> list:
    """Pobiera oferty z NoFluffJobs — wywołuje API bezpośrednio z kontekstu przeglądarki."""
    all_jobs = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()

            # Najpierw odwiedź stronę żeby dostać ciasteczka/nagłówki
            page.goto("https://nofluffjobs.com/pl", timeout=45000, wait_until="domcontentloaded")
            time.sleep(2)

            # Wywołaj API bezpośrednio z kontekstu przeglądarki (omija blokady CORS)
            result = page.evaluate("""
                async () => {
                    const response = await fetch('https://nofluffjobs.com/api/search/posting', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json',
                        },
                        body: JSON.stringify({
                            rawSearch: '',
                            category: 'data-engineering',
                            page: 1,
                            pageSize: 100,
                        })
                    });
                    if (!response.ok) return null;
                    return await response.json();
                }
            """)

            browser.close()

            if not result:
                print("[NoFluffJobs] Brak odpowiedzi z API")
                return []

            postings = result.get("postings", [])
            for posting in postings:
                job = _parse_posting(posting)
                if job and _matches_keywords(job):
                    all_jobs[job["id"]] = job

    except Exception as e:
        print(f"[NoFluffJobs] Błąd: {e}")

    result_list = list(all_jobs.values())
    print(f"[NoFluffJobs] Pobrano {len(result_list)} unikalnych ofert")
    return result_list

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

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
