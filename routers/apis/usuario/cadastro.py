from routers.router import router

@router.get("/teste")
def teste():
    return {"message": "API is working!"}