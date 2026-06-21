import os
import pandas as pd
import nltk
import joblib
from datetime import datetime
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from openpyxl.utils import get_column_letter
from openpyxl import load_workbook

def normalizar_es_corredor(valor):
    if pd.isna(valor):
        return None
    try:
        valor = str(valor).strip().lower()
        if valor in {'1', '1.0', 'si', 'sí', 'true'}:
            return 1
        if valor in {'0', '0.0', 'no', 'false'}:
            return 0
    except:
        return None
    return None



# === CONFIGURACIÓN GENERAL ===
ENTRENAR_MODELO = False  # ⚙️ No reentrena el modelo
FECHA_MODELO = None      # 🗓️ Especifica '2025-05-28' o deja None para usar el modelo más reciente
TIPOS_PROPIEDAD = ["casas", "departamentos", "terrenos"]
FOLDER_ENTRADA_BASE = "salida3"
FOLDER_SALIDA_BASE = "salida4"
FECHA_ACTUAL = datetime.now().strftime("%Y-%m-%d")

nltk.download('stopwords')
stopwords_es = stopwords.words('spanish')

os.makedirs(FOLDER_SALIDA_BASE, exist_ok=True)

for tipo in TIPOS_PROPIEDAD:
    folder_entrada = os.path.join(FOLDER_ENTRADA_BASE, tipo)
    folder_salida = os.path.join(FOLDER_SALIDA_BASE, tipo)
    os.makedirs(folder_salida, exist_ok=True)

    archivo_entrada = f"consolidado_corredor_heuristica_{FECHA_ACTUAL}.xlsx"
    ruta_entrada = os.path.join(folder_entrada, archivo_entrada)

    if not os.path.exists(ruta_entrada):
        print(f"❌ No se encontró archivo de entrada para {tipo}: {ruta_entrada}")
        continue

    print(f"\n📂 Procesando: {ruta_entrada}")
    df = pd.read_excel(ruta_entrada)

    df = df.drop_duplicates()
    df = df.dropna(subset=['Descripción', 'Contacto', 'Es Corredor (Heurística)'])

    df['Descripción'] = df['Descripción'].fillna('')
    df['Contacto'] = df['Contacto'].fillna('')
    df['texto_combinado'] = df['Descripción'] + ' ' + df['Contacto']
    df["Es Corredor (Heurística)"] = df["Es Corredor (Heurística)"].astype(str)

    df['es_corredor'] = df['Es Corredor (Heurística)'].apply(normalizar_es_corredor)
    print(f"[{tipo}] Conteo es_corredor después de normalizar:\n", df['es_corredor'].value_counts(dropna=False))


    df = df.dropna(subset=['texto_combinado', 'es_corredor'])

    X = df['texto_combinado']
    y = df['es_corredor']

    modelo_path = None
    modelo_pattern = f"modelo_entrenado_{tipo}_"

    if ENTRENAR_MODELO:
        print(f"⚙️ Entrenando nuevo modelo para '{tipo}'...")
        if len(set(y)) < 2:
            print(f"⚠️ Solo se encontró una clase en '{tipo}'. No se entrena modelo.")
            continue

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                stop_words=stopwords_es,
                ngram_range=(1, 2),
                max_features=5000
            )),
            ('clf', LogisticRegression(solver='liblinear'))
        ])

        pipeline.fit(X_train, y_train)

        modelo_filename = f"{modelo_pattern}{FECHA_ACTUAL}.pkl"
        modelo_path = os.path.join(folder_salida, modelo_filename)
        joblib.dump(pipeline, modelo_path)

        print(f"💾 Modelo guardado en: {modelo_path}")
        print(f"\n📊 Evaluación del modelo ({tipo}):\n")
        print(classification_report(y_test, pipeline.predict(X_test)))

    else:
        print(f"🔍 Buscando modelo para '{tipo}'...")
        archivos_modelos = [
            f for f in os.listdir(folder_salida)
            if f.startswith(modelo_pattern) and f.endswith(".pkl")
        ]

        if not archivos_modelos:
            print(f"❌ No hay modelos previos guardados para '{tipo}'.")
            continue

        if FECHA_MODELO:
            modelo_nombre = f"{modelo_pattern}{FECHA_MODELO}.pkl"
            if modelo_nombre in archivos_modelos:
                modelo_path = os.path.join(folder_salida, modelo_nombre)
                print(f"📦 Cargando modelo de fecha específica: {modelo_path}")
            else:
                print(f"❌ No se encontró el modelo para la fecha {FECHA_MODELO}.")
                continue
        else:
            modelo_path = os.path.join(
                folder_salida,
                max(archivos_modelos, key=lambda f: os.path.getmtime(os.path.join(folder_salida, f)))
            )
            print(f"📦 Cargando modelo más reciente: {modelo_path}")

        pipeline = joblib.load(modelo_path)

    # Usar modelo cargado para predecir
    df['probabilidad_corredor'] = pipeline.predict_proba(df['texto_combinado'])[:, 1]

    archivo_salida = f"con_probabilidades_{FECHA_ACTUAL}.xlsx"
    ruta_salida = os.path.join(folder_salida, archivo_salida)
    with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Hoja1')

    print(f"✅ Archivo exportado con probabilidades: {ruta_salida}")
