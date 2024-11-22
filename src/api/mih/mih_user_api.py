from fastapi import APIRouter, HTTPException, Depends, FastAPI, HTTPException, status, APIRouter
from sqlmodel import Session, select
from typing import List
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import random
from fastapi import Request
from fastapi import Body
from db.manager import Database  # Assumindo que você já tenha isso configurado
from schema.mih.schema_mih import User, UserCreate, UserRead, UserUpdate  # Seus modelos
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




# Criar um novo usuário (responsável)
@mih_user_router.post(BASE_URL_USER, response_model=UserRead)
def create_user(
        *,
        session: Session = Depends(Database.get_session),
        user: UserCreate
):
    ##"""Create a new user"""
    ##db_user = session.exec(select(User).where(User.email == user.email)).first()
    #if db_user:
        #raise HTTPException(status_code=400, detail="Email already registered")
    dates = {"created_at": datetime.now(), "updated_at": datetime.now()}
    db_user = User.model_validate(user, update=dates)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
    
    #new_user = User.from_orm(user)
    #session.add(new_user)
    #session.commit()
    #session.refresh(new_user)
    #return new_user






# Listar todos os usuários
@mih_user_router.get(BASE_URL_USER, response_model=List[UserRead])
def get_users(session: Session = Depends(Database.get_session)):
    users = session.exec(select(User)).all()
    return users

# Obter um usuário por ID
@mih_user_router.get(BASE_URL_USER + "{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(Database.get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Atualizar um usuário
@mih_user_router.put(BASE_URL_USER + "{user_id}", response_model=UserRead)
def update_user(user_id: int, user: UserUpdate, session: Session = Depends(Database.get_session)):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

# Deletar um usuário
@mih_user_router.delete(BASE_URL_USER + "{user_id}")
def delete_user(user_id: int, session: Session = Depends(Database.get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"ok": True}
