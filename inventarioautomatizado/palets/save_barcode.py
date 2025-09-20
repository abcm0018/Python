import logging

from config.db import get_connection

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Función para insertar los códigos de barras directamente en la base de datos
def save_barcode_db(value, type, description_type, scanning_date):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM PALET_INFO_SCAN WHERE value = %s", (value,))
        if cursor.fetchone():
            logging.warning(f"⚠️ Código {value} ya existe en PALET_INFO_SCAN. No se insertará.")
            return {"success": False, "error": f"Código {value} ya existe"}

        sql = """
        INSERT INTO PALET_INFO_SCAN (value, type, description_type, status, scanning_date)
        VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            value,
            type,
            description_type,
            "CORRECT",  # status inicial (puedes cambiarlo según tu enum Status)
            scanning_date
        )

        cursor.execute(sql, values)
        conn.commit()

        logging.info(f"✅ Código {value} guardado correctamente en PALET_INFO_SCAN.")
        return {"success": True, "value": value}
    
    except Exception as e:
        logging.error(f"❌ Error al guardar el código {value} en PALET_INFO_SCAN: {e}")
        return {"success": False, "error": str(e)}
    
    finally:
        cursor.close()
        conn.close()
