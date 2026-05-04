"""Diagnostyka paginacji"""
import time
from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="pl-PL",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # === JustJoin - sprawdź czy ?page=2 działa ===
        print("=" * 60)
        print("JustJoin - strona 2")
        page.goto("https://justjoin.it/job-offers/all-locations/data?page=2", timeout=45000, wait_until="networkidle")
        time.sleep(3)
        count = page.evaluate("() => document.querySelectorAll('a[href*=\"/job-offer/\"]').length")
        print(f"Kart na stronie 2: {count}")

        # Szukaj elementów paginacji
        pagination = page.evaluate("""
            () => {
                const all = document.querySelectorAll('a, button');
                const pg = [];
                all.forEach(el => {
                    const txt = el.innerText.trim();
                    const aria = el.getAttribute('aria-label') || '';
                    if (txt.match(/^\\d+$/) || aria.includes('page') || aria.includes('next') || txt === 'Next' || txt === '>') {
                        pg.push({ tag: el.tagName, text: txt, aria: aria, href: el.href || '' });
                    }
                });
                return pg.slice(0, 15);
            }
        """)
        print(f"Elementy paginacji:")
        for el in pagination:
            print(f"  {el}")

        # === NoFluffJobs - sprawdź czy ?page=2 działa ===
        print("\n" + "=" * 60)
        print("NoFluffJobs - strona 2")
        page.goto("https://nofluffjobs.com/pl/data-engineering?page=2", timeout=45000, wait_until="networkidle")
        time.sleep(3)
        count2 = page.evaluate("() => document.querySelectorAll('.posting-list-item').length")
        print(f"Kart na stronie 2: {count2}")

        pagination2 = page.evaluate("""
            () => {
                const all = document.querySelectorAll('a, button');
                const pg = [];
                all.forEach(el => {
                    const txt = el.innerText.trim();
                    const aria = el.getAttribute('aria-label') || '';
                    if (txt.match(/^\\d+$/) || aria.includes('page') || aria.includes('next') || aria.includes('Next') || txt === 'Next' || txt === '>' || el.className.includes('pagination')) {
                        pg.push({ tag: el.tagName, text: txt.substring(0,30), aria: aria, class: el.className.substring(0,50) });
                    }
                });
                return pg.slice(0, 15);
            }
        """)
        print(f"Elementy paginacji:")
        for el in pagination2:
            print(f"  {el}")

        browser.close()

if __name__ == "__main__":
    debug()
