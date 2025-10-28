from fastapi import Depends
from sqlalchemy.orm import Session
from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.consultas import consulta_get
from src.routers.models.usuario_model import PostCadastro, PostLogin
import bcrypt


@router.post("/cadastro")
def cadastro(user: PostCadastro, session: Session = Depends(get_db_mysql)):
    # query = f"""
    # SELECT 1 FROM TCC.usuario WHERE username = '{user.username}' OR email = '{user.email}'
    # """
    
    # if consulta_get(query, session):
    #     return {"message": "CPF ou email já cadastrado!"}


    hashed = bcrypt.hashpw(user.senha.encode('utf-8'), bcrypt.gensalt())
    hashed_senha = hashed.decode('utf-8')


    return hashed_senha


@router.post("/login")
def login_usuario(login: PostLogin, session: Session = Depends(get_db_mysql)):
    query = "SELECT id_cliente, senha FROM TCC.USUARIO WHERE email = :email"
    if not query: return {"message": "usuário não cadastrado"}
    result = session.execute(text(query), {"email": login.email}).fetchone()
    if result and bcrypt.checkpw(login.senha.encode('utf-8'), result[1].encode('utf-8')):
        return {"message": "Login realizado com sucesso!", "id_cliente": result[0]}
    else:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos!")