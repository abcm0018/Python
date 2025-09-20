import logging
from fastapi import HTTPException, Depends
from users.get_users import get_all_users_service
from api.auth import get_current_user

def get_all_users_public():
    try:
        users = get_all_users_service()
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


def get_all_users_protected(employee_number: str = Depends(get_current_user)):
    try:
        logging.info(f"Usuario autenticado {employee_number} listó los usuarios")
        users = get_all_users_service()
        if not users:
            raise HTTPException(status_code=404, detail="No users found")
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")
