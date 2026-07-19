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
    id_rol: int = 4


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    usuario: str
    nombre: str
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    id_rol: int | None = None
    rol: str | None = None
    activo: bool | None = None
