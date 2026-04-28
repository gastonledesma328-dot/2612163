import json
import time
import os
import curl_cffi.requests as requests

URL = "https://streamhdx.com/eventos.json"
OUTPUT_FILE = "eventos_streamhdx.json"
PROXY = os.environ.get("PROXY_URL", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://streamhdx.com/",
    "Accept": "application/json, */*",
}

def get_eventos():
    kwargs = {
        "headers": HEADERS,
        "timeout": 30,
        "impersonate": "chrome120",
    }
    if PROXY:
        kwargs["proxies"] = {"http": PROXY, "https": PROXY}
    r = requests.get(f"{URL}?nocache={int(time.time()*1000)}", **kwargs)
    r.raise_for_status()
    return r.json()

def main():
    print("Obteniendo eventos de streamhdx.com...")
    data = get_eventos()
    results = []
    total_eventos = 0
    total_canales = 0

    for dia in data.get("dias", []):
        fecha = dia.get("fecha", "")
        print(f"\n{fecha}")
        for evento in dia.get("eventos", []):
            titulo = evento.get("titulo", "")
            hora = evento.get("hora", "")
            canales = evento.get("canales", [])
            print(f"  [{hora}] {titulo}")
            entry = {
                "titulo": titulo,
                "categoria": evento.get("categoria", ""),
                "clase": evento.get("clase", ""),
                "fecha": fecha,
                "fecha_iso": dia.get("fecha_iso", ""),
                "hora": hora,
                "duracion_min": evento.get("duracion_min", 0),
                "canales": []
            }
            for canal in canales:
                entry["canales"].append({
                    "nombre": canal.get("nombre", ""),
                    "calidad": canal.get("calidad", ""),
                    "url": canal.get("url", "")
                })
                total_canales += 1
                print(f"    {canal.get('nombre')}: {canal.get('url')}")
            results.append(entry)
            total_eventos += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{total_eventos} eventos | {total_canales} canales | Guardado: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
