from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.consultas import consulta_get
from src.routers.models.usuario_model import PostCadastro, PostLogin
from datetime import datetime, timedelta
from jose import jwt, JWTError
from src.core.config import SettingsAuth
import bcrypt


@router.post("/cadastro")
def cadastro(user: PostCadastro, session: Session = Depends(get_db_mysql)):
    query = f"""
    SELECT 1 FROM TCC.usuario WHERE username = '{user.username}' OR email = '{user.email}'
    """
    
    if consulta_get(query, session):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário ou e-mail já cadastrado!")


    hashed = bcrypt.hashpw(user.senha.encode('utf-8'), bcrypt.gensalt())
    hashed_senha = hashed.decode('utf-8')

    query = """
        INSERT INTO TCC.usuario (nome, email, username, senha) VALUES (:nome, :email, :username, :senha);
    """

    params = {
        'nome': user.nome,
        'email': user.email,
        'username': user.username,
        'senha': hashed_senha
    }

    session.execute(text(query), params)
    session.commit()

    return HTTPException(status_code=status.HTTP_201_CREATED, detail="Usuário cadastrado com sucesso!")


@router.post("/login")
def login_usuario(login: PostLogin, session: Session = Depends(get_db_mysql)):

    query = "SELECT id, senha FROM TCC.USUARIO WHERE email = :email"
    result = session.execute(text(query), {"email": login.email}).fetchone()
    if not result: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário ou senha inválidos!")


    if bcrypt.checkpw(login.senha.encode('utf-8'), result[1].encode('utf-8')):

        return generate_token(login.email)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário ou senha inválidos!")
    

def generate_token(email):

    exp = datetime.now() + timedelta(hours=1)

    payload = {
            "sub": email,
            "exp": exp
        }

    acecess_token = jwt.encode(
        payload,
        SettingsAuth().SECRET_KEY,
        algorithm=SettingsAuth().ALGORITHM
    )

    return {
        'access_token': acecess_token,
        'expiration': exp.isoformat()
    }
