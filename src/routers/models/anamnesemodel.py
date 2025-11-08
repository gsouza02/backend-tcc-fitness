from pydantic import BaseModel
from fastapi import UploadFile, UploadFile
from datetime import datetime

class PostAnamnese(BaseModel):
    usuario_id: int
    idade: int
    sexo: str
    peso: float
    experiencia: str
    tempo_treino: int
    dias_semana: int
    tempo_treino_por_dia: int
    objetivos: str
    objetivo_especifico: str
    lesao: str
    condicao_medica: str
    exercicio_nao_gosta: str
    equipamentos: str