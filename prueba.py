import cv2
import numpy as np
from pyzbar.pyzbar import decode
import datetime
from collections import defaultdict
import requests
import json
from datetime import datetime

# API de Spring Boot para guardar datos de códigos de barras
SPRING_BOOT_URL = "http://localhost:8080/api/codigos"
SPRING_BOOT_PALET_URL = "http://localhost:8080/api/v1/palets"

# Función para enviar datos a Spring Boot
def save_barcode(valor, tipo, descripcion_tipo, fecha_escaneo):
    headers = {"Content-Type": "application/json"}
    datos = {
        "valor": valor,
        "tipo": tipo,
        "descripcionTipo": descripcion_tipo,
        "fechaEscaneo": fecha_escaneo
    }
    try:
        response = requests.post(SPRING_BOOT_URL, data=json.dumps(datos), headers=headers)
        if response.status_code in (200, 201):
            print("✅ Código enviado exitosamente a Spring Boot")
        else:
            print(f"❌ Error al enviar código a Spring Boot: {response.status_code}")
            print(f"Respuesta: {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción al intentar enviar el código: {e}")

def formatear_fecha_gs1_a_java(fecha_gs1):
    """Convierte fecha GS1 (YYMMDD) a formato Java yyyy-MM-dd"""
    if fecha_gs1 and len(fecha_gs1) == 6:
        year = int(fecha_gs1[0:2])
        # Determinar el siglo (asumimos 20YY para años < 50, 19YY para >= 50)
        if year < 50:
            year += 2000
        else:
            year += 1900
        month = int(fecha_gs1[2:4])
        day = int(fecha_gs1[4:6])
        # Validar componentes de la fecha
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year}-{month:02d}-{day:02d}"
    return None

def formatear_hora_gs1_a_java(hora_gs1):
    """Convierte hora GS1 (HHMM) a formato Java HH:mm:ss"""
    if hora_gs1 and len(hora_gs1) == 4:
        hour = int(hora_gs1[0:2])
        minute = int(hora_gs1[2:4])
        # Validar hora y minutos
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}:00"
    return None

def save_palet(ean, batchNumber, expirationDate, productionDate, time, sscc):
    headers = {"Content-Type": "application/json"}
    
    # Convertir los formatos de fecha y hora a formato Java compatible
    expirationDate_java = formatear_fecha_gs1_a_java(expirationDate)
    productionDate_java = formatear_fecha_gs1_a_java(productionDate)
    time_java = formatear_hora_gs1_a_java(time)
    
    payload = {
        "ean": ean,
        "batchNumber": batchNumber,
        "expirationDate": expirationDate_java,  # Formato yyyy-MM-dd para java.sql.Date
        "productionDate": productionDate_java,  # Formato yyyy-MM-dd para java.sql.Date
        "time": time_java,  # Formato HH:mm:ss para java.sql.Time
        "sscc": sscc,
        "createdAt": datetime.now().replace(microsecond=0).isoformat()
    }

    print("Payload a enviar a Spring Boot:")
    print(json.dumps(payload, indent=4))
    try:
        response = requests.post(SPRING_BOOT_PALET_URL, json=payload, headers=headers)
        if response.status_code in (200, 201):
            print("✅ Palet enviado correctamente.")
        elif response.status_code == 400:
            print("❌ Error de validación:", response.text)
        elif response.status_code == 409:
            print("⚠️ Palet duplicado:", response.text)
        else:
            print(f"❌ Error inesperado ({response.status_code}):", response.text)
    except requests.exceptions.RequestException as e:
        print("🚨 Error al conectar con Spring Boot:", str(e))


# Captura de video
cap = cv2.VideoCapture(0)
#cap = cv2.VideoCapture(1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cv2.namedWindow("Escáner", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Escáner", 1280, 720)

# Diccionario para evitar duplicados y guardar información adicional
seen_barcodes = {}
# Diccionario para acumular datos por EAN
etiquetas_detectadas = defaultdict(dict)
# Diccionario para almacenar datos de la etiqueta actual
label_data = {
    "ean": None,
    "batchNumber": None,
    "expirationDate": None,
    "productionDate": None,
    "time": None,
    "sscc": None
}

