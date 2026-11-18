# REPOSITORIO — GET general agrupado por expediente (`modo=agrupado` por defecto)

> **Contexto:** módulo `api/repositorio` (API). **Sin migración** (sin cambios de
> esquema/datos). Rama `migraciones`. Fecha: 2026-11-17. Complementa
> `REPOSITORIO_codigo_documento_v267.md`.

## 1. Objetivo y decisiones

El `GET /api/v2/repositorio/documentos` (consulta general de vista nacional) ahora
**devuelve grupos/expedientes en lugar de documentos sueltos**, con el nº de documentos
por grupo, igual que el usuario pidió:

- **Mismo endpoint, respuesta cambiada** (decisión usuario). Como escape hatch existe
  `modo=plano` con el comportamiento anterior.
- Reglas de agrupación (prioridad RIDA sobre EDAN heredado):
  - `origen=RIDA` → grupo por **`id_evento_rida`** aunque el documento también traiga
    `id_edan` (los 2 docs de un evento RIDA comparten el EDAN y **se mantienen solo
    como RIDA**, no se mezclan con el grupo EDAN).
  - `origen=EDAN` → grupo por **`id_edan`**.
  - `origen=DOC_PRECEDENTE` → grupo por **`codigo_documento`**; hoy siempre existe
    (autogenerado en la subida); si algún fila lo tuviera NULL, forma su propio grupo
    (`DOC-<id_documento>`), nunca se fusiona con otros sin código.
- Cada grupo incluye `total_documentos` (decisión usuario) y `total` del envelope pasa
  a ser **nº de grupos** sin paginar (con `modo=plano` sigue siendo nº de documentos).
- Drill-down reutiliza los filtros existentes con `modo=plano` (sin endpoint nuevo):
  `?modo=plano&id_edan=79` / `?modo=plano&id_evento_rida=15` /
  `?modo=plano&codigo_documento=RES-...` (y la ruta previa
  `GET /documentos/codigo/{codigo_documento}` sigue igual).
- `/documentos/filtrar` y `/documentos/buscar` **siguen planos** (compatibilidad).
- La agrupación se hace **en la API** (regla única servidor + paginación correcta);
  el front solo renderiza.

## 2. Archivos modificados

| Ruta | Qué cambió |
|---|---|
| `api/repositorio/service.py` | +`_GRUPO_KEY_SQL` (expresión de clave: `EV-{id_evento_rida}` / `ED-{id_edan}` / codigo o `DOC-{id}`) y +`list_documentos_grupos(db, ...filtros..., limit, skip, todos)` (GROUP BY tipo+clave; COUNT como `total_documentos`; `min(...)` geo e ids; `max(fecha_documento)/max(fecha_subida)`; etiqueta EDAN con `edan.edan.codigo_edan`; total = grupos). |
| `api/repositorio/router.py` | `GET /documentos` (`listar_documentos`): nuevo Query `modo: Literal["agrupado","plano"] = "agrupado"`; ramifica a `list_documentos_grupos` (mensaje `Grupos de documentos listados`) o `list_documentos_filtrados` (mensaje `Documentos listados`); descripción OpenAPI actualizada. Ninguna otra ruta tocada. |
| `mi_repositorio.md` | Sección 2 reescrita (grupos, JSON de ejemplo real, drill-down, ejemplos 7-8). |

## 3. BD / Migraciones
No aplica: sin migración, sin datos nuevos (las pruebas de hoy crearon 2 docs de
ensayo y fueron hard-deleteados; la BD volvió a 4 docs con `codigo_documento` NULL).

## 4. API — contrato nuevo

`GET /api/v2/repositorio/documentos` (auth JWT; filtros idénticos a los de antes:
`origen, codigo_documento, id_edan, id_evento_rida, id_departamento, id_provincia,
id_municipio, id_tipo_documento, id_usuario_subio, fecha_desde, fecha_hasta, q,
tiene_firma_digital, include_inactive` + `limit(50,1..200)/skip/todos`)

Nuevo parámetro:

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `modo` | `agrupado` \| `plano` | **`agrupado`** | `agrupado`: un objeto por expediente/grupo; `plano`: documentos individuales (contrato anterior) |

Fila de grupo (`modo=agrupado`): `tipo, clave, id_edan, id_evento_rida,
codigo_documento, etiqueta, id_departamento, id_provincia, id_municipio,
total_documentos, fecha_documento_max, fecha_subida_max`.
Orden de grupos: por documento más reciente del grupo (`max(fecha_documento) DESC
NULLS LAST, max(fecha_subida) DESC`). `total` = nº de grupos con los mismos filtros.

**Importante para clientes existentes:** por el cambio de default, quien necesite la
lista plana de siempre debe enviar `modo=plano` (o usar `/documentos/filtrar`, que no
cambió). (Acordado con el usuario: el frontend aún no consume este endpoint; estamos
en inicio.)

## 4.1 Ampliación: copias idénticas entre grupos por hash (mismo commit, sin API nueva)

Decisión del usuario: identificar documentos **iguales** (hash SHA-256 exacto)
**dentro del mismo GET agrupado**, sin endpoints nuevos y **siempre activado**.

- Cada grupo añade `documentos_compartidos` (int: nº de docs del grupo cuyo
  `hash_sha256` aparece en OTRO grupo) y `comparte_con` (jsonb array de grupos
  hermanos: `{tipo, clave, etiqueta, documentos_comunes, documentos:[{id_documento,
  nombre_documento, hash_sha256(left 16)}]}`, ordenados por `documentos_comunes`
  DESC; `[]` si no hay). Copias dentro del mismo grupo NO cuentan (unión con
  `a.clave <> b.clave`).
