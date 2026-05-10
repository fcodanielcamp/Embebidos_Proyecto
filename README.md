# SGAI-IoT: Sistema de Gestión Avícola Inteligente
**Arquitectura de 3 Capas basada en Ganadería de Precisión (PLF)**

Este repositorio contiene el ecosistema completo para el monitoreo individual de aves mediante RFID, orquestación en el borde con Docker y análisis masivo de datos. El sistema permite una gestión quirúrgica de la producción, optimizando el bienestar animal y la rentabilidad mediante decisiones basadas estrictamente en datos telemétricos.

---

## Estructura del Repositorio y Roles
La estructura se organiza por capas para garantizar la autonomía del desarrollo y la resiliencia operativa del sistema:

| Carpeta / Ruta | Capa | Responsable | Tecnología Core |
| :--- | :--- | :--- | :--- |
| `/firmware` | **1. Campo (ESP32)** | Ing. de Firmware | C++, MQTT, RFID |
| `/capas/borde_rpi` | **2. Borde (Rpi Zero 2W)** | Ing. de Redes/Software | Docker, Mosquitto, Node-RED |
| `/capas/datos_pc` | **3. Datos (PC Central)** | Ing. de Datos | MariaDB, SQL, Grafana |
| `/tools` | **Soporte** | Todo el equipo | Python (Scripts de prueba) |

---

## Guía de Inicio para Desarrolladores

### 1. Preparación del Entorno
Antes de iniciar, cada integrante debe realizar lo siguiente en su máquina local:
1. Instalar **Docker Desktop** y **Git Bash**.
2. Clonar este repositorio: `git clone <url_repo>`.
3. **Configurar Credenciales**: 
   * Copiar la plantilla: `cp .env.example .env`.
   * **IMPORTANTE (Windows Fix)**: Crear un archivo vacío en `capas/borde_rpi/mosquitto/config/mosquitto.passwd`. Esto es mandatorio para que el contenedor de Mosquitto inicie correctamente en Windows debido a políticas de seguridad de volúmenes.

### 2. Despliegue de Servicios por Hardware
El despliegue se realiza de forma independiente según el nodo físico:

*   **En la Raspberry Pi (Capa de Borde)**: 
    Navegar a `cd capas/borde_rpi/` y ejecutar `docker-compose up -d`.
*   **En la PC Central (Capa de Datos)**: 
    Navegar a `cd capas/datos_pc/` y ejecutar `docker-compose up -d`.

### 3. Registro de Usuario MQTT (Solo la primera vez)
Para activar la seguridad del broker, una vez levantado el contenedor de borde, ejecutar:
`docker exec -it mosquitto_broker mosquitto_passwd -b //mosquitto/config/mosquitto.passwd admin_avicola gallina_inteligente_2025`

---

## Manual por Áreas de Trabajo

### Área 1: Arquitectura de Campo (`/firmware`)
*   **Misión**: Adquisición física de identidades (RFID) y ejecución de señales PWM para actuadores.
*   **Contrato de Salida**: Publicar en `granja/telemetria/rfid` el JSON: `{"id_sensor": X, "uid": "HEX", "timestamp": BIGINT}`.
*   **Pines Críticos**: GPIO 5 (Zona Comida A), 17 (Zona Comida B) y 16 (Módulo de Salud).

### Área 2: Orquestación de Borde (`/capas/borde_rpi`)
*   **Misión**: Ruteo local de datos, gestión de HMI y ruteo de señales UDP.
*   **Configuración Obligatoria**: Configurar un **Archivo Swap de 2GB** en la Raspberry Pi Zero 2W para evitar el colapso del stack por falta de RAM (512MB).
*   **Trigger UDP**: Al recibir un JSON con `{"id_sensor": 3}`, Node-RED debe inyectar un datagrama UDP al puerto `5005`.

### Área 3: Interfaz HMI y Control (Dentro de `/borde_rpi/hmi_area`)
*   **Misión**: Desarrollo de interfaz táctil para reportes de salud y comandos de flujo inverso.
*   **Precisión Táctil**: Implementar una **Matriz de Homografía** para mapear coordenadas resistivas (0-4095) a la resolución de 240x320 píxeles.
*   **Threaded Listener**: La escucha del socket UDP (Puerto 5005) debe ser no-bloqueante respecto a la renderización gráfica.

### Área 4: Datos y Analítica (`/capas/datos_pc`)
*   **Misión**: Persistencia masiva en PC Central para proteger la integridad de la tarjeta SD de la Raspberry Pi.
*   **Esquema**: Tabla `registros_gallinas` diseñada para soportar timestamps de alta precisión (13 dígitos/epoch ms).
*   **Acceso**: Configurar el firewall para permitir tráfico entrante en el puerto `3306` (MariaDB).

---

## 📡 Contrato de Comunicación Global (API Interna)

### Protocolo de Telemetría (MQTT)
*   **Broker**: `mosquitto_broker` (Puerto 1883).
*   **Tópicos Críticos**:
    *   `granja/telemetria/rfid`: Datos provenientes de la ESP32.
    *   `granja/control/iluminacion`: Comandos inversos desde la HMI (Patrones 1: Verde, 2: Amarillo, 3: Rojo).

### Protocolo de Alerta (UDP)
*   **Puerto Mandatorio**: `5005`.
*   **Lógica**: Activa automáticamente el menú de salud por una ventana de 60 segundos tras la detección en el Módulo de Salud.

### Protocolo de Persistencia (SQL)
*   **Puerto**: `3306` (Apuntando a la IP estática de la PC Central).
*   **Reportes de Salud**: Los estados permitidos son `Saludable`, `Letárgica`, `Herida` y `Problema con alimento`.

---

## Reglas de Colaboración en Git
1. **Despliegue por Capas**: No mezclar servicios de la PC (MariaDB) en el despliegue de la Raspberry Pi para evitar saturación de RAM.
2. **Uso de `.gitignore`**: Queda estrictamente prohibido subir carpetas de datos locales (`/data`, `/mysql_data`) o archivos de contraseñas (`.passwd`).
3. **Commits Semánticos**: Usar `feat:` para nuevas funciones, `fix:` para correcciones, `arch:` para cambios de estructura y `docs:` para documentación.