# Diccionario con descripción de los tipos de códigos
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

# Definición de identificadores de aplicación (AI) según estándar GS1
AIs = {
    "00": {"nombre": "SSCC", "longitud": 18, "tipo": "sscc"},
    "01": {"nombre": "EAN", "longitud": 14, "tipo": "ean"},
    "10": {"nombre": "LOTE", "longitud": -1, "tipo": "lote"},  # Longitud variable
    "15": {"nombre": "FECHA CONSUMO", "longitud": 6, "tipo": "fecha_preferente_consumo"},
    "17": {"nombre": "FECHA CADUCIDAD", "longitud": 6, "tipo": "fecha_caducidad"},
    "8008": {"nombre": "FECHA Y HORA PRODUCCIÓN", "longitud": 10, "tipo": "fecha_hora_produccion"}
}

def procesar_gs1(codigo):
    """Procesa un código GS1 y extrae información basada en identificadores de aplicación"""
    i = 0
    actualizado = False
    
    while i < len(codigo):
        # Buscar identificadores de aplicación al inicio o después de un separadorq
        ai_encontrado = False
        
        # Comprobar AI de 4 dígitos
        if i + 4 <= len(codigo) and codigo[i:i+4] in AIs:
            ai = codigo[i:i+4]
            i += 4
            ai_encontrado = True
        # Comprobar AI de 2 dígitos
        elif i + 2 <= len(codigo) and codigo[i:i+2] in AIs:
            ai = codigo[i:i+2]
            i += 2
            ai_encontrado = True
            
        if ai_encontrado:
            ai_info = AIs[ai]
            tipo_dato = ai_info["tipo"]
            
            # Extraer datos según longitud definida en AI
            if ai_info["longitud"] > 0:
                # Longitud fija
                if i + ai_info["longitud"] <= len(codigo):
                    valor = codigo[i:i+ai_info["longitud"]]
                    i += ai_info["longitud"]
                else:
                    # Código incompleto, tomar lo que queda
                    valor = codigo[i:]
                    i = len(codigo)
            else:
                # Longitud variable (buscar siguiente AI o tomar hasta el final)
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
            
            # Guardar valores según el tipo
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
                
            elif tipo_dato == "fecha_preferente_consumo" and label_data["expirationDate"] is None:
                label_data["expirationDate"] = valor
                print(f"✓ Fecha preferente consumo: {valor}")
                print(f"✓ Fecha en formato Java: {formatear_fecha_gs1_a_java(valor)}")
                actualizado = True
                
            elif tipo_dato == "fecha_hora_produccion":
                if len(valor) >= 10:
                    if label_data["productionDate"] is None:
                        fecha_prod = valor[:6]
                        label_data["productionDate"] = fecha_prod
                        print(f"✓ Fecha producción: {fecha_prod}")
                        print(f"✓ Fecha producción en formato Java: {formatear_fecha_gs1_a_java(fecha_prod)}")
                        actualizado = True
                    
                    if label_data["time"] is None and len(valor) >= 10:
                        hora_prod = valor[6:10]
                        label_data["time"] = hora_prod
                        print(f"✓ Hora producción: {hora_prod}")
                        print(f"✓ Hora producción en formato Java: {formatear_hora_gs1_a_java(hora_prod)}")
                        actualizado = True
        else:
            # Si no se encuentra un AI, avanzar un carácter
            i += 1
            
    return actualizado

def consolidar_datos(ean, nuevos_datos):
    """Acumula datos para un EAN específico"""
    if ean:
        for key, value in nuevos_datos.items():
            if value is not None and key != 'ean':  # No sobreescribir el EAN
                etiquetas_detectadas[ean][key] = value

def obtener_descripcion_tipo(tipo_codigo):
    """Obtiene una descripción legible del tipo de código"""
    return TIPOS_CODIGOS.get(tipo_codigo, tipo_codigo)

