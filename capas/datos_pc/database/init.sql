CREATE DATABASE IF NOT EXISTS sistema_avicola;
USE sistema_avicola;

-- Crear la tabla para el historial
CREATE TABLE IF NOT EXISTS historial_salud (
    id_registro INT AUTO_INCREMENT PRIMARY KEY,
    id_gallina VARCHAR(50) NOT NULL,
    id_sensor VARCHAR(50) NOT NULL,
    estado_salud VARCHAR(100) NOT NULL,
    fecha_hora BIGINT NOT NULL
);

-- CONFIGURACIÓN DE USUARIO PARA CONEXIÓN REMOTA
-- 1. Crear el usuario 'hmi_user' con acceso desde cualquier IP ('%')
-- La contraseña debe coincidir con MYSQL_PASSWORD en tu .env
CREATE USER IF NOT EXISTS 'hmi_user'@'%' IDENTIFIED BY 'hmi_password_sql';

-- 2. Darle permisos sobre la base de datos del sistema
GRANT ALL PRIVILEGES ON sistema_avicola.* TO 'hmi_user'@'%';

-- 3. Aplicar los cambios
FLUSH PRIVILEGES;