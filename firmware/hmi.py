import busio
import digitalio
import board
import time
import json
import socket  # Librería nativa para comunicación UDP
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import color565
import adafruit_rgb_display.ili9341 as ili9341
import xpt2046_circuitpython

# Librería cliente MQTT
import paho.mqtt.client as mqtt

# ==============================================================================
# CONFIGURACIÓN DE PROTOCOLO Y RED (CONTRATO .ENV)
# ==============================================================================
MQTT_BROKER = "192.168.0.181"  
MQTT_PORT = 1883
MQTT_USER = "admin_avicola"
MQTT_PASS = "gallina_inteligente_2025"

# Tópico de registro/salud en Node-RED según el contrato de interfaz
MQTT_TOPIC = "granja/hmi/registro" 

# Configuración del Socket UDP
UDP_IP = "0.0.0.0"  # Escucha en todas las interfaces de red de la RPi
UDP_PORT = 5005
# ==============================================================================

# Matriz Homográfica H (Calibración de pantalla táctil)
H = np.array([
    [1.02971195, 0.0189082162, -2.78349843],
    [-0.0228697078, 1.18643027, 4.25787018],
    [0.0000125727046, 0.000153301207, 1.0]
], dtype=np.float32)

# Configuración de Pines SPI para Pantalla e Interrupciones del Táctil
cs_d = digitalio.DigitalInOut(board.CE0)
dc_d = digitalio.DigitalInOut(board.D22)
rst_d = digitalio.DigitalInOut(board.D27)

cs_t = digitalio.DigitalInOut(board.CE1)
irq_t = digitalio.DigitalInOut(board.D17)

spi = busio.SPI(clock=board.SCLK, MOSI=board.MOSI, MISO=board.MISO)

display = ili9341.ILI9341(spi, rotation=0, cs=cs_d, dc=dc_d, rst=rst_d, baudrate=40000000)
touch = xpt2046_circuitpython.Touch(spi, cs=cs_t, interrupt=irq_t, force_baudrate=4000000)

WIDTH = display.width   
HEIGHT = display.height 

X_MITAD = WIDTH // 2
Y_MITAD = HEIGHT // 2

def transformar_punto(x_t, y_t):
    punto = np.array([[x_t, y_t]], dtype=np.float32)
    punto_transformado = cv2.perspectiveTransform(punto.reshape(-1, 1, 2), H)
    return punto_transformado[0][0]

