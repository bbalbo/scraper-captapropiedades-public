# Scraper CaptaPropiedades

Pipeline de scraping y machine learning que extrae anuncios inmobiliarios de yapo.cl y estima, por anuncio, la probabilidad de que ya tenga un corredor a cargo — para identificar leads de captación (propietarios vendiendo sin intermediario).

Es el motor de datos detrás de [CaptaPropiedades](https://github.com/bbalbo/captapropiedades-public), una plataforma que estuvo en producción vendiendo estas bases filtradas a corredores de propiedades.

> 🇬🇧 [English version below](#scraper-captapropiedades-english)

---

## El pipeline

```
00_loop_scraper.py        → ejecuta el scraper repetidamente con pausas aleatorias (anti-bloqueo)
01_scraper.py              → scraping de yapo.cl (casas, departamentos, terrenos)
02_pipeline.py              → consolida varios días de scraping, elimina duplicados
03_heuristica_corredor.py    → reglas de texto → etiqueta inicial "es corredor" (0/1)
04a/04b_aplicar_modelo.py     → TF-IDF + Logistic Regression entrenado sobre la heurística → probabilidad continua
05_crea_bases.py                → filtra por zona y probabilidad, prioriza, exporta Excel formateado
verificar_faltantes.py           → QA: detecta huecos o inconsistencias en los datos scrapeados
```

Cada paso lee la salida del anterior desde una carpeta numerada (`salida1/` → `salida4/`, `bbdd_finales/`) — un pipeline de archivos simple, sin orquestador, pensado para correr como tarea programada en una sola máquina.

## El problema que resuelve

Encontrar propietarios vendiendo **sin** corredor entre cientos de anuncios por comuna no escala manualmente. El pipeline ataca esto en dos etapas:

1. **Heurística (`03`):** reglas de texto — nombres de inmobiliarias conocidas, frases típicas de corretaje, negadores explícitos ("vende dueño directo") — generan una etiqueta inicial razonablemente buena, sin necesidad de etiquetar miles de anuncios a mano.
2. **Modelo (`04a`/`04b`):** esas etiquetas alimentan un pipeline de `TfidfVectorizer` + `LogisticRegression` (scikit-learn) entrenado sobre el texto combinado de descripción y contacto. El modelo generaliza más allá de las reglas explícitas y entrega una **probabilidad continua** por anuncio, no solo una etiqueta binaria.

Es un patrón de *weak supervision*: usar reglas para generar etiquetas iniciales y entrenar un modelo encima que generaliza mejor que las reglas solas.

## Priorización por zona (`05_crea_bases.py`)

El paso final no solo filtra por probabilidad — también prioriza:

- Filtra anuncios con `probabilidad corredor ≤ 35%`
- Agrupa por zona geográfica (comunas agrupadas en macrozonas: Santiago Oriente, Gran Santiago, Chile Norte, Chile Sur, etc.)
- Ordena por fecha de publicación (los leads más recientes primero)
- Limita la cantidad de filas por zona según un cupo predefinido (`ZONAS_PRIORIDAD`)
- Exporta a Excel con formato condicional: la columna de probabilidad se colorea (verde/amarillo/rojo) según qué tan confiable es el lead

## Stack

| Etapa | Tecnología |
|---|---|
| Scraping | Python, requests/BeautifulSoup |
| Consolidación | pandas |
| Clasificación | scikit-learn (TF-IDF + Logistic Regression), NLTK |
| Reportes | pandas, openpyxl (formato condicional, anchos de columna, freeze panes) |

## Variables de entorno / configuración

Este pipeline corre con rutas relativas al propio directorio del script (`CARPETA_BASE`, `SALIDA_ZONAS`, `script_path`) y usa `sys.executable` para detectar el Python activo (`python_exe`), por lo que no requiere configuración adicional para correr en otra máquina.

## Nota sobre los datos

Este repositorio no incluye ninguna base de datos generada por el scraper (`bbdd_finales/`, `salida*/`) — son anuncios inmobiliarios reales extraídos de un portal público, y eran el producto comercial del proyecto, no datos personales. El código del pipeline completo sí está incluido y es funcional contra datos propios.

## Qué haría distinto hoy

- Reemplazar TF-IDF + Logistic Regression por embeddings preentrenados para generalizar mejor con vocabulario y formatos de anuncio nuevos.
- Reemplazar el pipeline de carpetas numeradas por un orquestador simple (aunque sea un Makefile o un script único con etapas), para que el orden y las dependencias entre pasos sean explícitos.
- Medir el modelo contra un set de datos etiquetado a mano, no solo contra las etiquetas que genera la propia heurística.

---

<a name="scraper-captapropiedades-english"></a>
## Scraper CaptaPropiedades (English)

A scraping + machine learning pipeline that extracts real-estate listings from yapo.cl and scores each one with the probability that it's already represented by an agent — surfacing leads where the owner is selling directly.

It's the data engine behind [CaptaPropiedades](https://github.com/bbalbo/captapropiedades-public), a platform that ran in production selling these filtered, scored listings to real-estate agents.

**Pipeline:** scrape → consolidate & dedupe → rule-based heuristic labels → TF-IDF + Logistic Regression model → zone-based filtering, prioritization, and formatted Excel export. This is a weak-supervision pattern: hand-written rules generate initial labels, and a model trained on those labels generalizes better than the rules alone.

See the Spanish section above for the full stack, pipeline breakdown, and notes on the data (real listings, not personal data, withheld because they were the project's commercial product).
