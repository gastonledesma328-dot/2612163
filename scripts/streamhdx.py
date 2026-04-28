"""
Script de inspección - correrlo localmente para ver la estructura del sitio
"""
import curl_cffi.requests as requests
from bs4 import BeautifulSoup
import os

PROXY = os.environ.get("PROXY_URL", "")

def get(url):
    kwargs = {"impersonate": "chrome120", "timeout": 30}
    if PROXY:
        kwargs["proxies"] = {"http": PROXY, "https": PROXY}
    r = requests.get(url, **kwargs)
    return r.text

html = get("https://streamhdx.com/")
soup = BeautifulSoup(html, "html.parser")

print("=== TODOS LOS LINKS ===")
for a in soup.find_all("a", href=True)[:30]:
    print(f"  {a['href']!r:50} | {a.get_text(strip=True)[:40]}")

print("\n=== CLASES DE CONTENEDORES ===")
for tag in soup.find_all(["div","section","ul"], class_=True)[:20]:
    print(f"  <{tag.name} class='{' '.join(tag.get('class',[]))[:60]}'>")
