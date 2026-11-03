# 09 · Administración

> Usuarios, roles, permisos, sesiones y auditoría.
> Prefijos: `/api/v2/usuarios` · **Requiere permisos `SISTEMA`** (roles 1 y 2; el rol 1 bypasea todo).

## 1. Cuentas de usuario

| Endpoint | Método | Uso |
|---|---|---|
| `/api/v2/usuarios` | GET | Listar usuarios (filtros y paginación) |
| `/api/v2/usuarios` | POST | Crear usuario |
| `/api/v2/usuarios/{id}` | GET / PUT / DELETE | Ver, modificar, eliminar |
| `/api/v2/usuarios/{id}/cuenta` | PUT | Cambiar contraseña, rol o estado (solo permiso `SISTEMA.UPDATE`) |
| `/api/v2/usuarios/importar` | POST | **Carga masiva desde Excel (.xlsx)** |

### Checklist de alta de un usuario

- [ ] 1. Crear la cuenta con usuario y contraseña (`POST /usuarios`).
- [ ] 2. Asignar el **rol** correcto (ver §3).
- [ ] 3. Asignar **geografía** (`id_departamento`, `id_provincia`, `id_municipio`): define qué datos verá.
- [ ] 4. Dejar `activo: true`.
- [ ] 5. Verificar con el usuario que puede iniciar sesión.

### Carga masiva desde Excel

`POST /api/v2/usuarios/importar` recibe un `.xlsx` con las columnas de usuario. Es la vía recomendada para dotación inicial. Plantilla relacionada: `Usuarios.xlsx` en la raíz del repositorio.

## 2. Roles

Catálogo: `GET /api/v2/usuarios/roles` · CRUD: `POST/PUT/DELETE /roles[/{id}]`

| id | Rol | Uso típico |
|---|---|---|
| 1 | superadmin | Acceso total |
| 2 | admin | Acceso total |
| 3 | VIDECI Regional | Supervisión regional |
| 4 | UGR Sectores | Rol por defecto al registrarse |
| 5 | DGR Gobernación | Gobernación departamental |
| 6 | UGR Municipio | Gestión municipal completa |
| 7 | Responsable Local | Captura en localidad |
| 8 | Alcalde | Aprobación y lectura |
| 9 | VIDECI Departamental | Supervisión departamental |
| 12 | Usuario recolector | Captura de datos SINB |
| 13 | Observador local | Observación SINB |

Detalle de permisos reales: [../02-autenticacion-y-roles.md §3](../02-autenticacion-y-roles.md).

## 3. Matriz de permisos

El sistema es una matriz de **rol × aplicación × acción**:

- **Aplicaciones:** `EDAN`, `RIDA`, `SINB`, `REA`, `SISTEMA`, `REPOSITORIO`
- **Acciones:** `CREATE`, `READ`, `UPDATE`, `DELETE`

| Endpoint | Uso |
|---|---|
| `GET /permisos/estructura` | Árbol completo para pintar la interfaz |
| `GET /permisos/rol/{id}` | Permisos de un rol |
| `PUT /roles/{id}/permisos` | **Reemplaza** toda la matriz del rol |
| `GET /permisos` | Listado plano |
| `POST /permisos/{rol}/{aplicacion}/{accion}` | Añadir un permiso |
| `DELETE /permisos/{rol}/{aplicacion}/{accion}` | Quitar un permiso |

### Checklist de dar permisos a un rol

- [ ] 1. `GET /permisos/estructura` para ver las opciones.
- [ ] 2. `GET /permisos/rol/{id}` para ver el estado actual.
- [ ] 3. Modificar con `POST`/`DELETE` puntuales (recomendado) o `PUT /roles/{id}/permisos` (reeemplazo completo ⚠️).
- [ ] 4. Verificar con `GET /permisos/rol/{id}`.

> ⚠️ `PUT /roles/{id}/permisos` **sustituye toda la matriz**: si envías una lista incompleta, el resto desaparece.

> Nota: las **lecturas (READ) están bypaseadas** en la API (`api/auth/permisos.py:25`): todos los roles autenticados pueden leer; lo que limita es el alcance geográfico. Conviene conocerlo al diseñar roles.

## 4. Aplicaciones y acciones

| Recurso | Endpoints |
|---|---|
| Aplicaciones | `GET/POST /aplicaciones`, `GET/PUT/DELETE /aplicaciones/{id}` |
| Acciones | `GET/POST /acciones`, `GET/PUT/DELETE /acciones/{id}` |

## 5. Sesiones

`GET /api/v2/usuarios/sesiones` — lista de sesiones registradas (`usuarios.sesion`: token, activo, fecha inicio/expiración).

Cómo se comportan:

- Roles distintos de 6 y 7: **cada login desactiva las sesiones previas** del usuario.
- Roles 6 y 7: se **reutiliza** la sesión activa (token de larga duración).

## 6. Auditoría

`GET /api/v2/usuarios/auditoria`

| Filtro | Ejemplo |
|---|---|
| `id_usuario` | Quién realizó la acción |
| `id_aplicacion` / `modulo` / acción | Qué módulo y operación |
| `fecha_desde` / `fecha_hasta` | Rango temporal |
| `busqueda` | JSON con criterios adicionales |
| `skip` / `limit` | Paginación |

**Qué se registra:** toda **POST/PUT/DELETE** con respuesta < 400 (`api/audit.py`). Se guarda el cuerpo JSON **sin la contraseña**, los query params y la IP (respeta `X-Forwarded-For`).

**Qué NO se registra:** las lecturas (GET), los intentos fallidos de login y los cambios de contraseña.

### Checklist de revisión de auditoría semanal

- [ ] Filtrar por `fecha_desde` de la semana.
- [ ] Revisar escrituras de catálogos (`shared`, `usuarios`) realizadas por roles inesperados.
- [ ] Revisar eliminaciones (`DELETE`) en EDAN/RIDA.
- [ ] Contrastar `id_usuario` con las sesiones activas.

## 7. Endpoints transversales útiles

| Endpoint | Uso |
|---|---|
| `GET /api/v2/shared/departamentos` etc. | Catálogos geográficos (CRUD en v2 con solo token) |
| `POST /api/v2/upload` | Subir imágenes |
| `GET /api/v2/repositorio/documentos/filtrar` | Buscar documentos por metadata |
| `POST /api/v2/firma-digital/validar-pdf` | Validar firma AGETIC de un PDF |

## 8. Advertencias

- ⚠️ En **v2**, la escritura de catálogos compartidos (`shared`, `usuarios`) solo exige token válido; en v1 exigía permiso `SISTEMA`. Conocer esto al definir la exposición pública.
- ⚠️ `POST /auth/cambiar-contrasena` no exige token (hallazgo abierto, ver [../INFORME_ENTREGA.md](../INFORME_ENTREGA.md)).
- ⚠️ Credenciales de prueba: no usar en producción.

---

**Anterior:** [08 · Offline](08-offline-y-sincronizacion.md) · **Siguiente:** [10 · FAQ y problemas](10-faq-y-problemas.md)
