import time
import hashlib
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
                viewport={"width": 1280, "height": 900},
            )
            page = context.new_page()

            # JustJoin ma paginację w URL: ?page=1, ?page=2 itd.
            page_num = 1
            max_pages = 10
            
            while page_num <= max_pages:
                url = f"https://justjoin.it/job-offers/all-locations/data?page={page_num}"
                page.goto(url, timeout=45000, wait_until="networkidle")
                time.sleep(3)

                offers = page.evaluate("""
                    () => {
                        const results = [];
                        const cards = document.querySelectorAll('a[href*="/job-offer/"]');
                        cards.forEach(card => {
                            const url = card.href || '';
                            const lines = (card.innerText || '')
                                .split('\\n')
                                .map(l => l.trim())
                                .filter(l => l.length > 0);

                            let idx = 0;
                            if (lines[0] === 'Super offer') idx = 1;

                            const title = lines[idx] || '';
                            const salary = lines[idx + 1] || '';
                            const company = lines[idx + 2] || '';
                            const city = lines[idx + 3] || '';

                            const skipWords = ['Remote', 'Locations', 'left', 'New', 'Super offer'];
                            const tags = lines.slice(idx + 4)
                                .filter(l => !skipWords.some(w => l.includes(w)) && !/^\\d/.test(l) && !/^,/.test(l));

                            if (title && url) results.push({ url, title, salary, company, city, tags });
                        });
                        return results;
                    }
                """)

                if not offers:
                    break

                before = len(all_jobs)
                for offer in offers:
                    job = _parse_offer(offer)
                    if job and _matches_keywords(job):
                        all_jobs[job["id"]] = job

                print(f"[JustJoin] Strona {page_num}: {len(offers)} kart, lacznie pasujacych: {len(all_jobs)}")

                # Sprawdź czy jest następna strona
                has_next = page.evaluate("""
                    () => {
                        const next = document.querySelector('a[aria-label="Go to next page"], button[aria-label="next"], [data-testid="next-page"]');
                        return next !== null && !next.disabled;
                    }
                """)
                if not has_next:
                    break
                page_num += 1

            browser.close()

    except Exception as e:
        print(f"[JustJoin] Blad: {e}")

    result_list = list(all_jobs.values())
    print(f"[JustJoin] Lacznie pobrano {len(result_list)} pasujacych ofert")
    return result_list

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_offer(offer: dict) -> dict:
    url = offer.get("url", "")
    title = offer.get("title", "")
    tags = offer.get("tags", [])
    salary = offer.get("salary", "")
    if salary in ("Undisclosed Salary", "Undisclosed"):
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
