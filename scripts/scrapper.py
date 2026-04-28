"""
streamed.pk - API oficial con proxy residencial
"""
import json
import time
import os
import curl_cffi.requests as requests

BASE_URL = "https://streamed.pk"
OUTPUT_FILE = "partidos_embeds.json"
PROXY = os.environ.get("PROXY_URL", "")

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://streamed.pk/category/football",
    "Origin": "https://streamed.pk",
}

def get(url):
    kwargs = {"headers": HEADERS, "timeout": 30, "impersonate": "chrome120"}
    if PROXY:
        kwargs["proxies"] = {"http": PROXY, "https": PROXY}
    r = requests.get(url, **kwargs)
    r.raise_for_status()
    return r.json()

def main():
    if PROXY:
        print(f"🔒 Proxy: {PROXY.split('@')[-1]}")
    else:
        print("⚠️  Sin proxy")

    print("📡 Obteniendo partidos de fútbol...")
    matches = get(f"{BASE_URL}/api/matches/football")
    print(f"✅ {len(matches)} partidos")

    results = []

    for i, match in enumerate(matches, 1):
        title = match.get("title", "Unknown")
        sources = match.get("sources", [])
        print(f"\n[{i}/{len(matches)}] 🏟️  {title}")

        entry = {"partido": title, "id": match.get("id"), "streams": []}

        for src in sources:
            try:
                streams = get(f"{BASE_URL}/api/stream/{src['source']}/{src['id']}")
                for s in streams:
                    embed = s.get("embedUrl", "")
                    hd = "HD" if s.get("hd") else "SD"
                    entry["streams"].append({
                        "source": src["source"],
                        "streamNo": s.get("streamNo"),
                        "quality": hd,
                        "language": s.get("language", ""),
                        "embed": embed
                    })
                    print(f"    ✅ [{hd}] Stream {s.get('streamNo')}: {embed}")
                time.sleep(0.3)
            except Exception as e:
                print(f"    ❌ {src['source']}: {e}")

        if not entry["streams"]:
            print("    ⚠️  Sin streams aún")

        results.append(entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total = sum(len(m["streams"]) for m in results)
    found = sum(1 for m in results for s in m["streams"] if s["embed"])
    print(f"\n✅ {len(results)} partidos | {found}/{total} embeds | Guardado: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
