from fastapi import FastAPI, Depends, HTTPException, APIRouter
from sqlalchemy.sql import text
from src.core.database import get_db_mysql
from sqlalchemy.orm import Session
from src.routers.models.consultas import consulta_get
from fastapi.middleware.cors import CORSMiddleware
from src.core.init_db import create_db_tcc
# IMPORTAÇÃO DOS ROUTERS
from src.routers.router import router
from src.routers.apis.usuario import cadastro
from src.routers.apis.usuario import gpt
from src.routers.apis.treino import listagem
## ----------------------------------------------
# from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

create_db_tcc()

app.include_router(router)

origins = [
    "http://localhost:4200",
    "http://localhost:8000",
    "http://localhost:8081"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# class CookieMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#             token = request.cookies.get('BBSSOToken')
#             if token:
#                 response = await call_next(request)
#             else:
#                 response = Response(content="Unauthorized", status_code=401)
#             return response

# app.add_middleware(CookieMiddleware)