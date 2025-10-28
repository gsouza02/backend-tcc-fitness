from sqlalchemy import text
from src.core.database import get_db_mysql  # ajuste conforme seu projeto

def create_db_tcc():
    """Cria o banco 'tcc' e a tabela USUARIO se não existirem usando a sessão do get_db_mysql."""
    db_gen = get_db_mysql()
    session = next(db_gen)
    try:
        # Criação do banco de dados 'tcc' se não existir
        session.execute(text("CREATE DATABASE IF NOT EXISTS tcc"))
        session.execute(text("USE tcc"))

        # Criação da tabela USUARIO
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS USUARIO (
            ID INT PRIMARY KEY AUTO_INCREMENT,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            username VARCHAR(50) NOT NULL UNIQUE,
            senha VARCHAR(255) NOT NULL
        );
        """
        session.execute(text(create_table_sql))
        session.commit()
    except Exception as e:
        print(f"Erro ao criar banco ou tabela: {e}")
    finally:
        session.close()