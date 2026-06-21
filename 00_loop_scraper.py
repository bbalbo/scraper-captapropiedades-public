import os
import subprocess
import random
import time
from datetime import datetime
import sys

# === CONFIGURACIÓN =================================================================================================================
min_minutes = 2
max_minutes = 7
inactividad_extra = 5  # minutos extra de tolerancia
timeout_total = (max_minutes + inactividad_extra) * 60
tipo_propiedad = "casas"   # Opciones: "casas", "departamentos", "terrenos"
topx = 40
iterations = 8
# ===================================================================================================================================

script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "01_scraper.py")
python_exe = sys.executable

threshold_alert_403 = 3
threshold_alert_429 = 3
threshold_stop_403 = 10
threshold_stop_429 = 10

# Último timestamp de ejecución exitosa
last_exec_time = time.time()

# === LOOP INFINITO ===
while True:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n🕒 {now} → Ejecutando: scraper1.py")
    try:
        comando = f'"{python_exe}" "{script_path}" --tipo {tipo_propiedad} --topx {topx} --iterations {iterations}'
        start_time = time.time()
        result = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_total
        )
        tiempo_ejecucion = time.time() - start_time
        stdout = result.stdout.lower()
        stderr = result.stderr.lower()

        if result.returncode == 0 and "todas las páginas ya fueron scrapeadas" in stdout:
            print("✅ Detención detectada (código 0 y mensaje en stdout).")
            sys.exit(0)

        if tiempo_ejecucion < 20:
            print(f"⏱️ Ejecución demasiado rápida ({tiempo_ejecucion:.2f} segundos). Terminando loop.")
            sys.exit(0)

        count_403 = stdout.count("403") + stderr.count("403")
        count_429 = stdout.count("429") + stderr.count("429")

        if count_403 >= threshold_alert_403:
            print(f"⚠️ Alerta: {count_403} errores 403 (Forbidden).")

        if count_429 >= threshold_alert_429:
            print(f"⛔ Advertencia: {count_429} errores 429 (Too Many Requests).")

        if count_403 >= threshold_stop_403 or count_429 >= threshold_stop_429:
            print("🚨 Se alcanzó el umbral crítico de errores.")
            print(f"🚫 Deteniendo ejecución por exceso de errores HTTP (403: {count_403}, 429: {count_429})")
            break

        last_exec_time = time.time()


    except subprocess.TimeoutExpired:
        print(f"⏱️ Inactividad detectada: más de {timeout_total//60} minutos sin ejecución.")
        print("🚫 Terminando script por inactividad prolongada.")
        break

    except Exception as e:
        print(f"❌ Error al ejecutar scraper1.py: {e}")
        # esperar antes de continuar el loop, pero no intentar usar `result`
        wait_minutes = random.randint(min_minutes, max_minutes)
        print(f"⏳ Esperando {wait_minutes} minutos antes de la siguiente ejecución...\n")
        time.sleep(wait_minutes * 60)
        continue

    # Si no hubo error, espera aleatoria antes del próximo intento
    wait_minutes = random.randint(min_minutes, max_minutes)
    print(f"⏳ Esperando {wait_minutes} minutos antes de la siguiente ejecución...\n")
    time.sleep(wait_minutes * 60)

