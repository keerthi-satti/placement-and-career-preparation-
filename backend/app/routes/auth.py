from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
def signup():
    return {"message": "fake signup ok", "user_id": "u_1"}


@router.post("/login")
def login():
    return {"message": "fake login ok", "token": "fake-token"}


@router.post("/logout")
def logout():
    return {"message": "fake logout ok"}


@router.post("/reset-password")
def reset_password():
    return {"message": "fake reset email sent"}