def dibujar_interfaz_color():
    """Dibuja los 4 botones con colores contrastantes y etiquetas centradas"""
    imagen = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except IOError:
        font = ImageFont.load_default()

    # Definición de Paleta de Colores en formato PIL (R, G, B)
    BLANCO = (255, 255, 255)
    VERDE = (34, 139, 34)       # Saludable
    AZUL = (30, 144, 255)       # En tratamiento
    AMARILLO = (218, 165, 32)   # En observación
    ROJO = (178, 34, 34)        # Grave

    # Dibujar Cuadrante 1: Saludable (Verde)
    dibujo.rectangle([(5, 5), (X_MITAD - 5, Y_MITAD - 5)], outline=BLANCO, fill=VERDE)
    dibujo.text((15, Y_MITAD // 2 - 10), "Saludable", fill=BLANCO, font=font)

    # Dibujar Cuadrante 2: En tratamiento (Azul)
    dibujo.rectangle([(X_MITAD + 5, 5), (WIDTH - 5, Y_MITAD - 5)], outline=BLANCO, fill=AZUL)
    dibujo.text((X_MITAD + 12, Y_MITAD // 2 - 10), "Tratamiento", fill=BLANCO, font=font)

    # Dibujar Cuadrante 3: En observación (Amarillo)
    dibujo.rectangle([(5, Y_MITAD + 5), (X_MITAD - 5, HEIGHT - 5)], outline=BLANCO, fill=AMARILLO)
    dibujo.text((10, Y_MITAD + Y_MITAD // 2 - 10), "Observacion", fill=BLANCO, font=font)

    # Dibujar Cuadrante 4: Grave (Rojo)
    dibujo.rectangle([(X_MITAD + 5, Y_MITAD + 5), (WIDTH - 5, HEIGHT - 5)], outline=BLANCO, fill=ROJO)
    dibujo.text((X_MITAD + 30, Y_MITAD + Y_MITAD // 2 - 10), "Grave", fill=BLANCO, font=font)

    display.image(imagen)

# MQTT Callbacks básicos de depuración local
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("-> HMI Conectada exitosamente al Broker de forma local.", flush=True)
    else:
        print(f"-> Fallo en conexión MQTT. Código de error: {rc}", flush=True)

# Configuración e inicialización del Cliente MQTT de Paho
mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.on_connect = on_connect

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Advertencia: No se pudo conectar al Broker Mosquitto ({e}). Modo offline.", flush=True)

# Inicialización y vinculación del Socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# ESTADO DE REPOSO INICIAL: Borrar pantalla y dejarla en negro absoluto al arrancar
display.fill(color565(0, 0, 0))
print(f"HMI lista en modo pasivo. Pantalla en reposo (negro). Escuchando puerto {UDP_PORT}...", flush=True)

while True:
    try:
        # ----------------------------------------------------------------------
        # FASE 1: ESCUCHA PASIVA Y BLOQUEANTE POR UDP
        # ----------------------------------------------------------------------
        data, addr = sock.recvfrom(1024)  # El script se detiene aquí pacientemente
        
        try:
            mensaje_udp = json.loads(data.decode('utf-8'))
        except Exception:
            print("-> [UDP Warning] Se recibió un paquete pero NO es un formato JSON válido.", flush=True)
            continue  
            
        # Validación del trigger exclusivo
        if mensaje_udp.get("trigger") != "active health menu":
            print(f"-> [UDP Ignorado] Trigger incorrecto o inválido: {mensaje_udp.get('trigger')}", flush=True)
            continue
            
        # Captura dinámica de variables del mensaje UDP (Cualquier UID y su Timestamp original)
        uid_recibido = mensaje_udp.get("uid")
        timestamp_recibido = mensaje_udp.get("timestamp")
        
        # Validar la existencia de parámetros clave para prevenir fallos posteriores
        if not uid_recibido or not timestamp_recibido:
            print(f"-> [UDP Rechazado] Faltan campos obligatorios. UID: {uid_recibido}, Timestamp: {timestamp_recibido}", flush=True)
            continue
            
        # SI PASÓ TODAS LAS REGLAS: Se activa el programa
        print(f"\n[UDP] ¡Trigger Válido Detectado! Activando HMI para UID: {uid_recibido}", flush=True)
        
        # ENCENDER PANTALLA: Se dibuja la interfaz a color únicamente al recibir el trigger
        dibujar_interfaz_color()
        print(" -> Ventana táctil activa en pantalla por 60 segundos...", flush=True)
        
        # ----------------------------------------------------------------------
        # FASE 2: VENTANA TEMPORAL DE 60 SEGUNDOS PARA EL TOUCH
        # ----------------------------------------------------------------------
        tiempo_inicio = time.time()
        mensaje_enviado = False
        
        while (time.time() - tiempo_inicio) < 60:
            try:
                # Intenta leer las coordenadas aislando la excepción de hardware
                try:
                    xt, yt = touch.get_coordinates()
                except Exception as e:
                    if "Out-of-bounds" in str(e) or "2047" in str(e):
                        time.sleep(0.01)
                        continue
                    else:
                        raise e
                
                # Filtro de ruido eléctrico estático
                if yt == 311:
                    time.sleep(0.01)
                    continue
                    
                xc, yc = transformar_punto(xt, yt)
                xc, yc = round(xc), round(yc)
                
                # Filtro de límites físicos de la pantalla
                if xc < 0 or xc > WIDTH or yc < 0 or yc > HEIGHT:
                    time.sleep(0.01)
                    continue
                    
                estado_seleccionado = None
                
                # Clasificación por cuadrantes táctiles
                if 0 <= xc < X_MITAD and 0 <= yc < Y_MITAD:
                    estado_seleccionado = "Saludable"
                elif X_MITAD <= xc <= WIDTH and 0 <= yc < Y_MITAD:
                    estado_seleccionado = "En tratamiento"
                elif 0 <= xc < X_MITAD and Y_MITAD <= yc <= HEIGHT:
                    estado_seleccionado = "En observacion"
                elif X_MITAD <= xc <= WIDTH and Y_MITAD <= yc <= HEIGHT:
                    estado_seleccionado = "Grave"
                else:
                    time.sleep(0.01)
                    continue
                    
                if estado_seleccionado:
                    print(f" -> Touch detectado: [{estado_seleccionado}]", flush=True)
                    
                    # Estructura final del JSON con los datos originales del UDP
                    mensaje_json = {
                        "uid": uid_recibido,
                        "estado": estado_seleccionado,
                        "timestamp": timestamp_recibido
                    }
                    
                    payload_string = json.dumps(mensaje_json)
                    
                    # Envío vía MQTT con QoS 1 (Garantía de entrega)
                    mqtt_client.publish(MQTT_TOPIC, payload_string, qos=1)
                    print(f"    [MQTT] Publicado con éxito -> {payload_string}", flush=True)
                    
                    mensaje_enviado = True
                    time.sleep(0.4)
                    break  # Sale de la ventana táctil y fuerza el regreso al reposo
                
            except Exception as e:
                print(f"Error interno en ventana touch: {e}", flush=True)
            
            time.sleep(0.01)  # Descanso de CPU para el sub-bucle táctil
            
        # Si el temporizador pasa los 60s sin un touch válido
        if not mensaje_enviado:
            print(" -> Tiempo agotado (60s). No se registró toque. Información descartada.", flush=True)
            
        # REGRESO AL ESTADO DE REPOSO: Limpiar pantalla y apagar botones
        print(" -> Apagando interfaz. Descartando paquetes UDP acumulados...", flush=True)
        display.fill(color565(0, 0, 0))

        # ----------------------------------------------------------------------
        # FASE 3: VACIAR EL BUZÓN UDP (Ignorar lo acumulado en los 60 segundos)
        # ----------------------------------------------------------------------
        sock.setblocking(False)  # Pone el socket en modo no-bloqueante temporalmente
        try:
            while True:
                # Lee de forma masiva todo lo que haya en el buffer hasta que se vacíe
                sock.recvfrom(1024)
        except BlockingIOError:
            # Esta excepción significa que el buzón ya se vació por completo
            pass
        finally:
            sock.setblocking(True)  # Regresa el socket a su modo bloqueante normal para el bucle
            
        print(" -> Modo pasivo reactivado. Listo para un nuevo trigger.\n", flush=True)
            
    except Exception as e:
        print(f"Error crítico en el bucle principal: {e}", flush=True)
        time.sleep(1)