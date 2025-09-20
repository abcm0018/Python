import logging
from api.auth import login_user
from api.users import get_all_users_public_service, get_all_users_protected_service
from scanner.scanner import start_scanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def menu_principal():
    print("\n=== MENÚ PRINCIPAL ===")
    print("1. Login")
    print("2. Ver usuarios públicos")
    print("3. Salir")
    return input("Elige una opción: ")

def menu_post_login(user):
    print(f"\n=== MENÚ USUARIO ({user['name']}) ===")
    print("1. Escanear palet")
    print("2. Ver usuarios protegidos")
    print("3. Volver al menú principal")
    return input("Elige una opción: ")

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

def ver_usuarios_publicos():
    users = get_all_users_public_service()
    logging.info(f"🌐 Usuarios públicos: {users}")

def ver_usuarios_protegidos(user):
    users = get_all_users_protected_service(user["employee_number"])
    logging.info(f"🔒 Usuarios protegidos: {users}")

def escanear_palet(user):
    logging.info(f"📷 Iniciando escáner para {user['name']} {user['surname']}...")
    start_scanner(user["employee_number"])

# Bucle principal
if __name__ == "__main__":
    user_logueado = None
    while True:
        if not user_logueado:
            opcion = menu_principal()
            if opcion == "1":
                user_logueado = login()
            elif opcion == "2":
                ver_usuarios_publicos()
            elif opcion == "3":
                print("Adiós!")
                break
            else:
                print("Opción no válida")
        else:
            opcion = menu_post_login(user_logueado)
            if opcion == "1":
                escanear_palet(user_logueado)
            elif opcion == "2":
                ver_usuarios_protegidos(user_logueado)
            elif opcion == "3":
                user_logueado = None  # Volver al menú principal
            else:
                print("Opción no válida")
