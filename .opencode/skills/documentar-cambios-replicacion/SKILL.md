---
name: documentar-cambios-replicacion
description: Use when making, finishing, or reviewing any code, database, API, schema, script, or config change that must be replicable on another server — across ALL database schemas (shared, edan, rida, sinb, rea, usuarios, repositorio, etc.) and ALL APIs/modules (not only EDAN or hogares). For each change, record and keep aligned a handoff in `cambios_replicacion/`: create/update a markdown with objective, decisions, exact files (new/modified), migrations (with `despliegue/migraciones/` mirror), DB/API/schema impacts, replication steps, and verification (SQL/curl/checks), and update the folder index INSTRUCCIONES.md. Trigger: documentar cambio, replicar, handoff, migración, otro servidor, desplegar, alinear cambios, cualquier esquema, toda la BD.
---

# Documentar cambios para replicación (handoff) — toda la BD y todas las APIs

Carpeta de handoff del proyecto: **`cambios_replicacion/`** (paquete general para
replicar cambios en otro servidor). Aplica a **toda la base de datos** (cualquier
esquema: `shared`, `edan`, `rida`, `sinb`, `rea`, `usuarios`, `repositorio`, …) y a
**todas las APIs/módulos**, no solo a un esquema o módulo concreto.

## Cuándo usar
- Al implementar o cerrar **cualquier** cambio replicable: BD/migraciones (de
  cualquier esquema), API/endpoints, esquemas Pydantic, servicios, scripts, docs o
  config de despliegue.
- Cuando el usuario pida documentar, alinear, preparar handoff o “subir para que en
  el otro servidor se aplique”.

## Por cada cambio (obligatorio)
1. **Crear o actualizar un `.md`** en `cambios_replicacion/` (p.ej.
   `<ESQUEMA_o_MODULO>_<cambio>.md`, o sección fechada) con esta estructura:
   - **Contexto**: esquema(s) y módulo(s) afectados.
   - **Objetivo y decisiones** (qué cambia, por qué, reglas/validaciones).
   - **Archivos** (lista exacta): NUEVOS y MODIFICADOS con rutas.
   - **Migraciones**: archivo en `database/migrations/` + **copia espejo textual** en
     `despliegue/migraciones/`; idempotencia (`IF NOT EXISTS`/`BEGIN..COMMIT`), orden
     y cómo aplicarlas (`psql` o `despliegue/scripts/actualizar.sh`).
   - **BD**: tablas/columnas/índices/datos afectados (por esquema).
   - **APIs y esquemas**: endpoints (método/ruta/auth), cuerpos, respuestas, y qué
     modelos/lecturas los exponen (cubrir todos los puntos de escritura y lectura).
   - **Replicación**: pasos concretos en servidor limpio (código/migración/reinicio/
     carga de datos si aplica).
   - **Verificación**: SQL + `curl`/pruebas y resultados esperados (incluir casos de
     error como 422 cuando aplique).
   - **Notas**: compatibilidad, comportamiento preexistente, rollback/limitaciones.
2. **Actualizar el índice**: en `cambios_replicacion/INSTRUCCIONES.md` agregar o
   ajustar la entrada/puntero al doc, reflejar el **estado** (rama/commit pushed o
   pendiente, artefactos sin commitear) y la lista de archivos a replicar. Mantenerlo
   como índice general (toda la BD/APIs), con una entrada por cambio/tema/esquema.
3. **Alinear artefactos**: si migraciones o scripts necesarios existen pero no están
   versionados/commiteados, incluirlos en la lista de replicación y dejarlos
   preparados (y commitear/pushear solo si el usuario lo pide o para alinear el
   paquete, sin mezclar cambios ajenos).

## Reglas
- **Alcance total**: no asumir un solo esquema (p.ej. EDAN) — cubrir el esquema/módulo
  real del cambio y toda la BD/APIs afectada.
- **No inventar**: derivar todo de archivos/diffs/consultas reales; indicar lo no
  verificado.
- **Fuentes de verdad**: rutas reales del repo, nombres de migración/endpoint
  exactos, y comportamiento observado.
- **No mezclar**: no incluir cambios no relacionados en el paquete o commit de handoff.
- **Commits**: nunca commitear salvo que el usuario lo pida; al hacerlo, usar
  ramas/commits claros y listar qué va en cada uno.
- **Exhaustividad**: cubrir todos los puntos de escritura/lectura y esquemas
  afectados por el cambio (no solo el endpoint principal).
