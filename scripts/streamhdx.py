import json
import time
import os
import re
import unicodedata
from datetime import datetime, timedelta

import curl_cffi.requests as requests

# Fuente principal de eventos con canales
URL = "https://streamhdx.com/eventos.json"

# Worker propio con agenda ESPN + 365Scores en horario Argentina
AGENDA_URL = "https://partidos-hoy-worker.gastonledesma328.workers.dev"

OUTPUT_FILE = "eventos_streamhdx.json"
PROXY = os.environ.get("PROXY_URL", "")

# StreamHDX viene 2 horas atrasado en tu caso.
# Ejemplo: 11:45 debe quedar 13:45.
HORA_OFFSET_STREAMHDX = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://streamhdx.com/",
    "Accept": "application/json, */*",
}

HEADERS_AGENDA = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, */*",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def request_get_json(url, headers=None, timeout=30):
    kwargs = {
        "headers": headers or HEADERS,
        "timeout": timeout,
        "impersonate": "chrome120",
    }

    if PROXY:
        kwargs["proxies"] = {"http": PROXY, "https": PROXY}

    r = requests.get(url, **kwargs)
    r.raise_for_status()
    return r.json()


def get_eventos():
    print("Obteniendo eventos de streamhdx.com...")
    return request_get_json(
        f"{URL}?nocache={int(time.time() * 1000)}",
        headers=HEADERS,
        timeout=30,
    )


def get_agenda_worker():
    """
    Trae la agenda desde tu Worker.

    Importante:
    Esta agenda ya viene en horario Argentina.
    La usamos para corregir horarios cuando encontramos el mismo partido.
    """
    try:
        print("Obteniendo agenda del Worker...")
        data = request_get_json(
            f"{AGENDA_URL}?v={int(time.time() * 1000)}",
            headers=HEADERS_AGENDA,
            timeout=30,
        )

        partidos = data.get("partidos", [])

        if isinstance(partidos, list):
            print(f"Agenda Worker cargada: {len(partidos)} partidos")
            return partidos

    except Exception as e:
        print(f"⚠️ No se pudo cargar el Worker. Se usará offset +{HORA_OFFSET_STREAMHDX}h. Error: {e}")

    return []


def normalizar_texto(texto):
    texto = str(texto or "")
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def limpiar_equipo(nombre):
    texto = normalizar_texto(nombre)

    reemplazos = {
        "bayern munchen": "bayern munich",
        "psg": "paris saint germain",
        "de graafschap": "de graafschap",
        "almere city": "almere city",
        "torque": "montevideo city torque",
        "santa fe": "independiente santa fe",
        "olim pia": "olimpia",
        "olimpia": "club olimpia",
        "vasco da gama": "vasco da gama",
        "vasco": "vasco da gama",
    }

    return reemplazos.get(texto, texto)


def equipos_desde_titulo(titulo):
    """
    Extrae local y visitante desde títulos tipo:
    Eredivisie: Almere City vs De Graafschap
    Copa Libertadores: Cusco vs Estudiantes
    NBA Playoffs: Knicks vs. 76ers
    """
    titulo = str(titulo or "")

    if ":" in titulo:
        titulo = titulo.split(":", 1)[1].strip()

    partes = re.split(r"\s+vs\.?\s+", titulo, flags=re.I)

    if len(partes) < 2:
        return "", ""

    local = limpiar_equipo(partes[0])
    visitante = limpiar_equipo(partes[1])

    return local, visitante


def score_similitud(a, b):
    a = limpiar_equipo(a)
    b = limpiar_equipo(b)

    if not a or not b:
        return 0

    if a == b:
        return 100

    if a in b or b in a:
        return 85

    tokens_a = set(a.split())
    tokens_b = set(b.split())

    if not tokens_a or not tokens_b:
        return 0

    comunes = tokens_a.intersection(tokens_b)
    return int((len(comunes) / max(len(tokens_a), len(tokens_b))) * 100)


def buscar_en_worker(titulo, fecha_iso, agenda):
    """
    Busca el evento de StreamHDX dentro del Worker.

    Si lo encuentra, devuelve el partido del Worker.
    Si no lo encuentra, devuelve None.
    """
    local_stream, visitante_stream = equipos_desde_titulo(titulo)

    if not local_stream or not visitante_stream:
        return None

    mejor = None
    mejor_score = 0

    for partido in agenda:
        if fecha_iso and partido.get("fecha") and partido.get("fecha") != fecha_iso:
            continue

        local_worker = limpiar_equipo(partido.get("local", ""))
        visitante_worker = limpiar_equipo(partido.get("visitante", ""))

        directa = (
            score_similitud(local_stream, local_worker) +
            score_similitud(visitante_stream, visitante_worker)
        )

        invertida = (
            score_similitud(local_stream, visitante_worker) +
            score_similitud(visitante_stream, local_worker)
        )

        score = max(directa, invertida)

        if score > mejor_score:
            mejor_score = score
            mejor = partido

    # 130 suele ser buen mínimo para evitar falsos positivos.
    if mejor and mejor_score >= 130:
        return mejor

    return None


def sumar_horas(fecha_iso, hora, horas=2):
    """
    Suma horas a un horario HH:MM.

    También maneja cambio de día:
    23:30 + 2h -> 01:30 del día siguiente.
    """
    hora = str(hora or "").strip()

    if not re.match(r"^\d{1,2}:\d{2}$", hora):
        return fecha_iso, hora

    try:
        fecha_base = fecha_iso or "2000-01-01"
        dt = datetime.strptime(f"{fecha_base} {hora}", "%Y-%m-%d %H:%M")
        dt = dt + timedelta(hours=horas)

        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

    except Exception:
        return fecha_iso, hora


def fecha_legible_desde_iso(fecha_iso, fecha_original=""):
    """
    Mantiene la fecha original si no hay cambio.
    Si por sumar horas cambia el día, genera una fecha simple en español.
    """
    if not fecha_iso:
        return fecha_original

    try:
        dt = datetime.strptime(fecha_iso, "%Y-%m-%d")

        dias = [
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        ]

        meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

        return f"{dias[dt.weekday()]} {dt.day:02d} de {meses[dt.month - 1]} {dt.year}"

    except Exception:
        return fecha_original


def obtener_hora_corregida(evento, dia, agenda):
    """
    Regla de prioridad:

    1. Si el partido existe en el Worker, usamos hora_inicio/hora del Worker.
       Esa hora ya viene en Argentina.

    2. Si no existe en el Worker, corregimos StreamHDX sumando +2 horas.
       Esto arregla el caso Almere City 11:45 -> 13:45.
    """
    titulo = evento.get("titulo", "")
    fecha_iso = dia.get("fecha_iso", "")
    hora_original = evento.get("hora", "")

    partido_worker = buscar_en_worker(titulo, fecha_iso, agenda)

    if partido_worker:
        hora_worker = partido_worker.get("hora_inicio") or partido_worker.get("hora")

        if hora_worker and re.match(r"^\d{1,2}:\d{2}$", str(hora_worker)):
            return {
                "fecha_iso": partido_worker.get("fecha") or fecha_iso,
                "fecha": fecha_legible_desde_iso(partido_worker.get("fecha") or fecha_iso, dia.get("fecha", "")),
                "hora": str(hora_worker).zfill(5),
                "fuente_hora": "worker",
                "partido_worker": partido_worker.get("partido", ""),
            }

    nueva_fecha_iso, nueva_hora = sumar_horas(
        fecha_iso,
        hora_original,
        HORA_OFFSET_STREAMHDX,
    )

    return {
        "fecha_iso": nueva_fecha_iso,
        "fecha": fecha_legible_desde_iso(nueva_fecha_iso, dia.get("fecha", "")),
        "hora": nueva_hora,
        "fuente_hora": f"streamhdx_offset_+{HORA_OFFSET_STREAMHDX}h",
        "partido_worker": "",
    }


def main():
    data = get_eventos()
    agenda = get_agenda_worker()

    results = []
    total_eventos = 0
    total_canales = 0
    total_worker = 0
    total_offset = 0

    for dia in data.get("dias", []):
        fecha = dia.get("fecha", "")
        fecha_iso = dia.get("fecha_iso", "")

        print(f"\n{fecha} ({fecha_iso})")

        for evento in dia.get("eventos", []):
            titulo = evento.get("titulo", "")
            hora_original = evento.get("hora", "")
            canales = evento.get("canales", [])

            correccion = obtener_hora_corregida(evento, dia, agenda)

            hora_final = correccion["hora"]
            fecha_final = correccion["fecha"]
            fecha_iso_final = correccion["fecha_iso"]
            fuente_hora = correccion["fuente_hora"]

            if fuente_hora == "worker":
                total_worker += 1
            else:
                total_offset += 1

            print(f"  [{hora_original} -> {hora_final}] {titulo} ({fuente_hora})")

            entry = {
                "titulo": titulo,
                "categoria": evento.get("categoria", ""),
                "clase": evento.get("clase", ""),
                "fecha": fecha_final,
                "fecha_iso": fecha_iso_final,
                "hora": hora_final,
                "duracion_min": evento.get("duracion_min", 0),
                "canales": [],
            }

            for canal in canales:
                entry["canales"].append({
                    "nombre": canal.get("nombre", ""),
                    "calidad": canal.get("calidad", ""),
                    "url": canal.get("url", ""),
                })

                total_canales += 1
                print(f"    {canal.get('nombre')}: {canal.get('url')}")

            results.append(entry)
            total_eventos += 1

    results.sort(key=lambda x: (
        x.get("fecha_iso", ""),
        x.get("hora", ""),
        x.get("titulo", ""),
    ))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("")
    print(f"{total_eventos} eventos | {total_canales} canales | Guardado: {OUTPUT_FILE}")
    print(f"Horarios tomados del Worker: {total_worker}")
    print(f"Horarios corregidos con offset +{HORA_OFFSET_STREAMHDX}h: {total_offset}")


if __name__ == "__main__":
    main()
