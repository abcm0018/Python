import datetime
from config.db import get_connection
from utils.utils import (formatear_fecha_gs1_a_java, formatear_hora_gs1_a_java, determinar_turno)

def save_palet_db(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employeeNumber):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Buscar el producto por EAN
        cursor.execute("SELECT id FROM PRODUCT WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        if not row:
            print(f"⚠️ Producto EAN {ean} no encontrado")
            return
        product_id = row[0]
        
        # Buscar el usuario por employee_number
        cursor.execute("SELECT id FROM USER WHERE employee_number = %s", (employeeNumber,))
        row = cursor.fetchone()
        user_id = row[0] if row else None

        if not user_id:
            print(f"⚠️ No se encontró el usuario con número de empleado {employeeNumber}. El palet no se insertará.")
            return
        
        # Formatear fechas y hora
        productUseByDate_sql = formatear_fecha_gs1_a_java(productUseByDate)
        packagingDate_sql = formatear_fecha_gs1_a_java(packagingDate)
        time_sql = formatear_hora_gs1_a_java(time)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener el turno de trabajo
        shift = determinar_turno(time_sql)

        # Insertar palet en la bd
        sql = """
        INSERT INTO PALET (ean, batch_number, production_date, expiration_date, time, sscc, created_at, shift, product_id, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (ean, batchNumber, packagingDate_sql, productUseByDate_sql, time_sql, sscc, created_at, shift, product_id, user_id)

        cursor.execute(sql, values)
        conn.commit()
        print(f"✅ Palet {sscc} guardado correctamente en la base de datos. Turno: {shift}")

    finally:
        cursor.close()
        conn.close()
