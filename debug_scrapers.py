"""Sprawdza JustJoin from=900+"""
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

        for from_val in [900, 950, 960, 970, 980, 990, 1000, 1050, 1100, 1500, 2000]:
            result = page.evaluate(f"""
                async () => {{
                    const r = await fetch('/api/candidate-api/offers?categories=data&from={from_val}&sortBy=newest&currency=pln&keywordType=any', {{
                        headers: {{ 'Accept': 'application/json' }}
                    }});
                    const data = await r.json();
                    return {{
                        count: data.data?.length || 0,
                        total: data.meta?.totalItems || 0,
                        first: data.data?.[0]?.title?.substring(0,40) || 'BRAK'
                    }};
                }}
            """)
            print(f"from={from_val:5}: count={result['count']}, total={result['total']}, first={result['first']}")

        browser.close()

if __name__ == "__main__":
    debug()
