from fastapi import Depends, FastAPI
import os

from db.manager import Database
#from api.common.users_api import router
from api.mih.mih_user_api import mih_user_router  # Importe o roteador de usuários
from api.mih.mih_patients_api import mih_patients_router
from api.mih.mih_api import mih_router
from api.mih.mih_tracking_records_api import mih_tracking_records_router
from api.mih.images_api import images_router

#from api.medications.medication_users import medications_user_router
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from auth.oauth_google import login_router


from dotenv import load_dotenv

load_dotenv()

Database.db_engine()

app = FastAPI()
app.include_router(login_router)

# Modelo de Token
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from this source
    allow_credentials=True, # Allows sending cookies, authentication tokens and other types of credentials in requests
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# origins = [
#     "http://localhost.tiangolo.com",
#     "https://localhost.tiangolo.com",
#     "http://localhost",
#     "http://localhost:8000"
# ]


#app.include_router(router)
app.include_router(mih_patients_router)
app.include_router(mih_router)
app.include_router(mih_tracking_records_router)
#app.include_router(medications_user_router)
app.include_router(mih_user_router)
app.include_router(images_router)
