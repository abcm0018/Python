from fastapi import APIRouter, Depends
from api.auth import login_user, get_current_user
from api.palets import scan_palet

router = APIRouter()

@router.post("/login")
def login(employee_number: str, password: str):
    return login_user(employee_number, password)

@router.post("/palets/scan")
def scan(
    ean: str,
    batchNumber: str,
    productUseByDate: str,
    packagingDate: str,
    time: str,
    sscc: str,
    employee_number: str = Depends(get_current_user)
):
    return scan_palet(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employee_number)