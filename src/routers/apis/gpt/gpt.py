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
from pydantic import BaseModel, Field

PROMPT_TEMPLATE = """
Você é uma IA de prescrição de treinos. Sua única tarefa é gerar, a partir das respostas de anamnese descritas abaixo, um JSON válido que represente um programa de treino completo. Leia todo o enunciado antes de responder.

REQUISITOS OBRIGATÓRIOS
1. A resposta deve ser EXCLUSIVAMENTE um JSON bem formatado, sem comentários, cabeçalhos, explicações ou texto adicional.
2. O foco é musculação tradicional em academia. Utilize exercícios com pesos livres, máquinas, cabos ou peso corporal, sempre coerentes com uma rotina de musculação.
3. Siga exatamente o esquema:

{
  "programaTreino": {
    "nomePrograma": "string obrigatória",
    "descricaoPrograma": "string obrigatória"
  },
  "treinos": [
    {
      "nome": "string obrigatória",
      "descricao": "string obrigatória",
      "idUsuario": inteiro >= 1,
      "duracaoMinutos": inteiro >= 10,
      "dificuldade": "iniciante" | "intermediario" | "avancado",
      "exercicios": [
        {
          "idExercicio": inteiro >= 1,
          "series": inteiro >= 1,
          "repeticoes": inteiro >= 1,
          "descansoSegundos": inteiro >= 15
        }
      ]
    }
  ]
}

4. Todos os campos devem estar preenchidos com valores coerentes com as respostas da anamnese.
5. Gere pelo menos 1 treino e entre 1 e 10 exercícios por treino.
6. Use apenas números inteiros para campos numéricos.
7. `idUsuario` deve ser coerente: se a anamnese informar um ID, use-o; se não, adote um número plausível (ex.: 1).
8. Nomes e descrições precisam ser específicos e padronizados: use títulos como "Treino 01 - Peito e Tríceps Hipertrofia" ou "Treino 03 - Pernas Ênfase Quadríceps". A descrição deve mencionar objetivo do dia, intensidade e recomendações rápidas.
9. Exercícios devem ser compatíveis com as condições e equipamento informados. Ajuste séries, repetições e descanso conforme o nível/objetivo (ex.: hipertrofia, resistência, emagrecimento).
10. Mesmo quando o usuário pedir foco em um grupo muscular específico, distribua o programa para cobrir todo o corpo ao longo da semana. Apenas aumente a ênfase (mais volume/variações) no objetivo informado, sem negligenciar os demais grupos.
11. Se houver lesões ou limitações, adapte a seleção de exercícios e descreva isso no campo `descricao` do treino.
12. Sempre retorne um JSON sintaticamente válido (aberturas/fechamentos corretos, aspas em strings, vírgulas adequadas).
13. Gere um treino para cada dia disponível do usuário.

PROCESSO DE GERAÇÃO
- Primeiro, interprete o perfil do usuário (idade, experiência, disponibilidade, objetivos, lesões, equipamentos).
- Determine a dificuldade adequada ("iniciante", "intermediario" ou "avancado").
- Defina nome e descrição do programa resumindo o objetivo principal e a abordagem.
- Para cada treino:
  • Defina nome e descrição específicos, destacando foco muscular, objetivo do dia e recomendações.
  • Escolha exercícios compatíveis; distribua os grupos musculares ao longo da semana, priorizando o objetivo sem excluir os demais.
  • Ajuste séries, repetições e descanso para refletir intensidade e tempo disponível.
  • Mantenha a duração total aproximada coerente com o tempo informado.

ANAMNESE DO USUÁRIO
<<<RESPOSTAS_ANAMNESE>>>
"""

