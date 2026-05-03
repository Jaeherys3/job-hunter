"""
Diagnostyka v4 - sprawdza dokładną strukturę HTML kart ofert
"""
import time
from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="pl-PL",
        )
        page = context.new_page()

        # === NoFluffJobs - pełny HTML pierwszych 2 kart ===
        print("=" * 60)
        print("NoFluffJobs - HTML pierwszych 2 kart ofert")
        page.goto("https://nofluffjobs.com/pl/data-engineering", timeout=45000, wait_until="networkidle")
        time.sleep(3)

        cards = page.query_selector_all(".posting-list-item, [class*='posting-list-item']")
        print(f"Kart: {len(cards)}")
        for card in cards[:2]:
            print("\n--- KARTA ---")
            print(card.inner_html()[:800])

        # === JustJoin - pełny HTML pierwszych 2 kart ===
        print("\n" + "=" * 60)
        print("JustJoin - HTML pierwszych 2 kart ofert")
        page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=45000, wait_until="networkidle")
        time.sleep(4)

        # Spróbuj różnych selektorów
        for selector in ["a[href*='/job-offer/']", "[data-index]", "li[class*='offer']"]:
            cards_jj = page.query_selector_all(selector)
            if cards_jj:
                print(f"\nSelektor '{selector}' znalazł {len(cards_jj)} elementów")
                print("HTML pierwszego:")
                print(cards_jj[0].inner_html()[:800])
                break

        browser.close()

if __name__ == "__main__":
    debug()