- Cálculo en `service.list_documentos_grupos` con CTEs `docs/pares/comp/por_dest/
  comp_con` sobre **todos los documentos activos con hash** (independiente de los
  filtros/paginación del listado, para que el badge sea siempre cierto). `total`
  sigue siendo nº de grupos. `modo=plano` NO cambia (no añade campos).
- El hash ya lo graban las 3 vías de subida (`save_documento_pdf`); no hubo
  cambios de BD ni migración.

## 5. Verificación (dev 2026-11-17, resultados reales)

Datos actuales: docs 18/19 (EDAN, `id_edan=79`) y 71/72 (RIDA, `id_evento_rida=15`,
heredan `id_edan=79`).

1. `GET /documentos` (default) → `total=2`, `data=[{tipo:RIDA, clave:"EV-15", etiqueta:"EVENTO RIDA 15", total_documentos:2}, {tipo:EDAN, clave:"ED-79", etiqueta:"EDAN 070101/2026/003", total_documentos:2}]` — **los RIDA quedan como RIDA pese al id_edan común** ✓
2. Subida de 2 DOC_PRECEDENTE con `codigo_documento=PRUEBA-AGRUP-2026-001` → grupos=3 con `{tipo:DOC_PRECEDENTE, total_documentos:2}` primero (más reciente) ✓
3. `?modo=plano` → 6 docs, `message="Documentos listados"` ✓
4. `?modo=plano&codigo_documento=PRUEBA-AGRUP-2026-001` → 2 docs (drill-down) ✓
5. `GET /documentos/filtrar?origen=DOC_PRECEDENTE` → sigue plano (2 docs de la prueba) ✓
6. Limpieza: hard delete de los 2 docs prueba (dueño, en plazo) → 200×2; BD volvió a 4 docs y `count(codigo_documento)=0`; grupos finales=2 ✓
7. `python3 -m compileall -q api/repositorio` OK; API reiniciada (4 workers); protegidos intactos.

Prueba de copias por hash (mismo PDF `sha256 b4b2f45d041f9d89…` subido a dos grupos):
8. `POST /edan/79/documentos` (doc 373, admin) + `POST /documentos`
   `codigo_documento=PRUEBA-CROSS-1` (doc 374, user 30) → GET agrupado: grupo
   `PRUEBA-CROSS-1` con `documentos_compartidos=1` y `comparte_con=[{tipo:EDAN,
   clave:ED-79, documentos_comunes:1, documentos:[{id_documento:373,
   hash_sha256:"b4b2f45d041f9d89"}]}]`; el grupo `ED-79` muestra la contraparte
   simétrica (doc 374) ✓
9. Grupo sin gemelos (`EV-15`) → `documentos_compartidos=0`, `comparte_con=[]` ✓
10. `modo=plano` inalterado (docs con `hash_sha256` propio, sin `comparte_con`) ✓
11. Limpieza: hard-delete de 373 (admin) y 374 (dueño) → 200×2; BD volvió a 4 docs
    y agrupado final = 2 grupos con `documentos_compartidos=0` ✓

## 6. Replicación en el gemelo
Sin migración ni env nuevo:
```bash
git pull origin migraciones
./stop.sh && ./start_api.sh     # o systemctl restart sinagersat-api
# verificar: GET /api/v2/repositorio/documentos -> message "Grupos de documentos listados"
# y GET ...?modo=plano -> message "Documentos listados"
```

## 6.0 Swagger/OpenAPI (esquemas reales generados por FastAPI)

Verificado contra `GET /openapi.v2.json` (2026-11-17):
- `components.schemas`: `DocumentoGrupoResponse` (14 props incl.
  `documentos_compartidos` y `comparte_con`), `GrupoCoincidenciaResponse`,
  `DocumentoCopiaResponse`; `DocumentoResponse` expone `codigo_documento` y
  `hash_sha256`; `Body_..._put` (PUT) con `observaciones/activo/codigo_documento`.
- `GET /documentos`: `response_model=DataListResponse[Union[
  DocumentoGrupoResponse, DocumentoResponse]]` → esquema `oneOf` correcto +
  `responses` con **ejemplos reales** `agrupado`/`plano` (se muestran en Swagger UI);
  parámetros documentados incluyen `modo`, `codigo_documento` y todo el set de
  filtros.
- `GET /documentos/codigo/{...}`, `/filtrar` y `/buscar`:
  `response_model=DataListResponse[DocumentoResponse]`.
- Forms multipart en OpenAPI: `/documentos` (3ª subida) con 9 campos incl.
  `codigo_documento`; `/edan/{id}/documentos` y `/rida/eventos/{id}/documentos`
  con 8 campos **sin** `codigo_documento` (contratos EDAN/RIDA intactos).
- Cambio implementado en `api/repositorio/schemas.py` (modelos nuevos) y
  `api/repositorio/router.py` (response_model + diccionario
  `_EJEMPLOS_GET_DOCUMENTOS` pasado a `responses=`; import `Union`). Sin efecto
  en runtime más allá de la serialización/validación de respuesta.

## 6.1 Límite conocido (decisión registrada)
Solo **hash exacto** (copias byte-idénticas). Escaneos/re-exportes del mismo papel
en municipios distintos NO se detectan (bytes distintos); si algún día hace falta,
sería una tabla de relaciones manual (`v2.68.0`, descartada por ahora).

## 7. Notas / rollback
- El agrupamiento SQL filtra por documento y agrupa: un filtro (`q`, tipo, fechas)
  aplica **a los documentos**; el grupo aparece si al menos un miembro coincide, con
  `total_documentos` = miembros que pasaron los filtros (no del total histórico).
- Rollback: quitar el bloque `modo` del router y `list_documentos_grupos` (o revertir
  el commit); sin efectos en BD.
