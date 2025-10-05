import cv2
from pyzbar.pyzbar import decode
from datetime import datetime
from collections import defaultdict

from api.palets import scan_palet, scan_barcode
from utils.utils import formatear_fecha_gs1_a_java, formatear_hora_gs1_a_java, determinar_turno
from constants.constants import TIPOS_CODIGOS, AIs

import logging

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Diccionarios de control
seen_barcodes = {}
etiquetas_detectadas = defaultdict(dict)
label_data = {"ean": None, "batchNumber": None, "productUseByDate": None,
              "packagingDate": None, "time": None, "sscc": None}

unique_codes_for_summary = {}

# ==============================
# NUEVO: definición de ROIs fijos
# ==============================
def extraer_rois(frame):
    h, w = frame.shape[:2]
    rois = {
        "vertical_grande": ((int(0.25*h), int(0.95*h)), (int(0.70*w), int(0.95*w))),
        "vertical_pequena": ((int(0.25*h), int(0.95*h)), (int(0.55*w), int(0.70*w))),
        "horizontal_superior": ((int(0.15*h), int(0.35*h)), (int(0.15*w), int(0.65*w))),
        "horizontal_medio": ((int(0.40*h), int(0.55*h)), (int(0.15*w), int(0.65*w))),
        "horizontal_inferior": ((int(0.65*h), int(0.85*h)), (int(0.15*w), int(0.65*w)))
    }
    return rois

# ==============================
# Preprocesado original
# ==============================
def preprocesar_imagen(roi, aplicar_threshold=True):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.equalizeHist(gray)

    if aplicar_threshold:
        processed = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        return processed
    else:
        return enhanced

# ==============================
# FUNCIONES GS1 y consolidación
# ==============================
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
                logging.info(f"✓ SSCC detectado: {valor}")
                actualizado = True
            elif tipo_dato == "ean" and label_data["ean"] is None:
                label_data["ean"] = valor
                logging.info(f"✓ EAN detectado: {valor}")
                actualizado = True
            elif tipo_dato == "lote" and label_data["batchNumber"] is None:
                label_data["batchNumber"] = valor
                logging.info(f"✓ Lote detectado: {valor}")
                actualizado = True
            elif tipo_dato == "fecha_preferente_consumo" and label_data["productUseByDate"] is None:
                label_data["productUseByDate"] = valor
                logging.info(f"✓ Fecha consumo: {valor}")
                actualizado = True
            elif tipo_dato == "fecha_hora_produccion":
                if len(valor) >= 10:
                    if label_data["packagingDate"] is None:
                        label_data["packagingDate"] = valor[:6]
                        logging.info(f"✓ Fecha producción: {valor[:6]}")
                        actualizado = True
                    if label_data["time"] is None:
                        label_data["time"] = valor[6:10]
                        logging.info(f"✓ Hora producción: {valor[6:10]}")
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

# ==============================
# Escáner
# ==============================
def start_scanner(employeeNumber):
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

        h_frame, w_frame = frame.shape[:2]
        resultados = []

        # 1) Forzar lectura ROI por ROI
        for nombre, ((y1, y2), (x1, x2)) in extraer_rois(frame).items():
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            roi_resized = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
            processed_roi = preprocesar_imagen(roi_resized, aplicar_threshold=True)
            barcodes_roi = decode(processed_roi)

            if barcodes_roi:
                for bc in barcodes_roi:
                    data = bc.data.decode('utf-8')
                    barcode_type = bc.type
                    resultados.append((data, barcode_type, nombre))
                    logging.info(f"[{nombre}] ✅ Detectado: {data} ({barcode_type})")

        # 2) Fallback: decode en todo el frame
        barcodes = decode(frame)
        for barcode in barcodes:
            data = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            resultados.append((data, barcode_type, "pyzbar_auto"))

        # 3) Procesamiento
        for data, barcode_type, origen in resultados:
            if data not in seen_barcodes:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                seen_barcodes[data] = {
                    'tipo': barcode_type,
                    'fecha_escaneo': timestamp,
                    'descripcion_tipo': obtener_descripcion_tipo(barcode_type)
                }
                unique_codes_for_summary[data] = seen_barcodes[data]

                logging.info(f"Nuevo código detectado desde {origen}: {data}")
                logging.info(f"Tipo: {barcode_type} ({obtener_descripcion_tipo(barcode_type)})")
                logging.info(f"Fecha y hora: {timestamp}")

                scan_barcode(
                    value=data,
                    type=barcode_type,
                    description_type=TIPOS_CODIGOS.get(barcode_type, barcode_type),
                    scanning_date=timestamp
                )

                procesar_gs1(data)

                if label_data["ean"] is not None:
                    ean = label_data["ean"]
                    consolidar_datos(ean, label_data)
                    datos_requeridos = ["ean", "batchNumber", "productUseByDate", "packagingDate", "time", "sscc"]
                    completado = all(key in etiquetas_detectadas[ean] or (key == "ean" and ean) for key in datos_requeridos)

                    if completado:
                        logging.info(f"=== PALET {ean} COMPLETO ===")
                        fecha_consumo = etiquetas_detectadas[ean].get("productUseByDate")
                        fecha_produccion = etiquetas_detectadas[ean].get("packagingDate")
                        hora_produccion = etiquetas_detectadas[ean].get("time")
                        sscc = etiquetas_detectadas[ean].get("sscc")

                        turno_test = determinar_turno(formatear_hora_gs1_a_java(hora_produccion))

                        scan_palet(
                            ean=ean,
                            batchNumber=etiquetas_detectadas[ean].get("batchNumber"),
                            productUseByDate=fecha_consumo,
                            packagingDate=fecha_produccion,
                            productionTime=hora_produccion,
                            sscc=sscc,
                            employeeNumber=employeeNumber
                        )

                    label_data = {"ean": None, "batchNumber": None, "productUseByDate": None,
                                  "packagingDate": None, "time": None, "sscc": None}

        cv2.imshow("Escáner", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
