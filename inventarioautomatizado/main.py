from api.auth import login_user
from api.palets import scan_palet

if __name__ == "__main__":
    # Pedir las credenciales por consola
    employeeNumber = input("Introduce tu número de empleado: ")
    password = input("Introduce tu contraseña: ")

    try:

        # Login
        data = login_user(employeeNumber, password)
        token = data["token"]
        refreshToken = data["refresh_token"]
        user = data["user"]

        print("\n✅ Login exitoso")
        print("Token: ", token)
        print("Refresh token: ", refreshToken)
        print("\n👤 Datos del usuario:", user)

        opcion = input("\n¿Quieres escanear un palet? (s/n): ")
        if opcion.lower() == "s":
            ean = input("EAN: ")
            batchNumber = input("Lote: ")
            productUseByDate = input("Fecha caducidad (GS1): ")
            packagingDate = input("Fecha producción (GS1): ")
            time = input("Hora (GS1): ")
            sscc = input("SSCC: ")

            scan_palet(ean, batchNumber, productUseByDate, packagingDate, time, sscc, employeeNumber)

    except Exception as e:
        print("❌ Error al iniciar sesión:", str(e))

