# RIDA — Shim de compatibilidad acciones de etapa (v2.60.0)

> **Esquema/módulo:** `rida` / solicitudes (`api/rida/solicitudes`).  
> **Migración:** **ninguna** (usa el motor de aprobaciones/etapas ya existente de v2.60.0 y motor AH).  
> **Rama/commit:** `migraciones` (este paquete).

## 1. Objetivo
Mantener compatibilidad con el frontend legado que invoca acciones de etapa retiradas en v2.60.0, traduciéndolas al motor de 7 niveles (y al flujo de Ayuda Humanitaria) **sin reabrir** la máquina de estados anterior (`EN_REVISION`/`OBSERVADA`/`VALIDADA` siguen inactivas).

## 2. Archivos (modificados)
| Archivo | Cambio |
|---|---|
| `api/rida/solicitudes/router.py` | Endpoints `POST /rida/solicitudes/{id}/revisar`, `/validar`, `/observar`, `/corregir` (tags `[Compat]`, docs). `_payload_legacy` acepta JSON o `multipart/form-data` (campos `motivo`/`observacion`, `archivo`, `nombre_documento`, `fecha_documento`); en `revisar/validar` sobre `ENVIADA` (modalidad ≠ Ayuda Humanitaria) puede adjuntar/registrar informe PDF de validación. |
| `api/rida/solicitudes/service.py` | `transicion_legacy(...)` y helpers (`_nivel_actual`, `_observacion_legacy`, etc.): resuelve el nivel accionable según cadena (visaciones `rida.aprobaciones_solicitud` o AH `rida.aprobaciones_ayuda_humanitaria`) y delega en el motor. |

## 3. Contrato / comportamiento
| Acción | Modalidad | Etapa | Efecto |
|---|---|---|---|
| `revisar`/`validar` | Ayuda Humanitaria (1) | `ENVIADA` | Inicia motor AH (`iniciar_motor`, exige checklist instancia 1; 409 si falta). |
| `revisar`/`validar` | Ayuda Humanitaria (1) | `EN_APROBACION` | Aprueba el nivel accionable (rol validado por motor AH). |
| `revisar`/`validar` | Otras | `ENVIADA` | Aprueba `validacion` (informe PDF opcional en mismo request; 409 si falta checklist/informe según motor). |
| `revisar`/`validar` | Otras | `EN_APROBACION`… | Aprueba el nivel accionable. |
| `observar` | Cualquiera | motor activo (`EN_APROBACION`; AH exige motor iniciado) | Devuelve nivel accionable al anterior. **422** si `motivo/observacion` < 10 caracteres. Sin nivel previo aprobado → **409** (usar `POST /{id}/rechazar`). |
| `corregir` | Cualquiera | — | **409**: la devolución ya deja el nivel en `espera_correccion`. |

- Respuesta: envelope habitual; `data` = solicitud (con `etapa`) + `data.aprobacion` (payload de `GET /{id}/aprobacion`).
- Errores/permiso/estado conservan códigos del motor (403/404/409/422). No se reactivan etapas retiradas.
- Contrato recomendado a futuro: `PUT /rida/solicitudes/{id}/aprobacion/{nivel}` y `GET /rida/solicitudes/{id}/aprobacion`.

## 4. Replicación
1. Actualizar código (`api/rida/solicitudes/router.py`, `service.py`) y docs asociadas.
2. Sin migración de BD.
3. Reiniciar API (`./stop.sh && ./start_api.sh`).

## 5. Verificación (ejemplos, con token y solicitud válida)
```bash
# revisar/validar (JSON; o multipart con archivo/nombre_documento/fecha_documento)
curl -X POST "$API/api/v2/rida/solicitudes/$ID/revisar" -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{}'
# observar (motivo >= 10)
curl -X POST "$API/api/v2/rida/solicitudes/$ID/observar" -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{"motivo":"Falta documentación de sustento"}'
# corregir -> 409
curl -X POST "$API/api/v2/rida/solicitudes/$ID/corregir" -H "Authorization: Bearer $T" -H "Content-Type: application/json" -d '{}'
# observar con motivo corto -> 422
```
- Compilación: `python3 -m compileall -q api/rida`.

## 6. Notas
- Shim de transición: delega íntegramente en el motor (no duplica reglas de negocio). Las etapas legadas no vuelven a estar activas.
