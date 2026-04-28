"""
streamhdx.com scrapper - Con proxy residencial (mismo de WebShare)
Requiere variable de entorno: PROXY_URL
"""

import json
import time
import os
import re
from bs4 import BeautifulSoup
import curl_cffi.requests as requests

BASE_URL = "https://streamhdx.com"
OUTPUT_FILE = "partidos_streamhdx.json"
PROXY = os.environ.get("PROXY_URL", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://streamhdx.com/",
}

def get(url):
    kwargs = {"headers": HEADERS, "timeout": 30, "impersonate": "chrome120"}
    if PROXY:
        kwargs["proxies"] = {"http": PROXY, "https": PROXY}
    r = requests.get(url, **kwargs)
    r.raise_for_status()
    return r.text

def extract_matches():
    """Extrae todos los links de partidos desde la home"""
    print("📡 Cargando home...")
    html = get(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    matches = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Normalizar URL
        if href.startswith("/"):
            href = BASE_URL + href
        elif not href.startswith("http"):
            continue

        # Solo links internos que sean de partidos
        if BASE_URL not in href:
            continue
        # Excluir home, about, etc
        path = href.replace(BASE_URL, "")
        if path in ["", "/", "/about", "/contact", "/faq"] or path.startswith("/#"):
            continue

        title = a.get_text(strip=True)
        if href not in seen and title:
            seen.add(href)
            matches.append({"title": title, "url": href})

    print(f"✅ {len(matches)} partidos encontrados")
    return matches

def extract_streams(match_url):
    """Extrae los iframes/embeds de la página de un partido"""
    html = get(match_url)
    soup = BeautifulSoup(html, "html.parser")
    streams = []

    # Buscar iframes directos
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if src and src not in streams:
            streams.append(src)

    # Buscar en el JS inline (a veces el embed está en un script)
    if not streams:
        for script in soup.find_all("script"):
            text = script.string or ""
            found = re.findall(r'https?://[^\s"\'<>]+(?:embed|stream|player)[^\s"\'<>]+', text)
            for f in found:
                if f not in streams:
                    streams.append(f)

    # Buscar src en atributos data-*
    if not streams:
        for el in soup.find_all(attrs={"data-src": True}):
            src = el["data-src"]
            if "embed" in src or "stream" in src:
                streams.append(src)

    return streams

def main():
    if PROXY:
        print(f"🔒 Proxy: {PROXY.split('@')[-1]}")
    else:
        print("⚠️  Sin proxy — puede fallar en servidores cloud")

    matches = extract_matches()

    if not matches:
        print("❌ No se encontraron partidos")
        return

    results = []

    for i, m in enumerate(matches, 1):
        print(f"\n[{i}/{len(matches)}] ⚽ {m['title']}")
        try:
            streams = extract_streams(m["url"])
            entry = {
                "partido": m["title"],
                "url": m["url"],
                "streams": [{"embed": s} for s in streams]
            }
            results.append(entry)

            if streams:
                for s in streams:
                    print(f"    ✅ {s}")
            else:
                print("    ⚠️  Sin streams")

            time.sleep(1)
        except Exception as e:
            print(f"    ❌ Error: {e}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    total = sum(len(r["streams"]) for r in results)
    print(f"\n✅ {len(results)} partidos | {total} streams | Guardado: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
