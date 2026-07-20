from pydantic import BaseModel


class DepartamentoCreate(BaseModel):
    codigo_ine: str
    nombre: str


class DepartamentoUpdate(BaseModel):
    codigo_ine: str | None = None
    nombre: str | None = None


class DepartamentoResponse(BaseModel):
    id: int
    codigo_ine: str
    nombre: str

    class Config:
        from_attributes = True


class ProvinciaCreate(BaseModel):
    codigo_ine: str
    id_departamento: int
    nombre: str


class ProvinciaUpdate(BaseModel):
    codigo_ine: str | None = None
    id_departamento: int | None = None
    nombre: str | None = None


class ProvinciaResponse(BaseModel):
    id: int
    codigo_ine: str
    id_departamento: int
    nombre: str
    departamento: DepartamentoResponse | None = None

    class Config:
        from_attributes = True


class MunicipioCreate(BaseModel):
    codigo_ine: str
    id_departamento: int
    id_provincia: int
    nombre: str


class MunicipioUpdate(BaseModel):
    codigo_ine: str | None = None
    id_departamento: int | None = None
    id_provincia: int | None = None
    nombre: str | None = None


class MunicipioResponse(BaseModel):
    id: int
    codigo_ine: str
    id_departamento: int
    id_provincia: int
    nombre: str
    departamento: DepartamentoResponse | None = None
    provincia: ProvinciaResponse | None = None

    class Config:
        from_attributes = True
