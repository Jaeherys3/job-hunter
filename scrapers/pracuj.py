import requests
import hashlib
import xml.etree.ElementTree as ET
import time
import re

# Pracuj.pl udostępnia RSS dla wyników wyszukiwania - legalne i bez blokad
PRACUJ_RSS_BASE = "https://www.pracuj.pl/praca.rss"

SEARCHES = [
    "data+engineer+databricks",
    "senior+data+engineer+azure",
    "data+engineer+airflow+python",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def fetch_pracuj() -> list:
    """Pobiera oferty z Pracuj.pl przez RSS."""
    all_jobs = []
    seen_ids = set()

    for query in SEARCHES:
        try:
            jobs = _fetch_rss(query)
            for job in jobs:
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    all_jobs.append(job)
            time.sleep(1.5)
        except Exception as e:
            print(f"[Pracuj] Błąd dla '{query}': {e}")

    print(f"[Pracuj] Pobrano {len(all_jobs)} ofert")
    return all_jobs

def _fetch_rss(query: str) -> list:
    url = f"{PRACUJ_RSS_BASE}?q={query}&cc=5016&tt=6"  # cc=5016 IT, tt=6 pełny etat
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    channel = root.find("channel")
    if channel is None:
        return []

    jobs = []
    for item in channel.findall("item"):
        job = _parse_item(item)
        if job:
            jobs.append(job)
    return jobs

def _parse_item(item) -> dict:
    title = _get_text(item, "title")
    link = _get_text(item, "link")
    description_html = _get_text(item, "description")

    if not title or not link:
        return None

    # Wyciągnij tekst z HTML description
    description = re.sub(r"<[^>]+>", " ", description_html or "")

    # Wyciągnij firmę i lokalizację z tytułu RSS (format: "Stanowisko - Firma - Lokalizacja")
    parts = title.split(" - ")
    company = parts[1].strip() if len(parts) > 1 else ""
    location = parts[2].strip() if len(parts) > 2 else "Polska"
    clean_title = parts[0].strip()

    # Unikalny ID z URL
    job_id = f"pracuj_{hashlib.md5(link.encode()).hexdigest()[:10]}"

    return {
        "id": job_id,
        "title": clean_title,
        "company": company,
        "location": location,
        "salary": _extract_salary(description),
        "url": link,
        "source": "Pracuj.pl",
        "description": description,
    }

def _get_text(element, tag: str) -> str:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else ""

def _extract_salary(text: str) -> str:
    """Próbuje wyciągnąć widełki płacowe z opisu."""
    patterns = [
        r"(\d[\d\s]+)\s*[-–]\s*(\d[\d\s]+)\s*(PLN|zł|USD|EUR)",
        r"(\d[\d\s]+)\s*(PLN|zł)\s*/\s*(?:mies|msc|miesiąc|mc)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""
