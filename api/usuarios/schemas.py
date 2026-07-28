from pydantic import BaseModel


class UsuarioCreate(BaseModel):
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
    activo: bool = True


class UsuarioUpdate(BaseModel):
    contrasena: str | None = None
    nombre: str | None = None
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    correo: str | None = None
    cargo: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    id_rol: int | None = None
    activo: bool | None = None


class UsuarioDepartamento(BaseModel):
    id: int
    codigo_ine: str | None = None
    nombre: str | None = None


class UsuarioProvincia(BaseModel):
    id: int
    codigo_ine: str | None = None
    nombre: str | None = None


class UsuarioMunicipio(BaseModel):
    id: int
    codigo_ine: str | None = None
    nombre: str | None = None


class UsuarioRol(BaseModel):
    id_rol: int
    nombre: str
    descripcion: str | None = None


class UsuarioResponse(BaseModel):
    id_usuario: int
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
    id_rol: int
    activo: bool | None = None
    departamento: UsuarioDepartamento | None = None
    provincia: UsuarioProvincia | None = None
    municipio: UsuarioMunicipio | None = None
    rol: UsuarioRol | None = None

    class Config:
        from_attributes = True


class RolCreate(BaseModel):
    nombre: str
    descripcion: str | None = None


class RolUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class AplicacionCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    activo: bool = True


class AplicacionUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    activo: bool | None = None


class AplicacionResponse(BaseModel):
    id_aplicacion: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    activo: bool | None = None
    class Config:
        from_attributes = True


class AccionCreate(BaseModel):
    codigo: str
    nombre: str


class AccionUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None


class AccionResponse(BaseModel):
    id_accion: int
    codigo: str
    nombre: str
    class Config:
        from_attributes = True


class PermisoCreate(BaseModel):
    id_rol: int
    id_aplicacion: int
    id_accion: int


class PermisoResponse(BaseModel):
    id_permiso: int
    id_rol: int
    id_aplicacion: int
    id_accion: int
    class Config:
        from_attributes = True


class PermisoBatchRequest(BaseModel):
    permisos: dict[str, list[str]]


class SesionResponse(BaseModel):
    id_sesion: int
    id_usuario: int
    token: str
    fecha_inicio: str | None = None
    fecha_expiracion: str | None = None
    ip_origen: str | None = None
    activo: bool | None = None
    class Config:
        from_attributes = True


class AuditoriaResponse(BaseModel):
    id_auditoria: int
    id_usuario: int | None = None
    id_aplicacion: int | None = None
    accion: str
    detalle: str | None = None
    ip_origen: str | None = None
    fecha: str | None = None
    class Config:
        from_attributes = True
