# 10 · FAQ y solución de problemas

> Síntomas frecuentes, causas y qué hacer.

## 1. Formatos de error

La API usa **dos formatos** según el tipo de error:

**Errores de validación y de negocio (HTTPException):**

```json
{ "detail": "Transición inválida: BORRADOR → APROBADA" }
```

**Errores globales (500 y 422):**

```json
{ "success": false, "message": "Error interno del servidor", "error_code": 500 }
{ "success":": false, "message": "Error de validación en los datos enviados", "error_code": 422 }
```

**Errores de permiso (403):**

```json
{ "detail": "Sin permiso: CREATE en RIDA" }
```

## 2. Autenticación

| Síntoma | Causa | Solución |
|---|---|---|
| `401 Not authenticated` / `403` | Falta o está mal el header | Usa `Authorization: Bearer <token>` (con espacio) |
| `401` "Usuario no encontrado o inactivo" | Cuenta desactivada o token de un usuario borrado | [09 · Administración](09-administracion.md) §1 |
| El token caducó (72 h) | Pasaste la vigencia | Vuelve a `POST /auth/login` |
| No recuerdo la contraseña | — | `POST /auth/cambiar-contrasena` con tu `id_usuario` (o pedir al administrador) |
| Cambié de usuario y sigue viendo datos viejos | Caché local de la interfaz | Cierra sesión y vuelve a entrar (el login anterior queda inactivado) |

## 3. Permisos (403)

| Mensaje | Significado | Qué hacer |
|---|---|---|
| `Sin permiso: CREATE en RIDA` | Tu rol no tiene escritura RIDA | Solo roles 1, 2, 6, 7 pueden escribir |
| `Rol X no permitido. Roles requeridos: (1, 2, 5, 6, 9)` | Restricción puntual (p. ej. gestionar eventos) | Pedir el rol adecuado |
| `Sin permiso: UPDATE en SISTEMA` | No puedes modificar catálogos/usuarios | Rol 1 o 2 |
| Puedo leer todo lo que no debería | Falta alcance geográfico | [01 §4](01-acceso-y-roles.md) · revisar geografía del usuario |

> Recuerda: **READ está bypaseado** en la API — la protección real de lectura es el alcance geográfico.

## 4. Validaciones (422 / 400)

| Mensaje | Causa | Solución |
|---|---|---|
| `Error de validación en los datos enviados` (422) | Falta un campo obligatorio o formato inválido | Revisa el `description` del endpoint en `/docs` |
| `id_edan_localidad es obligatorio` | Falta la clave del formulario | Ver [02 §4](02-empadronamiento.md) |
| `No se pudo resolver id_formulario` | Familia enviada antes que su formulario | Ordenar el lote: formularios → familias → integrantes |
| `Ya existe un registro con el mismo valor` (23505) | Duplicado (p. ej. una localidad ya tiene formulario) | Buscar el registro existente antes de crear |
| `El registro referenciado no existe` (23503) | FK inexistente (id fuera de alcance o borrado) | Verificar el ID con un GET previo |
| `La prioridad debe ser 1, 2 o 3` | Valor fuera de rango | Usar 1–3 |
| `cantidad debe ser > 0` | Cantidad en cero | Cantidad positiva |

## 5. Geografía

| Mensaje | Causa | Solución |
|---|---|---|
| `Inconsistencia geográfica: municipio 70101 pertenece a departamento 7` | Filtros contradictorios | Enviar depto=7, prov=701, mun=70101 |
| Lista vacía con filtros correctos | El dato no existe en ese territorio | Probar sin filtros o con otro nivel |
| Veo menos datos que un colega | Tu rol limita a tu depto/municipio | Comparar `id_rol` y geografía de ambos |

## 6. Sincronización offline

Ver el capítulo dedicado: [08 §10](08-offline-y-sincronizacion.md). Resumen:

| Síntoma | Solución |
|---|---|
| Errores en `errores[]` del lote | Reenviar solo los ítems fallidos, en orden correcto |
| Registros duplicados | Reutilizar siempre el mismo `*_off` por registro |
| Conflicto devuelto con `data` | Revisar la versión del servidor y decidir |
| `401` tras varios días | Renovar token |

## 7. Reportes e indicadores

| Síntoma | Causa | Solución |
|---|---|---|
| No encuentro el botón de "descargar Excel/PDF" | **No existe aún** | Ver [07 §6](07-reportes.md) |
| El reporte RIDA no me da totales | No hay endpoint de KPIs | Derivar de los listados ([06 §4](06-indicadores.md)) |
| JSON muy grande | Sin paginación | Añadir `limit` / filtros geográficos |

## 8. El servidor no responde

| Síntoma | Qué comprobar |
|---|---|
| `Connection refused` en el puerto 8000 | ¿Está la API activa? `bash start_api.sh` · `curl http://localhost:8000/health` |
| `{"status":"ok"}` pero rutas fallan | Revisar versión: la API activa debe ser **1.4.0** (`GET /`) |
| 404 en rutas RIDA | RIDA **solo existe en `/api/v2`**, no en v1 |
| El navegador bloquea la llamada (CORS) | El servidor permite todos los orímites; revisa URL y método |
| 500 `Error interno del servidor` | Mirar los logs del servicio: `journalctl -u sinagersat-api -f` o la consola de uvicorn |

## 9. Documentación interactiva

| URL | Contenido |
|---|---|
| `http://<servidor>:8000/docs` | Portada con acceso a v1 y v2 |
| `http://<servidor>:8000/docs/v2` | Swagger de la API v2 (la que contiene RIDA) |
| `http://<servidor>:8000/docs/v1` | Swagger de la API v1 (legado) |
| `http://<servidor>:8000/openapi.v2.json` | Especificación OpenAPI descargable |

**Para probar cualquier endpoint desde Swagger:** pulsa **Authorize**, escribe `Bearer <token>` (o solo el token, según el campo) y ejecuta.

## 10. ¿A quién reportar un problema?

1. **Captura:** endpoint llamado, `id_usuario`, `id_rol`, fecha/hora, cuerpo enviado y respuesta completa.
2. **Reproduce** con otro usuario/rol para descartar permisos.
3. **Revisa** la auditoría (`GET /api/v2/usuarios/auditoria`) para ver si la operación quedó registrada.
4. **Documenta** el caso en el repositorio o en la incidencia correspondiente.

## 11. Preguntas frecuentes

**¿Puedo usar la API v1 para RIDA?**
No. RIDA, SINB, NDVI y firma digital solo están en `/api/v2`.

**¿Hay interfaz web en este repositorio?**
No. La web institucional y la app móvil son proyectos externos; este repositorio contiene la API y la base de datos.

**¿Por qué dos versiones de la API (v1/v2)?**
v1 mantiene compatibilidad con clientes antiguos; v2 añade RIDA, los catálogos de EDAN por secciones y los módulos nuevos. Ver [../01-componentes-y-arquitectura.md](../01-componentes-y-arquitectura.md).

**¿Se guardan las contraseñas en texto plano?**
No: se guardan con hash **bcrypt** (`api/auth/jwt.py:9`).

**¿Quién puede ver todos los datos del país?**
Los roles 1 (superadmin) y 2 (admin).

---

**Anterior:** [09 · Administración](09-administracion.md) · Volver al [índice](README.md)
