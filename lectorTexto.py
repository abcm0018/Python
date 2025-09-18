import cv2
import pytesseract
import re
import json

# Configurar Tesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Ajusta ruta si usas Windows
# En Linux/Mac no hace falta poner ruta si está en el PATH

def extraer_campos(texto):
    datos = {}

    # C.P. (6 dígitos exactos)
    cp_match = re.search(r"C\.P\.\s*([0-9]{6})", texto)
    if cp_match:
        datos["C.P."] = cp_match.group(1)

    # Cajas/Palet
    cajas_match = re.search(r"Cajas/Palet\s*([0-9]+)", texto, re.IGNORECASE)
    if cajas_match:
        datos["Cajas/Palet"] = int(cajas_match.group(1))

    # Kgs/Palet
    kgs_match = re.search(r"Kgs./Palet\s*([0-9.,]+)", texto, re.IGNORECASE)
    if kgs_match:
        datos["Kgs./Palet"] = float(kgs_match.group(1).replace(",", "."))

    # Apilado → capturar dos números (normal + pirámide)
    apilado_match = re.search(
        r"APILADO\s*([0-9]+)\s*Alturas?\s*([0-9]+)\s*altura/s?\s*en\s*Piramide",
        texto, re.IGNORECASE
    )
    if apilado_match:
        datos["Apilado_Maximo"] = {
            "Alturas": int(apilado_match.group(1)),
            "Piramide": int(apilado_match.group(2))
        }

    return datos



def leer_etiqueta():
    cap = cv2.VideoCapture(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ No se pudo abrir la cámara")
            break

        # Mostrar frame original
        cv2.imshow("Escaneo Etiqueta (pulsa 'q' para salir)", frame)

        # 🔹 Pasamos frame a escala de grises para mejorar OCR
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # OCR con Tesseract
        texto = pytesseract.image_to_string(gray, lang="spa")

        # Extraemos datos
        datos = extraer_campos(texto)

        # Mostramos JSON en consola si encuentra algo
        if datos:
            print(json.dumps(datos, indent=4, ensure_ascii=False))

        # Pulsar 'q' para salir
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    leer_etiqueta()