ADJUSTMENT_SUFFIX_TEMPLATE = """

PLANO ATUAL EM JSON:
{plano_atual}

ALTERAÇÕES SOLICITADAS PELO USUÁRIO:
{ajustes}

Produza um NOVO plano de treino seguindo todas as regras anteriores e aplicando exatamente as alterações solicitadas. Continue com foco em musculação, use nomes padronizados no estilo \"Treino 02 - Costas e Bíceps Intensidade Média\" e mantenha a distribuição equilibrada dos grupos musculares, apenas aumentando a ênfase naquilo que o usuário solicitou. A resposta deve ser exclusivamente um JSON válido, no mesmo formato especificado anteriormente.
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


def build_adjustment_prompt(anamnese: PostAnamnese, plano_atual: dict, ajustes: str) -> str:
    base_prompt = build_prompt(anamnese)
    plano_json = json.dumps(plano_atual, ensure_ascii=False, indent=2)
    ajustes_texto = ajustes.strip() or "Sem ajustes adicionais fornecidos."
    return base_prompt + ADJUSTMENT_SUFFIX_TEMPLATE.format(
        plano_atual=plano_json,
        ajustes=ajustes_texto,
    )


def parse_response_output(response: Any) -> str:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    text_chunks: list[str] = []
    output_items = getattr(response, "output", [])

    for item in output_items or []:
        contents = getattr(item, "content", [])
        for content in contents:
            if isinstance(content, dict):
                text_value = content.get("text") or content.get("value")
                if text_value:
                    text_chunks.append(text_value)
            else:
                text_value = getattr(content, "text", None) or getattr(content, "value", None)
                if text_value:
                    text_chunks.append(text_value)
    return "".join(text_chunks)


def extract_json_payload(raw_text: str) -> str:
    if not raw_text:
        return ""

    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        newline_index = cleaned.find("\n")
        if newline_index != -1:
            cleaned = cleaned[newline_index + 1 :].strip()

    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace >= first_brace:
        return cleaned[first_brace : last_brace + 1]

    return cleaned


def gpt_response(prompt: str) -> dict:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY não configurada")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-4o-mini-2024-07-18",
        input=prompt
    )

    raw_text = parse_response_output(response)
    if not raw_text:
        raise HTTPException(status_code=502, detail="Resposta vazia do modelo")

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            json_payload = extract_json_payload(raw_text)
            return json.loads(json_payload)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail=f"Falha ao decodificar JSON da IA: {exc}") from exc


def persist_workout_plan(plan: dict, session: Session) -> dict:
    programa = plan.get("programaTreino")
    treinos = plan.get("treinos")

    if not isinstance(programa, dict) or not isinstance(treinos, list) or not treinos:
        raise HTTPException(status_code=400, detail="Estrutura do plano inválida")

    select_exercicio_sql = text(
        """
        SELECT id_exercicio
        FROM TCC.EXERCICIOS
        WHERE id_exercicio = :id_exercicio
        LIMIT 1
        """
    )

    insert_programa_sql = text(
        """
        INSERT INTO TCC.PROGRAMA_TREINO (id_usu, nome, descricao)
        VALUES (:id_usuario, :nome_programa, :descricao_programa)
        """
    )

    insert_treino_sql = text(
        """
        INSERT INTO TCC.TREINO (nome, descricao, id_usuario, id_programa_treino, duracao, dificuldade)
        VALUES (:nome, :descricao, :id_usuario, :id_programa_treino, :duracao, :dificuldade)
        """
    )

    insert_exercicio_treino_sql = text(
        """
        INSERT INTO TCC.EXERCICIO_TREINO (id_exercicio, id_treino, descanso)
        VALUES (:id_exercicio, :id_treino, :descanso)
        """
    )

    insert_serie_sql = text(
        """
        INSERT INTO TCC.SERIES (numero_serie, repeticoes, carga, id_ex_treino)
        VALUES (:numero_serie, :repeticoes, :carga, :id_ex_treino)
        """
    )

    treinos_inseridos: list[int] = []

    nome_programa = programa.get("nomePrograma")
    descricao_programa = programa.get("descricaoPrograma")

    if not nome_programa or not descricao_programa:
        raise HTTPException(status_code=400, detail="Dados do programa incompletos")

    try:
        usuario_programa_id = int(treinos[0].get("idUsuario"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="ID de usuário inválido no plano gerado")

    programa_result = session.execute(
        insert_programa_sql,
        {
            "id_usuario": usuario_programa_id,
            "nome_programa": nome_programa,
            "descricao_programa": descricao_programa,
        }
    )
    programa_id = programa_result.lastrowid
    if not programa_id:
        raise HTTPException(status_code=500, detail="Falha ao inserir programa de treino")

    for treino in treinos:
        try:
            id_usuario = int(treino.get("idUsuario"))
            duracao = int(treino.get("duracaoMinutos"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Campos numéricos inválidos no treino gerado")

        if id_usuario < 1 or duracao < 10:
            raise HTTPException(status_code=400, detail="Valores inconsistentes no treino gerado")

        if id_usuario != usuario_programa_id:
            raise HTTPException(status_code=400, detail="Todos os treinos do programa devem pertencer ao mesmo usuário")

        nome_treino = treino.get("nome")
        descricao_treino = treino.get("descricao")
        dificuldade = treino.get("dificuldade")

        if not nome_treino or not descricao_treino or not dificuldade:
            raise HTTPException(status_code=400, detail="Dados obrigatórios do treino ausentes")

        result_treino = session.execute(
            insert_treino_sql,
            {
                "nome": nome_treino,
                "descricao": descricao_treino,
                "id_usuario": id_usuario,
                "id_programa_treino": programa_id,
                "duracao": duracao,
                "dificuldade": dificuldade.lower(),
            }
        )
        treino_id = result_treino.lastrowid
        if not treino_id:
            raise HTTPException(status_code=500, detail="Falha ao inserir treino")

        treinos_inseridos.append(treino_id)

        exercicios = treino.get("exercicios") or []
        if not exercicios:
            raise HTTPException(status_code=400, detail="Treino gerado sem exercícios")

        for exercicio in exercicios:
            try:
                id_exercicio = int(exercicio.get("idExercicio"))
                series_total = int(exercicio.get("series"))
                repeticoes = int(exercicio.get("repeticoes"))
                descanso = int(exercicio.get("descansoSegundos"))
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="Campos numéricos inválidos nos exercícios gerados")

            if id_exercicio < 1 or series_total < 1 or repeticoes < 1 or descanso < 15:
                raise HTTPException(status_code=400, detail="Valores inconsistentes nos exercícios gerados")

            exercicio_existe = session.execute(
                select_exercicio_sql, {"id_exercicio": id_exercicio}
            ).scalar()

            if not exercicio_existe:
                raise HTTPException(
                    status_code=400,
                    detail=f"Exercício com ID {id_exercicio} não encontrado na tabela EXERCICIOS.",
                )

            result_ex_treino = session.execute(
                insert_exercicio_treino_sql,
                {
                    "id_exercicio": id_exercicio,
                    "id_treino": treino_id,
                    "descanso": descanso,
                }
            )
            id_ex_treino = result_ex_treino.lastrowid
            if not id_ex_treino:
                raise HTTPException(status_code=500, detail="Falha ao inserir exercício do treino")

            for numero in range(1, series_total + 1):
                session.execute(
                    insert_serie_sql,
                    {
                        "numero_serie": numero,
                        "repeticoes": repeticoes,
                        "carga": None,
                        "id_ex_treino": id_ex_treino,
                    }
                )

    if not treinos_inseridos:
        raise HTTPException(status_code=500, detail="Nenhum treino foi inserido para o programa")

    return {
        "programa": {
            "id_programa_treino": programa_id,
            "nome": nome_programa,
            "descricao": descricao_programa,
        },
        "treinos_inseridos": treinos_inseridos,
        "plano": plan,
    }


class PlanPayload(BaseModel):
    plano: dict


class AdjustmentPayload(BaseModel):
    anamnese: PostAnamnese
    plano_atual: dict = Field(..., alias="planoAtual")
    ajustes: str


@router.post("/gpt")
def gpt(anamnese: PostAnamnese):
    prompt = build_prompt(anamnese)
    plano = gpt_response(prompt)
    print(plano)
    return {
        "message": "Plano gerado com sucesso",
        "plano": plano,
    }


@router.post("/gpt/ajustar")
def ajustar_plano(payload: AdjustmentPayload):
    prompt = build_adjustment_prompt(payload.anamnese, payload.plano_atual, payload.ajustes)
    plano = gpt_response(prompt)
    print(plano)
    return {
        "message": "Plano ajustado com sucesso",
        "plano": plano,
    }


@router.post("/gpt/confirm")
def confirmar_plano(payload: PlanPayload, session: Session = Depends(get_db_mysql)):
    try:
        resultado = persist_workout_plan(payload.plano, session)
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