import cv2
import numpy as np
import matplotlib.pyplot as plt
from pyzbar.pyzbar import decode

# --- Cargar imagen ---
img = cv2.imread("etiqueta.jpg")
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # para mostrar con matplotlib
gray_full = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

# --- Buscar la etiqueta grande (tu heurística previa) ---
_, thresh = cv2.threshold(gray_full, 200, 255, cv2.THRESH_BINARY_INV)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)

codigo_roi = None
etiqueta_roi = None

for cnt in contours:
    x, y, w, h = cv2.boundingRect(cnt)
    if w > 500 and h > 500:
        etiqueta_roi = img[y:y+h, x:x+w].copy()
        # recorte relativo dentro de la etiqueta (ajusta si hace falta)
        y1 = int(0.345 * h)
        y2 = int(0.765 * h)
        codigo_roi = etiqueta_roi[y1:y2, :].copy()
        break

if codigo_roi is None:
    raise RuntimeError("No se encontró la ROI de la etiqueta (ajusta el umbral / tamaños).")

# --- Preprocesado principal (uso adaptative como base) ---
gray_roi = cv2.cvtColor(codigo_roi, cv2.COLOR_RGB2GRAY)
adapt = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                             cv2.THRESH_BINARY, 21, 10)
adapt_inv = cv2.bitwise_not(adapt)
eq = cv2.equalizeHist(gray_roi)

# *** NUEVO: copia del adaptive en color para dibujar resultados ***
out = cv2.cvtColor(adapt, cv2.COLOR_GRAY2BGR)

# Hacemos detección SOLO en estas variantes
imagenes_a_probar = [adapt, adapt_inv, gray_roi, eq]

# --- Utilidades: IoU y duplicado ---
def iou(b1, b2):
    x1, y1, w1, h1 = b1
    x2, y2, w2, h2 = b2
    xa = max(x1, x2)
    ya = max(y1, y2)
    xb = min(x1 + w1, x2 + w2)
    yb = min(y1 + h1, y2 + h2)
    inter_w = max(0, xb - xa)
    inter_h = max(0, yb - ya)
    inter = inter_w * inter_h
    union = w1 * h1 + w2 * h2 - inter
    return inter / union if union > 0 else 0

def es_duplicado(texto, bbox, existentes, iou_thresh=0.25):
    for e in existentes:
        if e['text'] == texto:
            return True
        if iou(bbox, e['bbox']) > iou_thresh:
            return True
    return False

detections = []

# --- 1) Pyzbar sobre variantes ---
for variante in imagenes_a_probar:
    decoded = decode(variante)
    for obj in decoded:
        texto = obj.data.decode("utf-8")
        (px, py, pw, ph) = obj.rect
        bbox = (int(px), int(py), int(pw), int(ph))
        if not es_duplicado(texto, bbox, detections):
            detections.append({'text': texto, 'bbox': bbox, 'source': 'pyzbar'})
            print("Detectado (Pyzbar):", texto)

# --- 2) Detección vertical (tu mismo código) ---
h_roi, w_roi = gray_roi.shape
kernel_height = max(10, int(h_roi * 0.12))
vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, kernel_height))
inv = cv2.bitwise_not(adapt)
vertical_mask = cv2.morphologyEx(inv, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
vertical_mask = cv2.morphologyEx(vertical_mask, cv2.MORPH_CLOSE, vertical_kernel, iterations=1)
cnts_v, _ = cv2.findContours(vertical_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

for cnt in cnts_v:
    x, y, w, h = cv2.boundingRect(cnt)
    if h > 0.45 * h_roi and w < 0.35 * w_roi and h > 40 and w > 10:
        pad_x = int(w * 0.12)
        pad_y = int(h * 0.05)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(w_roi, x + w + pad_x)
        y1 = min(h_roi, y + h + pad_y)
        crop = codigo_roi[y0:y1, x0:x1].copy()

        textos_encontrados = set()
        crop_gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        crop_adapt = cv2.adaptiveThreshold(crop_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                           cv2.THRESH_BINARY, 21, 10)
        for prueba in [crop_adapt, cv2.bitwise_not(crop_adapt), crop_gray]:
            decoded = decode(prueba)
            for obj in decoded:
                textos_encontrados.add(obj.data.decode("utf-8"))

        crop_rot = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
        crop_rot_gray = cv2.cvtColor(crop_rot, cv2.COLOR_RGB2GRAY)
        crop_rot_adapt = cv2.adaptiveThreshold(crop_rot_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                               cv2.THRESH_BINARY, 21, 10)
        for prueba in [crop_rot_adapt, cv2.bitwise_not(crop_rot_adapt), crop_rot_gray]:
            decoded = decode(prueba)
            for obj in decoded:
                textos_encontrados.add(obj.data.decode("utf-8"))

        for txt in textos_encontrados:
            bbox_global = (int(x0), int(y0), int(x1 - x0), int(y1 - y0))
            if not es_duplicado(txt, bbox_global, detections):
                detections.append({'text': txt, 'bbox': bbox_global, 'source': 'vertical'})
                print("Detectado (vertical):", txt)

# --- 3) Complemento OpenCV BarcodeDetector ---
try:
    detector = cv2.barcode_BarcodeDetector()
    ok, decoded_infos, decoded_points, _ = detector.detectAndDecodeMulti(adapt)
    if ok and decoded_infos is not None:
        for txt, pts in zip(decoded_infos, decoded_points):
            if not txt:
                continue
            pts = np.array(pts).astype(int)
            x_min = int(np.min(pts[:, 0]))
            y_min = int(np.min(pts[:, 1]))
            x_max = int(np.max(pts[:, 0]))
            y_max = int(np.max(pts[:, 1]))
            bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
            if not es_duplicado(txt, bbox, detections):
                detections.append({'text': txt, 'bbox': bbox, 'source': 'opencv'})
                print("Detectado (OpenCV):", txt)
except Exception:
    pass


# --- Dibujar resultados (ahora en 'out' que es adapt_color) ---
for i, d in enumerate(detections, start=1):
    x, y, w, h = d['bbox']
    source = d['source']
    color = (0, 255, 0)       # pyzbar -> verde
    if source == 'opencv':
        color = (255, 0, 255) # magenta
    if source == 'vertical':
        color = (0, 0, 255)   # azul/rojo
    cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
    cv2.putText(out, f"{i}", (x + 4, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

# Mostrar resultados
plt.figure(figsize=(14,7))
plt.title("Códigos detectados en ROI adaptive (con rectángulos)")
plt.imshow(out)
plt.axis('off')
plt.show()

# Lista final única
codigos_unicos = []
for d in detections:
    if d['text'] not in codigos_unicos:
        codigos_unicos.append(d['text'])
print("Códigos únicos encontrados:", codigos_unicos)
