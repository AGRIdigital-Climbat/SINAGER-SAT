from pydantic import BaseModel
from typing import Any


class SuccessResponse(BaseModel):
    model_config = {"json_schema_extra": {
        "examples": [{
            "success": True,
            "message": "Login exitoso",
            "data": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user_id": 1,
                "usuario": "admin",
                "nombre": "Administrador",
                "id_rol": 1,
                "rol": "superadministrador",
                "activo": True,
                "permisos": "full_access"
            }
        }]
    }}
    success: bool = True
    message: str
    data: Any = None
    total: int | None = None


class ErrorResponse(BaseModel):
    model_config = {"json_schema_extra": {
        "examples": [{"success": False, "message": "Error interno del servidor", "error_code": 500}]
    }}
    success: bool = False
    message: str
    error_code: int


class MessageResponse(BaseModel):
    model_config = {"json_schema_extra": {
        "examples": [{"message": "Usuario registrado exitosamente", "id": 1}]
    }}
    message: str
    id: int | None = None
