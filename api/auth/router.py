from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..response import SuccessResponse, MessageResponse
from .schemas import LoginRequest, RegisterRequest, TokenResponse
from .service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", responses={200: {"model": SuccessResponse}})
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = authenticate_user(db, data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    return SuccessResponse(message="Login exitoso", data=result)


@router.post("/register", status_code=status.HTTP_201_CREATED, responses={201: {"model": MessageResponse}})
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user_id = register_user(db, data)
        return MessageResponse(message="Usuario registrado exitosamente", id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
