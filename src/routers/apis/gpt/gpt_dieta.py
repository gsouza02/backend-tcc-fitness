from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.anamnesemodel import PostAnamneseDieta
from src.routers.apis.gpt.funcs_gpt import gpt_response
from src.routers.models.consultas import consulta_get
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

    anamnese_text = (
    f"ID do usuário: {anamnese.usuario_id}\n"
    f"Sexo: {anamnese.sexo}\n"
    f"Idade: {anamnese.idade}\n"
    f"Altura (m): {anamnese.altura}\n"
    f"Peso atual (kg): {anamnese.pesoatual}\n"
    f"Peso desejado (kg): {anamnese.pesodesejado}\n"
    f"Objetivo: {anamnese.objetivo}\n"
    f"Data meta: {anamnese.data_meta}\n"
    f"Avaliação da rotina: {anamnese.avalicao_rotina}\n"
    f"Orçamento disponível: {anamnese.orcamento}\n"
    f"Alimentos acessíveis: {'sim' if anamnese.alimentos_acessiveis else 'não'}\n"
    f"Come fora com frequência: {'sim' if anamnese.come_fora else 'não'}\n"
    f"Tipo de alimentação: {anamnese.tipo_alimentacao}\n"
    f"Alimentos que gosta: {anamnese.alimentos_gosta or 'nenhum'}\n"
    f"Alimentos que não gosta: {anamnese.alimentos_nao_gosta or 'nenhum'}\n"
    f"Quantidade de refeições por dia: {anamnese.qtd_refeicoes}\n"
    f"Faz lanches entre refeições: {'sim' if anamnese.lanche_entre_refeicoes else 'não'}\n"
    f"Horário de alimentação: {anamnese.horario_alimentacao}\n"
    f"Prepara a própria refeição: {'sim' if anamnese.prepara_propria_refeicao else 'não'}\n"
    f"Onde costuma comer: {anamnese.onde_come}\n"
    f"Possui alergias: {'sim' if anamnese.possui_alergias else 'não'}\n"
    f"Condição médica: {anamnese.possui_condicao_medica or 'nenhuma'}\n"
    f"Usa suplementos: {'sim' if anamnese.uso_suplementos else 'não'}"
)

    return PROMPT_TEMPLATE.replace("<<<RESPOSTAS_ANAMNESE>>>", anamnese_text)


@router.post("/gpt/dieta")
def gpt_dieta(anamnese: PostAnamneseDieta):
    """
    Gera um plano de dieta personalizado usando GPT com base na anamnese fornecida.
    Args:
        anamnese (PostAnamneseDieta): Dados da anamnese do usuário.
    Returns:
        dict: Resposta contendo o plano de dieta gerado.
    """
    prompt = build_prompt(anamnese)
    plano = gpt_response(prompt)
    print(plano)
    return {
        "message": "Plano gerado com sucesso",
        "plano": plano,
    }

@router.post("/gpt/dieta/confirm")
def confirmar_dieta(payload: dict, session: Session = Depends(get_db_mysql)):
    """
    Confirma e persiste o plano de dieta gerado pelo GPT no banco de dados.
    Args:
        payload (dict): Dados contendo o plano de dieta a ser salvo.
        session (Session): Sessão do banco de dados.
    Returns:
        dict: Resposta indicando o sucesso da operação e detalhes do plano salvo.
    """
    try:
        resultado = persist_diet_plan(payload['plano'], session)
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

        get_last_dieta_id_query = """
        SELECT id_dieta AS last_id from TCC.DIETA WHERE id_usuario = :usuario ORDER BY id_dieta DESC LIMIT 1;
        """

        insert_refeicoes_query = text("""
        INSERT INTO TCC.REFEICOES (id_dieta, tipo_refeicao, alimentos, calorias)
        VALUES (:id_dieta, :tipo_refeicao, :alimentos, :calorias);
        """)

        session.execute(insert_dieta_query, {
            "nome": plano["nome"],
            "descricao": plano["descricao"],
            "usuario": plano["usuario"],
        })

        last_dieta_id = consulta_get(get_last_dieta_id_query, session, {"usuario": plano["usuario"]})[0]["last_id"]

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