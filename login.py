import requests

API_LOGIN = "http://localhost:8080/api/v1/auth/auth/login"
payload = {
    "employeeNumber": "A1234",
    "password": "fed1cbd55cebfa8e"
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(API_LOGIN, json=payload, headers=headers)

# La respuesta será idéntica a la que viste en Swagger
print(response.json())
