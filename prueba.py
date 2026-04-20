import requests
import time
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# ==============================
# CONFIGURACIÓN
# ==============================

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

URL_CALENDARIO = "https://apicapacitaciones.educaciontuc.edu.ar/api/gestionCapas/calendario"

ARCHIVO_GUARDADO = "cursos_enviados.json"

# ==============================
# SERVIDOR PARA RENDER (IMPORTANTE)
# ==============================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot funcionando")

def iniciar_servidor():
    puerto = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", puerto), Handler)
    print(f"🌐 Servidor activo en puerto {puerto}")
    server.serve_forever()

# ==============================
# UTILIDADES
# ==============================

def formatear_fecha(fecha_str):
    if not fecha_str:
        return "Sin fecha"
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d %H:%M:%S")
        return fecha.strftime("%d/%m/%Y %H:%M")
    except:
        return fecha_str

def cargar_enviados():
    try:
        with open(ARCHIVO_GUARDADO, "r") as f:
            return set(json.load(f))
    except:
        return set()

def guardar_enviados(lista):
    with open(ARCHIVO_GUARDADO, "w") as f:
        json.dump(list(lista), f)

# ==============================
# OBTENER CURSOS PRÓXIMOS
# ==============================

def obtener_proximos():
    headers = {
        "accept": "application/json",
        "origin": "https://capacitaciondocente.educaciontuc.gov.ar",
        "referer": "https://capacitaciondocente.educaciontuc.gov.ar/",
        "user-agent": "Mozilla/5.0"
    }

    response = requests.get(URL_CALENDARIO, headers=headers)

    if response.status_code != 200:
        print("❌ Error al obtener datos")
        return []

    try:
        data = response.json()
    except:
        print("❌ No es JSON")
        return []

    cursos = []

    for c in data:
        # Solo cursos que todavía NO abrieron inscripción
        if c.get("fecha_apertura_preinscripcion") and c.get("nombre"):

            cursos.append({
                "nombre": c.get("nombre"),
                "lugar": c.get("lugar"),
                "modalidad": c.get("modalidad"),
                "apertura": c.get("fecha_apertura_preinscripcion"),
                "slug": c.get("slug")
            })

    print(f"📚 Total próximos encontrados: {len(cursos)}")
    return cursos

# ==============================
# ENVIAR A TELEGRAM
# ==============================

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    response = requests.post(url, data=data)

    print("📡 STATUS TELEGRAM:", response.status_code)
    print("📩 RESPUESTA TELEGRAM:", response.text)

# ==============================
# BOT PRINCIPAL
# ==============================

def ejecutar_bot():
    print("\n🔎 Buscando cursos...")

    cursos = obtener_proximos()
    enviados = cargar_enviados()

    nuevos = []

    for c in cursos:
        identificador = c["nombre"] + str(c["apertura"])

        if identificador not in enviados:

            apertura = formatear_fecha(c["apertura"])
            link = f"https://capacitaciondocente.educaciontuc.gov.ar/#/capacitacion/{c['slug']}"

            mensaje = f"""
🟣 <b>PRÓXIMA CAPACITACIÓN</b>

📚 <b>{c['nombre']}</b>

🎓 Modalidad: {c['modalidad']}
📍 Lugar: {c['lugar']}

🟢 Apertura de inscripción:
{apertura}

🔗 <a href="{link}">Ver detalles del curso</a>
"""

            enviar_telegram(mensaje)

            enviados.add(identificador)
            nuevos.append(c["nombre"])

    guardar_enviados(enviados)

    if nuevos:
        print(f"✅ Enviados {len(nuevos)} cursos nuevos")
    else:
        print("✅ Sin cursos nuevos")

# ==============================
# LOOP CADA 5 MINUTOS
# ==============================

def loop_bot():
    while True:
        ejecutar_bot()
        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    # Servidor para Render
    threading.Thread(target=iniciar_servidor).start()

    # Ejecutar bot
    loop_bot()
