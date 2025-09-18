from palets.save import save_palet_db

def scan_palet(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employee_number):
    save_palet_db(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employee_number)
    return {"message": f"Palet {sscc} guardado correctamente"}