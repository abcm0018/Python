from fastapi import APIRouter, Depends
from api.auth import login_user, get_current_user
from api.palets import scan_palet
from api.timesheet import save_signing, save_check_out

router = APIRouter()

@router.post("/login")
def login(employee_number: str, password: str):
    user_data = login_user(employee_number, password)

    user = user_data["user"]

    if user.get("role", "").lower() == "operator":
        save_signing(user["employee_number"], user["name"])

    return user_data

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

@router.post("/logout")
def logout_route(employee_number: str):
    save_check_out(employee_number)
    return {"message": "Logout registrado correctamente"}