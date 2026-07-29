from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user
from ..response import SuccessResponse, MessageResponse
from .schemas import LoginRequest, RegisterRequest, TokenResponse, VerificarIdentidadRequest, CambiarContrasenaRequest
from .service import authenticate_user, register_user, verificar_identidad, cambiar_contrasena, _get_permisos_response

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


@router.post("/verificar-identidad", responses={200: {"model": SuccessResponse}})
def verify_identity(data: VerificarIdentidadRequest, db: Session = Depends(get_db)):
    result = verificar_identidad(db, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Los datos no coinciden con ningún usuario registrado")
    return SuccessResponse(message="Identidad verificada correctamente", data=result)


@router.post("/cambiar-contrasena", responses={200: {"model": MessageResponse}})
def change_password(data: CambiarContrasenaRequest, db: Session = Depends(get_db)):
    if not cambiar_contrasena(db, data):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado o inactivo")
    return MessageResponse(message="Contraseña actualizada correctamente")


@router.get("/mis-permisos", responses={200: {"model": SuccessResponse}})
def mis_permisos(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    permisos = _get_permisos_response(user["id_rol"], db)
    return SuccessResponse(message="Permisos obtenidos correctamente", data={
        "id_usuario": user["id_usuario"],
        "usuario": user["usuario"],
        "nombre": user["nombre"],
        "id_rol": user["id_rol"],
        "permisos": permisos,
    })
