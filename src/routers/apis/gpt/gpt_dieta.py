from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.anamnesemodel import PostAnamnese
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from typing import Any

PROMPT_TEMPLATE = """
"""


def build_prompt(anamnese: PostAnamnese) -> str:
    objetivos_text = ", ".join(anamnese.objetivos) if anamnese.objetivos else "não especificado"
    equipamentos_text = anamnese.equipamentos or "não informado"

    anamnese_text = (
        f"ID do usuário: {anamnese.usuario_id}\n"
        f"Idade: {anamnese.idade}\n"
        f"Sexo: {anamnese.sexo}\n"
        f"Peso (kg): {anamnese.peso}\n"
        f"Experiência: {anamnese.experiencia}\n"
        f"Tempo de treino atual: {anamnese.tempo_treino}\n"
        f"Dias por semana disponíveis: {anamnese.dias_semana}\n"
        f"Tempo disponível por treino: {anamnese.tempo_treino_por_dia}\n"
        f"Objetivos principais: {objetivos_text}\n"
        f"Objetivo específico: {anamnese.objetivo_especifico}\n"
        f"Lesões ou limitações: {anamnese.lesao or 'nenhuma'}\n"
        f"Condições médicas: {anamnese.condicao_medica or 'nenhuma'}\n"
        f"Exercícios que não gosta: {anamnese.exercicio_nao_gosta or 'nenhum'}\n"
        f"Equipamentos disponíveis: {equipamentos_text}"
    )
    return PROMPT_TEMPLATE.replace("<<<RESPOSTAS_ANAMNESE>>>", anamnese_text)