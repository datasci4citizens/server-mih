from fastapi import HTTPException, Request, Depends
from sqlalchemy.orm import Session
from db.manager import Database
from schema.mih.schema_mih import User  # Importe o modelo User do banco de dados

class AuthService:
    @staticmethod
    def get_current_user(request: Request, session: Session = Depends(Database.get_session)):
        credentials = request.session.get("credentials")
        if not credentials or not credentials.get("token"):
            raise HTTPException(status_code=401, detail="User not authenticated")

        email = request.session.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Email not found in session")

        user = session.query(User).filter(User.email == email).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found in database")

        user_name = user.name  # Aqui você pega o nome do banco de dados

        return {"email": email, "user_name" : user_name}