"""
Scrapper streamed.pk - Optimizado para GitHub Actions
"""
import json, time, re
from playwright.sync_api import sync_playwright

BASE_URL = "https://streamed.pk"
CATEGORY_URL = f"{BASE_URL}/category/football"
OUTPUT_FILE = "partidos_embeds.json"

def get_match_links(page):
    print("📡 Cargando partidos...")
    page.goto(CATEGORY_URL, wait_until="domcontentloaded", timeout=60000)
    time.sleep(5)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    content = page.content()
    hrefs = re.findall(r'href=["\'](/watch/[^/"\']+)["\']', content)
    seen = set()
    urls = []
    for h in hrefs:
        u = BASE_URL + h
        if u not in seen:
            seen.add(u); urls.append(u)
    print(f"✅ {len(urls)} partidos")
    return urls

def get_stream_links(page, match_url):
    page.goto(match_url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(4)
    content = page.content()
    hrefs = re.findall(r'href=["\'](/watch/[^"\']+/[^"\']+/\d+)["\']', content)
    seen = set(); urls = []
    for h in hrefs:
        u = BASE_URL + h
        if u not in seen:
            seen.add(u); urls.append(u)
    return urls

def get_embed_src(page, stream_url):
    captured = []
    def on_request(req):
        url = req.url
        if "embedsports" in url or "embed" in url.lower():
            if url not in captured: captured.append(url)
    page.on("request", on_request)
    try:
        page.goto(stream_url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(4)
        for sel in ['button:has-text("Embed")', 'a:has-text("Embed")']:
            try:
                btn = page.query_selector(sel)
                if btn: btn.click(); time.sleep(2); break
            except: pass
        content = page.content()
        m = re.findall(r'src=["\']([^"\']*embedsports\.top[^"\']*)["\']', content)
        if m: return m[0]
        m = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', content)
        for x in m:
            if "embed" in x: return x
        for url in captured:
            if "embedsports.top/embed" in url: return url
        return captured[0] if captured else None
    except Exception as e:
        print(f"    ❌ {e}"); return None
    finally:
        page.remove_listener("request", on_request)

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox",
                  "--disable-dev-shm-usage","--disable-blink-features=AutomationControlled"]
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = ctx.new_page()
        match_urls = get_match_links(page)
        if not match_urls:
            print("❌ Sin partidos"); browser.close(); return
        for i, mu in enumerate(match_urls, 1):
            name = mu.split("/watch/")[-1]
            print(f"\n[{i}/{len(match_urls)}] 🏟️  {name}")
            streams = get_stream_links(page, mu)
            entry = {"partido": name, "url": mu, "streams": []}
            for su in streams:
                embed = get_embed_src(page, su)
                entry["streams"].append({"stream_url": su, "embed": embed})
                print(f"    {'✅ '+embed if embed else '⚠️  Sin embed'}")
                time.sleep(1)
            results.append(entry)
        browser.close()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    total = sum(len(m["streams"]) for m in results)
    found = sum(1 for m in results for s in m["streams"] if s["embed"])
    print(f"\n✅ {len(results)} partidos | {found}/{total} embeds | Guardado: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
