from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from db.manager import Database
from schema.mih.schema_mih import User  # Importe o modelo User do banco de dados

class AuthService:
    @staticmethod
    def get_current_user(request: Request):
        user_id = request.session.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User not authenticated")
        return request.session.get("email")