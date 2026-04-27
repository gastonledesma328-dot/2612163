import json
import time
import os
import re
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

# 🔥 NORMALIZAR TEXTO (clave para match)
def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())

# 🧠 obtener posters limpios
def get_poster_map():
    try:
        print("🖼️ Obteniendo posters...")
        r = requests.get("https://streamed.pk/category/football", headers=HEADERS)
        html = r.text

        posters = {}

        matches = re.findall(r'href="(/watch/.*?)".*?img src="(.*?)"', html, re.DOTALL)

        for link, img in matches:

            # 🔥 FILTRAR SOLO IMÁGENES REALES
            if not img.endswith((".jpg", ".png", ".webp")):
                continue

            if img.startswith("/"):
                img = BASE_URL + img

            if "streamed.pk" not in img:
                continue

            posters[link] = img

        print(f"✅ {len(posters)} posters válidos")
        return posters

    except Exception as e:
        print(f"❌ Error obteniendo posters: {e}")
        return {}

def parse_match_time(raw_time):
    try:
        # timestamp (ms)
        if isinstance(raw_time, int) or str(raw_time).isdigit():
            ts = int(raw_time) / 1000
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        # ISO
        return datetime.fromisoformat(raw_time.replace("Z", "+00:00"))

    except:
        return None

def main():
    if PROXY:
        print(f"🔒 Usando proxy: {PROXY.split('@')[-1]}")
    else:
        print("⚠️ Sin proxy configurado — puede fallar en servidores cloud")

    print("📡 Obteniendo partidos de fútbol...")
    matches = get(f"{BASE_URL}/api/matches/football")
    print(f"✅ {len(matches)} partidos totales")

    poster_map = get_poster_map()

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
            print(f"❌ Error parseando fecha: {raw_time}")
            continue

        match_time = match_time.astimezone(tz_ar)

        # 🔥 filtro 24h
        diff = abs((match_time - now).total_seconds())
        if diff > 86400:
            continue

        # 🔥 MATCH INTELIGENTE DE POSTER
        title_norm = normalize(title)
        poster = ""

        for link, img in poster_map.items():
            link_norm = normalize(link)

            if title_norm[:15] in link_norm:
                poster = img
                break

        sources = match.get("sources", [])

        print(f"\n[{i}] 🏟️ {title}")
        print(f"    🕒 {match_time.strftime('%H:%M')}")
        print(f"    🖼️ Poster: {poster}")

        entry = {
            "partido": title,
            "id": match.get("id"),
            "hora": match_time.strftime("%H:%M"),
            "poster": poster,
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

                    print(f"    ✅ [{hd}] {s.get('streamNo')}")

                time.sleep(0.3)

            except Exception as e:
                print(f"    ❌ {src['source']}: {e}")

        results.append(entry)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Guardado en: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
