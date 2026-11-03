# 02 · Autenticación y roles

> Verificado contra `api/auth/*`, `api/dependencies.py` y las tablas `usuarios.*` en octubre de 2026.

## 1. Esquema de autenticación

**JWT Bearer (HS256) + tabla de sesiones.** No hay cookies, ni refresh token, ni endpoint de logout.

| Pieza | Ubicación | Detalle |
|---|---|---|
| Esquema de seguridad | `api/dependencies.py:8` | `HTTPBearer(scheme_name="JWT")` |
| Validación de petición | `api/dependencies.py:15-42` | `get_current_user()`: verifica token, consulta `usuarios.usuario`, exige `activo = true` |
| Firma/verificación | `api/auth/jwt.py:17-31` | `create_access_token()` / `verify_token()` con `jti` (uuid) y `exp` |
| Hash de contraseña | `api/auth/jwt.py:9-14` | bcrypt (`bcrypt==4.2.1`) |
| Configuración | `api/config.py:15-17` | `JWT_SECRET`, `JWT_ALGORITHM=HS256`, `JWT_EXPIRE_MINUTES=480` |

### Flujo de login (`POST /api/v{1,2}/auth/login`, `api/auth/router.py:12` → `api/auth/service.py`)

1. SELECT con joins a `usuarios.rol` y `shared.departamento/provincia/municipio`.
2. `verify_password()` bcrypt.
3. **Expiración por rol** (`_calcular_expiracion`, `api/auth/service.py:13-17`):
   - Roles **6 y 7** (UGR Municipio, Responsable Local): token de larga duración (fecha 2099) que **reutiliza la sesión activa** si existe — pensado para equipos de campo con poca conectividad.
   - Resto de roles: **72 horas**; se desactivan las sesiones previas y se inserta una nueva.
4. Responde con el token, los datos del usuario, su geografía y sus permisos agrupados por aplicación.

**Ejemplo de respuesta** (`api/auth/service.py:112-151`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user_id": 1,
  "usuario": "admin",
  "nombre": "Administrador",
  "carnet": "...", "celular": "...", "comunidad": "...", "correo": "...", "cargo": "...",
  "departamento": {"id": 1, "codigo_ine": "1", "nombre": "La Paz"},
  "provincia": {"id": ..., "codigo_ine": "101", "nombre": "..."},
  "municipio":  {"id": ..., "codigo_ine": "10101", "nombre": "..."},
  "id_rol": 6,
  "rol": "UGR Municipio",
  "activo": true,
  "permisos": {"EDAN": ["READ","CREATE"], "RIDA": ["READ","CREATE","UPDATE","DELETE"]},
  "expires_at": "2026-10-08T12:00:00Z",
  "expires_in": 259200
}
```

> Los campos `expires_at` / `expires_in` **solo se envían a los roles que no son 6 ni 7**.

### Endpoints de autenticación (`api/auth/router.py`)

| Método | Ruta | Línea | Auth | Notas |
|---|---|---|---|---|
| POST | `/auth/login` | 12 | pública | Devuelve token + permisos |
| POST | `/auth/register` | 26 | pública | Crea usuario con rol por defecto **4 (UGR Sectores)** |
| POST | `/auth/verificar-identidad` | 38 | **pública** | Compara carnet/celular/geografía contra un usuario |
| POST | `/auth/cambiar-contrasena` | 49 | **pública** | ⚠️ No exige token: solo necesita `id_usuario` (ver §6) |
| GET | `/auth/mis-permisos` | 59 | Bearer | Permisos del usuario autenticado |

Uso del token:

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v2/rida/empadronamiento/formularios
```

## 2. Tablas de identidad y autorización

Esquema `usuarios`:

| Tabla | Contenido |
|---|---|
| `usuario` | Cuenta: `usuario`, `contrasena` (hash), `nombre`, `carnet`, `celular`, `correo`, `cargo`, `comunidad`, geografía (`id_departamento`, `id_provincia`, `id_municipio`), `activo` |
| `rol` | 11 roles activos (§3) |
| `aplicacion` | Módulos: `EDAN`(1), `RIDA`(2), `SINB`(3), `REA`(4), `SISTEMA`(9), `REPOSITORIO`(12) |
| `accion` | `CREATE`(1), `READ`(2), `UPDATE`(3), `DELETE`(4) |
| `permiso` | Matriz **rol × aplicación × acción** |
| `sesion` | Token, `activo`, `fecha_inicio`, `fecha_expiracion` |
| `auditoria` | Registro de escrituras (ver `api/audit.py`) |

