import json
import time
import os
from datetime import datetime, timedelta, timezone
import curl_cffi.requests as requests

BASE_URL = "https://streamed.pk"
OUTPUT_FILE = "partidos_embeds.json"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://streamed.pk/category/football",
    "Origin": "https://streamed.pk",
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

def main():
    if PROXY:
        print(f"🔒 Usando proxy: {PROXY.split('@')[-1]}")
    else:
        print("⚠️  Sin proxy configurado — puede fallar en servidores cloud")

    print("📡 Obteniendo partidos de fútbol...")
    matches = get(f"{BASE_URL}/api/matches/football")
    print(f"✅ {len(matches)} partidos totales")

    # 🧠 Hora actual en Argentina (UTC-3)
    now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(
        timezone(timedelta(hours=-3))
    )

    results = []

    for i, match in enumerate(matches, 1):
        title = match.get("title", "Unknown")
        raw_time = match.get("startTime") or match.get("date")

        if not raw_time:
            continue

        try:
            # 🔥 Parseo correcto ISO + zona horaria
            match_time = datetime.fromisoformat(
                raw_time.replace("Z", "+00:00")
            )

            # 🔄 Convertir a Argentina
            match_time = match_time.astimezone(
                timezone(timedelta(hours=-3))
            )

        except Exception as e:
            print(f"❌ Error parseando fecha: {raw_time}")
            continue

        # 🔥 FILTRO INTELIGENTE (24h antes/después)
        diff = abs((match_time - now).total_seconds())

        if diff > 86400:  # 24 horas
            continue

        sources = match.get("sources", [])

        print(f"\n[{i}] 🏟️ {title}")
        print(f"    🕒 Hora AR: {match_time.strftime('%H:%M')}")

        entry = {
            "partido": title,
            "id": match.get("id"),
            "hora": match_time.strftime("%H:%M"),
            "streams": []
        }

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

                    print(f"    ✅ [{hd}] {s.get('streamNo')}: {embed}")

                time.sleep(0.3)

            except Exception as e:
                print(f"    ❌ {src['source']}: {e}")

        if not entry["streams"]:
            print("    ⚠️ Sin streams aún")

        results.append(entry)

    # 💾 Guardar JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total = sum(len(m["streams"]) for m in results)
    found = sum(1 for m in results for s in m["streams"] if s["embed"])

    print(f"\n✅ {len(results)} partidos filtrados (24h) | {found}/{total} embeds")
    print(f"📁 Guardado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
