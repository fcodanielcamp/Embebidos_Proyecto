import busio
import digitalio
import board
import time
import json
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
MQTT_BROKER = "192.168.0.181"  # IP Corregida
MQTT_PORT = 1883
MQTT_USER = "admin_avicola"
MQTT_PASS = "gallina_inteligente_2025"

# Tópico Corregido según el contrato de interfaz
MQTT_TOPIC = "granja/hmi/registro" 
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

# Borrar pantalla e inicializar la nueva botonera a color
display.fill(color565(0, 0, 0))
dibujar_interfaz_color()

print("Botonera HMI iniciada. Lista para envío de estados de salud...", flush=True)

while True:
    try:
        # Intenta leer las coordenadas aislando la excepción de "Out-of-bounds" de la pantalla táctil
        try:
            xt, yt = touch.get_coordinates()
        except Exception as e:
            # Si el error es de hardware por lecturas fuera de rango o ruido, se ignora en silencio
            if "Out-of-bounds" in str(e) or "2047" in str(e):
                time.sleep(0.01)
                continue
            else:
                raise e # Si es otro tipo de error, lo pasa al bloque exterior
        
        # Filtro de ruido eléctrico estático
        if yt == 311:
            continue
            
        xc, yc = transformar_punto(xt, yt)
        xc, yc = round(xc), round(yc)
        
        # Filtro de límites físicos de la pantalla ILI9341
        if xc < 0 or xc > WIDTH or yc < 0 or yc > HEIGHT:
            continue
            
        estado_seleccionado = None
        
        # Clasificación por cuadrantes táctiles corregidos
        if 0 <= xc < X_MITAD and 0 <= yc < Y_MITAD:
            estado_seleccionado = "Saludable"
        elif X_MITAD <= xc <= WIDTH and 0 <= yc < Y_MITAD:
            estado_seleccionado = "En tratamiento"
        elif 0 <= xc < X_MITAD and Y_MITAD <= yc <= HEIGHT:
            estado_seleccionado = "En observacion"
        elif X_MITAD <= xc <= WIDTH and Y_MITAD <= yc <= HEIGHT:
            estado_seleccionado = "Grave"
        else:
            continue
            
        if estado_seleccionado:
            print(f"Toque detectado -> Estado seleccionado: {estado_seleccionado}", flush=True)
            
            # Construcción exacta del objeto JSON solicitado con timestamp dinámico
            mensaje_json = {
                "uid": "A1B2C3D4",
                "estado": estado_seleccionado,
                "timestamp": int(time.time() * 1000)
            }
            
            # Serializar diccionario a formato string/JSON crudo
            payload_string = json.dumps(mensaje_json)
            
            # Publicación asíncrona mediante MQTT con QoS 1 (Garantía de entrega)
            info = mqtt_client.publish(MQTT_TOPIC, payload_string, qos=1)
            print(f"   [MQTT] Mensaje enviado a Node-RED -> {payload_string}", flush=True)
            
            # Delay de rebote (Debounce) para evitar múltiples publicaciones involuntarias
            time.sleep(0.4)
        
    except Exception as e:
        print(f"Error crítico en lectura de hardware o envío: {e}", flush=True)
        
    time.sleep(0.01)