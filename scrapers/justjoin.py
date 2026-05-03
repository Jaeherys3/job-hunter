import time
import hashlib
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark"]

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

            # Zbierz dane z kart ofert przez JavaScript
            offers = page.evaluate("""
                () => {
                    const results = [];
                    const cards = document.querySelectorAll('a[href*="/job-offer/"]');
                    cards.forEach(card => {
                        const url = card.href;
                        // Tytuł jest w alt obrazka logo firmy
                        const img = card.querySelector('img[id="offerCardCompanyLogo"]');
                        const title = img ? img.alt : '';
                        // Firma - szukaj w tekstach
                        const allText = card.innerText || '';
                        const lines = allText.split('\\n').map(s => s.trim()).filter(s => s.length > 0);
                        results.push({ url, title, lines });
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
    lines = offer.get("lines", [])

    # Linie z karty: zwykle [firma, lokalizacja, technologie..., wynagrodzenie]
    company = lines[0] if len(lines) > 0 else ""
    location = lines[1] if len(lines) > 1 else ""
    salary = ""
    # Szukaj wynagrodzenia (zawiera cyfry i PLN/USD)
    for line in lines:
        if any(c in line for c in ["PLN", "USD", "EUR", "zł"]) and any(c.isdigit() for c in line):
            salary = line
            break

    description = " ".join(lines)
    job_id = hashlib.md5(url.encode()).hexdigest()[:12]

    return {
        "id": f"jj_{job_id}",
        "title": title,
        "company": company,
        "location": location,
        "salary": salary,
        "url": url,
        "source": "JustJoin.it",
        "description": description,
    }
