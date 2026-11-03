# 01 · Acceso y roles

> Qué necesitas para entrar, qué puedes hacer según tu rol y cómo se protege tu sesión.

## 1. Antes de empezar

- [ ] Tienes una cuenta creada por el administrador (o te registraste y quedaste con rol **4 · UGR Sectores**).
- [ ] Conoces la dirección del servidor: `http://<servidor>:8000` (en producción: `https://api.climbat.net`).
- [ ] Si trabajas en campo, revisa también el [Cap. 08 · Offline](08-offline-y-sincronizacion.md).

## 2. Iniciar sesión

**Endpoint:** `POST /api/v2/auth/login`

```bash
curl -X POST http://localhost:8000/api/v2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "mi_usuario", "contrasena": "mi_contraseña"}'
```

**Respuesta** (simplificada):

```json
{
  "success": true,
  "message": "Login exitoso",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "user_id": 12,
    "usuario": "ugr_muni_1",
    "nombre": "María Flores",
    "id_rol": 6,
    "rol": "UGR Municipio",
    "activo": true,
    "municipio": {"id": 7, "codigo_ine": "70101", "nombre": "San Ignacio"},
    "permisos": {"EDAN": ["READ","CREATE","UPDATE","DELETE"], "RIDA": ["READ","CREATE","UPDATE","DELETE"]},
    "expires_at": "2099-12-31T00:00:00Z"
  }
}
```

**Guarda el token** y envíalo en cada petición:

```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v2/rida/empadronamiento/formularios
```

### Checklist de acceso

- [ ] Obtuve `access_token` en la respuesta.
- [ ] Guardé `id_rol`, `rol` y `permisos` (la interfaz los usa para mostrar u ocultar opciones).
- [ ] Verifiqué mi geografía (`departamento` / `provincia` / `municipio`): determina **qué datos ves**.

### Vigencia del token

| Rol | Vigencia | Comportamiento |
|---|---|---|
| **6 (UGR Municipio)** y **7 (Responsable Local)** | Larga duración | Diseñado para campo: reutiliza la sesión activa si ya existe |
| Resto de roles | 72 horas | Cada login desactiva la sesión anterior |

No hay botón de "cerrar sesión" en la API: al volver a iniciar sesión se invalida la sesión previa (roles distintos de 6 y 7).

## 3. Qué puedo hacer según mi rol

| id | Rol | RIDA | EDAN | Observación |
|---|---|---|---|---|
| 1 | superadmin | Todo | Todo | Bypasea todos los controles; puede visar cualquier nivel |
| 2 | admin | Todo | Todo | Bypasea todos los controles; puede visar cualquier nivel |
| 3 | VIDECI Regional | Lectura + actualización | Lectura | **Ya no visa ningún nivel** (v2.60.0) |
| 4 | UGR Sectores | Lectura | Lectura | **Ya no visa ningún nivel** (v2.59.0) |
| 5 | DGR Gobernación | Lectura + actualización | Lectura | **Ya no visa ningún nivel** (v2.59.0) |
| 6 | UGR Municipio | **CRUD completo** | CRUD | Gestiona eventos; aprueba el nivel `entrega` (su municipio) |
| 7 | Responsable Local | **Creación y lectura** | CRUD | Token largo. **No aprueba ningún nivel** |
| 8 | Alcalde | Lectura | Lectura | **Ya no visa ningún nivel** (v2.59.0); token largo |
| 9 | VIDECI Departamental | Lectura + actualización | Lectura | Ve su departamento; aprueba `validacion` y `despacho` |
| 14 | Almacén | Lectura + actualización | — | **Ya no visa ningún nivel** (v2.60.0) |
| 15 | Viceministro | Lectura + actualización | — | Visas `viceministro` y `revision_articulos` (nacional) |
| 16 | DGEA | Lectura + actualización | — | Visas `dgea` (nacional) |
| 17 | Gestión de Suministro | Lectura + actualización | — | Visas `suministro` (nacional) |
| 12 | Usuario recolector | *(sin permisos explícitos)* | — | Solo lectura general |
| 13 | Observador local | *(sin permisos explícitos)* | — | Solo lectura general |

**Restricciones específicas RIDA:**

- Escribir empadronamiento y solicitudes: roles **1, 2, 6, 7** (`api/rida/router.py:26`).
- Habilitar / cerrar / anular eventos: roles **1, 2, 5, 6, 9** (`api/rida/router_eventos.py:23`).
- Rechazar una solicitud (`ENVIADA`/`EN_APROBACION`): roles **1, 2, 5, 6, 7, 9**.
  Las acciones `enviar/revisar/observar/corregir/validar/iniciar-aprobacion/
  autorizar/cerrar` **ya no existen** (v2.60.0).
- Aprobar o devolver un nivel: solo el rol del nivel (§4 de
  [05 · Solicitudes](05-solicitudes-workflow.md)), más **1 y 2 que pueden todos**.
- Configurar la cadena de aprobación de una modalidad: roles **1, 2**.
- **Todos los roles pueden leer** (el control `READ` está bypaseado en `api/auth/permisos.py:25`); el alcance geográfico es quien limita realmente lo que ves.

> **Alcance geográfico en solicitudes (v2.36.0).** A partir de esta versión el
> módulo de solicitudes **sí** acota las operaciones al territorio: el rol 5 y el
> 9 solo sobre su departamento, el 8 solo sobre su municipio, en las lecturas y
> en todas las transiciones. Antes solo se filtraba el listado, y cualquier rol
> podía aprobar, rechazar, autorizar o cerrar una solicitud ajena. Los roles 6 y
> 7 **no** tienen filtro geográfico: `rida.solicitud` no tiene columna de
> propietario, solo `id_usuario_crea`.

## 4. Qué datos ves (alcance geográfico)

| Tu rol | Alcance |
|---|---|
| 1, 2 | Todo el país |
| 9 | Tu departamento |
| 6, 7, 8 | Tu municipio |
| 12, 13 | Sin filtro por defecto (revisar con administración) |

Detalle técnico: [../02-autenticacion-y-roles.md §5](../02-autenticacion-y-roles.md).

## 5. Verificar mis permisos en cualquier momento

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v2/auth/mis-permisos
```

## 6. Registro y cambio de contraseña

| Acción | Endpoint | Nota |
|---|---|---|
| Registrarse | `POST /api/v2/auth/register` | Crea cuenta con rol 4 · UGR Sectores |
| Cambiar contraseña | `POST /api/v2/auth/cambiar-contrasena` | ⚠️ Requiere `id_usuario`; ver [../02 §7](../02-autenticacion-y-roles.md) |
| Verificar identidad | `POST /api/v2/auth/verificar-identidad` | Compara carnet/celular/geografía |

## 7. Autoevaluación

- [ ] Puedo explicar la diferencia entre mi rol y el rol 7.
- [ ] Sé qué municipio/departamento veo y por qué.
- [ ] Sé dónde mirar si la API me devuelve `403` → [Cap. 10 §3](10-faq-y-problemas.md).

---

**Siguiente:** [02 · Empadronamiento](02-empadronamiento.md) · Volver al [índice](README.md)
