from pydantic import BaseModel


class UsuarioCreate(BaseModel):
    usuario: str
    contrasena: str
    nombre: str
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    activo: bool = True


class UsuarioUpdate(BaseModel):
    contrasena: str | None = None
    nombre: str | None = None
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    activo: bool | None = None


class UsuarioResponse(BaseModel):
    id_usuario: int
    usuario: str
    nombre: str
    celular: str | None = None
    carnet: str | None = None
    comunidad: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    id_municipio: int | None = None
    activo: bool | None = None

    class Config:
        from_attributes = True


class RolCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    jerarquia: int


class RolUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    jerarquia: int | None = None


class RolResponse(BaseModel):
    id_rol: int
    nombre: str
    descripcion: str | None = None
    jerarquia: int
    class Config:
        from_attributes = True


class UsuarioRolCreate(BaseModel):
    id_usuario: int
    id_rol: int


class UsuarioRolResponse(BaseModel):
    id_usuario: int
    id_rol: int
    class Config:
        from_attributes = True


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


class PermisoAplicacionCreate(BaseModel):
    id_rol: int
    id_aplicacion: int


class PermisoAplicacionResponse(BaseModel):
    id_rol: int
    id_aplicacion: int
    class Config:
        from_attributes = True


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


class ResetContrasenaResponse(BaseModel):
    id_reset: int
    id_usuario: int
    token: str
    usado: bool | None = None
    fecha_solicitud: str | None = None
    fecha_expiracion: str | None = None
    ip_origen: str | None = None
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str
    id: int | None = None
