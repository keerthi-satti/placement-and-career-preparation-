from fastapi import APIRouter

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("")
def delete_account():
    return {"message": "fake account delete ok"}
