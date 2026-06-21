import os
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# === CONFIGURACIÓN GENERAL ===
N_FECHAS_RECIENTES = 3
FOLDER_ENTRADA_BASE = "salida1"
FOLDER_SALIDA_BASE = "salida2"
TIPOS_PROPIEDAD = ["casas", "departamentos", "terrenos"]
fecha_actual = datetime.now().strftime("%Y-%m-%d")


# === Función auxiliar para extraer la fecha del nombre del archivo ===
def extraer_fecha_archivo(nombre_archivo):
    try:
        partes = nombre_archivo.split("_")
        fecha_str = partes[3]  # ej: '2025-07-21'
        return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except Exception:
        return None


# === Procesar por tipo de propiedad ===
for tipo in TIPOS_PROPIEDAD:
    folder_entrada = os.path.join(FOLDER_ENTRADA_BASE, tipo)
    folder_salida = os.path.join(FOLDER_SALIDA_BASE, tipo)
    os.makedirs(folder_salida, exist_ok=True)

    archivo_salida = f"consolidado_yapo_{fecha_actual}.xlsx"
    output_path = os.path.join(folder_salida, archivo_salida)

    # Buscar archivos válidos con fecha reconocible
    archivos_con_fechas = []
    for f in os.listdir(folder_entrada):
        if f.startswith(f"yapo_{tipo}_output_") and f.endswith(".xlsx"):
            fecha = extraer_fecha_archivo(f)
            if fecha:
                archivos_con_fechas.append((f, fecha))

    # Seleccionar los archivos con las N fechas más recientes
    fechas_unicas = sorted({fecha for _, fecha in archivos_con_fechas}, reverse=True)[:N_FECHAS_RECIENTES]
    archivos = [f for f, fecha in archivos_con_fechas if fecha in fechas_unicas]

    if not archivos:
        print(f"⚠️ No hay archivos recientes para '{tipo}'")
        continue

    print(f"\n📂 [{tipo}] Archivos seleccionados (últimos {N_FECHAS_RECIENTES} días):")
    for f in archivos:
        print(f"   • {f}")

    # === Cargar y concatenar ===
    dataframes = []

    for archivo in archivos:
        path = os.path.join(folder_entrada, archivo)

        if os.path.getsize(path) < 5 * 1024:
            print(f"⚠️ Archivo omitido por tamaño sospechoso: {archivo}")
            continue

        try:
            df = pd.read_excel(path, engine="openpyxl")
            dataframes.append(df)
            print(f"✅ Cargado ({tipo}): {archivo} ({len(df)} filas)")
        except Exception as e:
            print(f"❌ Error en {archivo}: {e}")

    if not dataframes:
        print(f"⚠️ No se pudieron cargar archivos válidos para '{tipo}'")
        continue

    # === Consolidar y limpiar ===
    combinado = pd.concat(dataframes, ignore_index=True)
    print(f"\n📊 [{tipo}] Registros antes de eliminar duplicados: {len(combinado)}")

    combinado['published_date'] = pd.to_datetime(combinado['published_date'], errors='coerce')
    combinado = combinado.sort_values(by='published_date', ascending=False)

    combinado = combinado.drop_duplicates(subset=["id", "title", "description"], keep="first")

    print(f"✅ [{tipo}] Registros únicos tras limpieza: {len(combinado)}")

    # === Seleccionar y renombrar columnas ===
    columnas_finales = [
        "title", "price_clp", "price_uf", "url", "location",
        "meters", "bedrooms", "bathrooms", "published_date",
        "localization", "price_per_m2", "description", "contact_info"
    ]

    combinado = combinado[columnas_finales].rename(columns={
        "title": "Título",
        "price_clp": "Precio CLP",
        "price_uf": "Precio UF",
        "url": "URL",
        "location": "Ubicación",
        "meters": "Metros²",
        "bedrooms": "Dormitorios",
        "bathrooms": "Baños",
        "published_date": "Fecha Publicación",
        "localization": "Comuna",
        "price_per_m2": "Precio x m²",
        "description": "Descripción",
        "contact_info": "Contacto"
    })

    # === Exportar a Excel ===
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        combinado.to_excel(writer, index=False, sheet_name='Hoja1')

    # === Ajustar ancho de columnas ===
    wb = load_workbook(output_path)
    ws = wb.active
    for column_cells in ws.columns:
        col_letter = get_column_letter(column_cells[0].column)
        header = column_cells[0].value
        if header == "Descripción":
            ws.column_dimensions[col_letter].width = 80
        else:
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            ws.column_dimensions[col_letter].width = max_length + 2
    wb.save(output_path)

    print(f"📁 Consolidado guardado: {output_path}")
