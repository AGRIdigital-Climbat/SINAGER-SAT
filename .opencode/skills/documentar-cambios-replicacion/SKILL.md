---
name: documentar-cambios-replicacion
description: Use when making, finishing, or reviewing any code, database, API, schema, script, or config change that must be replicable on another server. For each change, record and keep aligned a handoff in `cambios_hogares_censo2024/`: create/update a markdown with objective, decisions, exact files (new/modified), migrations (with `despliegue/migraciones/` mirror), DB/API/schema impacts, replication steps, and verification (SQL/curl/checks), and update the folder index/INSTRUCCIONES. Trigger: documentar cambio, replicar, handoff, migración, otro servidor, desplegar, alinear cambios.
---

# Documentar cambios para replicación (handoff)

Carpeta de handoff del proyecto: **`cambios_hogares_censo2024/`** (paquete de
cambios para replicar en otro servidor, aunque el cambio no sea de hogares).

## Cuándo usar
- Al implementar o cerrar **cualquier** cambio que deba replicarse: BD/migraciones,
  API/endpoints, esquemas Pydantic, servicios, scripts, docs/config de despliegue.
- Cuando el usuario pida documentar, alinear, preparar handoff o “subir para que en
  el otro servidor se aplique”.

## Por cada cambio (obligatorio)
1. **Crear o actualizar un `.md`** en `cambios_hogares_censo2024/` (p.ej.
   `<TEMA>_<cambio>.md`) con esta estructura:
   - **Objetivo y decisiones** (qué cambia, por qué, reglas/validaciones).
   - **Archivos** (lista exacta): NUEVOS y MODIFICADOS con rutas.
   - **Migraciones**: archivo en `database/migrations/` + **copia espejo textual** en
     `despliegue/migraciones/`; idempotencia (`IF NOT EXISTS`/`BEGIN..COMMIT`), orden
     y cómo aplicarlas (`psql` o `despliegue/scripts/actualizar.sh`).
   - **BD**: tablas/columnas/índices/datos afectados.
   - **APIs y esquemas**: endpoints (método/ruta/auth), cuerpos, respuestas, y qué
     modelos/lecturas los exponen.
   - **Replicación**: pasos concretos en servidor limpio (código/migración/reinicio/
     carga de datos si aplica).
   - **Verificación**: SQL + `curl`/pruebas y resultados esperados (incluir casos de
     error como 422 cuando aplique).
   - **Notas**: compatibilidad, comportamiento preexistente, rollback/limitaciones.
2. **Actualizar el índice**: en `cambios_hogares_censo2024/INSTRUCCIONES.md` agregar
   o ajustar la entrada/puntero al doc, y reflejar el **estado** (rama/commit pushed
   o pendiente, artefactos sin commitear) y la lista de archivos a replicar.
3. **Alinear artefactos**: si la migración o scripts necesarios existen pero no están
   versionados/commiteados, incluirlos en la lista de replicación y dejarlos
   preparados (y commitear/pushear solo si el usuario lo pide o para alinear el
   paquete, sin mezclar cambios ajenos).

## Reglas
- **No inventar**: derivar todo de archivos/diffs/consultas reales; indicar lo no
  verificado.
- **Fuentes de verdad**: rutas reales del repo, nombres de migración/endpoint
  exactos, y comportamiento observado.
- **No mezclar**: no incluir cambios no relacionados (otros módulos/docs/RIDA) en el
  paquete o commit de handoff.
- **Commits**: nunca commitear salvo que el usuario lo pida; al hacerlo, usar
  ramas/commits claros y listar qué va en cada uno. Preferir mantener la carpeta y
  los artefactos de replicación consistentes entre sí.
- **Exhaustividad**: cubrir todos los puntos de escritura/lectura y esquemas
  afectados por el cambio (no solo el endpoint principal).
