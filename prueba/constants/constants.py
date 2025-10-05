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