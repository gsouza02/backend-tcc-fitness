from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.routers.router import router
from src.core.database import get_db_mysql
from src.routers.models.consultas import consulta_get

@router.get("/exercicios-treinos")
def listar_ex(
    user_id: int,
    id_treino: int,
    session: Session = Depends(get_db_mysql)
):
    """Retorna os exercícios associados a um treino específico."""
    query = """
   SELECT et.id_ex_treino, e.nome, e.grupo_muscular, e.equipamento, et.descanso, s.series FROM TCC.TREINO t
LEFT JOIN TCC.EXERCICIO_TREINO et ON t.ID = et.id_treino
LEFT JOIN TCC.EXERCICIOS e ON et.id_exercicio = e.id_exercicio
LEFT JOIN (SELECT id_ex_treino, COUNT(*) as series FROM TCC.SERIES GROUP BY ID_EX_TREINO) s ON s.id_ex_treino = et.id_ex_treino
where et.id_treino = :id_treino;
"""

    exercicios = consulta_get(query, session, {"id_treino": id_treino})
    return {"exercicios": exercicios}


@router.get("/programas")
def listar_programas_treino(
    user_id: int = Query(..., alias="userId", description="ID do usuário"),
    session: Session = Depends(get_db_mysql)
):
    """Retorna os programas de treino associados a um usuário."""
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
    return {"programas_treino": programas}


@router.get("/treinos-programa")
def listar_treinos_programas(
    user_id: int,
    id_programa: int,
    session: Session = Depends(get_db_mysql)
):
    query = """
    SELECT t.id, t.nome, t.descricao, t.duracao, t.dificuldade FROM 
TCC.PROGRAMA_TREINO pt 
LEFT JOIN TCC.TREINO t ON t.id_programa_treino = pt.id_programa_treino
where t.id_programa_treino = :id_programa;
"""

    treinos = consulta_get(query, session, {"id_programa": id_programa})
    return treinos
