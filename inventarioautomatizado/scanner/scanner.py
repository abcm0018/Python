import cv2
from pyzbar.pyzbar import decode
from datetime import datetime
from collections import defaultdict

from paletinfoscan.paletInfoScan import save_barcode_db
from api.palets import save_palet_db
from utils.utils import formatear_fecha_gs1_a_java, formatear_hora_gs1_a_java, determinar_turno

# Número de empleado fijo (puedes cambiarlo cuando tengas login de usuario)
EMPLOYEE_NUMBER = "12345"

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

# Diccionarios de control
seen_barcodes = {}  # para evitar duplicados
etiquetas_detectadas = defaultdict(dict)
label_data = {"ean": None, "batchNumber": None, "productUseByDate": None,
              "packagingDate": None, "time": None, "sscc": None}

# Almacenar códigos únicos para resumen
unique_codes_for_summary = {}

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

def start_scanner(employeeNumber):
    # Configuración de la cámara
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cv2.namedWindow("Escáner", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Escáner", 1280, 720)

    global label_data

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        barcodes = decode(frame)

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

                # Guardar en PALET_INFO_SCAN
                save_barcode_db(
                    value=data,
                    type=barcode_type,
                    description_type=TIPOS_CODIGOS.get(barcode_type, barcode_type),
                    scanning_date=timestamp
                )

                # Procesar GS1
                procesar_gs1(data)

                print("Estado actual de datos capturados:")
                for key, value in label_data.items():
                    estado = "✓" if value else "❌"
                    print(f"{key}: {estado} {value if value else ''}")

                # Consolidar y guardar si está completo
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
                        sscc = etiquetas_detectadas[ean].get("sscc")

                        turno_test = determinar_turno(formatear_hora_gs1_a_java(hora_produccion))

                        print(f"EAN: {ean}")
                        print(f"LOTE: {etiquetas_detectadas[ean].get('batchNumber')}")
                        print(f"FECHA CONSUMO: {fecha_consumo}")
                        print(f"FECHA PRODUCCIÓN: {fecha_produccion}")
                        print(f"HORA PRODUCCIÓN: {hora_produccion}")
                        print(f"SSCC: {sscc}")
                        print(f"TURNO: {turno_test}")
                        print("-" * 50)

                        # Guardar palet en BD
                        save_palet_db(
                            ean=ean,
                            batchNumber=etiquetas_detectadas[ean].get("batchNumber"),
                            productUseByDate=fecha_consumo,
                            packagingDate=fecha_produccion,
                            time=hora_produccion,
                            sscc=sscc,
                            employeeNumber=EMPLOYEE_NUMBER
                        )

                    # Resetear datos para la siguiente etiqueta
                    label_data = {"ean": None, "batchNumber": None, "productUseByDate": None,
                                  "packagingDate": None, "time": None, "sscc": None}

            # Dibujar recuadro en el frame
            x, y, w, h = barcode.rect
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            barcode_info = seen_barcodes[data]
            tipo_texto = f"{barcode_info['descripcion_tipo']}"
            cv2.putText(frame, f"{data}", (x, y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(frame, f"Tipo: {tipo_texto}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Escáner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Resumen final
    print("\n=== RESUMEN DE CÓDIGOS ESCANEADOS ===")
    print(f"Total de códigos diferentes: {len(unique_codes_for_summary)}")
    print("-" * 50)
    for i, (codigo, info) in enumerate(unique_codes_for_summary.items(), 1):
        print(f"Código #{i}:")
        print(f"  Valor: {codigo}")
        print(f"  Tipo: {info['tipo']} ({info['descripcion_tipo']})")
        print(f"  Fecha y hora: {info['fecha_escaneo']}")
        print("-" * 50)
