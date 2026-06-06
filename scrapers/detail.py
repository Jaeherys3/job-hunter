"""
Faza 2 scrapowania: dociaga PELNY detal oferty (opis + wymagania jezykowe),
ktorego brakuje w listingu. Listing dawal tylko nazwy skilli, wiec filtr
angielskiego nie mial czego czytac.

Strategia: pobierz JSON detalu -> splaszcz WSZYSTKIE stringi z payloadu do
jednego tekstu -> oddaj go do detect_english_level. Nie zalezymy od dokladnych
nazw pol API (ktore sa niedokumentowane i potrafia sie zmienic).

Uzycie w main.py:
    from scrapers.detail import enrich_jobs
    enrich_jobs(survivors)        # mutuje liste, dodaje job["detail_text"]

Inspekcja realnego API (gdy cos nie lapie):
    python -m scrapers.detail --inspect
"""

import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# Endpointy detalu probowane po kolei (pierwszy zwracajacy JSON wygrywa).
# {slug} podstawiamy z ostatniego segmentu job["url"].
DETAIL_ENDPOINTS = {
    "JustJoin.it": [
        "/api/offers/{slug}",
        "/api/candidate-api/offers/{slug}",
    ],
    "NoFluffJobs": [
        "/api/posting/{slug}",
    ],
}

ORIGINS = {
    "JustJoin.it": "https://justjoin.it",
    "NoFluffJobs": "https://nofluffjobs.com",
}


def _slug_from_url(url: str) -> str:
    """Ostatni niepusty segment sciezki, np. .../job-offer/<slug> -> <slug>."""
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] if path else ""


def _flatten_text(obj, out: list, depth: int = 0):
    """Rekurencyjnie zbiera wszystkie stringi z JSON-a do listy."""
    if depth > 12:
        return
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _flatten_text(v, out, depth + 1)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _flatten_text(v, out, depth + 1)


# JS: probuje liste endpointow, zwraca pierwszy poprawny JSON (jako obiekt).
_FETCH_JS = """
async (endpoints) => {
    for (const ep of endpoints) {
        try {
            const r = await fetch(ep, { headers: { 'Accept': 'application/json' } });
            if (r.ok) {
                const data = await r.json();
                if (data && typeof data === 'object') return { ok: true, ep, data };
            }
        } catch (e) { /* nastepny */ }
    }
    return { ok: false };
}
"""


def _fetch_detail_json(page, source: str, slug: str):
    endpoints = [tpl.format(slug=slug) for tpl in DETAIL_ENDPOINTS.get(source, [])]
    if not endpoints:
        return None, None
    res = page.evaluate(_FETCH_JS, endpoints)
    if res and res.get("ok"):
        return res["data"], res["ep"]
    return None, None


def enrich_jobs(jobs: list, verbose: bool = False) -> None:
    """
    Mutuje `jobs` w miejscu: dla kazdej oferty dodaje job["detail_text"]
    (splaszczony tekst detalu) lub "" jesli nie udalo sie pobrac.
    Jeden browser na cala paczke; grupowanie po zrodle = jeden goto na origin.
    """
    if not jobs:
        return

    by_source = {}
    for job in jobs:
        by_source.setdefault(job.get("source", ""), []).append(job)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="pl-PL",
        )
        page = context.new_page()

        for source, group in by_source.items():
            origin = ORIGINS.get(source)
            if not origin:
                for job in group:
                    job["detail_text"] = ""
                continue

            try:
                page.goto(origin, timeout=60000, wait_until="domcontentloaded")
                time.sleep(1)
            except Exception as e:
                if verbose:
                    print(f"[detail] Nie udalo sie wejsc na {origin}: {e}")
                for job in group:
                    job["detail_text"] = ""
                continue

            for job in group:
                slug = _slug_from_url(job.get("url", ""))
                job["detail_text"] = ""
                if not slug:
                    continue
                try:
                    data, ep = _fetch_detail_json(page, source, slug)
                    if data:
                        chunks = []
                        _flatten_text(data, chunks)
                        job["detail_text"] = " ".join(chunks)
                        if verbose:
                            print(f"[detail] OK {source} {slug[:30]} via {ep} "
                                  f"({len(job['detail_text'])} zn.)")
                    elif verbose:
                        print(f"[detail] BRAK JSON {source} {slug[:30]}")
                except Exception as e:
                    if verbose:
                        print(f"[detail] Blad {source} {slug[:30]}: {e}")
                time.sleep(0.25)

        browser.close()


def _inspect():
    """Pobiera 1 ofesrte z kazdego zrodla i pokazuje, ktory endpoint dziala."""
    from scrapers.justjoin import fetch_justjoin
    from scrapers.pracuj import fetch_pracuj

    print(">> Pobieram po kilka ofert z kazdego zrodla...")
    jj = fetch_justjoin()[:1]
    nfj = fetch_pracuj()[:1]
    sample = jj + nfj
    if not sample:
        print("Brak ofert do inspekcji.")
        return

    for job in sample:
        print(f"\n=== {job.get('source')} | {job.get('title','')[:50]} ===")
        print(f"url:  {job.get('url')}")
        print(f"slug: {_slug_from_url(job.get('url',''))}")

    enrich_jobs(sample, verbose=True)

    for job in sample:
        txt = job.get("detail_text", "")
        print(f"\n--- {job.get('source')} detail_text (pierwsze 600 zn.) ---")
        print(txt[:600] if txt else "(pusto)")


if __name__ == "__main__":
    import sys
    if "--inspect" in sys.argv[1:]:
        _inspect()
    else:
        print("Uzyj: python -m scrapers.detail --inspect")
