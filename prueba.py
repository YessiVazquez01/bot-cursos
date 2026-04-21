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
# SERVIDOR PARA RENDER (OBLIGATORIO)
# ==============================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot funcionando")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

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

    try:
        response = requests.get(URL_CALENDARIO, headers=headers, timeout=10)
    except Exception as e:
        print("❌ Error de conexión:", e)
        return []

    if response.status_code != 200:
        print("❌ Error HTTP:", response.status_code)
        return []

    try:
        data = response.json()
    except:
        print("❌ No es JSON")
        return []

    cursos = []

    ahora = datetime.now()

    for c in data:
        apertura = c.get("fecha_apertura_preinscripcion")

        if not apertura:
            continue

        try:
            fecha_apertura = datetime.strptime(apertura, "%Y-%m-%d %H:%M:%S")
        except:
            continue

        # 🔥 SOLO FUTUROS
        if fecha_apertura > ahora:
            cursos.append({
                "nombre": c.get("nombre"),
                "lugar": c.get("lugar"),
                "modalidad": c.get("modalidad"),
                "apertura": apertura,
                "slug": c.get("slug")
            })

    print(f"📚 Total próximos encontrados: {len(cursos)}")
    return cursos

# ==============================
# TELEGRAM
# ==============================

def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID:
        print("❌ Falta TOKEN o CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        print("📡 STATUS TELEGRAM:", response.status_code)
    except Exception as e:
        print("❌ Error enviando a Telegram:", e)

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
# LOOP
# ==============================

def loop_bot():
    while True:
        try:
            ejecutar_bot()
        except Exception as e:
            print("❌ Error en el bot:", e)

        print("⏳ Esperando 5 minutos...\n")
        time.sleep(300)

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    loop_bot()
