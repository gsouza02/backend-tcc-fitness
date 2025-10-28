from pydantic import BaseModel
from fastapi import UploadFile, UploadFile
from datetime import datetime

class PostCadastro(BaseModel):
    username: str
    nome: str
    senha: str
    email: str

class PostLogin(BaseModel):
    email: str
    senha: str


# from sqlalchemy import Column, Integer, String
# from sqlalchemy.orm import declarative_base

# Base = declarative_base()

# class Cliente(Base):
#     __tablename__ = "cliente"
#     id = Column(Integer, primary_key=True, index=True)
#     nome = Column(String)
#     username = Column(String, unique=True, index=True)
#     email = Column(String, unique=True, index=True)
#     senha = Column(String)