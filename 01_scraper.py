import os
import random
import uuid
import time
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import sys
import argparse

# === CONFIGURACIÓN ===
parser = argparse.ArgumentParser()
parser.add_argument("--tipo", type=str, default="casas", choices=["casas", "departamentos", "terrenos"])
parser.add_argument("--topx", type=int, default=30, choices=range(1, 101))  # entre 1 y 100
parser.add_argument("--iterations", type=int, default=5, choices=range(1, 51))  # entre 1 y 50
args = parser.parse_args()

TIPO_PROPIEDAD = args.tipo   
TOPX = args.topx
ITERATIONS = args.iterations


URLS_POR_TIPO = {
    "casas": "https://www.yapo.cl/searchresult/bienes-raices-venta-de-propiedades-casas",
    "departamentos": "https://www.yapo.cl/searchresult/bienes-raices-venta-de-propiedades-apartamentos",
    "terrenos": "https://www.yapo.cl/searchresult/bienes-raices-venta-de-propiedades-lotes-y-terrenos"
}

BASE_URL = URLS_POR_TIPO.get(TIPO_PROPIEDAD)
if not BASE_URL:
    raise ValueError(f"Tipo de propiedad inválido: {TIPO_PROPIEDAD}")

USADO_PATH = f"paginas_usadas_{TIPO_PROPIEDAD}.txt"
UF_VALUE = 39267.07

SALIDA_DIR = f"salida1/{TIPO_PROPIEDAD}"
os.makedirs(SALIDA_DIR, exist_ok=True)

# HEADERS = {
#     "User-Agent": random.choice([
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
#         "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
#         "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
#     ]),
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
#     "Accept-Language": "es-CL,es;q=0.9",
#     "Referer": "https://www.yapo.cl/",
#     "Connection": "keep-alive",
#     "DNT": "1",  # Do Not Track
#     "Upgrade-Insecure-Requests": "1"
# }

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def escape_excel_formula(s):
    return f"'{s}" if s.startswith(('=', '+', '-', '@')) else s

def obtener_numero_pagina(url):
    match = re.search(r"\.(\d+)$", url)
    return int(match.group(1)) if match else 1

def parse_price_per_m2(raw_value, uf_value):
    if not raw_value or raw_value == "N/A":
        return None
    raw = raw_value.replace(".", "").replace(",", "").strip().lower()
    if raw.startswith("uf"):
        try:
            return float(re.sub(r"[^\d.]+", "", raw))
        except:
            return None
    elif raw.startswith("$"):
        try:
            clp = int(re.sub(r"[^\d]", "", raw))
            return round(clp / uf_value, 2)
        except:
            return None
    return None

def parse_price(raw_price, uf_value):
    clean_text = re.sub(r"-\d+%", "", raw_price.lower()).replace(".", "").replace(",", "").strip()
    if "uf" in clean_text:
        match = re.search(r"uf(\d+(\.\d+)?)", clean_text)
        if match:
            uf = float(match.group(1))
            return int(uf * uf_value), uf
    elif "$" in clean_text:
        match = re.search(r"\$?(\d+)", clean_text)
        if match:
            clp = int(match.group(1))
            return clp, clp / uf_value
    return None, None

def export_to_excel(properties, filename):
    df = pd.DataFrame(properties)

    if df.empty:
        print("⚠️ No se extrajeron datos. No se generará Excel.")
        return

    if "published_date" in df.columns:
        df["published_date"] = pd.to_datetime(df["published_date"], format="%d/%m/%Y", errors="coerce")

    columnas_ordenadas = [
        "id", "title", "price", "price_clp", "price_uf", "url", "location",
        "meters", "bedrooms", "bathrooms", "published_date", "localization",
        "price_per_m2", "description", "contact_info"
    ]

    columnas_existentes = [col for col in columnas_ordenadas if col in df.columns]

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda x: escape_excel_formula(str(x).replace("\n", " ").strip()) if isinstance(x, str) else x)

    df.to_excel(filename, index=False, columns=columnas_existentes)
    print(f"\n✅ Excel exportado exitosamente: {filename}")

