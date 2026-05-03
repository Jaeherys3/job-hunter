"""
Skrypt diagnostyczny - uruchom: python debug_scrapers.py
Pokaże co dokładnie zwracają API portali.
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

        # === TEST 1: JustJoin API v1 ===
        print("=" * 50)
        print("TEST 1: JustJoin API v1")
        page.goto("https://justjoin.it", timeout=45000, wait_until="domcontentloaded")
        time.sleep(2)

        result = page.evaluate("""
            async () => {
                try {
                    const r = await fetch('https://api.justjoin.it/v1/offers', {
                        headers: { 'Accept': 'application/json', 'Referer': 'https://justjoin.it/' }
                    });
                    return { status: r.status, ok: r.ok, text: await r.text() };
                } catch(e) {
                    return { error: e.toString() };
                }
            }
        """)
        print(f"Status: {result.get('status')} | OK: {result.get('ok')}")
        print(f"Odpowiedź (pierwsze 300 znaków): {str(result.get('text', result.get('error', '')))[:300]}")

        # === TEST 2: JustJoin nowe API ===
        print("\n" + "=" * 50)
        print("TEST 2: JustJoin nowe API /v2")
        result2 = page.evaluate("""
            async () => {
                try {
                    const r = await fetch('https://api.justjoin.it/v2/user-panel/offers?page=1&perPage=10&sortBy=newest', {
                        headers: { 'Accept': 'application/json', 'Referer': 'https://justjoin.it/' }
                    });
                    return { status: r.status, ok: r.ok, text: await r.text() };
                } catch(e) {
                    return { error: e.toString() };
                }
            }
        """)
        print(f"Status: {result2.get('status')} | OK: {result2.get('ok')}")
        print(f"Odpowiedź: {str(result2.get('text', result2.get('error', '')))[:300]}")

        # === TEST 3: NoFluffJobs POST ===
        print("\n" + "=" * 50)
        print("TEST 3: NoFluffJobs API")
        page.goto("https://nofluffjobs.com/pl", timeout=45000, wait_until="domcontentloaded")
        time.sleep(2)

        result3 = page.evaluate("""
            async () => {
                try {
                    const r = await fetch('https://nofluffjobs.com/api/search/posting', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify({ rawSearch: 'databricks', page: 1, pageSize: 5 })
                    });
                    return { status: r.status, ok: r.ok, text: await r.text() };
                } catch(e) {
                    return { error: e.toString() };
                }
            }
        """)
        print(f"Status: {result3.get('status')} | OK: {result3.get('ok')}")
        print(f"Odpowiedź: {str(result3.get('text', result3.get('error', '')))[:300]}")

        # === TEST 4: Przechwytywanie requestów na JustJoin ===
        print("\n" + "=" * 50)
        print("TEST 4: Nasłuchiwanie requestów na justjoin.it/job-offers")
        captured_urls = []

        def on_request(request):
            if 'justjoin' in request.url and 'api' in request.url:
                captured_urls.append(request.url)

        page.on("request", on_request)
        page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=45000, wait_until="networkidle")
        time.sleep(3)
        print(f"Przechwycone API URLs ({len(captured_urls)}):")
        for url in captured_urls[:10]:
            print(f"  {url}")

        browser.close()

if __name__ == "__main__":
    debug()