## 3. Roles

| id | Rol | Permisos explícitos en `usuarios.permiso` |
|---|---|---|
| 1 | superadmin | EDAN, RIDA, SINB, REA, SISTEMA, REPOSITORIO × CREATE/READ/UPDATE/DELETE |
| 2 | admin | Igual que 1 |
| 3 | VIDECI Regional | EDAN.READ, **RIDA.READ+UPDATE**, REA.* |
| 4 | UGR Sectores | EDAN.READ, RIDA.READ, REA.* (rol por defecto al registrarse) |
| 5 | DGR Gobernación | EDAN.READ, RIDA.READ+UPDATE, REA.* |
| 6 | UGR Municipio | EDAN.*, RIDA.*, REA.READ/UPDATE, SISTEMA.CREATE/READ/UPDATE, REPOSITORIO.* |
| 7 | Responsable Local | EDAN.*, RIDA.CREATE/READ/UPDATE, REA.*, SISTEMA.READ, REPOSITORIO.* |
| 8 | Alcalde | EDAN.READ, RIDA.READ, REA.READ, SISTEMA.READ, REPOSITORIO.* |
| 9 | VIDECI Departamental | EDAN.READ, RIDA.READ+UPDATE |
| 14 | Almacén | RIDA.READ+UPDATE |
| 15 | Viceministro | RIDA.CREATE/READ/UPDATE (v2.60.0) |
| 16 | DGEA | RIDA.CREATE/READ/UPDATE (v2.60.0) |
| 17 | Gestión de Suministro | RIDA.CREATE/READ/UPDATE (v2.60.0) |
| 12 | Usuario recolector | *(sin permisos explícitos)* |
| 13 | Observador local | *(sin permisos explícitos)* |

Los roles 1 y 2 poseen además `permisos = "full_access"` en el login y **bypasean toda comprobación** (`api/auth/permisos.py:15,42`).

## 4. Mecanismos de autorización (cuatro)

1. **`module_permiso(modulo)`** — `api/auth/permisos.py:7-34`. Se aplica como dependencia de router; mapea método HTTP → acción y consulta `usuarios.permiso`. **by-pass automático de READ para todos los roles** y de todo para el rol 1. Lo usan `rida/router.py:20`, `rida/solicitudes/router.py:19`, `edan/*`, `repositorio/router.py:27`, `firma_digital/router.py:17`.
2. **`permiso_required(modulo, accion)`** — `api/auth/permisos.py:37-61`. Idem con acción explícita; usado en `shared/router.py:27` (v1).
3. **`require_rol(*roles)`** — `api/edan/utils.py:6` y `api/sinb/utils.py:17` (implementaciones duplicadas). Grupos SINB en `api/sinb/utils.py:8-13`.
4. **Aprobación por nivel (solicitudes RIDA)** — `api/rida/solicitudes/service.py` (matriz `ROLES_NIVEL`, v2.60.0):

```python
ROLES_NIVEL = {
    "validacion":         (9,),   # VIDECI Departamental (alcance departamento)
    "viceministro":       (15,),  # Viceministro (nacional)
    "dgea":               (16,),  # DGEA (nacional)
    "revision_articulos": (15,),  # Viceministro (nacional)
    "suministro":         (17,),  # Gestión de Suministro (nacional)
    "despacho":           (9,),   # VIDECI Departamental (alcance departamento)
    "entrega":            (6,),   # UGR Municipio (alcance municipio)
}
```

Secuencia estricta: solo se aprueba el primer nivel no aprobado; los roles 1 y 2
bypasean rol y alcance en cualquier nivel. Los roles 3, 4, 5, 8 y 14 no visan
ningún nivel desde v2.60.0.

**Restricciones adicionales RIDA:**

