import time
import hashlib
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark", "azure data", "azure", "python", "spark"]

def fetch_pracuj() -> list:
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
            page.goto("https://nofluffjobs.com/pl/data-engineering", timeout=45000, wait_until="networkidle")
            time.sleep(3)

            # Scrolluj żeby załadować wszystkie oferty
            prev_count = 0
            for _ in range(15):
                page.keyboard.press("End")
                time.sleep(1.5)
                count = page.evaluate("() => document.querySelectorAll('.posting-list-item').length")
                if count == prev_count:
                    break
                prev_count = count

            print(f"[NoFluffJobs] Zaladowano {prev_count} kart po scrollowaniu")

            offers = page.evaluate("""
                () => {
                    const results = [];
                    const cards = document.querySelectorAll('.posting-list-item');
                    cards.forEach(card => {
                        const linkEl = card.querySelector('a[href*="/job/"]');
                        let url = '';
                        if (linkEl) url = linkEl.href || ('https://nofluffjobs.com' + (linkEl.getAttribute('href') || ''));

                        const lines = (card.innerText || '')
                            .split('\\n')
                            .map(l => l.trim())
                            .filter(l => l.length > 0 && l !== 'Zapisz ofertę' && l !== 'NOWA');

                        const title = lines[0] || '';
                        const salary = lines.find(l => /\\d/.test(l) && /(PLN|USD|EUR|zł)/.test(l)) || '';
                        const city = lines[lines.length - 1] || '';
                        const company = lines[lines.length - 2] || '';
                        const salIdx = salary ? lines.indexOf(salary) : 0;
                        const compIdx = lines.length - 2;
                        const tags = lines.slice(salIdx + 1, compIdx).filter(l => l.length > 0);

                        if (title) results.push({ url, title, salary, company, city, tags });
                    });
                    return results;
                }
            """)

            # Zbierz URLe z linków (Angular routerLink fallback)
            hrefs = page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href*="/pl/job/"]')).map(a => a.href)
            """)

            browser.close()

            for i, offer in enumerate(offers):
                if not offer.get("title"):
                    continue
                if not offer.get("url") and i < len(hrefs):
                    offer["url"] = hrefs[i]
                job = _parse_offer(offer)
                if job and _matches_keywords(job):
                    all_jobs[job["id"]] = job

    except Exception as e:
        print(f"[NoFluffJobs] Blad: {e}")

    result_list = list(all_jobs.values())
    print(f"[NoFluffJobs] Pobrano {len(result_list)} pasujacych ofert")
    return result_list

def _matches_keywords(job: dict) -> bool:
    text = f"{job['title']} {job['description']}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)

def _parse_offer(offer: dict) -> dict:
    url = offer.get("url", "")
    title = offer.get("title", "")
    tags = offer.get("tags", [])
    description = f"{title} {' '.join(tags)}"
    uid = url if url else title
    job_id = hashlib.md5(uid.encode()).hexdigest()[:12]

    return {
        "id": f"nfj_{job_id}",
        "title": title,
        "company": offer.get("company", "").lstrip(),
        "location": offer.get("city", ""),
        "salary": offer.get("salary", ""),
        "url": url or "https://nofluffjobs.com/pl/data-engineering",
        "source": "NoFluffJobs",
        "description": description,
    }
