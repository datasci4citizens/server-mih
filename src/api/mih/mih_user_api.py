from fastapi import APIRouter, HTTPException, Depends, FastAPI, HTTPException, status, APIRouter, Query
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import random
from enum import Enum
from fastapi import Request
from fastapi import Body
from db.manager import Database  # Assumindo que você já tenha isso configurado
from schema.mih.schema_mih import User, UserRole, UserCreate, UserRead, UserUpdate  # Seus modelos
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi.staticfiles import StaticFiles
from auth.auth_service import AuthService



mih_user_router = APIRouter(
    dependencies=[Depends(AuthService.get_current_user)]
)

BASE_URL_USER = "/users/"


""" @mih_user_router.post("/choose_role/")
async def choose_role(email: str, role: UserRole, db: Session = Depends(Database)):
    # Verifica se o role é válido
    if role not in [UserRole.RESPONSIBLE, UserRole.SPECIALIST]:
        raise HTTPException(status_code=400, detail="Role inválido.")

    # Verifica se o usuário já existe
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    
    # Atualiza o role do usuário
    user.role = role
    db.commit()
    db.refresh(user)

    return {"message": "Usuário registrado com sucesso!", "user": user}
 """

# Criar um novo usuário (responsável ou especialista)
@mih_user_router.post(BASE_URL_USER, response_model=UserRead)
def create_user(
        *,
        session: Session = Depends(Database.get_session),
        user: UserCreate
):
    # Verifica se a role foi fornecida, caso contrário, atribui um valor padrão
    if not user.role:
        user.role = UserRole.RESPONSIBLE  # ou qualquer valor padrão que você prefira
    
    # Verifica se a role é válida
    if user.role not in UserRole:
        raise HTTPException(status_code=400, detail="Invalid role")

    
    dates = {"created_at": datetime.now(), "updated_at": datetime.now()}
    db_user = User.model_validate(user, update=dates)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user







# Listar todos os usuários (responsavel ou especialista)
@mih_user_router.get(BASE_URL_USER, response_model=List[UserRead])
def get_users(
        session: Session = Depends(Database.get_session),
        role: Optional[UserRole] = Query(None)  # Filtro opcional
):
    statement = select(User)
    if role:  # Aplica o filtro se o parâmetro for fornecido
        statement = statement.where(User.role == role)
    
    users = session.exec(statement).all()
    return users


# Obter um usuário por ID (responsavel ou especialista)
@mih_user_router.get(BASE_URL_USER + "{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(Database.get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Atualizar um usuário (responsavel ou especialista)
@mih_user_router.put(BASE_URL_USER, response_model=UserRead)
def update_user(request: Request, user: UserUpdate, session: Session = Depends(Database.get_session)):

    user_id = request.session.get("id")
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    db_user.updated_at = datetime.now()  # Atualiza a data de modificação
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

#Pegar todos os responsaveis ou todos os especialistas
@mih_user_router.get(BASE_URL_USER, response_model=List[UserRead])
def get_users_by_role(
        role: Optional[UserRole] = Query(None),  # Parâmetro opcional
        session: Session = Depends(Database.get_session)
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    
    users = session.exec(query).all()
    return users



# Deletar um usuário (responsável ou especialista)
# Função para exclusão condicional no endpoint
@mih_user_router.delete(BASE_URL_USER + "{user_id}")
def delete_user(user_id: int, session: Session = Depends(Database.get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verifica se o usuário é um responsável antes de deletar pacientes
    if user.role == UserRole.RESPONSIBLE:
        # Deleta os pacientes associados ao responsável
        for patient in user.patients:
            session.delete(patient)

    # Deleta o usuário (responsável ou especialista)
    session.delete(user)
    session.commit()
    return {"ok": True}



