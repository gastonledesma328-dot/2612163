import requests
from bs4 import BeautifulSoup
import json
import time

BASE_URL = "https://streamhdx.com"
OUTPUT_FILE = "partidos_streamhdx.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
}

def get_html(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

def extract_matches():
    html = get_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    matches = []

    # 🔥 esto depende del HTML real (puede variar)
    cards = soup.select("a")  # ajustar según estructura real

    for c in cards:
        href = c.get("href")
        title = c.text.strip()

        if "/watch" in str(href):
            matches.append({
                "title": title,
                "url": BASE_URL + href
            })

    return matches


def extract_streams(match_url):
    html = get_html(match_url)
    soup = BeautifulSoup(html, "html.parser")

    streams = []

    # 🔥 buscar iframes
    iframes = soup.find_all("iframe")
    for iframe in iframes:
        src = iframe.get("src")
        if src:
            streams.append(src)

    return streams


def main():
    print("📡 Buscando partidos...")
    matches = extract_matches()

    results = []

    for m in matches:
        print(f"\n⚽ {m['title']}")

        try:
            streams = extract_streams(m["url"])

            entry = {
                "partido": m["title"],
                "streams": [{"embed": s} for s in streams]
            }

            if streams:
                results.append(entry)

            time.sleep(1)

        except Exception as e:
            print("❌ Error:", e)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n✅ JSON generado")


if __name__ == "__main__":
    main()
