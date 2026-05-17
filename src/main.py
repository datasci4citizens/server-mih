from dotenv import load_dotenv

load_dotenv()

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

# from api.medications.medication_users import medications_user_router
from starlette.requests import Request

from api.mih.images_api import images_router
from api.mih.mih_api import mih_router
from api.mih.mih_patients_api import mih_patients_router
from api.mih.mih_tracking_records_api import mih_tracking_records_router

# from api.common.users_api import router
from api.mih.mih_user_api import mih_user_router  # Importe o roteador de usuários
from auth.oauth_google import login_router
from db.manager import Database

Database.db_engine()

app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# Adiciona um manipulador de exceção para HTTPException
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    print(
        f"Backend Exception Handler: Caught HTTPException - Status: {exc.status_code}, Detail: {exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# Modelo de Token
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY"),
    max_age=3600,
    same_site="none",
    https_only=True,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FRONT_URL").split(",")
    if os.getenv("FRONT_URL")
    else [],  # Especifique as origens permitidas
    allow_credentials=True,  # Permitir envio de cookies ou credenciais
    allow_methods=["*"],  # Métodos HTTP permitidos
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "ngrok-skip-browser-warning",
    ],  # Cabeçalhos permitidos
)

app.include_router(login_router)
app.include_router(mih_patients_router)
app.include_router(mih_router)
app.include_router(mih_tracking_records_router)
app.include_router(mih_user_router)
app.include_router(images_router)
