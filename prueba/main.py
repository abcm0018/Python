import logging
from api.auth import login_user
from scanner.scanner import start_scanner
from api.timesheet import save_signing, save_check_out 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def login():
    employeeNumber = input("Introduce tu número de empleado: ")
    password = input("Introduce tu contraseña: ")
    try:
        data = login_user(employeeNumber, password)
        token = data["token"]
        user = data["user"]
        logging.info("✅ Login exitoso")
        logging.info(f"Token: {token}")
        logging.info(f"👤 Datos del usuario: {user}")

        return user
    except Exception as e:
        logging.error(f"❌ Error al iniciar sesión: {str(e)}")
        return None
def logout(employee_number):
    try:
        save_check_out(employee_number)
        logging.info("✅ Logout registrado correctamente")
    except Exception as e:
        logging.error(f"❌ Error al registrar logout: {str(e)}")

def escanear_palet(user):
    logging.info(f"📷 Iniciando escáner para {user['name']} {user['surname']}...")
    start_scanner(user["employee_number"])
    logging.info("✅ Escaneo finalizado correctamente")

# Bucle principal
if __name__ == "__main__":
    user = login()
    if not user:
        logging.error("❌ No se pudo iniciar sesión. Cerrando aplicación.")
    else:
        if user.get("role", "").lower() == "operator":
            save_signing(user["employee_number"], user["name"])
            escanear_palet(user)
            save_check_out(user["employee_number"])
        else:
            logging.warning("⚠️ El usuario no tiene rol de operador. No puede escanear palets.")
            logging.info("👋 Cerrando aplicación.")
