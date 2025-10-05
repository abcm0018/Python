import mysql.connector
import os

# Configuración de la base de datos
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", "Miguelito-2001"),
    "database": os.getenv("DB_NAME", "barcodescanner"),
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)