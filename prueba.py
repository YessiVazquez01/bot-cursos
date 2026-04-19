import json
import os
import time
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


# ==============================
# CONFIGURACIÓN
# ==============================

URL = "https://capacitaciondocente.educaciontuc.gov.ar/"
ARCHIVO = "cursos.json"

# Variables de entorno (Render o local)
TOKEN = os.getenv("8729216683:AAHuZbT2Pj8-XvISSOxS_D3EH8EyvnBi_nY")
CHAT_ID = os.getenv("1558517150")


# ==============================
# FUNCIÓN TELEGRAM
# ==============================

def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID:
        print("⚠️ TOKEN o CHAT_ID no configurados")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    params = {
        "chat_id": CHAT_ID,
        "text": mensaje
    }

    try:
        requests.get(url, params=params)
    except Exception as e:
        print("Error enviando mensaje:", e)


# ==============================
# FUNCIÓN SCRAPING
# ==============================

def obtener_cursos():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(URL)

    time.sleep(5)

    botones = driver.find_elements(By.XPATH, "//*[contains(text(), 'VER DETALLES')]")

    cursos = []

    for b in botones:
        try:
            contenedor = b.find_element(By.XPATH, "./ancestor::div[2]")
            texto = contenedor.text.strip()

            if texto not in cursos:
                cursos.append(texto)

        except:
            pass

    driver.quit()

    # Extraer solo títulos
    titulos = []

    for c in cursos:
        titulo = c.split("\n")[0]
        titulos.append(titulo)

    return list(set(titulos))


# ==============================
# FUNCIÓN PRINCIPAL
# ==============================

def ejecutar_bot():
    print("\n🔎 Buscando cursos...")

    titulos = obtener_cursos()

    # Leer cursos anteriores
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            anteriores = json.load(f)
    else:
        anteriores = []

    # Detectar nuevos
    nuevos = [c for c in titulos if c not in anteriores]

    if nuevos:
        print("🚨 NUEVOS CURSOS:\n")

        mensaje = "🚨 NUEVOS CURSOS:\n\n"

        for n in nuevos:
            print("-", n)
            mensaje += f"- {n}\n"

        enviar_telegram(mensaje)

    else:
        print("Sin cursos nuevos")

    # Guardar estado
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(titulos, f, ensure_ascii=False, indent=2)


# ==============================
# LOOP 24/7
# ==============================

if __name__ == "__main__":
    while True:
        ejecutar_bot()

        print("⏳ Esperando 2 hora...\n")
        time.sleep(7200)

def run_bot():
    while True:
        ejecutar_bot()
        time.sleep(3600)

# correr bot en segundo plano
threading.Thread(target=run_bot).start()

# servidor mínimo (para que Render esté feliz 😄)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot funcionando")

port = int(os.environ.get("PORT", 10000))
server = HTTPServer(("0.0.0.0", port), Handler)
server.serve_forever()
