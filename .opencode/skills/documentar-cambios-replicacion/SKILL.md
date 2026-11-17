---
name: documentar-cambios-replicacion
description: Use when making, finishing, or reviewing any code, database, API, schema, script, config, service/systemd, or env change that must be replicated byte-for-byte on the twin server ("gemelo") — across ALL database schemas (shared, edan, rida, sinb, rea, usuarios, repositorio, motor_ia, publico, etc.) and ALL APIs/modules. For each change, record in `cambios_replicacion/` a handoff markdown with objective, decisions, exact file paths (new/modified), migrations (with `despliegue/migraciones/` mirror), EXACT names of every DB object (schemas, tables, columns, views, indexes), EXACT method+path+auth+params+response envelope of every endpoint touched (with sample JSON), env vars, systemd units/workers, ordered replication steps (security dump first), idempotency/rollback, and verification (SQL/curl with observed results and error codes). Update the folder index INSTRUCCIONES.md (row per change with state/branch/commit). Trigger: documentar cambio, replicar, gemelo, otro servidor, handoff, migración, desplegar, alinear cambios, cualquier esquema, toda la BD, registrar APIs.
---

# Documentar cambios para replicación (handoff) — servidor gemelo

Carpeta de handoff: **`cambios_replicacion/`**. Regla de oro: **el otro servidor es un
gemelo que NO puede ver lo que no está escrito aquí**. Todo lo necesario para dejarlo
idéntico debe quedar registrado con nombres exactos (rutas de archivos, endpoints,
esquemas/vistas/columnas, variables de entorno, unidades systemd). Si algo no se
documenta, "no existe".

## Cuándo usar
- Al implementar o cerrar **cualquier** cambio replicable: BD/migraciones (cualquier
  esquema), API/endpoints, esquemas Pydantic, servicios, scripts, docs, **config
  (.env)**, **servicios systemd/workers**, o cambios de operación (reinicios, dumps).
- Cuando el usuario pida documentar, alinear, preparar handoff, "registrar APIs" o
  "subir para que en el otro servidor (gemelo) se aplique lo mismo".

## Estructura obligatoria del `.md` por cambio
Crear/actualizar `cambios_replicacion/<ESQUEMA_o_MODULO>_<cambio>.md` con TODAS las
secciones (vaciar una solo si realmente no aplica, diciendo "no aplica"):

1. **Contexto**: esquema(s) y módulo(s) afectados; rama/commit; fecha.
2. **Objetivo y decisiones**: qué cambia y por qué; reglas/validaciones acordadas con el
   usuario (incluidas las rechazadas: p. ej. "sin k-anonimato", "solo v2").
3. **Archivos** (listas exactas, con ruta completa en el repo):
   - **NUEVOS**: uno por línea, con 1 frase de contenido.
   - **MODIFICADOS**: ruta → qué líneas/funciones/endpoints cambiaron (nombres de
     funciones y rutas FastAPI, no descripciones vagas).
   - **FUERA DEL REPO**: archivos tocados fuera del árbol (p. ej.
     `/etc/systemd/system/*.service`, caches en `~/.cache/...`), con contenido exacto o
     comando que lo genera.
4. **Migraciones**:
   - Nombre EXACTO del archivo en `database/migrations/` y confirmación de la **copia
     espejo textual idéntica** en `despliegue/migraciones/` (comprobar con `diff -q`).
   - Idempotencia declarada (`IF NOT EXISTS`, `CREATE OR REPLACE`, `BEGIN..COMMIT`) y
     prueba de la 2ª pasada sin error.
   - Comando de aplicación exacto (`psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f ...` o
     `despliegue/scripts/actualizar.sh`) y orden relativo a otras migraciones.
5. **BD — objetos creados/alterados**: tabla por tabla y objeto por objeto con **nombres
   exactos**: `esquema.objeto` (tablas, columnas + tipo + default, vistas con sus columnas
   de salida, índices, constraints, comentarios). Para vistas: listar columnas que
   expone y **fuente** de cada agregación (semántica, no solo el SQL): p. ej.
   `origen='RIDA' ⇔ id_evento_rida NOT NULL`, `personas_por_hogar = div(2*pob+hog_ine,
   2*hog_ine)` con base oficial `hogares_ine`.
