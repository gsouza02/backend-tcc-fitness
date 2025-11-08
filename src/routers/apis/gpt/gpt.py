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
Você é uma IA de prescrição de treinos. Sua única tarefa é gerar, a partir das respostas de anamnese descritas abaixo, um JSON válido que represente um programa de treino completo. Leia todo o enunciado antes de responder.

REQUISITOS OBRIGATÓRIOS
1. A resposta deve ser EXCLUSIVAMENTE um JSON bem formatado, sem comentários, cabeçalhos, explicações ou texto adicional.
2. Siga exatamente o esquema:

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

3. Todos os campos devem estar preenchidos com valores coerentes com as respostas da anamnese.
4. Gere pelo menos 1 treino e entre 4 e 8 exercícios por treino.
5. Use apenas números inteiros para campos numéricos.
6. `idUsuario` deve ser coerente: se a anamnese informar um ID, use-o; se não, adote um número plausível (ex.: 1).
7. Nomes e descrições precisam refletir objetivos, restrições, nível de experiência, tempo disponível e equipamentos do usuário.
8. Exercícios devem ser compatíveis com as condições e equipamento informados. Ajuste séries, repetições e descanso conforme o nível/objetivo (ex.: hipertrofia, resistência, emagrecimento).
9. Se houver lesões ou limitações, adapte a seleção de exercícios e descreva isso no campo `descricao` do treino.
10. Sempre retorne um JSON sintaticamente válido (aberturas/fechamentos corretos, aspas em strings, vírgulas adequadas).
11. Gere um treino para cada dia disponivel do usuario.

PROCESSO DE GERAÇÃO
- Primeiro, interprete o perfil do usuário (idade, experiência, disponibilidade, objetivos, lesões, equipamentos).
- Determine a dificuldade adequada ("iniciante", "intermediario" ou "avancado").
- Defina nome e descrição do programa resumindo o objetivo principal e a abordagem.
- Para cada treino:
  • Defina nome e descrição específicos, destacando foco muscular, objetivo do dia e recomendações.
  • Escolha exercícios compatíveis; variem grupos musculares conforme os objetivos.
  • Ajuste séries, repetições e descanso para refletir intensidade e tempo disponível.
  • Mantenha a duração total aproximada coerente com o tempo informado.

ANAMNESE DO USUÁRIO
<<<RESPOSTAS_ANAMNESE>>>
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
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao decodificar JSON da IA: {exc}") from exc


def persist_workout_plan(plan: dict, session: Session) -> dict:
    programa = plan.get("programaTreino")
    treinos = plan.get("treinos")

    if not isinstance(programa, dict) or not isinstance(treinos, list) or not treinos:
        raise HTTPException(status_code=400, detail="Estrutura do plano inválida")

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
    }


@router.post("/gpt")
def gpt(anamnese: PostAnamnese, session: Session = Depends(get_db_mysql)):
    prompt = build_prompt(anamnese)
    plano = gpt_response(prompt)
    print(plano)
    
    try:
        resultado = persist_workout_plan(plano, session)
        session.commit()
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar treino: {exc}") from exc

    return {
        "message": "Plano gerado e salvo com sucesso"
    }


    