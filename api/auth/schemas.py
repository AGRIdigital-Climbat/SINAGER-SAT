from pydantic import BaseModel


class LoginRequest(BaseModel):
    model_config = {"json_schema_extra": {
        "examples": [{"usuario": "admin", "contrasena": "pass123"}]
    }}
    usuario: str
    contrasena: str


class RegisterRequest(BaseModel):
    model_config = {"json_schema_extra": {
        "examples": [{
            "usuario": "enc1",
            "contrasena": "pass123",
            "nombre": "Encargado 1",
            "celular": "70000000",
            "carnet": "1234567",
            "comunidad": "Comunidad Test",
            "correo": "enc1@test.com",
            "cargo": "Encargado",
            "id_departamento": 2,
            "id_provincia": 201,
            "id_municipio": 20101,
            "id_rol": 4
        }]
    }}
    usuario: str
    contrasena: str
    nombre: str
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    correo: str | None = None
    cargo: str | None = None
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
    correo: str | None = None
    cargo: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    id_rol: int | None = None
    rol: str | None = None
    activo: bool | None = None


class VerificarIdentidadRequest(BaseModel):
    carnet: str
    celular: str
    id_departamento: int
    id_provincia: int
    id_municipio: int
    comunidad: str


class CambiarContrasenaRequest(BaseModel):
    id_usuario: int
    nueva_contrasena: str
