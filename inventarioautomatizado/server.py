from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="Inventario automatizado")

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

