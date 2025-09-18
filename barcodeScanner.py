import cv2
import numpy as np
from pyzbar.pyzbar import decode
from datetime import datetime
from collections import defaultdict
import mysql.connector
from enum import Enum

class Shift(Enum):
    MORNING = "MORNING" # 6:00 - 14:00
    AFTERNOON = "AFTERNOON" # 14:00 - 22:00
    NIGHT = "NIGHT" # 22:00 - 6:00

# Configuración de la base de datos
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Miguelito-2001",
    "database": "barcodescanner"
}

def determinar_turno(hora_str):
    """
    Recibe hora en formato 'HH:mm:ss' y devuelve el turno correspondiente.
    """
    if not hora_str:
        return None
    hour = int(hora_str.split(":")[0])
    if 6 <= hour < 14:
        return Shift.MORNING.value
    elif 14 <= hour < 22:
        return Shift.AFTERNOON.value
    else:
        return Shift.NIGHT.value
    
# Función para insertar los códigos de barras directamente en la base de datos
def save_barcode_db(value, type, description_type, scanning_date):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
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

    except mysql.connector.Error as err:
        print(f"❌ Error al guardar el código en la BD: {err}")

    finally:
        cursor.close()
        conn.close()


# Función para insertar un palet directamente en la base de datos
def save_palet_db(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employeeNumber):
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Buscar el producto por EAN
        cursor.execute("SELECT id FROM PRODUCT WHERE ean = %s", (ean,))
        row = cursor.fetchone()
        product_id = row[0] if row else None

        if not product_id:
            print(f"⚠️ No se encontró producto con EAN {ean}. El palet no se insertará.")
            return
        
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

    except mysql.connector.Error as err:
        print(f"❌ Error al guardar el palet en la BD: {err}")

    finally:
        cursor.close()
        conn.close()

# Funciones de conversión de fecha y hora GS1 a formato SQL
def formatear_fecha_gs1_a_java(fecha_gs1):
    if fecha_gs1 and len(fecha_gs1) == 6:
        year = int(fecha_gs1[0:2])
        year += 2000 if year < 50 else 1900
        month = int(fecha_gs1[2:4])
        day = int(fecha_gs1[4:6])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year}-{month:02d}-{day:02d}"
    return None

def formatear_hora_gs1_a_java(hora_gs1):
    if hora_gs1 and len(hora_gs1) == 4:
        hour = int(hora_gs1[0:2])
        minute = int(hora_gs1[2:4])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    return None


