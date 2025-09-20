from fastapi import APIRouter, Depends, HTTPException
from api.auth import login_user, get_current_user
from api.palets import scan_palet
from inventarioautomatizado.api.users import get_all_users_service

import logging

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

@router.get("/users/public")
def get_all_users_public():
    return get_all_users_service()

# Protegido: requiere login (token)
@router.get("/users")
def get_all_users_protected(employee_number: str = Depends(get_current_user)):
    logging.info(f"Usuario autenticado {employee_number} listó los usuarios")
    return get_all_users_service()