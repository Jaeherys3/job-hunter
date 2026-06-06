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


def _normalize_languages(source: str, data: dict) -> list:
    """
    Sprowadza roznych-portalowe pola jezykowe do wspolnego ksztaltu:
        [{"code": "en", "level": "C1" | None, "required": True/False}, ...]
    JustJoin: data["languages"] = [{code, level}]  (poziom CEFR)
    NoFluffJobs: data["requirements"]["languages"] = [{type, code}] (type=MUST/NICE, brak poziomu)
    """
    out = []
    if not isinstance(data, dict):
        return out

    if source == "JustJoin.it":
        for item in data.get("languages") or []:
            if isinstance(item, dict):
                out.append({
                    "code": str(item.get("code", "")).lower(),
                    "level": item.get("level"),
                    "required": True,
                })

    elif source == "NoFluffJobs":
        langs = (data.get("requirements") or {}).get("languages") or []
        for item in langs:
            if isinstance(item, dict):
                out.append({
                    "code": str(item.get("code", "")).lower(),
                    "level": item.get("level"),  # zwykle brak -> None
                    "required": str(item.get("type", "")).upper() == "MUST",
                })

    return out


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
                job["languages"] = []
                if not slug:
                    continue
                try:
                    data, ep = _fetch_detail_json(page, source, slug)
                    if data:
                        chunks = []
                        _flatten_text(data, chunks)
                        job["detail_text"] = " ".join(chunks)
                        job["languages"] = _normalize_languages(source, data)
                        if verbose:
                            langs = ", ".join(
                                f"{l['code']}:{l.get('level') or '?'}" for l in job["languages"]
                            ) or "-"
                            print(f"[detail] OK {source} {slug[:30]} via {ep} "
                                  f"({len(job['detail_text'])} zn., jezyki: {langs})")
                    elif verbose:
                        print(f"[detail] BRAK JSON {source} {slug[:30]}")
                except Exception as e:
                    if verbose:
                        print(f"[detail] Blad {source} {slug[:30]}: {e}")
                time.sleep(0.25)

        browser.close()


def _source_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "justjoin" in host:
        return "JustJoin.it"
    if "nofluffjobs" in host:
        return "NoFluffJobs"
    return ""


def _check(urls: list):
    """Lekki test: pobiera tylko podane oferty i pokazuje co lapie filtr angielskiego."""
    import re as _re
    from scoring.english import detect_english_level

    jobs = [{"url": u, "title": "", "description": "", "source": _source_from_url(u)} for u in urls]
    enrich_jobs(jobs, verbose=True)

    for job in jobs:
        txt = job.get("detail_text", "")
        level, matched = detect_english_level(txt)
        print(f"\n=== {job['source']} ===")
        print(f"url: {job['url']}")
        print(f"detail_text: {len(txt)} zn. | detekcja: {level} ({matched!r})")
        # pokaz kontekst wokol wzmianek o jezyku
        low = txt.lower()
        for kw in ["angiel", "english", "język", "language", " b2", " c1", " c2"]:
            i = low.find(kw)
            if i != -1:
                snippet = txt[max(0, i - 50):i + 60].replace("\n", " ")
                print(f"   …{snippet}…  [trafienie: {kw!r}]")


def _raw(urls: list):
    """Pokazuje surowa strukture JSON-a detalu - zwlaszcza pola dot. jezykow."""
    import json as _json

    def find_lang(obj, path="$"):
        """Zwraca liste (sciezka, wartosc) dla kluczy zawierajacych 'lang'."""
        hits = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "lang" in str(k).lower():
                    hits.append((f"{path}.{k}", v))
                hits.extend(find_lang(v, f"{path}.{k}"))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                hits.extend(find_lang(v, f"{path}[{i}]"))
        return hits

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="pl-PL",
        )
        page = ctx.new_page()
        for url in urls:
            source = _source_from_url(url)
            slug = _slug_from_url(url)
            origin = ORIGINS.get(source, "")
            print(f"\n{'='*60}\n{source} | {slug}\n{'='*60}")
            if not origin:
                print("  nieznane zrodlo"); continue
            try:
                page.goto(origin, timeout=60000, wait_until="domcontentloaded")
                time.sleep(1)
                data, ep = _fetch_detail_json(page, source, slug)
            except Exception as e:
                print(f"  blad: {e}"); continue
            if not data:
                print("  brak JSON"); continue
            print(f"  endpoint: {ep}")
            print(f"  top-level keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            lang_hits = find_lang(data)
            if lang_hits:
                print("  --- pola z 'lang' ---")
                for path, val in lang_hits:
                    print(f"  {path} = {_json.dumps(val, ensure_ascii=False)[:300]}")
            else:
                print("  (zadnego klucza z 'lang')")
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
    args = sys.argv[1:]
    if "--inspect" in args:
        _inspect()
    elif "--check" in args:
        urls = [a for a in args if a.startswith("http")]
        if urls:
            _check(urls)
        else:
            print("Podaj URL(e): python -m scrapers.detail --check <url> [<url> ...]")
    elif "--raw" in args:
        urls = [a for a in args if a.startswith("http")]
        if urls:
            _raw(urls)
        else:
            print("Podaj URL(e): python -m scrapers.detail --raw <url> [<url> ...]")
    else:
        print("Uzyj: python -m scrapers.detail --inspect")
        print("  lub: python -m scrapers.detail --check <url> [<url> ...]")
        print("  lub: python -m scrapers.detail --raw <url> [<url> ...]")
