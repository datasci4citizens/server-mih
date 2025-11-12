from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from db.manager import Database
from auth.auth_service import AuthService
from schema.mih.schema_mih import User, UserRead
from sqlmodel import Session, select
import requests
import os

login_router = APIRouter()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

GOOGLE_ACCESS_TOKEN_OBTAIN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

class GoogleLoginRequest(BaseModel):
    code: str

@login_router.post('/auth/login/google', response_model=UserRead)
async def google_login(
    data: GoogleLoginRequest,
    request: Request,
    session: Session = Depends(Database.get_session)
):

    # 1. Trocar o código por um access_token
    token_data = {
        "code": data.code,
        "client_id": os.getenv('CLIENT_ID'),
        "client_secret": os.getenv('CLIENT_SECRET'),
        "redirect_uri": "postmessage", 
        "grant_type": "authorization_code",
    }

    token_response = requests.post(GOOGLE_ACCESS_TOKEN_OBTAIN_URL, data=token_data)
    if not token_response.ok:
        error_details = token_response.json()
        print(f"ERRO DO GOOGLE: {error_details}")
        raise HTTPException(status_code=400, detail=f"Falha ao obter token do Google: {error_details}")

    access_token = token_response.json()["access_token"]

    # 2. Usar o access_token para obter informações do usuário
    user_info_response = requests.get(
        GOOGLE_USER_INFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if not user_info_response.ok:
        raise HTTPException(status_code=400, detail="Falha ao obter informações do usuário do Google")

    user_info = user_info_response.json()
    email = user_info.get("email")
    name = user_info.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="Email não encontrado no token do Google")

    # 3. Encontrar ou criar o usuário no seu banco de dados
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if user is None:
        user = User(email=email, name=name)
        session.add(user)
        session.commit()
        session.refresh(user)

    # 4. Criar a sessão no backend
    request.session['id'] = user.id
    request.session['email'] = user.email
    request.session['name'] = user.name

    return user

@login_router.post('/auth/login/google/native', response_model=UserRead)
async def google_login_native(
    data: GoogleLoginRequest,
    request: Request,
    session: Session = Depends(Database.get_session)
):
    # No login nativo, o frontend já envia o access_token diretamente.
    access_token = data.code

    # 1. Usar o access_token para obter informações do usuário
    user_info_response = requests.get(
        GOOGLE_USER_INFO_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if not user_info_response.ok:
        raise HTTPException(status_code=400, detail="Falha ao obter informações do usuário do Google com o token fornecido")

    user_info = user_info_response.json()
    email = user_info.get("email")
    name = user_info.get("name")

    if not email:
        raise HTTPException(status_code=400, detail="Email não encontrado nas informações do usuário do Google")

    # 2. Encontrar ou criar o usuário no seu banco de dados
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    if user is None:
        user = User(email=email, name=name)
        session.add(user)
        session.commit()
        session.refresh(user)

    # 3. Criar a sessão no backend
    request.session['id'] = user.id
    request.session['email'] = user.email
    request.session['name'] = user.name

    return user

# endpoint 'protegido' para buscar o usario ativo atualmente usando o token dos cookies
@login_router.get("/user/me")
async def me(
    request: Request,
    current_user: dict = Depends(AuthService.get_current_user),  # Obtém o usuário autenticado
    session: Session = Depends(Database.get_session)  # Conexão com o banco de dados
):
    user_id = request.session.get("id")

    user = session.get(User, user_id)
    if not user:
        print(f"Backend /user/me: Raising 404 HTTPException for user_id: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    
    return user  # Retorna o usuário encontrado no banco de dados


@login_router.post('/auth/logout')
async def logout(request: Request):
    request.session.clear()
    return {'message': 'Logout successful'}