6. **APIs y esquemas** — el detalle más importante para el frontend:
   - Tabla de **cada endpoint tocado**: `MÉTODO /ruta/completa` (incluye prefijo
     `/api/v1|v2`), auth exacta (ninguna / JWT `get_current_user` / `module_permiso(X)` /
     `X-API-Key`), content-type, parámetros (nombre, tipo, default, `le/ge`), y modelo
     Pydantic devuelto cuando exista.
   - **Envelope de respuesta con ejemplo JSON real** (recortado): `success`, `message`,
     `data`, `total` — y los campos derivados (p. ej. `origen`, `cantidad_firmas`,
     `firma_validada`).
   - Códigos de error con `detail` literal observado (400/401/403/404/409/422) y cuándo
     ocurren.
   - Nombres de tag OpenAPI y archivo router.
   - Contratos existentes que **NO cambian** (para tranquilidad del gemelo).
7. **Config/entorno**: variables de `.env` nuevas o usadas con su valor semántico (no
   secretos): nombre, default, efecto. Cambios en `requirements.txt`.
8. **Servicios/procesos**: unidades systemd afectadas (nombre exacto, `User=`,
   `ExecStart`, `Environment=`, nº de workers), puertos, y comandos
   `daemon-reload/restart/enable`. Incluir el estado esperado tras el despliegue
   (`active`, puertos escuchando).
9. **Replicación en el gemelo** (pasos numerados, ejecutables tal cual):
   0. **Respaldo de seguridad ANTES de tocar nada**: `bash
      despliegue/scripts/generar_dump.sh` (o `pg_dump -Fc` equivalente) y verificación de
      que el dump quedó en `despliegue/dump/`.
   1. `git pull <rama> <commits>` → 2. `pip install -r requirements.txt` si aplica →
   3. migraciones en orden exacto (idempotentes) → 4. recargar/configurar servicios →
   5. reiniciar API → 6. precargas (modelos, datos, `--importar`).
   Cada paso con el comando completo y qué salida confirma éxito.
10. **Verificación** (en el gemelo, después de replicar):
    - SQL: consultas con resultado esperado (`count`, `to_regclass`, columnas).
    - curl: **uno por endpoint nuevo/modificado**, mostrando HTTP esperado y fragmento de
      cuerpo; incluir casos negativos (401/403/404/409/422 con su `detail`).
    - Chequeos de regresión: endpoints protegidos siguen exigiendo auth; contratos viejos
      intactos.
    - **Resultados reales observados** en el servidor origen (fecha, valores, nº de
      workers), como línea base de comparación para el gemelo.
11. **Notas**: compatibilidad, comportamiento preexistente, limitaciones conocidas,
    pendientes explícitos (marcados "PENDIENTE"), y rollback preciso.

## Después de escribir el doc
1. **Actualizar `cambios_replicacion/INSTRUCCIONES.md`**:
   - Fila nueva/actualizada en la tabla índice: `#` secuencial, esquema/módulo, cambio,
     enlace al doc, migración exacta, **estado con rama y hash(es)** (y "pushed"/"sin
     commitear").
   - Reflejar pendientes fuera del paquete (cambios locales sin versionar).
2. **Alinear artefactos**: espejos de migración idénticos (`diff -q`), scripts necesarios
   versionados; nunca dejar un artefacto referenciado sin existir.
3. Al commitear (solo si el usuario lo pide o para alinear el paquete): commit por tema,
   mensaje que menciona migración+endpoints; **no mezclar cambios ajenos**; listar qué va
   en cada commit.

## Reglas
- **Nombres exactos siempre**: rutas de archivos, endpoints completos, `esquema.vista`,
  columnas, variables de entorno, unidades systemd. El gemelo se configura copiando y
  pegando este documento.
- **No inventar**: todo sale de archivos, diffs, `\d`, `openapi.json`, `curl` y logs
  reales. Marcar lo no verificado como "no verificado".
- **Registrar también lo que NO se hace** (decisiones tipo "EDAN/RIDA sin cambios", "sin
  migración nueva porque v2.61.0 ya existe") para evitar duplicados en el gemelo.
- **Errores y correcciones del proceso** se anotan (p. ej. "el commit X documentó Y pero
  no incluyó el archivo Z; corregido en W") para que el gemelo valide contra el estado
  final.
- **Exhaustividad de escritura/lectura**: cubrir TODOS los endpoints y vistas afectados,
  no solo el principal; incluir lecturas derivadas (origen, campos calculados).
- **Dump/posterior**: tras cambios de BD relevantes, regenerar
  `despliegue/dump/` con `generar_dump.sh` y decirlo en el doc (es el paquete que viaja).
- **Commits**: nunca commitear salvo pedido del usuario; al hacerlo, ramas/commits claros.
