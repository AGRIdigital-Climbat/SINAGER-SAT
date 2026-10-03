# 📋 APIs RIDA - Documentación Completa

**Versión:** v2.25.0  
**Fecha:** 30 de septiembre de 2026  
**Base URL:** `/api/v2/rida`

---

## 📖 Índice

1. [RIDA > Padres (Eventos)](#rida--padres-eventos)
2. [RIDA > Hijos (Empadronamiento)](#rida--hijos-empadronamiento)
3. [Anular Evento por Error](#anular-evento-rida-habilitado-por-error)
4. [Empadronamiento + Catálogos](#empadronamiento--catálogos)
5. [Motor de Búsqueda de Personas](#motor-de-búsqueda-potente-de-personas)
6. [RIDA > Sync (Offline)](#rida--sync-offline-first)
7. [Ejemplos de Uso](#ejemplos-de-uso)

---

## 🎯 RIDA > Padres (Eventos)

Los **Eventos RIDA** representan un desastre o emergencia habilitado para empadronamiento. Son el **PADRE** en la jerarquía.

### Estructura Jerárquica

```
EVENTO RIDA (Padre)
├── id_evento_rida: 1
├── id_edan: 79 (EDAN aprobado que origina el RIDA)
├── estado: HABILITADO (1) o CERRADO (2)
├── fecha_habilitacion: 2026-09-30
├── id_usuario_habilito: 2
└── LOCALIDADES (Hijos)
    ├── Localidad 1 → Formulario 32
    ├── Localidad 2 → Formulario 33
    └── Localidad 3 → Formulario 34
```

### Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/eventos` | Listar eventos RIDA (padres) |
| `GET` | `/evento/{id_evento_rida}` | Obtener evento con localidades |
| `POST` | `/evento/{id_edan}/habilitar` | Habilitar evento desde EDAN aprobado |
| `POST` | `/evento/{id_evento_rida}/cerrar` | Cerrar evento (finalizar empadronamiento) |
| `POST` | `/evento/{id_evento_rida}/anular` | **Anular evento habilitado por error** |

### Respuesta Típica

```json
{
  "success": true,
  "data": {
    "id_evento_rida": 1,
    "id_edan": 79,
    "estado": {
      "id_estado_evento": 1,
      "codigo": "HABILITADO",
      "nombre": "Habilitado"
    },
    "id_usuario_habilito": 2,
    "fecha_habilitacion": "2026-09-30T10:00:00",
    "anulado": false,
    "n_familias": 45,
    "n_integrantes": 180,
    "n_necesidades": 23,
    "num_localidades": 3,
    "localidades": [...],
    "departamento": {"id": 7, "nombre": "Santa Cruz"},
    "municipio": {"id": 70101, "nombre": "Santa Cruz de la Sierra"},
    "tipo_evento": {"id_tipo_evento": 5, "nombre": "Granizadas"}
  }
}
```

---

## 👨‍👩‍👧‍👦 RIDA > Hijos (Empadronamiento)

Los **Hijos** son los datos de empadronamiento asociados a un evento RIDA.

### Jerarquía de Hijos

```
Formulario (por localidad)
├── id_formulario: 32
├── id_edan_localidad: 325643
├── estado: PENDIENTE (1), EN_PROCESO (2), CERRADO (3)
└── Familias
    ├── Familia 1
    │   ├── Integrante 1 (Jefe)
    │   ├── Integrante 2 (Esposo/a)
    │   ├── Integrante 3 (Hijo)
    │   └── Ubicaciones GPS
    └── Familia 2
        └── ...
```

### Endpoints de Hijos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/evento/{id_evento_rida}/localidades` | Listar localidades del evento |
| `GET` | `/formularios/{id_formulario}` | Formulario con árbol completo |
| `GET` | `/formularios/{id_formulario}/familias` | Familias de un formulario |
| `GET` | `/familias/{id_familia}` | Familia con integrantes |
| `GET` | `/familias/{id_familia}/integrantes` | Integrantes de familia |
| `GET` | `/familias/{id_familia}/ubicaciones` | Ubicaciones GPS de familia |
| `GET` | `/necesidades/formularios/{id}/necesidades` | Necesidades del formulario |
| `GET` | `/necesidades/familias/{id}/necesidades` | Necesidades de familia |

### Campos de Integrantes (Nuevos)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `numero_documento` | VARCHAR(20) | Número de carnet O certificado |
| `tipo_documento` | VARCHAR(20) | `CARNET` o `CERTIFICADO` |
| `nombre` | VARCHAR(100) | Nombre completo |
| `apellido` | VARCHAR(100) | Apellido completo |
| `fecha_nacimiento` | DATE | Fecha de nacimiento |
| `sexo` | CHAR(1) | `M` o `F` |

### Control de Duplicados

**Regla:** No se permite registrar la misma persona dos veces con:
- **Mismo tipo de documento** (CARNET o CERTIFICADO)
- **Mismo número de documento**
- **Mismo nombre + apellido**
- **Misma fecha de nacimiento**

```
❌ DUPLICADO: CARNET 12345678 + Juan Pérez + 1990-01-15 (ya existe)
✅ VÁLIDO: CERTIFICADO 12345678 + Juan Pérez + 1990-01-15 (distinto tipo)
✅ VÁLIDO: CARNET 87654321 + Juan Pérez + 1990-01-15 (distinto número)
```

---

## 🚫 Anular Evento RIDA (Habilitado por Error)

Cuando se habilita un evento RIDA por error, se puede **ANULAR** siempre que:

### ✅ Condiciones para Anular

1. El evento debe estar en estado **HABILITADO** (no cerrado)
2. **NO** debe tener formularios creados
3. **NO** debe tener familias registradas
4. **NO** debe tener integrantes empadronados
5. **NO** debe tener necesidades registradas

### ❌ Error si hay datos

```json
{
  "detail": "No se puede anular: el evento tiene formularios de empadronamiento asociados. "
            "Primero elimine todos los formularios y sus datos (familias, integrantes, necesidades)."
}
```

### Endpoint

```http
POST /api/v2/rida/evento/{id_evento_rida}/anular
Authorization: Bearer {token}
```

### Campos de Auditoría

| Campo | Descripción |
|-------|-------------|
| `anulado` | `true` si el evento fue anulado |
| `id_usuario_anulo` | Usuario que anuló el evento |
| `fecha_anulacion` | Fecha y hora de anulación |

### Flujo de Anulación

```
1. Usuario habilita EDAN 79 por error
   → Se crea evento_rida id=1
   → Estado: HABILITADO

2. Usuario se da cuenta del error ANTES de empadronar
   → POST /evento/1/anular
   
3. Sistema valida:
   ✅ ¿Estado es HABILITADO? → SÍ
   ✅ ¿Tiene formularios? → NO
   ✅ ¿Tiene familias? → NO
   
4. Sistema anula:
   → anulado = TRUE
   → id_usuario_anulo = 2
   → fecha_anulacion = NOW()
```

---

## 📚 Empadronamiento + Catálogos

### Catálogos Disponibles

Todos los catálogos están en el grupo **"Empadronamiento + Catálogos"** y **NO tienen paginación** (traen todos los registros).

| Catálogo | Endpoint | Contenido |
|----------|----------|-----------|
| Estados de Formulario | `GET /empadronamiento/cat-estado-formulario` | PENDIENTE(1), EN_PROCESO(2), CERRADO(3) |
| Tipos de Albergue | `GET /empadronamiento/cat-tipo-albergue` | Albergues temporales, casas de familia, etc. |
| Parentescos | `GET /empadronamiento/cat-parentesco` | Jefe, Esposo/a, Hijo/a, etc. |
| Discapacidades | `GET /empadronamiento/cat-tipo-discapacidad` | Física, Visual, Auditiva, etc. |
| Estados de Evento | `GET /evento/cat-estado-evento` | HABILITADO(1), CERRADO(2) |
| Categorías Ayuda | `GET /necesidades/cat-categorias` | Alimentos, Abrigo, Salud, etc. |
| Artículos | `GET /necesidades/cat-articulos` | Arroz, Frijol, Manta, etc. |

### Formularios (CRUD)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/empadronamiento/formularios` | Listar formularios (paginado) |
| `GET` | `/empadronamiento/formularios/mis` | Mis formularios (rol 6/7) |
| `GET` | `/empadronamiento/formularios/{id}` | Formulario con árbol completo |
| `POST` | `/empadronamiento/formularios` | Crear formulario |
| `PUT` | `/empadronamiento/formularios/{id}` | Actualizar estado |
| `DELETE` | `/empadronamiento/formularios/{id}` | Eliminar formulario |

---

## 🔍 Motor de Búsqueda Potente de Personas

El endpoint más potente para buscar personas (integrantes) en todo el sistema RIDA.

### Endpoint

```http
GET /api/v2/rida/empadronamiento/personas/buscar
```

### Parámetros de Búsqueda

| Parámetro | Tipo | Descripción | Ejemplo |
|-----------|------|-------------|---------|
| `busqueda` | string | Búsqueda libre (nombre, apellido, documento) | `?busqueda=Juan` |
| `nombre` | string | Filtrar por nombre | `?nombre=Juan` |
| `apellido` | string | Filtrar por apellido | `?apellido=Perez` |
| `numero_documento` | string | Número exacto de documento | `?numero_documento=12345678` |
| `tipo_documento` | string | CARNET o CERTIFICADO | `?tipo_documento=CARNET` |
| `fecha_nacimiento` | string | Fecha exacta (YYYY-MM-DD) | `?fecha_nacimiento=1990-01-15` |
| `sexo` | string | M o F | `?sexo=M` |
| `id_departamento` | int | Filtrar por departamento | `?id_departamento=7` |
| `id_municipio` | int | Filtrar por municipio | `?id_municipio=70101` |
| `id_parentesco` | int | Filtrar por parentesco | `?id_parentesco=1` |
| `es_jefe` | bool | Jefe de familia | `?es_jefe=true` |
| `skip` | int | Offset para paginación | `?skip=0` |
| `limit` | int | Límite de resultados (1-200) | `?limit=50` |
| `todos` | bool | Devolver todos sin paginar | `?todos=true` |

### Ejemplos de Uso

#### 1. Búsqueda por nombre

```bash
curl "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?nombre=Juan&limit=10" \
  -H "Authorization: Bearer {token}"
```

#### 2. Búsqueda por documento

```bash
curl "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?numero_documento=12345678" \
  -H "Authorization: Bearer {token}"
```

#### 3. Búsqueda geográfica (municipio)

```bash
curl "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?id_municipio=70101&limit=50" \
  -H "Authorization: Bearer {token}"
```

#### 4. Búsqueda combinada

```bash
curl "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?apellido=Perez&sexo=M&es_jefe=true" \
  -H "Authorization: Bearer {token}"
```

### Respuesta

```json
{
  "success": true,
  "message": "Búsqueda completada correctamente",
  "data": [
    {
      "id_integrante": 8,
      "nombre": "Horacio",
      "apellido": "Perez",
      "fecha_nacimiento": "1965-02-15",
      "sexo": "M",
      "numero_documento": "12735123",
      "tipo_documento": "CARNET",
      "es_jefe": true,
      "parentesco_nombre": "Jefe/a de hogar",
      "localidad_nombre": "Zona Los Pinos",
      "municipio_nombre": "Santa Cruz de la Sierra",
      "departamento_nombre": "Santa Cruz"
    }
  ],
  "total": 1
}
```

---

## 🔄 RIDA > Sync (Offline-First)

Sincronización de datos para dispositivos móviles sin conexión.

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/empadronamiento/sync` | POST | Sincronizar formulario + familias + integrantes + ubicaciones |
| `/necesidades/sync` | POST | Sincronizar necesidades (batch offline) |

### Características

- **Idempotente:** Usa `id_*_off` para UPSERT
- **Resuelve vínculos:** `id_familia_off` → `id_familia` del servidor
- **No falla completo:** Errores individuales en `errores[]`
- **Devuelve mapeos:** `off → server` para reenlace en dispositivo

---

## 📊 Consolidados por Evento y Formulario

Todos los endpoints de lista incluyen consolidados automáticos:

### En Eventos (Padre)

```json
{
  "id_evento_rida": 1,
  "n_familias": 45,
  "n_integrantes": 180,
  "n_necesidades": 23,
  "num_localidades": 3
}
```

### En Localidades (Hijos)

```json
{
  "id_formulario": 32,
  "localidad": "Comunidad San Miguel",
  "n_familias": 15,
  "n_integrantes": 60,
  "n_necesidades": 8,
  "estado_codigo": "EN_PROCESO"
}
```

### En Formularios (GET individual)

```json
{
  "id_formulario": 32,
  "n_familias": 15,
  "n_integrantes": 60,
  "n_necesidades": 8,
  "familias": [...]
}
```

---

## 🔐 Roles y Permisos

### Roles para Gestión de Eventos

| Rol | ID | Habilitar | Cerrar | Anular |
|-----|----|-----------|--------|--------|
| Super Admin | 1 | ✅ | ✅ | ✅ |
| Admin | 2 | ✅ | ✅ | ✅ |
| DGR Gobernación | 5 | ✅ | ✅ | ✅ |
| VIDECI Departamental | 9 | ✅ | ✅ | ✅ |

### Roles para Escritura (Empadronamiento)

| Rol | ID | Crear/Editar |
|-----|----|--------------|
| Super Admin | 1 | ✅ |
| Admin | 2 | ✅ |
| UGR Municipio | 6 | ✅ |
| Responsable Local | 7 | ✅ |

---

## 📝 Ejemplos de Uso Completo

### 1. Habilitar Evento RIDA

```bash
# Habilitar desde EDAN aprobado (estado 3 o 5)
curl -X POST "http://localhost:8000/api/v2/rida/evento/79/habilitar" \
  -H "Authorization: Bearer {token}"

# Respuesta:
{
  "success": true,
  "message": "Evento RIDA habilitado correctamente",
  "data": {
    "id_evento_rida": 1,
    "id_edan": 79,
    "estado": {"nombre": "HABILITADO"},
    "num_localidades": 3,
    "localidades": [
      {"localidad": "Comunidad San Miguel", "id_formulario": 32},
      {"localidad": "Barrio Nueva Jerusalén", "id_formulario": 33},
      {"localidad": "Zona Los Pinos", "id_formulario": 34}
    ]
  }
}
```

### 2. Anular Evento por Error

```bash
# Anular evento habilitado por error (debe estar vacío)
curl -X POST "http://localhost:8000/api/v2/rida/evento/1/anular" \
  -H "Authorization: Bearer {token}"

# Respuesta exitosa:
{
  "success": true,
  "message": "Evento RIDA anulado correctamente",
  "data": {
    "id_evento_rida": 1,
    "anulado": true,
    "id_usuario_anulo": 2,
    "fecha_anulacion": "2026-09-30T15:30:00"
  }
}

# Error si hay datos:
{
  "detail": "No se puede anular: el evento tiene formularios de empadronamiento asociados. "
            "Primero elimine todos los formularios y sus datos (familias, integrantes, necesidades)."
}
```

### 3. Buscar Personas

```bash
# Búsqueda por apellido y departamento
curl "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?apellido=Perez&id_departamento=7&limit=20" \
  -H "Authorization: Bearer {token}"

# Búsqueda por documento (evitar duplicados antes de crear)
curl "http://localhost:8000/api/v2/rida/empadronamiento/personas/buscar?numero_documento=12345678&tipo_documento=CARNET" \
  -H "Authorization: Bearer {token}"
```

### 4. Crear Integrante (con validación de duplicados)

```bash
# Crear integrante nuevo
curl -X POST "http://localhost:8000/api/v2/rida/empadronamiento/familias/6/integrantes" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "María",
    "apellido": "Gonzalez",
    "fecha_nacimiento": "1995-05-20",
    "sexo": "F",
    "numero_documento": "9876543",
    "tipo_documento": "CARNET",
    "id_parentesco": 2
  }'

# Error si ya existe:
{
  "detail": "Ya existe una persona registrada con CARNET 9876543, nombre María Gonzalez, fecha nacimiento 1995-05-20"
}
```

### 5. Listar Eventos con Filtros

```bash
# Listar eventos de un departamento
curl "http://localhost:8000/api/v2/rida/eventos?id_departamento=7&limit=10" \
  -H "Authorization: Bearer {token}"

# Listar TODOS los eventos (sin paginar)
curl "http://localhost:8000/api/v2/rida/eventos?todos=true" \
  -H "Authorization: Bearer {token}"
```

---

## 🔗 Swagger / OpenAPI

**Documentación Interactiva:** http://localhost:8000/docs/v2

**Tags Disponibles:**
- Empadronamiento + Catálogos
- RIDA > Padres
- RIDA > Hijos
- RIDA > Búsqueda
- RIDA > Sync
- Repositorio > Documentos

---

## 📌 Resumen de Cambios v2.25.0

| Feature | Descripción |
|---------|-------------|
| ✅ **Anular Evento** | endpoint `POST /evento/{id}/anular` para deshacer habilitación por error |
| ✅ **Validación Vacío** | No permite anular si hay familias/integrantes/necesidades |
| ✅ **Tipo Documento** | Campos `numero_documento` y `tipo_documento` (CARNET/CERTIFICADO) |
| ✅ **Control Duplicados** | Índice único por tipo_documento + numero + nombre + fecha |
| ✅ **Búsqueda Potente** | `GET /empadronamiento/personas/buscar` con 12 filtros |
| ✅ **Consolidados** | `n_familias`, `n_integrantes`, `n_necesidades` en todos los GET |
| ✅ **Paginación** | `skip`, `limit`, `todos=true` en todas las listas |
| ✅ **Catálogos** | Todos juntos en "Empadronamiento + Catálogos", sin paginación |

---

**Fin de la documentación**
