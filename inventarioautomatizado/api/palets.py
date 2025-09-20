from palets.save_palets import save_palet_db
from palets.save_barcode import save_barcode_db

def scan_palet(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employeeNumber):
    try:
        save_palet_db(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employeeNumber)
        return {"message": f"✅ Palet {sscc} guardado correctamente"}
    except Exception as e:
        return {"error": str(e)}

def scan_barcode(value, type, description_type, scanning_date):
    try:
        save_barcode_db(value, type, description_type, scanning_date)
        return {"message": f"✅ Código {value} guardado correctamente"}
    except Exception as e:
        return {"error": str(e)}