from fastapi import FastAPI

from app.routes import account, auth, resumes

app = FastAPI(title="Interview Question Generator - Backend (fake skeleton)")

app.include_router(auth.router)
app.include_router(resumes.router)
app.include_router(account.router)


@app.get("/")
def home():
    return {"message": "Backend skeleton is running"}