queries_db = {
    
    "usuario": """
        CREATE TABLE IF NOT EXISTS TCC.USUARIO (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            senha VARCHAR(255) NOT NULL,
            username VARCHAR(50) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        );
    """,

    "treino": """
        CREATE TABLE IF NOT EXISTS TCC.TREINO (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            id_usuario INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (id_usuario)
                REFERENCES TCC.USUARIO(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );
    """,

    "exercicios": """
        CREATE TABLE IF NOT EXISTS TCC.EXERCICIOS (
            id_exercicio INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            equipamento VARCHAR(100),
            grupo_muscular VARCHAR(100)
        );
    """,

    "exercicio_treino": """
        CREATE TABLE IF NOT EXISTS TCC.EXERCICIO_TREINO (
            id_ex_treino INT AUTO_INCREMENT PRIMARY KEY,
            id_exercicio INT NOT NULL,
            id_treino INT NOT NULL,
            FOREIGN KEY (id_exercicio)
                REFERENCES TCC.EXERCICIOS(id_exercicio)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            FOREIGN KEY (id_treino)
                REFERENCES TCC.TREINO(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );
    """,

    "series": """
        CREATE TABLE IF NOT EXISTS TCC.SERIES (
            id_serie INT AUTO_INCREMENT PRIMARY KEY,
            numero_serie INT NOT NULL CHECK (numero_serie > 0),
            repeticoes INT NOT NULL CHECK (repeticoes > 0),
            carga DECIMAL(5,2) CHECK (carga >= 0),
            id_ex_treino INT NOT NULL,
            FOREIGN KEY (id_ex_treino)
                REFERENCES TCC.EXERCICIO_TREINO(id_ex_treino)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );
    """,

    "rotina": """
        CREATE TABLE IF NOT EXISTS TCC.ROTINA (
            id_rotina INT AUTO_INCREMENT PRIMARY KEY,
            id_usu INT NOT NULL,
            id_treino INT NOT NULL,
            nome VARCHAR(100) NOT NULL,
            descricao VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (id_usu)
                REFERENCES TCC.USUARIO(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            FOREIGN KEY (id_treino)
                REFERENCES TCC.TREINO(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );
    """
}
