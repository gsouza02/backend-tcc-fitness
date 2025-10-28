# Backend TCC fitness

Projeto backend do TCC, desenvolvido em Python 3.13 com FastAPI, gerenciado pelo [uv](https://docs.astral.sh/uv).
Abaixo como rodar essa aplicação.

## Pré-requisitos

- Python 3.13 ou superior  
- uv instalado (gerenciador oficial da Astral)
- criar **.env** para configuração de variáveis de ambient.

## Instalação do uv

**Windows (PowerShell):**
irm https://astral.sh/uv/install.ps1 | iex

**Linux / macOS:**
curl -LsSf https://astral.sh/uv/install.sh | sh

Após a instalação, feche e reabra o terminal e confirme:
uv --version
(deve aparecer algo como: uv 0.9.5 (https://astral.sh/uv))

## Configuração do ambiente

Para instalar todas as dependências do projeto:
**uv sync**

Esse comando cria automaticamente o ambiente virtual do projeto e instala todas as dependências listadas no pyproject.toml.

## Execução da aplicação

O projeto possui uma task configurada chamada `s`, que executa o servidor FastAPI em modo de desenvolvimento:

**uv run task s**

No pyproject.toml, a task está configurada assim:
[tool.taskipy.tasks]
s = "fastapi dev main.py"

O servidor será iniciado e poderá ser acessado em http://127.0.0.1:8000


## Referências

- [Documentação oficial do uv](https://docs.astral.sh/uv)  
- [FastAPI](https://fastapi.tiangolo.com/)