# Configuración de la cámara
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cv2.namedWindow("Escáner", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Escáner", 1280, 720)

# Diccionarios de control
seen_barcodes = {}  # para evitar duplicados
etiquetas_detectadas = defaultdict(dict)
label_data = {"ean": None, "batchNumber": None, "productUseByDate": None,
              "packagingDate": None, "time": None, "sscc": None}

# Tipos de códigos
TIPOS_CODIGOS = {
    "QRCODE": "Código QR",
    "CODE128": "Code 128",
    "CODE39": "Code 39",
    "EAN13": "EAN-13",
    "EAN8": "EAN-8",
    "UPCA": "UPC-A",
    "UPCE": "UPC-E",
    "PDF417": "PDF417",
    "DATAMATRIX": "DataMatrix",
    "ITF": "ITF (Interleaved 2 of 5)",
    "AZTEC": "Aztec",
    "CODABAR": "Codabar"
}

# Identificadores de aplicación GS1
AIs = {
    "00": {"nombre": "SSCC", "longitud": 18, "tipo": "sscc"},
    "01": {"nombre": "EAN", "longitud": 14, "tipo": "ean"},
    "10": {"nombre": "LOTE", "longitud": -1, "tipo": "lote"},
    "15": {"nombre": "FECHA CONSUMO", "longitud": 6, "tipo": "fecha_preferente_consumo"},
    "17": {"nombre": "FECHA CADUCIDAD", "longitud": 6, "tipo": "fecha_caducidad"},
    "8008": {"nombre": "FECHA Y HORA PRODUCCIÓN", "longitud": 10, "tipo": "fecha_hora_produccion"}
}


def procesar_gs1(codigo):
    codigo = codigo.replace("\x1d", "")
    i = 0
    actualizado = False
    while i < len(codigo):
        ai_encontrado = False
        if i + 4 <= len(codigo) and codigo[i:i+4] in AIs:
            ai = codigo[i:i+4]
            i += 4
            ai_encontrado = True
        elif i + 2 <= len(codigo) and codigo[i:i+2] in AIs:
            ai = codigo[i:i+2]
            i += 2
            ai_encontrado = True

        if ai_encontrado:
            ai_info = AIs[ai]
            tipo_dato = ai_info["tipo"]
            if ai_info["longitud"] > 0:
                if i + ai_info["longitud"] <= len(codigo):
                    valor = codigo[i:i + ai_info["longitud"]]
                    i += ai_info["longitud"]
                else:
                    valor = codigo[i:]
                    i = len(codigo)
            else:
                next_ai_pos = float('inf')
                for siguiente_ai in AIs:
                    pos = codigo.find(siguiente_ai, i)
                    if pos > i and pos < next_ai_pos:
                        next_ai_pos = pos
                if next_ai_pos < float('inf'):
                    valor = codigo[i:next_ai_pos]
                    i = next_ai_pos
                else:
                    valor = codigo[i:]
                    i = len(codigo)

            if tipo_dato == "sscc" and label_data["sscc"] is None:
                label_data["sscc"] = valor
                print(f"✓ SSCC detectado: {valor}")
                actualizado = True
            elif tipo_dato == "ean" and label_data["ean"] is None:
                label_data["ean"] = valor
                print(f"✓ EAN detectado: {valor}")
                actualizado = True
            elif tipo_dato == "lote" and label_data["batchNumber"] is None:
                label_data["batchNumber"] = valor
                print(f"✓ Lote detectado: {valor}")
                actualizado = True
            elif tipo_dato == "fecha_preferente_consumo" and label_data["productUseByDate"] is None:
                label_data["productUseByDate"] = valor
                print(f"✓ Fecha consumo: {valor}")
                actualizado = True
            elif tipo_dato == "fecha_hora_produccion":
                if len(valor) >= 10:
                    if label_data["packagingDate"] is None:
                        label_data["packagingDate"] = valor[:6]
                        print(f"✓ Fecha producción: {valor[:6]}")
                        actualizado = True
                    if label_data["time"] is None:
                        label_data["time"] = valor[6:10]
                        print(f"✓ Hora producción: {valor[6:10]}")
                        actualizado = True
        else:
            i += 1
    return actualizado


def consolidar_datos(ean, nuevos_datos):
    if ean:
        for key, value in nuevos_datos.items():
            if value is not None and key != 'ean':
                etiquetas_detectadas[ean][key] = value

def obtener_descripcion_tipo(tipo_codigo):
    return TIPOS_CODIGOS.get(tipo_codigo, tipo_codigo)


# Almacenar códigos únicos para resumen
unique_codes_for_summary = {}

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)

    for barcode in barcodes:
        data = barcode.data.decode('utf-8')
        barcode_type = barcode.type

        if data not in seen_barcodes:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            seen_barcodes[data] = {
                'tipo': barcode_type,
                'fecha_escaneo': timestamp,
                'descripcion_tipo': obtener_descripcion_tipo(barcode_type)
            }
            unique_codes_for_summary[data] = seen_barcodes[data]

            print(f"\nNuevo código detectado: {data}")
            print(f"Tipo: {barcode_type} ({obtener_descripcion_tipo(barcode_type)})")
            print(f"Fecha y hora: {timestamp}")

            save_barcode_db(
                value=data,
                type=barcode_type,
                description_type=TIPOS_CODIGOS.get(barcode_type, barcode_type),
                scanning_date=timestamp
            )

            procesar_gs1(data)
            print("Estado actual de datos capturados:")
            for key, value in label_data.items():
                estado = "✓" if value else "❌"
                print(f"{key}: {estado} {value if value else ''}")

            if label_data["ean"] is not None:
                ean = label_data["ean"]
                consolidar_datos(ean, label_data)
                datos_requeridos = ["ean", "batchNumber", "productUseByDate", "packagingDate", "time", "sscc"]
                completado = all(key in etiquetas_detectadas[ean] or (key == "ean" and ean) for key in datos_requeridos)

                if completado:
                    print(f"\n=== PALET {ean} COMPLETO ===")
                    fecha_consumo = etiquetas_detectadas[ean].get("productUseByDate")
                    fecha_produccion = etiquetas_detectadas[ean].get("packagingDate")
                    hora_produccion = etiquetas_detectadas[ean].get("time")
                    print(f"EAN: {ean}")
                    print(f"LOTE: {etiquetas_detectadas[ean].get('batchNumber')}")
                    print(f"FECHA CONSUMO: {fecha_consumo}")
                    print(f"FECHA PRODUCCIÓN: {fecha_produccion}")
                    print(f"HORA PRODUCCIÓN: {hora_produccion}")
                    print(f"SSCC: {etiquetas_detectadas[ean].get('sscc')}")
                    turno_test = determinar_turno(hora_produccion)
                    print(f"TURNO: {turno_test}")
                    print("-" * 50)

                    save_palet_db(
                        ean=ean,
                        batchNumber=etiquetas_detectadas[ean].get("batchNumber"),
                        productUseByDate=fecha_consumo,
                        packagingDate=fecha_produccion,
                        time=hora_produccion,
                        sscc=etiquetas_detectadas[ean].get("sscc")
                    )

                label_data = {"ean": None, "batchNumber": None, "productUseByDate": None,
                              "packagingDate": None, "time": None, "sscc": None}

        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        barcode_info = seen_barcodes[data]
        tipo_texto = f"{barcode_info['descripcion_tipo']}"
        cv2.putText(frame, f"{data}", (x, y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, f"Tipo: {tipo_texto}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    cv2.imshow("Escáner", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Filtrar solo etiquetas completas para el resumen final
etiquetas_completas = {}
for ean, datos in etiquetas_detectadas.items():
    datos_requeridos = ["ean", "productUseByDate", "packagingDate", "time"]
    # Verificar que todos los campos requeridos existen
    if all(key in datos or (key == "ean" and ean) for key in datos_requeridos):
        # Añadir el EAN al diccionario para la salida final
        datos["ean"] = ean
        etiquetas_completas[ean] = datos

# Mostrar resumen de todos los códigos escaneados (sin duplicados)
print("\n=== RESUMEN DE CÓDIGOS ESCANEADOS ===")
print(f"Total de códigos diferentes: {len(unique_codes_for_summary)}")
print("-" * 50)

for i, (codigo, info) in enumerate(unique_codes_for_summary.items(), 1):
    print(f"Código #{i}:")
    print(f"  Valor: {codigo}")
    print(f"  Tipo: {info['tipo']} ({info['descripcion_tipo']})")
    print(f"  Fecha y hora: {info['fecha_escaneo']}")
    print("-" * 50)

# Mostrar resumen de etiquetas detectadas (solo las completas, sin duplicados)
print("\n=== RESUMEN DE ETIQUETAS COMPLETAS ===")
etiquetas_unicas = {}
for ean, datos in etiquetas_completas.items():
    # Usar el EAN como clave para evitar duplicados
    if ean not in etiquetas_unicas:
        etiquetas_unicas[ean] = datos

for i, (ean, datos) in enumerate(etiquetas_unicas.items(), 1):
    print(f"Etiqueta #{i}:")
    
    # Obtener y formatear datos para la visualización
    fecha_consumo = datos.get("productUseByDate")
    fecha_consumo_java = formatear_fecha_gs1_a_java(fecha_consumo)
    
    fecha_produccion = datos.get("packagingDate")
    fecha_produccion_java = formatear_fecha_gs1_a_java(fecha_produccion)
    
    hora_produccion = datos.get("time")
    hora_produccion_java = formatear_hora_gs1_a_java(hora_produccion)
    
    print(f"  EAN: {ean}")
    print(f"  LOTE: {datos.get('batchNumber')}")
    print(f"FECHA CONSUMO (GS1): {fecha_consumo} → JAVA: {fecha_consumo_java}")
    print(f"FECHA PRODUCCIÓN (GS1): {fecha_produccion} → JAVA: {fecha_produccion_java}")
    print(f"HORA PRODUCCIÓN (GS1): {hora_produccion} → JAVA: {hora_produccion_java}")
    print("-" * 50)

cap.release()
cv2.destroyAllWindows()