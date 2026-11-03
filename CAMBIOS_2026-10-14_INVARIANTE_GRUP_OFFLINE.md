> **ACTUALIZACIÓN 2026-10-16:** `version` y los 409 por versión fueron
> eliminados de la familia nueva (LWW total). Ver
> `CAMBIOS_2026-10-16_LWW_FOTO_1_1.md` y PLAN §20.14.

# Cambios 2026-10-14 — Familia nueva EDAN v2: invariante grup_*, documento exacto, offline

Base: `/api/v2/edan` (familia nueva: `/formularios*`, `/fotografias`, `/sync`).
La API v2 vieja (`/localidades*`) y v1 quedan **intactas**.

## 1. Invariante `grup_* := OR(sus imp_* miembros)`

- **Backfill único** ejecutado y commiteado: 29/125 filas violaban (todas solo encienden, 0 apagan). Verificado `0 violaciones` post-backfill.
- **Red de lectura**: `get_formulario`, `get_formulario_completo`, `sync_pull` y `list_*` sobrescriben los 9 `grup_*` con `OR(imp)` vía `_sincronizar_grupos_fila` (inmune a drift legacy).
- **Escritura**: `_recalcular_grupos(db, id_loc)` en toda escritura que cambie `imp_*` (POST/PUT cabecera, /completo, secciones, viviendas). El cliente **NUNCA** envía `grup_*` (400 si llegan en /completo).
- `por_grupo` en `/formularios/estados` se computa en SQL desde `imp_*` (OR miembros), no desde las columnas `grup_*` crudas.

## 2. `/completo` = documento exacto

- **version obligatoria** al actualizar (400 si falta; 409 si difiere). Creación sin version OK.
- 14 `imp_*` obligatorias (booleanas).
- `imp=true` ⇒ ≥1 fila en el payload (400 si no).
- `imp=false` ⇒ **purga total** (1:1 incluidas) + fotos `borrado_logico=true` (incl. las de viviendas hijas de `danos_vivienda`) + viviendas cascada.
- Sección 1:N presente ⇒ **reemplazo exacto** (las no enviadas se borran).
- Sección 1:1 con `imp=true` ⇒ exactitud: solo queda la fila upserteada (in-place por `id_edan_localidad`).
- Sets 4 (impacto) / 8 (proteccion) intactos.
- Se eliminó el 400 legacy ">1 danos_vivienda → consolidar".

## 3. Estandarización de TODOS los GET de la familia nueva

**Nodo `grupos` ELIMINADO** de todas las respuestas. Los 9 `grup_*` son **planos en cabecera**, SIEMPRE sincronizados.

| Endpoint | Forma nueva |
|---|---|
| `GET /formularios` | items planos: todas las columnas + FK anidadas + `imp_*` + `grup_*` sync. Sin nodo `grupos`. |
| `GET /formularios/{uuid}` | **BREAKING**: `{cabecera, secciones_resumen}` (antes `data.*`). Cabecera = fila completa + FK + planos. |
| `GET /formularios/{uuid}/completo` | `{cabecera, 14 secciones, fotos}` sin nodo `grupos`; cabecera con planos. |
| `GET /formularios/estados` | **BREAKING**: `{items, resumen: {por_estado[], por_grupo[]}, total}`. Items con `grup_*` planos pero **sin** `imp_*` (payload mínimo). |

## 4. `fotografia` opcional-descartada en TODOS los POST/PUT

- Path opcional **aceptado y DESCARTADO** (nunca 400, nunca escrito) en secciones, viviendas y /completo.
- **Oculta del esquema Swagger** en `ViviendaUpsert` (`extra="ignore"`); documentada en docstrings.
- La foto se sube con `POST /fotografias` (multipart); el servidor espeja el path en la fila dueña.
- `upsert_seccion`/`upsert_vivienda` descartan vía `_CLAVES_DESCARTADAS = {"fotografia"}`.

## 5. Respuestas enriquecidas para modo offline (TODAS las APIs)

