import logging

from datetime import datetime
from config.db import get_connection
from utils.utils import (formatear_fecha_gs1_a_java, formatear_hora_gs1_a_java, determinar_turno)

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def save_palet_db(ean, batchNumber, productUseByDate, packagingDate, productionTime, sscc, employeeNumber):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Buscar el producto por SSCC
        cursor.execute("SELECT id FROM PALET WHERE sscc = %s", (sscc,))
        row = cursor.fetchone()
        if row:
            logging.warning(f"⚠️ El palet con SSCC {sscc} ya existe en la base de datos. No se insertará de nuevo.")
            return {"success": False, "error": f"Palet SSCC {sscc} ya existe"}

        # Buscar el producto por EAN
        cursor.execute("SELECT id FROM PRODUCT WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        if not row:
            logging.warning(f"⚠️ Producto EAN {ean} no encontrado")
            return {"success": False, "error": f"Producto EAN {ean} no encontrado"}
        product_id = row[0]
        
        # Validar que el usuario existe por employee_number
        cursor.execute("SELECT 1 FROM USER WHERE employee_number = %s", (employeeNumber,))
        row = cursor.fetchone()
       
        if not row:
            logging.warning(f"⚠️ No se encontró el usuario con número de empleado {employeeNumber}. El palet no se insertará.")
            return {"success": False, "error": f"Usuario {employeeNumber} no encontrado"}

        # Formatear fechas y hora
        productUseByDate_sql = formatear_fecha_gs1_a_java(productUseByDate)
        packagingDate_sql = formatear_fecha_gs1_a_java(packagingDate)
        time_sql = formatear_hora_gs1_a_java(productionTime)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener el turno de trabajo
        shift = determinar_turno(time_sql)

        # Insertar palet en la bd
        sql = """
        INSERT INTO PALET (ean, batch_number, packaging_date, product_use_by_date, production_time, sscc, created_at, shift, product_id, employee_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (ean, batchNumber, packagingDate_sql, productUseByDate_sql, time_sql, sscc, created_at, shift, product_id, employeeNumber)

        cursor.execute(sql, values)
        conn.commit()
        
        logging.info(f"✅ Palet {sscc} guardado correctamente en la base de datos. Turno: {shift}")
        return {"success": True, "sscc": sscc, "shift": shift}
    
    except Exception as e:
        logging.error(f"❌ Error al guardar el palet {sscc}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        cursor.close()
        conn.close()