def get_html(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            html = response.text
            if not html.strip():
                print(f"⚠️ HTML vacío para URL: {url}")
            return html
        else:
            print(f"❌ Error HTTP {response.status_code} al acceder a {url}")
            return ""
    except Exception as e:
        print(f"❌ Excepción al acceder a {url}: {e}")
        return ""

def get_random_page_url():
    html = get_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    try:
        last_page = soup.select_one("a.d3-pagination__page--last")
        if last_page:
            max_page = int(re.sub(r"[^\d]", "", last_page.get_text()))
        else:
            raise ValueError("No se encontró el botón de última página.")
    except Exception as e:
        print(f"⚠️ No se pudo extraer la última página: {e}")
        max_page = 100

    used_pages = set()
    if os.path.exists(USADO_PATH):
        with open(USADO_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if re.fullmatch(r"\d+", line):  # solo líneas que sean números enteros puros
                    used_pages.add(int(line))


    available_pages = [p for p in range(1, max_page + 1) if p not in used_pages]
    
    if not available_pages:
        print("✅ Ya no hay más páginas para procesar. Fin del scraping.")
        sys.exit(100)


    random_page = random.choice(available_pages)
    return BASE_URL if random_page == 1 else f"{BASE_URL}.{random_page}"


def extract_detail_by_title(soup, label):
    items = soup.select(".d3-property-insight__attribute")
    for item in items:
        dt = item.select_one("dt")
        dd = item.select_one("dd")
        if dt and dd and label.lower() in dt.get_text(strip=True).lower():
            return dd.get_text(strip=True)
    return "N/A"

def extract_detail(soup, label):
    details = soup.select(".d3-property-details__detail-label")
    for d in details:
        if label in d.text:
            value = d.select_one(".d3-property-details__detail")
            return value.get_text(strip=True) if value else "N/A"
    return "N/A"

def safe_extract_detail(soup, label):
    try:
        return extract_detail(soup, label) or "N/A"
    except:
        return "N/A"

def extract_description(soup):
    desc = soup.select_one(".d3-property-about__text")
    return desc.get_text(separator=" ", strip=True) if desc else "Sin descripción"

def extract_contact_info(soup):
    name = soup.select_one(".contact_info .contact_name")
    role = soup.select_one(".contact_info .contact_address")
    return (
        name.get_text(strip=True) if name else "Sin nombre",
        role.get_text(strip=True) if role else "Sin rol"
    )

def safe_int(value):
    try:
        return int(re.sub(r"\D", "", value)) if value and re.search(r"\d", value) else None
    except:
        return None

def scrape(topx=30, iterations=1):
    results = []
    for i in range(iterations):
        page_url = get_random_page_url()
        print(f"[{i+1}/{iterations}] Scrapeando página: {page_url}")
        html = get_html(page_url)
        soup = BeautifulSoup(html, "html.parser")

        scraped_successfully = False

        for tile in soup.select(".d3-ad-tile")[:topx]:
            title = tile.select_one(".d3-ad-tile__title")
            price = tile.select_one(".d3-ad-tile__price")
            link = tile.select_one("a.d3-ad-tile__description")
            location = tile.select_one(".d3-ad-tile__location")

            href = link["href"] if link and "href" in link.attrs else None
            detail_url = f"https://www.yapo.cl{href}" if href else "Sin URL"

            detail_html = get_html(detail_url)
            detail_soup = BeautifulSoup(detail_html, "html.parser")

            contact_name, contact_role = extract_contact_info(detail_soup)
            contact_info = f"{contact_name} ({contact_role})"

            raw_price = extract_detail_by_title(detail_soup, "Precio")
            clp, uf = parse_price(raw_price, UF_VALUE)
            meters = extract_detail_by_title(detail_soup, "m²")
            bedrooms = extract_detail_by_title(detail_soup, "Dormitorios")
            bathrooms = extract_detail_by_title(detail_soup, "Baños")

            result = {
                "id": str(uuid.uuid4()),
                "title": title.text.strip() if title else "Sin título",
                "price": raw_price,
                "price_clp": clp,
                "price_uf": uf,
                "url": detail_url,
                "location": location.text.strip() if location else "Sin ubicación",
                "meters": safe_int(meters),
                "bedrooms": safe_int(bedrooms),
                "bathrooms": safe_int(bathrooms),
                "localization": extract_detail(detail_soup, "Localización"),
                "published_date": safe_extract_detail(detail_soup, "Publicado"),
                "price_per_m2": parse_price_per_m2(extract_detail(detail_soup, "Precio/M²"), UF_VALUE),
                "description": extract_description(detail_soup),
                "contact_info": contact_info
            }

            results.append(result)
            scraped_successfully = True

        page_number = obtener_numero_pagina(page_url)
        with open(USADO_PATH, "a") as f:
            f.write(f"{page_number}\n")

        if not scraped_successfully:
            print(f"⚠️ Página sin datos útiles: {page_url}")

        time.sleep(2)

    return results

if __name__ == "__main__":
    try:
        # Verificar si ya no quedan páginas por scrapear antes de empezar
        used_pages = set()
        if os.path.exists(USADO_PATH):
            with open(USADO_PATH, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.isdigit():
                        used_pages.add(int(line))

        html = get_html(BASE_URL)
        soup = BeautifulSoup(html, "html.parser")
        try:
            last_page = soup.select_one("a.d3-pagination__page--last")
            max_page = int(re.sub(r"[^\d]", "", last_page.get_text())) if last_page else 100
        except:
            max_page = 100

        if all(p in used_pages for p in range(1, max_page + 1)):
            print("📦 Todas las páginas ya fueron scrapeadas.")
            sys.exit(0)  # ✅ esto es CLAVE: debe ser 0 para indicar éxito y cortar el loop

        # Si aún quedan páginas por scrapear, continuar
        datos = scrape(topx=TOPX, iterations=ITERATIONS)
        now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filename = f"{SALIDA_DIR}/yapo_{TIPO_PROPIEDAD}_output_{now}.xlsx"
        export_to_excel(datos, filename)
        print(f"✅ Datos exportados a: {filename}")

    except Exception as e:
        print(f"❌ Error inesperado en 01_scraper.py: {e}")
        sys.exit(1)  # 👈 Indicamos que falló si hubo error
