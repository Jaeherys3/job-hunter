import requests
import hashlib
import time

JUSTJOIN_API = "https://api.justjoin.it/v2/user-panel/offers"

SEARCH_PARAMS = [
    {"keyword": "data engineer databricks", "remoteOnly": "true"},
    {"keyword": "data engineer azure airflow", "remoteOnly": "true"},
    {"keyword": "senior data engineer python", "remoteOnly": "false", "city": "Warszawa"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

def fetch_justjoin() -> list:
    """Pobiera oferty z JustJoin.it przez publiczne API."""
    all_jobs = []
    seen_ids = set()

    for params in SEARCH_PARAMS:
        try:
            jobs = _fetch_page(params)
            for job in jobs:
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    all_jobs.append(job)
            time.sleep(1)  # grzeczny scraper
        except Exception as e:
            print(f"[JustJoin] Błąd dla {params}: {e}")

    print(f"[JustJoin] Pobrano {len(all_jobs)} ofert")
    return all_jobs

def _fetch_page(params: dict) -> list:
    query = {
        "page": 1,
        "perPage": 50,
        "sortBy": "newest",
        **params
    }

    response = requests.get(JUSTJOIN_API, params=query, headers=HEADERS, timeout=15)
    response.raise_for_status()
    data = response.json()

    offers = data.get("data", data.get("offers", []))
    return [_parse_offer(o) for o in offers if o]

def _parse_offer(offer: dict) -> dict:
    salary = ""
    employment_types = offer.get("employmentTypes") or offer.get("employment_types", [])
    if employment_types:
        et = employment_types[0]
        sal = et.get("salary") or et.get("from_pln", "")
        if isinstance(sal, dict):
            frm = sal.get("from", "")
            to = sal.get("to", "")
            currency = sal.get("currency", "PLN")
            if frm and to:
                salary = f"{frm} - {to} {currency}"

    city = offer.get("city") or (offer.get("multilocation", [{}])[0].get("city", "") if offer.get("multilocation") else "")
    remote = offer.get("workplaceType") == "remote" or offer.get("remote", False)
    location = "Remote" if remote else city

    slug = offer.get("slug") or offer.get("id", "")
    url = f"https://justjoin.it/job-offer/{slug}"

    description = offer.get("body") or offer.get("description") or ""

    return {
        "id": f"jj_{offer.get('id') or offer.get('slug')}",
        "title": offer.get("title", ""),
        "company": offer.get("companyName") or offer.get("company_name", ""),
        "location": location,
        "salary": salary,
        "url": url,
        "source": "JustJoin.it",
        "description": description,
    }
