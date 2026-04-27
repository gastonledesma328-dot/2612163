import json
import time
import os
from datetime import datetime, timedelta, timezone
import urllib.parse
import curl_cffi.requests as requests

BASE_URL = "https://streamed.pk"
OUTPUT_FILE = "partidos_embeds.json"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://streamed.pk/category/football",
}

PROXY = os.environ.get("PROXY_URL", "")

def get(url):
    kwargs = {
        "headers": HEADERS,
        "timeout": 30,
        "impersonate": "chrome120",
    }
    if PROXY:
        kwargs["proxies"] = {"http": PROXY, "https": PROXY}
    
    r = requests.get(url, **kwargs)
    r.raise_for_status()
    return r.json()

# 🔥 parse fecha
def parse_match_time(raw_time):
    try:
        if isinstance(raw_time, int) or str(raw_time).isdigit():
            ts = int(raw_time) / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        return datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    except:
        return None

# 🔥 LOGO REAL (MUCHO MEJOR QUE POSTER)
def generate_logo(title):
    query = urllib.parse.quote(title)
    return f"https://crests.football-data.org/{query}.png"

# 🔥 fallback bonito
def fallback_image(title):
    safe = title.replace(" ", "+")
    return f"https://ui-avatars.com/api/?name={safe}&background=111&color=fff&size=256"

def main():
    print("📡 Obteniendo partidos...")
    matches = get(f"{BASE_URL}/api/matches/football")

    tz_ar = timezone(timedelta(hours=-3))
    now = datetime.now(tz_ar)

    results = []

    for i, match in enumerate(matches, 1):
        title = match.get("title", "Unknown")
        raw_time = match.get("startTime") or match.get("date")

        if not raw_time:
            continue

        match_time = parse_match_time(raw_time)
        if not match_time:
            continue

        match_time = match_time.astimezone(tz_ar)

        # filtro 24h
        diff = abs((match_time - now).total_seconds())
        if diff > 86400:
            continue

        # 🔥 intentar logo real
        poster = generate_logo(title)

        # si falla visualmente → fallback
        if not poster:
            poster = fallback_image(title)

        sources = match.get("sources", [])

        print(f"\n[{i}] {title}")
        print(f"🕒 {match_time.strftime('%H:%M')}")
        print(f"🖼️ {poster}")

        entry = {
            "partido": title,
            "hora": match_time.strftime("%H:%M"),
            "poster": poster,
            "streams": []
        }

        for src in sources:
            try:
                streams = get(f"{BASE_URL}/api/stream/{src['source']}/{src['id']}")

                for s in streams:
                    entry["streams"].append({
                        "embed": s.get("embedUrl", "")
                    })

                time.sleep(0.3)

            except:
                pass

        if entry["streams"]:
            results.append(entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n✅ JSON generado")

if __name__ == "__main__":
    main()
