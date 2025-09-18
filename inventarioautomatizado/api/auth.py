import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer
from config.db import get_connection  
from config.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

security = HTTPBearer()

def create_token(employee_number, minutes=0, days=0):
    """Crea un JWT para un usuario con fecha de expiración."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes, days=days)
    payload = {
        "sub": employee_number,   # Claim "subject" → a quién pertenece el token
        "exp": int(expire.timestamp())  # Claim "expiration" → fecha de caducidad
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def login_user(employee_number: str, password: str):
    """Verifica las credenciales de un usuario y devuelve tokens y datos del usuario."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT employee_number, name, surname, email, job_position, role, password
            FROM user
            WHERE employee_number = %s
            """,
            (employee_number,)
        )
        user = cursor.fetchone()
        cursor.close()

        password_correct = user and bcrypt.checkpw(password.encode(), user["password"].encode())
        if not password_correct:
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

        access_token = create_token(user["employee_number"], minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token = create_token(user["employee_number"], days=REFRESH_TOKEN_EXPIRE_DAYS)

        return {
            "user": {
                "employee_number": user["employee_number"],
                "name": user["name"],
                "surname": user["surname"],
                "email": user["email"],
                "jobPosition": user["job_position"],
                "role": user["role"]
            },
            "token": access_token,
            "refresh_token": refresh_token
        }
    finally:
        conn.close()

def get_current_user(credentials=Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_number = payload.get("sub")
        if not employee_number:
            raise HTTPException(status_code=401, detail="Token inválido")
        return employee_number
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El Token ha expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")