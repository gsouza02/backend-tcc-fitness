from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, UploadFile
from datetime import datetime

class PostAnamnese(BaseModel):
    usuario_id: int
    idade: int
    sexo: str
    peso: float
    experiencia: str
    tempo_treino: str
    dias_semana: str
    tempo_treino_por_dia: str
    objetivos: List[str]
    objetivo_especifico: str
    lesao: str
    condicao_medica: str
    exercicio_nao_gosta: str
    equipamentos: Optional[str] = None