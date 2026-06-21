import os
import pandas as pd
from datetime import datetime
import re
import unicodedata

# === CONFIGURACIÓN ===
TIPOS_PROPIEDAD = ["casas", "departamentos", "terrenos"]
FOLDER_ENTRADA_BASE = "salida2"
FOLDER_SALIDA_BASE = "salida3"
fecha_actual = datetime.now().strftime("%Y-%m-%d")

def texto_raro(texto):
    if pd.isna(texto):
        return True
    texto = str(texto)
    if re.search(r'[A-Z]{3,}', texto): return True
    if re.search(r'[0-9]{6,}', texto): return True
    if re.search(r'-{2,}', texto): return True
    if len(texto.strip()) < 10: return True
    return False

def detectar_corredor(contacto, descripcion):
    def clean(text):
        text = str(text).lower()
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
        text = re.sub(r'[^a-z0-9áéíóúñ\s]', ' ', text)  # ← Elimina símbolos como "/", "(", etc.
        return re.sub(r'\s+', ' ', text).strip()

    contacto = clean(contacto)
    descripcion = clean(descripcion)
    texto = contacto + " " + descripcion

    palabras_contacto = [
        "propiedades", "spa", "inmobiliaria", "gestion", "gestora", "consultora",
        "servicios", "empresa", "inversiones", "agente", "realty", "property", "broker",
        "partner", "premium", "group", "grupo", "crm", "matteri"
    ]

    palabras_descripcion = [
        "corredor", "comision", "intermediario", "administrado por",
        "honorarios de corretaje", "publicado usando", "vende broker",
        "arrienda broker", "broker and partner", "honorarios",
        "trato directo con corredora", "contacta a elitte propiedades", "codigo"
    ]

    marcas_conocidas = [
        "remax", "century 21", "engel", "volkers", "procasa", "santander inmobiliaria",
        "alma inmobiliaria", "brokers", "fullhouse", "mg inmobiliaria", "synergy", "premier",
        "vivaqui", "easy prop", "kiteprop", "grupo premium", "asin propiedades", "re max"
    ]

    negadores = [
        "vende dueno", "vende duena", "vende dueño", "vende dueña", "dueño directo", "dueno directo", "venta directa", "sin corredor",
        "abstenerse corredores", "no corredores", "sin comision", "trato directo"
    ]

    # === 1. Exclusión explícita ===
    if any(p in texto for p in negadores):
        return 0

    # === 2. Indicadores fuertes ===
    if any(p in texto for p in palabras_contacto + palabras_descripcion + marcas_conocidas):
        return 1

    if "publicado usando" in texto or "kiteprop" in texto:
        return 1

    if re.search(r'\bcod(igo)?\.?\s?[a-z0-9\-]{2,}', texto):
        return 1

    if re.search(r'comision\s+\d+%|\d+%.*comision', texto):
        return 1

    # === 3. Patrón de empresa: Nombre compuesto con guión ===
    if re.search(r"[a-záéíóúñ]+ [a-záéíóúñ]+ - [a-záéíóúñ]+", contacto):
        return 1

    # === 4. Nombre poco claro ===
    pocas_palabras = len(contacto.split()) <= 2
    no_es_nombre = not re.fullmatch(r"[a-záéíóúñ]+ [a-záéíóúñ]+", contacto)
    if pocas_palabras and no_es_nombre:
        return 1

    # === 5. Nombre + aclaración entre paréntesis: lo dejamos pasar ===
    if re.fullmatch(r"[a-záéíóúñ]+ [a-záéíóúñ]+ \(.*\)", contacto):
        return 0

    return 0

# === Procesar cada tipo de propiedad ===
for tipo in TIPOS_PROPIEDAD:
    folder_entrada = os.path.join(FOLDER_ENTRADA_BASE, tipo)
    folder_salida = os.path.join(FOLDER_SALIDA_BASE, tipo)
    os.makedirs(folder_salida, exist_ok=True)

    nombre_archivo = f"consolidado_yapo_{fecha_actual}.xlsx"
    ruta_entrada = os.path.join(folder_entrada, nombre_archivo)

    if not os.path.exists(ruta_entrada):
        print(f"❌ Archivo no encontrado para {tipo}: {ruta_entrada}")
        continue

    print(f"\n📂 Procesando {tipo}: {ruta_entrada}")
    df = pd.read_excel(ruta_entrada)

    df["Es Corredor (Heurística)"] = df.apply(
        lambda fila: detectar_corredor(fila.get("Contacto", ""), fila.get("Descripción", "")),
        axis=1
    )

    print(df[["Título", "Contacto", "Descripción", "Es Corredor (Heurística)"]].head(10))
    print(df["Es Corredor (Heurística)"].value_counts(dropna=False))

    nombre_salida = f"consolidado_corredor_heuristica_{fecha_actual}.xlsx"
    ruta_salida = os.path.join(folder_salida, nombre_salida)
    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Hoja1')

    print(f"✅ Archivo guardado: {ruta_salida}")
