from sqlalchemy.orm import Session
from sqlalchemy.sql import text
import pandas as pd
import base64


def consulta_get(query: str, session: Session): # funcao para executar consulta no banco de dados
    result = session.execute(text(query))
    df = pd.DataFrame(result)
    return df.to_dict(orient='records')

def consulta_get_card(query, session: Session, params = None):
    # funcao para executar consulta no banco de dados
    if(type(query) == str):
        if(params):
            result = session.execute(text(query), params)
        else:
            result = session.execute(text(query))
            
    else:
        if(params):  
            result = session.execute(query, params)
        else:
            result = session.execute(query)
    df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df.map(serialize_data).to_dict(orient='records')

def serialize_data(value):
    # funcao para tratar os bits da imagem
    if isinstance(value, memoryview):
        return base64.b64encode(value).decode('utf-8')
    return value