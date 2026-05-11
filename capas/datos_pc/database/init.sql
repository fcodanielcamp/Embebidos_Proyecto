CREATE DATABASE IF NOT EXISTS sistema_avicola;
USE sistema_avicola;

CREATE TABLE IF NOT EXISTS historial_salud (
    id_registro INT AUTO_INCREMENT PRIMARY KEY,
    id_gallina VARCHAR(50) NOT NULL,
    id_sensor VARCHAR(50) NOT NULL,
    estado_salud VARCHAR(100) NOT NULL,
    fecha_hora BIGINT NOT NULL
);