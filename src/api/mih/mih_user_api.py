from fastapi import APIRouter, HTTPException, Depends, FastAPI, HTTPException, status, APIRouter
from sqlmodel import Session, select
from typing import List
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import random
from fastapi import Request
from fastapi import Body
from db.manager import Database  # Assumindo que você já tenha isso configurado
from schema.mih.schema_mih import User, UserCreate, UserRead, UserUpdate  # Seus modelos


security = HTTPBasic()

mih_user_router = APIRouter()

BASE_URL_USER = "/users/"


def authenticate_user(credentials: HTTPBasicCredentials = Depends(security)):
    user = users.get(credentials.username)
    if user is None or user["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user

def create_session(user_id: int):
    session_id = len(sessions) + random.randint(0, 1000000)
    sessions[session_id] = user_id
    return session_id   




# Create a new dependency to get the session ID from cookies
def get_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id is None or int(session_id) not in sessions:
        raise HTTPException(status_code=401, detail="Invalid session ID")
    return int(session_id)



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
    
    new_user = User.from_orm(user)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user




# Custom middleware for session-based authentication
def get_authenticated_user_from_session_id(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id is None or int(session_id) not in sessions:
        raise HTTPException(
            status_code=401,
            detail="Invalid session ID",
        )
    # Get the user from the session
    user = get_user_from_session(int(session_id))
    return user

# Use the valid session id to get the corresponding user from the users dictionary
def get_user_from_session(session_id: int):
    user = None
    for user_data in users.values():
        if user_data['user_id'] == sessions.get(session_id):
            user = user_data
            break

    return user



# Login endpoint - Creates a new session
@mih_user_router.post("/login")
def login(user: dict = Depends(authenticate_user)):
    session_id = create_session(user["user_id"])
    return {"message": "Logged in successfully", "session_id": session_id}



# Obter ponto de extremidade do usuário atual - Retorna o usuário correspondente ao ID da sessão 
@mih_user_router.get( "/getusers/me" ) 
def  read_current_user ( user: dict = Depends(get_user_from_session) ): 
    return user




# Ponto de extremidade protegido - Requer autenticação 
@mih_user_router.get( "/protected" ) 
def  protected_endpoint ( user: dict = Depends( get_authenticated_user_from_session_id ) ): 
    if user is  None : 
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail= "Não autenticado" ) 
    return { "message" : "Este usuário pode se conectar a um ponto de extremidade protegido pós autenticação bem-sucedida" , 
             "user" : user}




# Logout endpoint - Removes the session
@mih_user_router.post("/logout")
def logout(session_id: int = Depends(get_session_id)):
    if session_id not in sessions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    sessions.pop(session_id)
    return {"message": "Logged out successfully", "session_id": session_id}





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
