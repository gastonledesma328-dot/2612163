# Football Embeds Scrapper

Scrapper automático que extrae los links de embed de partidos de fútbol desde streamed.pk.

## ¿Cómo funciona?

- GitHub Actions corre el scrapper **cada 2 horas** automáticamente
- Los resultados se guardan en `partidos_embeds.json`
- También podés correrlo manualmente desde la pestaña **Actions** en GitHub

## Estructura del JSON

```json
[
  {
    "partido": "la-galaxy-vs-real-salt-lake-2406852",
    "url": "https://streamed.pk/watch/...",
    "streams": [
      {
        "stream_url": "https://streamed.pk/watch/.../admin/1",
        "embed": "https://embedsports.top/embed/admin/ppv-la-galaxy-vs-real-salt-lake/1"
      }
    ]
  }
]
```

## Acceder al JSON desde cualquier lado

Una vez que el repo es público, podés consumir el JSON así:

```
https://raw.githubusercontent.com/TU_USUARIO/TU_REPO/main/partidos_embeds.json
```

## Correr localmente

```bash
pip install playwright
playwright install chromium
python scripts/scrapper.py
```
