from fastapi import APIRouter, Depends, HTTPException, Request, FastAPI
from fastapi.responses import RedirectResponse
from auth.auth_service import AuthService
from db.manager import Database
from schema.mih.schema_mih import User, UserCreate, UserRead, UserUpdate  # Seus modelos
from sqlmodel import Session, select
from fastapi.middleware.cors import CORSMiddleware
import requests as rq
from google_auth_oauthlib.flow import Flow
import os
import json



login_router = APIRouter()

# Add this line to disable HTTPS checking during development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# This variable specifies the name of a file that contains the OAuth 2.0 information for this application
#CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")

# These OAuth 2.0 scopes allow access to the user's Google account OpenID, Email, and Profile.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

@login_router.get('/auth/login/google')
async def call_google_signin(request: Request, server_url = os.getenv("SERVER_URL")):
    """ flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, 
        scopes=SCOPES
    )
    flow.redirect_uri = 'http://localhost:8000/auth/login/google/callback'
    auth_url, state = flow.authorization_url(
        access_type='offline',
        #include_granted_scopes='true'
    )
    request.session['state'] = state
    return RedirectResponse(auth_url) """

    client_secrets = {
        "web":{
            "client_id":os.getenv('CLIENT_ID'),
            "project_id":"hypomineralisation",
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
            "client_secret":os.getenv('CLIENT_SECRET'),
            "redirect_uris":[os.getenv('SERVER_URL')]
        }
    }

    flow = Flow.from_client_config(
        client_secrets, 
        scopes=SCOPES
    )
    flow.redirect_uri = f'{server_url}/auth/login/google/callback'
    auth_url, state = flow.authorization_url(
        access_type='offline'
    )
    request.session['state'] = state
    return RedirectResponse(auth_url)


@login_router.get('/auth/login/google/callback')
async def callback_uri(request: Request, session: Session = Depends(Database.get_session), server_url = os.getenv("SERVER_URL"), front_url = os.getenv("FRONT_URL")):
    state = request.session.get('state')
    client_secrets = {
        "web":{
            "client_id":os.getenv('CLIENT_ID'),
            "project_id":"hypomineralisation",
            "auth_uri":"https://accounts.google.com/o/oauth2/auth",
            "token_uri":"https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
            "client_secret":os.getenv('CLIENT_SECRET'),
            "redirect_uris":[os.getenv('SERVER_URL')]
        }
    }
    flow = Flow.from_client_config(
        client_secrets, 
        scopes=SCOPES, 
        state=state
    )

    flow.redirect_uri = f'{server_url}/auth/login/google/callback'

    authorization_response = str(request.url)

    flow.fetch_token(authorization_response=authorization_response)

    user_info=None
    try:
        info = rq.get(f"https://www.googleapis.com/oauth2/v3/userinfo?access_token={flow.credentials.token}")
        user_info = info.json()
    except ValueError:
        raise HTTPException(status_code=401, detail="token inválido")

    statement = select(User).where(User.email == user_info['email'])
    user = session.exec(statement).first()
    if user is None:
        user = User(email=user_info['email'])  # Valor temporário
        session.add(user)
        session.commit()
        session.refresh(user)

    # adds the information we need from the user to the cookies
    request.session['id'] = user.id 
    request.session['email'] = user_info['email']
    request.session['name'] = user_info['name']
    required_fields = [user.email, user.role, user.name, user.city, user.state, user.neighborhood, user.phone_number, user.accept_tcle, user.id, user.created_at, user.updated_at]
    if all(field is None for field in required_fields):
        return RedirectResponse(os.getenv("LOGIN_CALLBACK_URL", front_url))
    else:
        return RedirectResponse(os.getenv("LOGIN_CALLBACK_URL", front_url))

# endpoint 'protegido' para buscar o usario ativo atualmente usando o token dos cookies
@login_router.get("/user/me")
async def me(
    request: Request,
    current_user: dict = Depends(AuthService.get_current_user),  # Obtém o usuário autenticado
    session: Session = Depends(Database.get_session)  # Conexão com o banco de dados
):

    if not current_user:
        raise HTTPException(status_code=401, detail="User unauthenticated")

    user_id = request.session.get("id")  # Pega o e-mail da sessão
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user  # Retorna o usuário encontrado no banco de dados
