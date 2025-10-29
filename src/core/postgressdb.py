from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import os

# Carrega a variável DATABASE_URL do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

# Cria o engine usando a URL completa
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=3600
)

def get_db_postgress() -> Generator[Session, None, None]:
    """Criação de sessão de banco de dados PostgreSQL via DATABASE_URL."""
    try:
        with Session(engine) as session:
            yield session
    except Exception as e:
        raise e