from pydantic import BaseModel
from datetime import datetime


class PostCliente(BaseModel):
    nome: str
    cpf: str
    telefone: str
    email: str
    endereco: str
    data_nascimento:str
    senha: str
    
class Cliente(BaseModel):
    email: str
    senha: str


class PostPedido(BaseModel):
    id_cliente: int
    quantidade: int
    id_produto: int