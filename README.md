# 🐔 SGAI-IoT: Sistema de Gestión Avícola Inteligente
**Arquitectura de 3 Capas basada en Ganadería de Precisión (PLF)**

Este repositorio contiene el ecosistema completo para el monitoreo individual de aves mediante RFID, orquestación en el borde con Docker y análisis masivo de datos[cite: 1]. El sistema permite una gestión quirúrgica de la producción, optimizando el bienestar animal y la rentabilidad mediante decisiones basadas estrictamente en datos telemétricos[cite: 1].

---

## 📂 Estructura del Repositorio y Roles
Cada carpeta representa un dominio de responsabilidad único para asegurar la autonomía del desarrollo[cite: 9]:

| Carpeta | Área | Responsable | Tecnología Core |
| :--- | :--- | :--- | :--- |
| `/firmware` | **1. Campo** | Ing. de Firmware | ESP32, C++, MQTT[cite: 1] |
| `/mosquitto` | **2. Borde (Broker)** | Ing. de Redes | Docker, Eclipse-Mosquitto[cite: 4] |
| `/node_red_data` | **2. Borde (Flujos)** | Ing. de Software | Node-RED, InfluxDB[cite: 8] |
| `/hmi_area` | **3. Interfaz** | Ing. de HMI/Python | Python, OpenCV, XPT2046[cite: 1] |
| `/database` | **4. Datos** | Ing. de Datos | MariaDB, SQL, Grafana[cite: 7] |
| `/tools` | **Soporte** | Todo el equipo | Python (Scripts de prueba) |

---

## 🏗️ Guía de Inicio para Desarrolladores

### 1. Preparación del Entorno
Antes de iniciar, cada integrante debe realizar lo siguiente en su máquina local:
1. Instalar **Docker Desktop** y **Git Bash**[cite: 2].
2. Clonar este repositorio: `git clone <url_repo>`.
3. Crear el archivo de credenciales: `cp .env.example .env` (y editar las claves según corresponda)[cite: 6].

### 2. Despliegue de Servicios
Desde la raíz del proyecto en Git Bash, ejecutar:
`docker-compose up -d`

Esto levantará el Broker MQTT, la base de datos MariaDB y el orquestador Node-RED de forma automática[cite: 2, 4, 8].

---

## 📑 Manual por Áreas de Trabajo

### Área 1: Arquitectura de Campo (`/firmware`)
*   **Misión**: Adquisición física de identidades (RFID) y ejecución de señales PWM para actuadores[cite: 1].
*   **Contrato de Salida**: Publicar en `granja/telemetria/rfid` el JSON: `{"id_sensor": X, "uid": "HEX", "timestamp": BIGINT}`[cite: 1].
*   **Pines Críticos**: GPIO 5 (Zona Comida A), 17 (Zona Comida B) y 16 (Módulo de Salud)[cite: 1].

### Área 2: Orquestación de Borde (`/mosquitto` y `/node_red_data`)
*   **Misión**: Ruteo local de datos, gestión de HMI y persistencia de series temporales[cite: 1].
*   **Configuración Obligatoria**: Configurar un **Archivo Swap de 2GB** en la Raspberry Pi Zero 2W para evitar el colapso del stack de microservicios[cite: 1].
*   **Trigger UDP**: Al recibir un JSON con `{"id_sensor": 3}`, Node-RED debe inyectar un datagrama UDP al puerto `5005`[cite: 1].

### Área 3: Interfaz HMI y Control (`/hmi_area`)
*   **Misión**: Desarrollo de interfaz táctil para reportes de salud y comandos de flujo inverso[cite: 1, 9].
*   **Precisión Táctil**: Implementar una **Matriz de Homografía** (`cv2.findHomography`) para mapear coordenadas resistivas a la resolución de 240x320 píxeles[cite: 1].
*   **Threaded Listener**: La escucha del socket UDP (Puerto 5005) debe ser no-bloqueante respecto a la renderización gráfica[cite: 1].

### Área 4: Datos y Analítica (`/database`)
*   **Misión**: Persistencia masiva y analítica avanzada mediante mapas de calor (Heatmaps)[cite: 1].
*   **Esquema**: Tabla `registros_gallinas` diseñada para soportar timestamps de alta precisión (13 dígitos)[cite: 1].
*   **Acceso**: Configurar el firewall para permitir tráfico en el puerto `3306` (MariaDB)[cite: 7].

---

## 📡 Contrato de Comunicación Global (API Interna)

### Protocolo de Telemetría (MQTT)
*   **Broker**: `mosquitto_broker` (Puerto 1883)[cite: 4].
*   **Tópicos Críticos**:
    *   `granja/telemetria/rfid`: Datos provenientes de la ESP32[cite: 1].
    *   `granja/control/iluminacion`: Comandos inversos desde la HMI (Patrones 1: Verde, 2: Amarillo, 3: Rojo)[cite: 1].

### Protocolo de Alerta (UDP)
*   **Puerto Mandatorio**: `5005`[cite: 1].
*   **Lógica**: Activa automáticamente el menú de salud por una ventana de 60 segundos tras la detección en el Módulo de Salud[cite: 1].

### Protocolo de Persistencia (SQL)
*   **Puerto**: `3306`[cite: 7].
*   **Reportes de Salud**: Los estados permitidos para inserción son `Saludable`, `Letárgica`, `Herida` y `Problema con alimento`[cite: 1].

---

## 🛠️ Reglas de Colaboración en Git
1. **Pull Diario**: Ejecutar `git pull` antes de cada sesión para asegurar la sincronía de los contenedores[cite: 9].
2. **Uso de `.gitignore`**: Queda estrictamente prohibido subir carpetas de datos locales (`/data`, `/mysql_data`) o archivos de contraseñas[cite: 4, 8].
3. **Commits Semánticos**: Usar `feat:` para nuevas funciones, `fix:` para correcciones y `docs:` para documentación[cite: 2].

---
*Este proyecto es parte de la materia de Sistemas Embebidos 2025-2. Profesor: Eduardo Fragoso Navarro.*[cite: 9]