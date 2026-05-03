"""
Diagnostyka v3 - sprawdza scraping HTML bezpośrednio ze stron
"""
import time
import json
import re
from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="pl-PL",
        )
        page = context.new_page()

        # === TEST 1: NoFluffJobs HTML scraping ===
        print("=" * 50)
        print("TEST 1: NoFluffJobs - scraping listy ofert HTML")
        page.goto("https://nofluffjobs.com/pl/data-engineering", timeout=45000, wait_until="networkidle")
        time.sleep(3)

        # Sprawdź ile kart ofert załadowało się
        cards = page.query_selector_all("[data-cy='list-item'], .posting-list-item, a[href*='/job/']")
        print(f"Znalezione karty ofert: {len(cards)}")
        if cards:
            print(f"Przykład HTML pierwszej karty (200 znaków):")
            print(cards[0].inner_html()[:200])

        # Sprawdź tytuły
        titles = page.query_selector_all("h3, [class*='title'], [data-cy='posting-item-title']")
        print(f"Znalezione tytuły: {len(titles)}")
        if titles:
            for t in titles[:3]:
                print(f"  - {t.inner_text()[:60]}")

        # Sprawdź czy jest JSON w __NEXT_DATA__ lub podobnym
        next_data = page.evaluate("""
            () => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent.substring(0, 500) : null;
            }
        """)
        print(f"\n__NEXT_DATA__ obecny: {next_data is not None}")
        if next_data:
            print(f"Fragment: {next_data[:300]}")

        # === TEST 2: JustJoin HTML scraping ===
        print("\n" + "=" * 50)
        print("TEST 2: JustJoin - scraping listy ofert HTML")
        page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=45000, wait_until="networkidle")
        time.sleep(4)

        cards_jj = page.query_selector_all("[data-index], [class*='offer'], a[href*='/job-offer/'], div[class*='JobOffer']")
        print(f"Znalezione karty: {len(cards_jj)}")

        titles_jj = page.query_selector_all("h2, h3, [class*='title']")
        print(f"Znalezione tytuły: {len(titles_jj)}")
        if titles_jj:
            for t in titles_jj[:5]:
                txt = t.inner_text().strip()
                if txt and len(txt) > 3:
                    print(f"  - {txt[:60]}")

        # Sprawdź __NEXT_DATA__
        next_data_jj = page.evaluate("""
            () => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent.substring(0, 1000) : null;
            }
        """)
        print(f"\n__NEXT_DATA__ obecny: {next_data_jj is not None}")
        if next_data_jj:
            print(f"Fragment: {next_data_jj[:400]}")

        browser.close()

if __name__ == "__main__":
    debug()
