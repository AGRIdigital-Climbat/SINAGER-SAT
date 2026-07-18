from pydantic import BaseModel


class LoginRequest(BaseModel):
    usuario: str
    contrasena: str


class RegisterRequest(BaseModel):
    usuario: str
    contrasena: str
    nombre: str
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    usuario: str
    nombre: str


class MessageResponse(BaseModel):
    message: str
    id: int | None = None
