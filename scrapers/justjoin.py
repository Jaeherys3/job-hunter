import time
import hashlib
from playwright.sync_api import sync_playwright

KEYWORDS = ["databricks", "data engineer", "airflow", "pyspark", "azure", "spark", "python", "etl"]
MAX_OFFERS = 960  # API limit dla niezalogowanych

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
            page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=60000, wait_until="domcontentloaded")
            time.sleep(2)

            count_data = page.evaluate("""
                async () => {
                    const r = await fetch('/api/candidate-api/offers/categories/count?categories=data&currency=pln&keywordType=any', {
                        headers: { 'Accept': 'application/json' }
                    });
                    return await r.json();
                }
            """)
            total = min(count_data[0]['count'] if count_data else MAX_OFFERS, MAX_OFFERS)
            print(f"[JustJoin] Pobieranie {total} ofert...")

            from_idx = 0
            while from_idx < total:
                result = page.evaluate(f"""
                    async () => {{
                        const r = await fetch('/api/candidate-api/offers?categories=data&from={from_idx}&sortBy=newest&currency=pln&keywordType=any', {{
                            headers: {{ 'Accept': 'application/json' }}
                        }});
                        if (!r.ok) return null;
                        return await r.json();
                    }}
                """)

                if not result:
                    break

                offers = result.get("data", [])
                if not offers:
                    break

                for offer in offers:
                    job = _parse_offer(offer)
                    if job and _matches_keywords(job):
                        all_jobs[job["id"]] = job

                if from_idx % 200 == 0:
                    print(f"[JustJoin] from={from_idx}/{total}, pasujacych: {len(all_jobs)}")

                from_idx += len(offers)

                if len(offers) < 10:
                    break

                time.sleep(0.2)

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
    if not offer:
        return None

    salary = ""
    emp_types = offer.get("employmentTypes") or offer.get("employment_types", [])
    if emp_types:
        sal = emp_types[0].get("salary") or {}
        if isinstance(sal, dict) and sal.get("from") and sal.get("to"):
            salary = f"{sal['from']} - {sal['to']} {sal.get('currency', 'PLN')}"

    workplace = offer.get("workplaceType", "")
    remote = workplace == "remote"

    cities = []
    if offer.get("city"):
        cities.append(str(offer["city"]))
    for ml in offer.get("multilocation") or []:
        if isinstance(ml, dict) and ml.get("city"):
            cities.append(str(ml["city"]))
    cities = [c.lower() for c in cities]

    location = "Remote" if remote else (offer.get("city", "") or "")

    skills = offer.get("requiredSkills") or offer.get("skills", [])
    skill_names = [s.get("name", "") if isinstance(s, dict) else str(s) for s in skills]
    description = " ".join(filter(None, skill_names))

    slug = offer.get("slug") or offer.get("id", "")
    guid = offer.get("guid") or offer.get("id", "")

    return {
        "id": f"jj_{guid}",
        "title": offer.get("title", ""),
        "company": offer.get("companyName") or offer.get("company_name", ""),
        "location": location,
        "remote": remote,
        "cities": cities,
        "salary": salary,
        "url": f"https://justjoin.it/job-offer/{slug}",
        "source": "JustJoin.it",
        "description": description,
    }
