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
        page.goto("https://justjoin.it/job-offers/all-locations/data", timeout=60000, wait_until="domcontentloaded")
        time.sleep(2)

        # Sprawdź różne parametry paginacji
        for test in [
            "cursor=0",
            "cursor=10", 
            "cursor=20",
            "from=0",
            "from=10",
            "from=20",
            "offset=0",
            "offset=10",
        ]:
            result = page.evaluate(f"""
                async () => {{
                    const r = await fetch('/api/candidate-api/offers?categories=data&{test}&sortBy=newest&currency=pln', {{
                        headers: {{ 'Accept': 'application/json' }}
                    }});
                    const data = await r.json();
                    const meta = data.meta || {{}};
                    const first = data.data?.[0]?.title || '';
                    const last = data.data?.[data.data?.length-1]?.title || '';
                    return {{ count: data.data?.length, meta_from: meta.from, next_cursor: meta.next?.cursor, first, last }};
                }}
            """)
            print(f"  {test:15} -> count={result.get('count')}, from={result.get('meta_from')}, next_cursor={result.get('next_cursor')}, first={result.get('first','')[:30]}")

        browser.close()

if __name__ == "__main__":
    debug()
