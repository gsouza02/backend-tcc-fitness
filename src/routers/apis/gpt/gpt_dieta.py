from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.anamnesemodel import PostAnamneseDieta
from src.routers.apis.gpt.funcs_gpt import gpt_response
from src.routers.models.consultas import consulta_get
from pydantic import BaseModel, Field
from typing import Any
import json

PROMPT_TEMPLATE = """
Você é uma IA de prescrição de dietas. Sua única tarefa é gerar, a partir das respostas de anamnese descritas abaixo, um JSON válido que represente um plano alimentar completo. Leia todo o enunciado antes de responder.

REQUISITOS OBRIGATÓRIOS

A resposta deve ser EXCLUSIVAMENTE um JSON bem formatado, sem comentários, cabeçalhos, explicações ou texto adicional.

Siga exatamente o esquema:

{
"nome": "string obrigatória",
"descricao": "string obrigatória (resuma objetivo nutricional, calorias alvo diárias e distribuição aproximada de macros)",
"usuario": inteiro >= 1,
"refeicoes": [
{
"calorias": inteiro >= 0 (calorias estimadas para a refeição, coerentes com a soma dos alimentos listados),
"alimentos": "string obrigatória: lista de pelo menos 3 alimentos no formato 'Nome Do Alimento - Quantidade Detalhada - Breve Preparação/Observação', sempre com a primeira letra de cada palavra em maiúsculo e separados por ponto e vírgula ';' (ex.: 'Peito De Frango Grelhado - 150 g - Grelhado Em Azeite; Arroz Integral - 120 g - Cozido Em Água; Brócolis Cozidos - 100 g - No Vapor'),",
"tipoRefeicao": "Café da manhã" | "Almoço" | "Jantar" | "Lanche" | "Ceia" 
}
]
}

Todos os campos devem ser preenchidos com valores coerentes com as respostas da anamnese.

Gere conforme rotina e objetivos do usuário.

Use apenas números inteiros para campos numéricos.

O campo usuario deve conter o ID informado na anamnese; se não houver, adote um número plausível (ex.: 1).

Os nomes e descrições devem refletir objetivos, preferências alimentares, restrições, rotina e metas do usuário. A descrição do plano deve explicar a estratégia calórica diária, a distribuição aproximada de macronutrientes (proteínas, carboidratos, gorduras) e orientações gerais (ex.: ingestão hídrica, temperos leves, opções de substituição).

As calorias devem ser proporcionais ao objetivo (ex.: déficit para emagrecimento, superávit para ganho de massa), distribuídas ao longo das refeições conforme os horários informados e o número de refeições desejado.

Os alimentos devem ser adequados às preferências e restrições informadas (ex.: vegetariano, intolerância à lactose, etc.). Cada alimento deve trazer porção/quantidade explícita em unidades do sistema métrico (gramas, mililitros) ou medidas caseiras detalhadas, com nome capitalizado (Title Case) e breve nota de preparo.

Sempre retorne um JSON sintaticamente válido (aberturas/fechamentos corretos, aspas em strings, vírgulas adequadas).

Cada refeição deve conter alimentos que façam sentido nutricionalmente para o horário e objetivo, cobrindo proteína magra, carboidrato complexo e fonte de micronutrientes/fibras.

PROCESSO DE GERAÇÃO

Primeiro, interprete o perfil do usuário (idade, sexo, peso, altura, objetivo, rotina, restrições, preferências alimentares e horários).

Determine o total calórico diário e divida entre as refeições conforme o padrão alimentar indicado, garantindo que a soma das calorias das refeições seja consistente (diferença máxima de ±50 kcal do total diário).

Defina o nome e descrição do plano de forma clara e resumida, destacando o objetivo principal.

Para cada refeição:

Escolha alimentos adequados e variados, sempre descrevendo a quantidade no formato "Nome Do Alimento - Quantidade - Preparo" (Title Case) e combinando fontes de proteína magra, carboidratos complexos, gorduras boas e fibras. Separe cada alimento por ponto e vírgula ';'.

Ajuste as calorias conforme a proporção do total diário, indicando refeições maiores em momentos estratégicos (ex.: pré/pós-treino, horários principais).

Adapte os alimentos a restrições e preferências informadas, sugerindo alternativas equivalentes quando houver limitações e mantendo a mesma formatação (Title Case + quantidade + preparo), sempre separados por ';'.

Use quantidades e combinações coerentes com o horário e o objetivo nutricional, evitando repetições excessivas e incluindo opções de frutas, vegetais e fontes integrais ao longo do dia, sempre com nomenclatura padronizada. Nunca liste apenas um alimento por refeição.

Mencione preparos simples (assado, grelhado, cozido, cru) e evite alimentos ultraprocessados; priorize temperos naturais e hidratação adequada. Certifique-se de que a soma calórica reflita porções realistas (ovo inteiro ~70 kcal, banana média ~90 kcal, frango grelhado 150 g ~165 kcal etc.).

ANAMNESE DO USUÁRIO
<<<RESPOSTAS_ANAMNESE>>>
"""

ADJUSTMENT_SUFFIX_TEMPLATE = """

PLANO ATUAL EM JSON:
{plano_atual}

ALTERAÇÕES SOLICITADAS PELO USUÁRIO:
{ajustes}

Produza um NOVO plano alimentar seguindo todas as instruções anteriores, ajustando exatamente o que foi solicitado e mantendo o formato JSON especificado. Garanta consistência calórica, variedade equilibrada e quantidades detalhadas por alimento, com no mínimo 3 itens por refeição.
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


def build_adjustment_prompt(anamnese: PostAnamneseDieta, plano_atual: dict, ajustes: str) -> str:
    base_prompt = build_prompt(anamnese)
    plano_json = json.dumps(plano_atual, ensure_ascii=False, indent=2)
    ajustes_texto = ajustes.strip() or "Sem ajustes adicionais fornecidos"
    return base_prompt + ADJUSTMENT_SUFFIX_TEMPLATE.format(
        plano_atual=plano_json,
        ajustes=ajustes_texto,
    )


class AdjustmentPayload(BaseModel):
    anamnese: PostAnamneseDieta
    plano_atual: dict = Field(..., alias="planoAtual")
    ajustes: str


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


@router.post("/gpt/dieta/ajustar")
def ajustar_dieta(payload: AdjustmentPayload):
    prompt = build_adjustment_prompt(payload.anamnese, payload.plano_atual, payload.ajustes)
    plano = gpt_response(prompt)
    print(plano)
    return {
        "message": "Plano de dieta ajustado com sucesso",
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