Cadena de uuids sin GET extra: `localidad ↔ fila ↔ dano ↔ vivienda ↔ foto`.

| Respuesta | Enriquecimiento |
|---|---|
| POST/PUT sección, GET fila(s) | `uuid_edan_localidad` |
| POST/PUT/GET/DELETE vivienda | `uuid_dano_vivienda` + `uuid_edan_localidad` |
| POST/GET/DELETE foto | `uuid_edan_localidad` |
| DELETE sección | `uuid_edan_localidad` + `id_edan_localidad` |
| `sync/pull` formularios | FK anidadas + `grup_*` sync |
| `sync/pull` secciones | `tipo_seccion` + `uuid_edan_localidad` |
| `sync/pull` viviendas | `uuid_dano_vivienda` + `uuid_edan_localidad` (join a dano padre; batch sin N+1) |
| `sync/pull` fotos | `uuid_edan_localidad` |

Identidad SOLO por **uuid** en todos los POST/PUT (`uuid_edan_localidad`, `uuid_registro`, `uuid_fotografia`, `uuid_dano_vivienda`); ids numéricos solo lectura (verificado en OpenAPI).

## 6. Regla de enviados (estados 2,3,4,5)

- Grupo true exige miembro `imp=true` con ≥1 fila → **400 + rollback**.
- Post-mutación en: POST/PUT cabecera, /completo, `DELETE seccion`.
- **`sync_push` con `validar=False`** (solo recálculo; el lote offline puede llevar parcialidad transitoria — documentado).

## 7. Bugs corregidos

| Bug | Síntoma | Fix |
|---|---|---|
| `router_v2_nuevas.py` estados | `SuccessResponse(data=out["data"])` → KeyError 500 | `SuccessResponse(data=out)` |
| `upsert_formulario_completo` | `form["id_edan_localidad"]` → KeyError 500 (tras el BREAKING de get_formulario) | `form["cabecera"]["id_edan_localidad"]` |
| `_marcar_fotos_borradas` + DELETEs | `uuid = ANY(text[])` → ProgrammingError 500 | `ANY(CAST(:us AS uuid[]))` |
| Purga/DELETE `danos_vivienda` | fotos de viviendas hijas NO marcadas `borrado_logico` | `_marcar_fotos_borradas` marca cascada de viviendas; `delete_seccion` reutiliza el helper |
| `GET /formularios/estados` | ruta capturada por `{uuid_ref}` | ya registrada antes (§20.12) |

## 8. Pruebas — 7 suites, 285 PASS / 0 FAIL

| Suite | Resultado |
|---|---|
| `test_nuevas.sh` | 51 PASS |
| `test_completo.sh` | 23 PASS |
| `test_regresion_grup.sh` | 18 PASS |
| `test_crud_sync.sh` | 43 PASS |
| `test_multifila.sh` | 46 PASS |
| `test_final.sh` | 79 PASS |
| **`test_invariante.sh` (nueva)** | **25 PASS** |

`test_invariante.sh` cubre: recalc imp→grup en POST/PUT, 400 imp=false+filas, version 400/409 en /completo, purga imp=false (filas+fotos+viviendas), reemplazo exacto 1:N y 1:1, regla de enviados (400+rollback) en POST y DELETE, resumen estados inmune a drift, estructura sin nodo grupos, foto descartada en todos los POST, cadena uuids offline, pull enriquecido, push sin regla.

## 9. Despliegue

- `py_compile` + `import api.main` OK.
- API reiniciada: 4 workers, health 200×5.
- Datos de test (`aaaa%`/`TEST%`) limpiados; tombstones `aaaaaaaa-%` limpios.

## 10. Tokens de prueba regenerados (12h)

`/tmp/tok_u6`, `/tmp/tok_u7a`, `/tmp/tok_u7b`, `/tmp/tok_u7c`, `/tmp/tok_u8`, `/tmp/tok_u9` (usuarios `TEST_NUEVAS_*`, ids 1210-1212).
