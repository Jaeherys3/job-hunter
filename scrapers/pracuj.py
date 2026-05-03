import time
import hashlib
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark", "azure data"]

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
            page.goto("https://nofluffjobs.com/pl/data-engineering", timeout=45000, wait_until="networkidle")
            time.sleep(3)

            offers = page.evaluate("""
                () => {
                    const results = [];
                    const cards = document.querySelectorAll('.posting-list-item');
                    cards.forEach(card => {
                        // URL
                        const link = card.querySelector('a[href*="/job/"]');
                        const url = link ? 'https://nofluffjobs.com' + link.getAttribute('href') : '';

                        // Tytuł
                        const titleEl = card.querySelector('[data-cy="posting-item-title"], h3, .posting-title__position');
                        const title = titleEl ? titleEl.innerText.trim() : '';

                        // Firma
                        const companyEl = card.querySelector('[data-cy="posting-item-company-name"], .posting-title__company');
                        const company = companyEl ? companyEl.innerText.trim() : '';

                        // Lokalizacja
                        const locEl = card.querySelector('[data-cy="posting-item-city"], .posting-info__location');
                        const location = locEl ? locEl.innerText.trim() : '';

                        // Wynagrodzenie
                        const salEl = card.querySelector('[data-cy="posting-item-salary"], .salary');
                        const salary = salEl ? salEl.innerText.trim() : '';

                        // Technologie (tagi)
                        const tags = Array.from(card.querySelectorAll('.posting-tag, [class*="tag"], [class*="technology"]'))
                            .map(t => t.innerText.trim())
                            .filter(t => t.length > 0);

                        if (title) results.push({ url, title, company, location, salary, tags });
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
        print(f"[NoFluffJobs] Błąd: {e}")

    result_list = list(all_jobs.values())
    print(f"[NoFluffJobs] Pobrano {len(result_list)} unikalnych ofert")
    return result_list

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_offer(offer: dict) -> dict:
    url = offer.get("url", "")
    title = offer.get("title", "")
    tags = offer.get("tags", [])
    description = f"{title} {' '.join(tags)}"
    job_id = hashlib.md5(url.encode()).hexdigest()[:12] if url else hashlib.md5(title.encode()).hexdigest()[:12]

    return {
        "id": f"nfj_{job_id}",
        "title": title,
        "company": offer.get("company", ""),
        "location": offer.get("location", ""),
        "salary": offer.get("salary", ""),
        "url": url,
        "source": "NoFluffJobs",
        "description": description,
    }
