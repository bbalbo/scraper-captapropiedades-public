import os
import re
import requests
from bs4 import BeautifulSoup

# === CONFIGURACIÓN ===
TIPOS_PROPIEDAD = {
    "casas": "casas",
    "departamentos": "apartamentos",  # 👈 esto es clave
    "terrenos": "lotes-y-terrenos"
}

CARPETA_TXT = "."
BASE_URL = "https://www.yapo.cl/searchresult/bienes-raices-venta-de-propiedades-{}"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def obtener_max_paginas(slug):
    try:
        url = BASE_URL.format(slug)
        html = requests.get(url, headers=HEADERS, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        last_btn = soup.select_one("a.d3-pagination__page--last")
        return int(re.sub(r"[^\d]", "", last_btn.text)) if last_btn else None
    except:
        return None

for nombre, slug in TIPOS_PROPIEDAD.items():
    path_txt = os.path.join(CARPETA_TXT, f"paginas_usadas_{nombre}.txt")
    if not os.path.exists(path_txt):
        print(f"❌ No se encontró: paginas_usadas_{nombre}.txt")
        continue

    try:
        with open(path_txt, "r", encoding="utf-8") as f:
            lineas = [int(x.strip()) for x in f if x.strip().isdigit()]
            paginas_visitadas = len(set(lineas))
    except Exception as e:
        print(f"⚠️ Error leyendo {path_txt}: {e}")
        continue

    max_pag = obtener_max_paginas(slug)
    if not max_pag:
        print(f"⚠️ No se pudo obtener la cantidad total de páginas para '{nombre}'")
        continue

    porcentaje = (paginas_visitadas / max_pag) * 100
    print(f"\n📄 Tipo: {nombre}")
    print(f"📌 Total en sitio: {max_pag} páginas")
    print(f"✅ Visitadas: {paginas_visitadas}")
    print(f"📉 Cobertura: {porcentaje:.2f}%")
