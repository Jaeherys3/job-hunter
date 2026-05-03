import time
import hashlib
import re
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark", "azure", "spark", "python", "etl"]

def fetch_justjoin() -> list:
    all_jobs = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = context.new_page()
            page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=45000, wait_until="networkidle")
            time.sleep(4)

            offers = page.evaluate("""
                () => {
                    const results = [];
                    const cards = document.querySelectorAll('a[href*="/job-offer/"]');
                    cards.forEach(card => {
                        const url = card.href || '';

                        // innerText struktura (z diagnostyki):
                        // opcjonalnie: "Super offer"
                        // tytuł
                        // wynagrodzenie lub "Undisclosed Salary"
                        // firma
                        // miasto
                        // opcjonalnie: ", +N Locations", "Remote", "Nd left"
                        // tagi technologii
                        const lines = (card.innerText || '')
                            .split('\\n')
                            .map(l => l.trim())
                            .filter(l => l.length > 0);

                        // Pomiń "Super offer" jeśli jest
                        let idx = 0;
                        if (lines[0] === 'Super offer') idx = 1;

                        const title = lines[idx] || '';
                        const salary = lines[idx + 1] || '';
                        const company = lines[idx + 2] || '';
                        const city = lines[idx + 3] || '';

                        // Tagi: wszystko po mieście, pomijając "Locations", "Remote", daty
                        const skipWords = ['Remote', 'Locations', 'left', 'New'];
                        const tags = lines.slice(idx + 4)
                            .filter(l => !skipWords.some(w => l.includes(w)) && !/^\\d/.test(l) && !/^,/.test(l));

                        results.push({ url, title, salary, company, city, tags });
                    });
                    return results;
                }
            """)

            for offer in offers:
                if not offer.get("title"):
                    continue
                job = _parse_offer(offer)
                if job and _matches_keywords(job):
                    all_jobs[job["id"]] = job

            browser.close()

    except Exception as e:
        print(f"[JustJoin] Błąd: {e}")

    result_list = list(all_jobs.values())
    print(f"[JustJoin] Pobrano {len(result_list)} unikalnych ofert")
    return result_list

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_offer(offer: dict) -> dict:
    url = offer.get("url", "")
    title = offer.get("title", "")
    tags = offer.get("tags", [])
    salary = offer.get("salary", "")
    if salary == "Undisclosed Salary":
        salary = ""

    description = f"{title} {' '.join(tags)}"
    job_id = hashlib.md5(url.encode()).hexdigest()[:12]

    return {
        "id": f"jj_{job_id}",
        "title": title,
        "company": offer.get("company", ""),
        "location": offer.get("city", ""),
        "salary": salary,
        "url": url,
        "source": "JustJoin.it",
        "description": description,
    }
