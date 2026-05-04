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
                viewport={"width": 1280, "height": 2000},  # wysoki viewport = więcej ofert na ekranie
            )
            page = context.new_page()
            page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=60000, wait_until="networkidle")
            time.sleep(3)

            prev_count = 0
            no_change_streak = 0

            for scroll_num in range(50):  # max 50 scrolli
                # Scrolluj o jedną wysokość strony w dół
                page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
                time.sleep(1.5)

                current_count = page.evaluate("() => document.querySelectorAll('a[href*=\"/job-offer/\"]').length")

                if current_count == prev_count:
                    no_change_streak += 1
                    if no_change_streak >= 3:
                        break  # 3 scrolle bez zmian = koniec listy
                else:
                    no_change_streak = 0
                    prev_count = current_count

            print(f"[JustJoin] Zaladowano {prev_count} kart lacznie")

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
                        let idx = lines[0] === 'Super offer' ? 1 : 0;
                        const title = lines[idx] || '';
                        const salary = lines[idx + 1] || '';
                        const company = lines[idx + 2] || '';
                        const city = lines[idx + 3] || '';
                        const skipWords = ['Remote', 'Locations', 'left', 'New', 'Super offer'];
                        const tags = lines.slice(idx + 4)
                            .filter(l => !skipWords.some(w => l.includes(w)) && !/^[0-9]/.test(l) && !/^,/.test(l));
                        if (title && url) results.push({ url, title, salary, company, city, tags });
                    });
                    return results;
                }
            """)

            browser.close()

            for offer in offers:
                job = _parse_offer(offer)
                if job and _matches_keywords(job):
                    all_jobs[job["id"]] = job

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
