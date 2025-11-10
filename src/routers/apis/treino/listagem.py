from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from pydantic import BaseModel, Field

from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.consultas import consulta_get


class ExerciseCatalogRequest(BaseModel):
    exercicios_ids: list[int] = Field(default_factory=list, alias="exerciciosIds")


@router.post("/exercicios/catalogo")
def catalogo_exercicios(payload: ExerciseCatalogRequest, session: Session = Depends(get_db_mysql)):
    ids = [ex for ex in payload.exercicios_ids if isinstance(ex, int) and ex > 0]
    if not ids:
        return {"exercicios": []}

    query = text(
        """
        SELECT id_exercicio, nome, grupo_muscular, equipamento
        FROM TCC.EXERCICIOS
        WHERE id_exercicio IN :ids
        ORDER BY id_exercicio
        """
    ).bindparams(bindparam("ids", expanding=True))

    result = session.execute(query, {"ids": ids})
    rows = [dict(row._mapping) for row in result.fetchall()]
    return {"exercicios": rows}


@router.get("/exercicios-treinos")
def listar_ex(
    user_id: int,
    id_treino: int,
    session: Session = Depends(get_db_mysql)
):
    """Retorna os exercícios associados a um treino específico.
    
    Args:
        user_id (int): ID do usuário.
        id_treino (int): ID do treino.
        session (Session): Sessão do banco de dados.
    Returns:
        dict: Dicionário contendo a lista de exercícios do treino.
    """

    query = """
   SELECT et.id_ex_treino, e.nome, e.grupo_muscular, e.equipamento, et.descanso, s.series, reps.repeticoes as reps  FROM TCC.TREINO t
LEFT JOIN TCC.EXERCICIO_TREINO et ON t.ID = et.id_treino
LEFT JOIN TCC.EXERCICIOS e ON et.id_exercicio = e.id_exercicio
LEFT JOIN (SELECT distinct(repeticoes), id_ex_treino FROM TCC.SERIES) reps ON reps.id_ex_treino = et.id_ex_treino
LEFT JOIN (SELECT id_ex_treino, COUNT(*) as series FROM TCC.SERIES GROUP BY ID_EX_TREINO) s ON s.id_ex_treino = et.id_ex_treino
where et.id_treino = :id_treino;
"""

    exercicios = consulta_get(query, session, {"id_treino": id_treino})
    return exercicios


@router.get("/programas")
def listar_programas_treino(
    user_id: int = Query(..., alias="userId", description="ID do usuário"),
    session: Session = Depends(get_db_mysql)
):
    """Retorna os programas de treino associados a um usuário.
    
    Args:
        user_id (int): ID do usuário.
        session (Session): Sessão do banco de dados.
    Returns:
        dict: Dicionário contendo a lista de programas de treino do usuário.
    """
    query = """
        SELECT 
            pt.id_programa_treino,
            pt.id_usu,
            pt.nome,
            pt.descricao,
            pt.created_at,
            pt.updated_at
        FROM TCC.PROGRAMA_TREINO pt
        WHERE pt.id_usu = :user_id
        ORDER BY pt.created_at DESC
    """

    programas = consulta_get(query, session, {"user_id": user_id})
    return programas


@router.get("/treinos-programa")
def listar_treinos_programas(
    user_id: int,
    id_programa: int,
    session: Session = Depends(get_db_mysql)
):
    
    """Retorna os treinos associados a um programa de treino específico.
    Args:
        user_id (int): ID do usuário.
        id_programa (int): ID do programa de treino.
        session (Session): Sessão do banco de dados.
    Returns:
        list: Lista de treinos do programa de treino.
    """
    query = """
    SELECT t.id, t.nome, t.descricao, t.duracao, t.dificuldade FROM 
TCC.PROGRAMA_TREINO pt 
LEFT JOIN TCC.TREINO t ON t.id_programa_treino = pt.id_programa_treino
where t.id_programa_treino = :id_programa;
"""

    treinos = consulta_get(query, session, {"id_programa": id_programa})
    return treinos


@router.get("/exercicios")
def get_exericicios_by_id(id_exercicio: int, session: Session = Depends(get_db_mysql)):
    """Retorna os detalhes de um exercício específico pelo seu ID.
    
    Args:
        id_exercicio (int): ID do exercício.
        session (Session): Sessão do banco de dados.
    Returns:
        dict: Dicionário contendo os detalhes do exercício.
    """
    query = """
    SELECT * FROM TCC.EXERCICIOS e
    WHERE id_exercicio = :id_exercicio;
    """

    exercicio = consulta_get(query, session, {"id_exercicio": id_exercicio})
    if not exercicio:
        raise HTTPException(status_code=404, detail="Exercício não encontrado")
    return exercicio[0]
