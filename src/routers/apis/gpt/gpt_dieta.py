from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.anamnesemodel import PostAnamneseDieta
from src.routers.apis.gpt.funcs_gpt import gpt_response
from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from typing import Any

PROMPT_TEMPLATE = """
Você é uma IA de prescrição de dietas. Sua única tarefa é gerar, a partir das respostas de anamnese descritas abaixo, um JSON válido que represente um plano alimentar completo. Leia todo o enunciado antes de responder.

REQUISITOS OBRIGATÓRIOS

A resposta deve ser EXCLUSIVAMENTE um JSON bem formatado, sem comentários, cabeçalhos, explicações ou texto adicional.

Siga exatamente o esquema:

{
"nome": "string obrigatória",
"descricao": "string obrigatória",
"usuario": inteiro >= 1,
"refeicoes": [
{
"calorias": inteiro >= 0 (calorias estimadas para a refeição),
"alimentos": "string obrigatória (alimentos separados por vírgula)",
"tipoRefeicao": "Café da manhã" | "Almoço" | "Jantar" | "Lanche" | "Ceia" 
}
]
}

Todos os campos devem ser preenchidos com valores coerentes com as respostas da anamnese.

Gere conforme rotina e objetivos do usuário.

Use apenas números inteiros para campos numéricos.

O campo usuario deve conter o ID informado na anamnese; se não houver, adote um número plausível (ex.: 1).

Os nomes e descrições devem refletir objetivos, preferências alimentares, restrições, rotina e metas do usuário.

As calorias devem ser proporcionais ao objetivo (ex.: déficit para emagrecimento, superávit para ganho de massa).

Os alimentos devem ser adequados às preferências e restrições informadas (ex.: vegetariano, intolerância à lactose, etc.).

Sempre retorne um JSON sintaticamente válido (aberturas/fechamentos corretos, aspas em strings, vírgulas adequadas).

Cada refeição deve conter alimentos que façam sentido nutricionalmente para o horário e objetivo.

PROCESSO DE GERAÇÃO

Primeiro, interprete o perfil do usuário (idade, sexo, peso, altura, objetivo, rotina, restrições, preferências alimentares e horários).

Determine o total calórico diário e divida entre as refeições conforme o padrão alimentar indicado.

Defina o nome e descrição do plano de forma clara e resumida, destacando o objetivo principal.

Para cada refeição:

Escolha alimentos adequados e variados.

Ajuste as calorias conforme a proporção do total diário.

Adapte os alimentos a restrições e preferências informadas.

Use quantidades e combinações coerentes com o horário e o objetivo nutricional.

ANAMNESE DO USUÁRIO
<<<RESPOSTAS_ANAMNESE>>>
"""


def build_prompt(anamnese: PostAnamneseDieta) -> str:
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


@router.post("/gpt/dieta")
def gpt(anamnese: PostAnamneseDieta):
    prompt = build_prompt(anamnese)
    plano = gpt_response(prompt)
    print(plano)
    return {
        "message": "Plano gerado com sucesso",
        "plano": plano,
    }

@router.post("/gpt/dieta/confirm")
def confirmar_plano(payload: dict, session: Session = Depends(get_db_mysql)):
    try:
        resultado = persist_diet_plan(payload.plano, session)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar treino: {exc}") from exc

    return {
        "message": "Plano gerado e salvo com sucesso",
        "programa": resultado["programa"],
        "treinosIds": resultado["treinos_inseridos"],
        "plano": resultado["plano"],
    }

def persist_diet_plan(plano: dict, session: Session) -> dict:
    try:
        insert_dieta_query = text("""
        INSERT INTO TCC.DIETA (nome, descricao, id_usuario)
        VALUES (:nome, :descricao, :usuario);
        """)

        get_last_dieta_id_query = text("""
        SELECT LAST_INSERT_ID() AS last_id WHERE ID_USUARIO = :usuario;
        """)

        insert_refeicoes_query = text("""
        INSERT INTO TCC.REFEICOES (id_dieta, tipo_refeicao, alimentos, calorias)
        VALUES (:id_dieta, :tipo_refeicao, :alimentos, :calorias);
        """)

        session.execute(insert_dieta_query, {
            "nome": plano["nome"],
            "descricao": plano["descricao"],
            "usuario": plano["usuario"],
        })

        result = session.execute(get_last_dieta_id_query, {
            "usuario": plano["usuario"],
        })

        last_dieta_id = result.fetchone()["last_id"]

        refeicoes_inseridas = []
        for refeicao in plano["refeicoes"]:
            session.execute(insert_refeicoes_query, {
                "id_dieta": last_dieta_id,
                "tipo_refeicao": refeicao["tipoRefeicao"],
                "alimentos": refeicao["alimentos"],
                "calorias": refeicao["calorias"],
            })
            refeicoes_inseridas.append(refeicao)

        return {
            "programa": plano["nome"],
            "treinos_inseridos": refeicoes_inseridas,
            "plano": plano,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao persistir plano de dieta: {exc}") from exc