# Almacenar códigos únicos para el resumen final
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
            # Guardar información del código con timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            seen_barcodes[data] = {
                'tipo': barcode_type,
                'fecha_escaneo': timestamp,
                'descripcion_tipo': obtener_descripcion_tipo(barcode_type)
            }

            # Nuevo código → enviar al backend
            save_barcode(
                valor=data,
                tipo=barcode_type,
                descripcion_tipo=obtener_descripcion_tipo(barcode_type),
                fecha_escaneo=timestamp
            )
            
            # También guardar en la lista para resumen final sin duplicados
            unique_codes_for_summary[data] = {
                'tipo': barcode_type,
                'fecha_escaneo': timestamp,
                'descripcion_tipo': obtener_descripcion_tipo(barcode_type)
            }
            
            print(f"\nNuevo código detectado: {data}")
            print(f"Tipo: {barcode_type} ({obtener_descripcion_tipo(barcode_type)})")
            print(f"Fecha y hora: {timestamp}")
            
            # Procesar el código siguiendo el estándar GS1
            procesar_gs1(data)
            
            # Mostrar el estado de label_data
            print("Estado actual de datos capturados:")
            for key, value in label_data.items():
                estado = "✓" if value else "❌"
                print(f"{key}: {estado} {value if value else ''}")
            
            # Si todos los datos importantes han sido capturados o se ha detectado un EAN
            if label_data["ean"] is not None:
                ean = label_data["ean"]
                # Acumular datos para este EAN
                consolidar_datos(ean, label_data)
                
                # Verificar si la etiqueta está completa
                datos_requeridos = ["ean", "batchNumber", "expirationDate", "productionDate", "time"]
                completado = all(key in etiquetas_detectadas[ean] or (key == "ean" and ean) for key in datos_requeridos)
                
                if completado:
                    print(f"\n=== PALET {ean} COMPLETO ===")
                    
                    # Mostrar datos originales y convertidos 
                    fecha_consumo = etiquetas_detectadas[ean].get("expirationDate")
                    fecha_consumo_java = formatear_fecha_gs1_a_java(fecha_consumo)
                    
                    fecha_produccion = etiquetas_detectadas[ean].get("productionDate")
                    fecha_produccion_java = formatear_fecha_gs1_a_java(fecha_produccion)
                    
                    hora_produccion = etiquetas_detectadas[ean].get("time")
                    hora_produccion_java = formatear_hora_gs1_a_java(hora_produccion)
                    
                    print(f"EAN: {ean}")
                    print(f"LOTE: {etiquetas_detectadas[ean].get('batchNumber')}")
                    print(f"FECHA CONSUMO (GS1): {fecha_consumo} → JAVA: {fecha_consumo_java}")
                    print(f"FECHA PRODUCCIÓN (GS1): {fecha_produccion} → JAVA: {fecha_produccion_java}")
                    print(f"HORA PRODUCCIÓN (GS1): {hora_produccion} → JAVA: {hora_produccion_java}")
                    print(f"SSCC: {etiquetas_detectadas[ean].get('sscc')}")
                    print("-" * 50)
                    
                    # Llamar a la función para guardar en Spring Boot
                    save_palet(
                        ean=ean,
                        batchNumber=etiquetas_detectadas[ean].get("batchNumber"),
                        expirationDate=fecha_consumo,
                        productionDate=fecha_produccion,
                        time=hora_produccion,
                        sscc=etiquetas_detectadas[ean].get("sscc")
                    )

                # Reiniciar para la siguiente captura
                label_data = {"ean": None, "batchNumber": None, "expirationDate": None, "productionDate": None, "time": None, "sscc": None}
        
        # Dibujar rectángulo y texto en la imagen
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Mostrar información del código en la imagen
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
    datos_requeridos = ["ean", "expirationDate", "productionDate", "time"]
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
    fecha_consumo = datos.get("expirationDate")
    fecha_consumo_java = formatear_fecha_gs1_a_java(fecha_consumo)
    
    fecha_produccion = datos.get("productionDate")
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