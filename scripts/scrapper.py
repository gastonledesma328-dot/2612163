import json
import time
from playwright.sync_api import sync_playwright

BASE_URL = "https://streamhdx.com"
OUTPUT_FILE = "partidos_streamhdx.json"


def get_html(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(3000)  # esperar carga JS
    return page.content()


def extract_matches(page):
    html = get_html(page, BASE_URL)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.text.strip()

        if "/watch" in href:
            full_url = href if href.startswith("http") else BASE_URL + href

            matches.append({
                "title": title if title else "Sin título",
                "url": full_url
            })

    return matches


def extract_streams(page, match_url):
    html = get_html(page, match_url)

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    streams = []

    # 🔥 iframes reales
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            streams.append(src)

    # 🔥 buscar m3u8 directo en scripts
    scripts = soup.find_all("script")
    for s in scripts:
        if s.string and ".m3u8" in s.string:
            streams.append(s.string)

    return list(set(streams))


def main():
    print("📡 Buscando partidos...")

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        matches = extract_matches(page)

        print(f"🎯 Encontrados: {len(matches)}")

        for m in matches:
            print(f"\n⚽ {m['title']}")

            try:
                streams = extract_streams(page, m["url"])

                if not streams:
                    print("⚠️ Sin streams")
                    continue

                entry = {
                    "partido": m["title"],
                    "streams": [{"embed": s} for s in streams]
                }

                results.append(entry)

                print(f"✅ {len(streams)} streams encontrados")

                time.sleep(1)

            except Exception as e:
                print("❌ Error:", e)

        browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n✅ JSON generado con", len(results), "partidos")


if __name__ == "__main__":
    main()
