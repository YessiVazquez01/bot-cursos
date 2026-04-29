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
URL_ACTIVAS = "https://apicapacitaciones.educaciontuc.edu.ar/api/gestionCapas/getCapaActivas"

ARCHIVO_GUARDADO = "cursos_enviados.json"
ARCHIVO_ESTADO = "estado_inscripcion.json"

# ==============================
# SERVIDOR PARA RENDER
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

# ESTADO DE INSCRIPCIÓN (SEPARADO)

def cargar_estado():
    try:
        with open(ARCHIVO_ESTADO, "r") as f:
            return json.load(f)
    except:
        return {}

def guardar_estado(data):
    with open(ARCHIVO_ESTADO, "w") as f:
        json.dump(data, f)

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
# OBTENER CURSOS ACTIVOS
# ==============================

def obtener_activas():
    headers = {
        "accept": "application/json",
        "origin": "https://capacitaciondocente.educaciontuc.gov.ar",
        "referer": "https://capacitaciondocente.educaciontuc.gov.ar/",
        "user-agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(URL_ACTIVAS, headers=headers, timeout=10)
        return response.json()
    except:
        print("❌ Error obteniendo activas")
        return []

def detectar_apertura(cursos, estado):
    abiertos = []

    for c in cursos:
        clave = str(c["id"])
        actual = c.get("inscripcion", 0)
        previo = estado.get(clave, 0)

        if previo == 0 and actual == 1:
            abiertos.append(c)

        estado[clave] = actual

    return abiertos

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

def mensaje_apertura(c):
    link = f"https://capacitaciondocente.educaciontuc.gov.ar/#/capacitacion/{c['slug']}"

    return f"""
🚨🚨 INSCRIPCIÓN ABIERTA 🚨🚨

📚 <b>{c['nombre']}</b>

🎓 {c.get('modalidad','')}
📍 {c.get('lugar','')}

⚡ ¡INSCRIBITE YA!

🔗 <a href="{link}">Ir al curso</a>
"""

# ==============================
# LOOP PRINCIPAL
# ==============================

def loop_bot():
    estado = cargar_estado()

    while True:
        try:
            print("\n🔎 Buscando cursos...")

            # 🟣 PRÓXIMOS
            proximos = obtener_proximos()
            enviados = cargar_enviados()

            for c in proximos:
                clave = c["nombre"] + str(c["apertura"])

                if clave not in enviados:
                    mensaje = f"""
🟣 <b>PRÓXIMA CAPACITACIÓN</b>

📚 <b>{c['nombre']}</b>

🎓 {c['modalidad']}
📍 {c['lugar']}

🟢 Apertura:
{formatear_fecha(c['apertura'])}
"""
                    enviar_telegram(mensaje)
                    enviados.add(clave)

            guardar_enviados(enviados)

            # 🚨 APERTURA REAL
            activas = obtener_activas()
            abiertas = detectar_apertura(activas, estado)

            for c in abiertas:
                enviar_telegram(mensaje_apertura(c))

            guardar_estado(estado)

        except Exception as e:
            print("❌ Error:", e)

        print("⏳ Esperando 30 segundos...\n")
        time.sleep(30)

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    threading.Thread(target=iniciar_servidor, daemon=True).start()
    loop_bot()
