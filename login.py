import cv2
import numpy as np
import zxingcpp   # ZXing-C++ binding para Python

# --- Abrir webcam ---
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error al abrir la cámara")
    exit()

vistos = set()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    gray_full = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Buscar la etiqueta grande (heurística)
    _, thresh = cv2.threshold(gray_full, 180, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    codigo_roi = None
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 300 and h > 300:  # Ajusta según tamaño en webcam
            # recortamos la zona central (donde están los códigos de barras en tu etiqueta)
            y1 = int(0.35 * h)
            y2 = int(0.75 * h)
            codigo_roi = img[y+y1:y+y2, x:x+w].copy()
            break

    if codigo_roi is not None:
        # Ampliar ROI para mejorar la lectura
        scale = 3
        big = cv2.resize(
            codigo_roi,
            (codigo_roi.shape[1]*scale, codigo_roi.shape[0]*scale),
            interpolation=cv2.INTER_LINEAR
        )

        # Decodificar con ZXing
        results = zxingcpp.read_barcodes(big)
        for res in results:
            texto = res.text.strip()
            if texto and texto not in vistos:
                print(f"Nuevo código detectado: {texto} (formato: {res.format})")
                vistos.add(texto)

            # Dibujar recuadro en la ROI
            if res.position:
                pts = np.array([(p.x, p.y) for p in res.position], dtype=np.int32)
                cv2.polylines(big, [pts], True, (0,255,0), 2)
                cv2.putText(big, texto[:15], (pts[0][0], pts[0][1]-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        cv2.imshow("ROI ampliada", cv2.cvtColor(big, cv2.COLOR_RGB2BGR))

    cv2.imshow("Frame", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
