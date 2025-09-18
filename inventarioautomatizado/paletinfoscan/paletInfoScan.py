from config.db import get_connection

# Función para insertar los códigos de barras directamente en la base de datos
def save_barcode_db(value, type, description_type, scanning_date):
    try:
        conn = get_connection()
        cursor = conn.cursor()

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
        print(f"✅ Código {value} guardado correctamente en PALET_INFO_SCAN.")

    finally:
        cursor.close()
        conn.close()
