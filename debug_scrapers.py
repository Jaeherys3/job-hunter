"""Diagnostyka v5 - sprawdza selektory dla firmy/lokalizacji/tagów"""
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

        # NoFluffJobs - pełny innerText pierwszych 3 kart
        print("=" * 60)
        print("NoFluffJobs - innerText i href pierwszych 3 kart")
        page.goto("https://nofluffjobs.com/pl/data-engineering", timeout=45000, wait_until="networkidle")
        time.sleep(3)

        data = page.evaluate("""
            () => {
                const cards = document.querySelectorAll('.posting-list-item');
                return Array.from(cards).slice(0, 3).map(card => {
                    const link = card.querySelector('a');
                    return {
                        href: link ? link.getAttribute('href') : '',
                        text: card.innerText,
                        html_snippet: card.innerHTML.substring(0, 600)
                    };
                });
            }
        """)
        for i, d in enumerate(data):
            print(f"\n--- Karta {i+1} ---")
            print(f"HREF: {d['href']}")
            print(f"TEXT:\n{d['text']}")
            print(f"HTML snippet:\n{d['html_snippet']}")

        # JustJoin - pełny innerText pierwszych 3 kart
        print("\n" + "=" * 60)
        print("JustJoin - innerText i href pierwszych 3 kart")
        page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=45000, wait_until="networkidle")
        time.sleep(4)

        data_jj = page.evaluate("""
            () => {
                const cards = document.querySelectorAll('a[href*="/job-offer/"]');
                return Array.from(cards).slice(0, 3).map(card => {
                    return {
                        href: card.href,
                        text: card.innerText,
                        html_snippet: card.innerHTML.substring(0, 600)
                    };
                });
            }
        """)
        for i, d in enumerate(data_jj):
            print(f"\n--- Karta {i+1} ---")
            print(f"HREF: {d['href']}")
            print(f"TEXT:\n{d['text']}")

        browser.close()

if __name__ == "__main__":
    debug()