- Escritura en empadronamiento y solicitudes: `ROLES_ESCRITURA = (1, 2, 6, 7)` (`rida/router.py:26`, `rida/solicitudes/router.py:25`).
- Gestión de eventos: `ROLES_GESTION_EVENTO = (1, 2, 5, 6, 9)` (`rida/router_eventos.py:23`).
- Catálogos de necesidades/rehabilitación: CRUD libre para roles con permiso `RIDA.CREATE/UPDATE/DELETE`.

### Diferencia v1 / v2 en escrituras de catálogos

| Router | v1 | v2 |
|---|---|---|
| `shared` | `permiso_required("SISTEMA", accion)` | solo `get_current_user` (token válido) |
| `usuarios` | `module_permiso("SISTEMA")` | solo `get_current_user` |
| `repositorio` | `module_permiso("REPOSITORIO")` | sin módulo |

> **La v2 abre más la escritura de catálogos:** cualquier usuario autenticado puede modificar catálogos compartidos en v2. Documentado como hallazgo en [INFORME_ENTREGA.md](INFORME_ENTREGA.md).

## 5. Alcance geográfico (seguridad a nivel de fila)

El filtro se aplica en el servicio, no en la BD:

- `scope_geografico(user, ...)` — `api/sinb/utils.py:30-74`:
  - roles 1 y 2 → sin filtro;
  - rol 9 → departamento del usuario;
  - roles 6 y 8 → municipio del usuario;
  - rol 7 → municipio del usuario;
  - roles 12 y 13 → sin filtro por defecto.
- `validar_geografia_jerarquica()` — `api/rida/geo_filters.py:9`: valida códigos INE (6/3/1 dígitos) y la jerarquía departamento → provincia → municipio.
- `_filtros_dep_factory(...)` — `api/edan/router_v2_edan.py:25`: roles 6/7 solo ven sus EDAN; 5/9 por departamento; 8 por municipio.
- `_validar_scope_formulario/_familia/_integrante/_ubicacion/_evento` — `api/rida/service.py:202-247,1127`.

**No existe Row-Level Security de PostgreSQL:** los filtros son exclusivamente de aplicación.

## 6. Auditoría

`AuditMiddleware` (`api/audit.py:80-139`, montado en `main.py:113`) registra en `usuarios.auditoria` toda **POST/PUT/DELETE con status < 400**:

- `id_usuario`, `id_aplicacion`, módulo, acción, cuerpo JSON (**sin el campo `contrasena`**), query params, IP (con soporte `X-Forwarded-For`).

Consulta: `GET /api/v{1,2}/usuarios/auditoria` (`api/usuarios/router.py:215-256`) con 14 filtros (usuario, aplicación, acción, módulo, fechas, geografía, `busqueda` JSON, paginación).

Contenido actual: 3.132 registros de auditoría y 287 sesiones (BD de desarrollo, oct-2026).

## 7. Hallazgos de seguridad (no corregidos en esta revisión)

| # | Hallazgo | Ubicación | Impacto |
|---|---|---|---|
| 1 | `POST /auth/cambiar-contrasena` **no exige token** | `api/auth/router.py:49` | Cualquiera que conozca un `id_usuario` puede cambiar su contraseña |
| 2 | `POST /auth/verificar-identidad` es pública | `api/auth/router.py:38` | Posible enumeración/validación de datos personales |
| 3 | CORS `allow_origins=["*"]` con `allow_credentials=True` | `api/main.py:105-111` | Cualquier origen puede llamar a la API |
| 4 | `JWT_SECRET` con valor por defecto hardcodeado | `api/config.py:15` | Firma forjable si no se sobreescribe en `.env` |
| 5 | Sin rate limiting ni bloqueo por intentos fallidos | — | Fuerza bruta de login |
| 6 | Sin endpoint `/refresh` ni rotación, pese a que el README lo menciona | — | Expectativa incumplida |
| 7 | Escritura de catálogos abierta en v2 a cualquier autenticado | `shared/`, `usuarios/` v2 | Alteración de catálogos por usuarios no previstos |

Estos puntos se registran en [INFORME_ENTREGA.md](INFORME_ENTREGA.md) como pendientes; **no se han corregido en esta entrega**.

---

**Anterior:** [01 · Componentes](01-componentes-y-arquitectura.md) · **Siguiente:** [03 · Offline y sincronización](03-offline-y-sincronizacion.md)
