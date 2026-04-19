import json
import os
import time
import requests
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from bs4 import BeautifulSoup


# ==============================
# CONFIG
# ==============================

URL = "https://capacitaciondocente.educaciontuc.gov.ar/"
ARCHIVO = "cursos.json"

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# ==============================
# TELEGRAM
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

    requests.get(url, params=params)


# ==============================
# SCRAPING (SIN SELENIUM 🔥)
# ==============================

def obtener_cursos():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    cursos = []

    elementos = soup.find_all("h5")

    for e in elementos:
        texto = e.text.strip()
        if len(texto) > 10:
            cursos.append(texto)

    return list(set(cursos))


# ==============================
# LOGICA PRINCIPAL
# ==============================

def ejecutar_bot():
    print("🔎 Buscando cursos...")

    titulos = obtener_cursos()

    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            anteriores = json.load(f)
    else:
        anteriores = []

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

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(titulos, f, ensure_ascii=False, indent=2)


# ==============================
# SERVIDOR PARA RENDER
# ==============================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot funcionando 🚀")


def iniciar_servidor():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"🌐 Servidor activo en puerto {port}")
    server.serve_forever()


# ==============================
# LOOP BOT
# ==============================

def loop_bot():
    while True:
        ejecutar_bot()
        print("⏳ Esperando 1 hora...\n")
        time.sleep(3600)


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    loop_bot()
