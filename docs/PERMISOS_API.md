# SINAGERSAT — Sistema de Permisos

Guía completa del sistema de permisos basado en **rol-aplicación-acción**. v1.2.7.

---

## 1. Arquitectura

```
ROL ──┬── PERMISO ── APLICACION
      │            └── ACCION (CREATE|READ|UPDATE|DELETE)
      └── USUARIO
```

### Tablas

| Tabla | Esquema | Propósito |
|-------|---------|-----------|
| `rol` | `usuarios` | Catálogo de roles (7 fijos) |
| `aplicacion` | `usuarios` | Módulos del sistema (EDAN, REA, SISTEMA, …) |
| `accion` | `usuarios` | Operaciones CRUD |
| `permiso` | `usuarios` | Tabla pivote: `(id_rol, id_aplicacion, id_accion)` UNIQUE |

---

## 2. Catálogos

### Roles

| id_rol | Nombre | Descripción |
|--------|--------|-------------|
| 1 | superadmin | Acceso total — bypass de chequeos |
| 2 | admin | CRUD completo + SISTEMA |
| 3 | VIDECI Regional | EDAN/REA: CREATE, READ, UPDATE |
| 4 | UGR Sectores | EDAN/REA: CREATE, READ, UPDATE |
| 5 | DGR Gobernacion | EDAN/REA: CREATE, READ, UPDATE |
| 6 | UGR Municipio | EDAN/REA: CREATE, READ, UPDATE — token eterno |
| 7 | Responsable Local | EDAN/REA: CREATE, READ, UPDATE — token eterno |

### Aplicaciones

| id | Código | Nombre |
|----|--------|--------|
| 1 | EDAN | Evaluación de Daños y Análisis de Necesidades |
| 4 | REA | Reportes de Eventos Adversos |
| 9 | SISTEMA | Administración del Sistema |

### Acciones

| id | Código |
|----|--------|
| 1 | CREATE |
| 2 | READ |
| 3 | UPDATE |
| 4 | DELETE |

---

## 3. APIs de Permisos

### `GET /api/v1/usuarios/permisos/estructura` — Matriz completa

Devuelve roles, apps, acciones y la matriz de permisos en una sola llamada.

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/usuarios/permisos/estructura
```

```json
{
  "roles": [ ... ],
  "aplicaciones": [ ... ],
  "acciones": [ ... ],
  "matriz": {
    "1": { "EDAN": ["CREATE","READ","UPDATE","DELETE"], "REA": [...], "SISTEMA": [...] },
    "2": { "EDAN": ["CREATE","READ","UPDATE","DELETE"], "SISTEMA": [...] },
    "3": { "EDAN": ["CREATE","READ","UPDATE"], "REA": ["CREATE","READ","UPDATE"] }
  }
}
```

### `PUT /api/v1/usuarios/roles/{id_rol}/permisos` — Batch

Reemplaza TODOS los permisos del rol:

```bash
curl -X PUT -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permisos": {"EDAN": ["CREATE","READ","UPDATE"], "REA": [], "SISTEMA": []}}' \
  http://localhost:8000/api/v1/usuarios/roles/7/permisos
```

### Permisos individuales

```bash
# Asignar
curl -X POST -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/usuarios/permisos/4/1/1

# Quitar
curl -X DELETE -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/usuarios/permisos/4/1/1
```

### Catálogos

```bash
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/usuarios/roles/
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/usuarios/aplicaciones/
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/usuarios/acciones/
```

---

## 4. Login con Permisos

`POST /api/v1/auth/login` incluye `permisos` en la respuesta:

```json
{
  "success": true,
  "message": "Login exitoso",
  "data": {
    "access_token": "eyJ...",
    "user_id": 3,
    "usuario": "encargado1",
    "id_rol": 3,
    "rol": "VIDECI Regional",
    "permisos": { "EDAN": ["CREATE","READ","UPDATE"], "REA": ["CREATE","READ","UPDATE"] }
  }
}
```

Para **superadmin (rol 1)**: `"permisos": "full_access"`.

---

## 5. Permisos del Usuario Actual

`GET /api/v1/auth/mis-permisos` (protegido):

```bash
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/auth/mis-permisos
```

```json
{
  "success": true,
  "message": "Permisos obtenidos correctamente",
  "data": {
    "id_usuario": 3,
    "usuario": "encargado1",
    "nombre": "Encargado Regional",
    "id_rol": 3,
    "permisos": { "EDAN": ["CREATE","READ","UPDATE"], "REA": ["CREATE","READ","UPDATE"] }
  }
}
```

---

## 6. Regla Especial: PUT /rea/reportes/{id}/estado

| Rol | Puede cambiar estado de |
|-----|------------------------|
| 1-5 | Cualquier reporte (sin restricción) |
| 6 | Solo reportes de **rol 7** en el **mismo municipio** |
| 7 | Solo sus propios reportes |

Esto permite al **UGR Municipio (rol 6)** gestionar el flujo de aprobación de los reportes ingresados por los **Responsables Locales (rol 7)** de su municipio, sin necesidad de escalar a roles superiores.

---

## 7. Matriz Visual

```
         |   EDAN          |   REA           | SISTEMA
         | C  R  U  D      | C  R  U  D      | C  R  U  D
---------+-----------------+-----------------+-----------------
superadm | ■  ■  ■  ■      | ■  ■  ■  ■      | ■  ■  ■  ■
admin    | ■  ■  ■  ■      | ■  ■  ■  ■      | ■  ■  ■  ■
VIDECI   | ■  ■  ■  □      | ■  ■  ■  □      | □  □  □  □
UGR Sec  | ■  ■  ■  □      | ■  ■  ■  □      | □  □  □  □
UGR Muni | ■  ■  ■  □      | ■  ■  ■  □      | □  □  □  □
Resp Loc | ■  ■  ■  □      | ■  ■  ■  □      | □  □  □  □
```

---

## 8. Tabla Resumen

| Característica | Rol 1 | Rol 2 | Roles 3-5 | Roles 6-7 |
|----------------|-------|-------|-----------|-----------|
| Bypass DB | ✅ Siempre | ❌ | ❌ | ❌ |
| DELETE | ✅ | ✅ | ❌ | ❌ |
| Acceso SISTEMA | ✅ | ✅ | ❌ | ❌ |
| Token expira | 72h | 72h | 72h | **Nunca** |
| Editar/eliminar REA ajeno | ✅ | ✅ | ✅ | ❌ solo propios |
| Cambiar estado REA ajeno | ✅ | ✅ | ✅ | ❌ (excepción: rol 6 a reportes de rol 7 en mismo municipio) |
