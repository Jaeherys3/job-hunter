"""
Skrypt diagnostyczny - uruchom: python debug_scrapers.py
"""
import time
import json
from playwright.sync_api import sync_playwright

def debug():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="pl-PL",
        )
        page = context.new_page()

        # === TEST NoFluffJobs z poprawnym parametrem ===
        print("=" * 50)
        print("TEST: NoFluffJobs API z salaryCurrency")
        page.goto("https://nofluffjobs.com/pl", timeout=45000, wait_until="domcontentloaded")
        time.sleep(2)

        result = page.evaluate("""
            async () => {
                try {
                    const r = await fetch('https://nofluffjobs.com/api/search/posting', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                        body: JSON.stringify({
                            rawSearch: 'databricks',
                            salaryCurrency: 'PLN',
                            salaryPeriod: 'month',
                            page: 1,
                            pageSize: 3,
                        })
                    });
                    const text = await r.text();
                    return { status: r.status, text: text };
                } catch(e) { return { error: e.toString() }; }
            }
        """)
        print(f"Status: {result.get('status')}")
        if result.get('status') == 200:
            data = json.loads(result['text'])
            postings = data.get('postings', [])
            print(f"Ofert: {len(postings)}")
            if postings:
                p0 = postings[0]
                print(f"Przykład: {p0.get('title')} @ {p0.get('name')}")
                print(f"Klucze: {list(p0.keys())}")
        else:
            print(f"Odpowiedź: {result.get('text', '')[:300]}")

        # === TEST JustJoin - przechwytywanie ===
        print("\n" + "=" * 50)
        print("TEST: JustJoin - przechwytywanie JSON responses")
        captured = []

        def on_response(response):
            if "justjoin.it" in response.url and response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        data = response.json()
                        captured.append({"url": response.url, "data": data})
                    except:
                        pass

        page.on("response", on_response)
        page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=45000, wait_until="networkidle")
        time.sleep(4)

        print(f"Przechwycono {len(captured)} odpowiedzi JSON:")
        for item in captured:
            data = item['data']
            size = len(data) if isinstance(data, list) else "dict"
            print(f"  [{size}] {item['url'][:80]}")
            if isinstance(data, list) and data:
                print(f"    Przykład klucze: {list(data[0].keys())[:8]}")
            elif isinstance(data, dict):
                print(f"    Klucze: {list(data.keys())[:8]}")

        browser.close()

if __name__ == "__main__":
    debug()
