import mysql.connector

# Configuración de la base de datos
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Miguelito-2001",
    "database": "barcodescanner"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)