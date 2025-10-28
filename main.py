from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.sql import text
from core.database import get_db
from sqlalchemy.orm import Session
from routers.models.consultas import consulta_get
from fastapi.middleware.cors import CORSMiddleware
from routers.models.models import PostCliente, Cliente, PostPedido
import bcrypt


# from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

origins = [
    "http://localhost:4200",
    "http://localhost:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/teste")
def teste():
    return {"message": "API is working!"}   

# class CookieMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#             token = request.cookies.get('BBSSOToken')
#             if token:
#                 response = await call_next(request)
#             else:
#                 response = Response(content="Unauthorized", status_code=401)
#             return response

# app.add_middleware(CookieMiddleware)