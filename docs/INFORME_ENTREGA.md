# Informe de entrega — Sistema RIDA (SINAGERSAT)

**Proyecto:** SINAGERSAT · Sistema Nacional de Alerta Temprana y Gestión de Riesgos
**Alcance de la entrega:** revisión, actualización y documentación del sistema RIDA
**Fecha de emisión:** 5 de octubre de 2026
**Versión del software documentado:** API 1.4.0 (rama `v1.4.0`) · Esquema de BD hasta `v2.35.0`
**Estado:** listo para revisión y aprobación

---

## 1. Objeto del informe

Dejar constancia formal de:

1. Los **componentes y funcionalidades** del sistema RIDA revisados y documentados.
2. La **correspondencia entre lo documentado y el código/base de datos reales**.
3. El **estado de cumplimiento** de cada requisito de la entrega.
4. Los **pendientes conocidos**, con su responsable y alcance.

## 2. Alcance de la entrega

### 2.1 Incluido

| # | Elemento | Resultado |
|---|---|---|
| 1 | Documentación inicial de funcionalidades y componentes hallados en el repositorio | `docs/01`–`docs/04` + índice |
| 2 | Actualización de la documentación obsoleta de RIDA | `Documentacion-Base-Datos-RIDA.md` y `Arquitectura_RIDA.md` reescritos |
| 3 | Manual interactivo | `docs/manual/` (11 capítulos) |
| 4 | Informe de entrega | El presente documento |

### 2.2 Fuera de alcance de esta entrega (decisión adoptada)

| Elemento | Estado | Registro |
|---|---|---|
| Endpoint de indicadores KPI de RIDA | No implementado | §6, pendiente P-1 |
| Generación automática de 3 reportes (Excel/PDF) | No implementada | §6, pendiente P-2 |
| Corrección de hallazgos de seguridad | No realizada | §6, pendiente P-3 |
| Corrección de enlaces rotos del `README.md` raíz | No realizada | §6, pendiente P-4 |
| Verificación automatizada (tests/lint/CI) | No existe infraestructura en el repo | §6, pendiente P-5 |

## 3. Componentes del sistema documentados

| Componente | Ubicación | Documentación |
|---|---|---|
| API REST FastAPI v1.4.0 (393 rutas / 612 operaciones) | `api/` | [docs/01](01-componentes-y-arquitectura.md) |
| Módulo RIDA (85 rutas / 124 operaciones) | `api/rida/`, `api/repositorio/` | [docs/01 §2.2](01-componentes-y-arquitectura.md) |
| Base de datos PostgreSQL/PostGIS (8 esquemas, 118 tablas) | `database/` | [Documentacion-Base-Datos-RIDA.md](../Documentacion-Base-Datos-RIDA.md) |
| Autenticación JWT y RBAC (11 roles) | `api/auth/` | [docs/02](02-autenticacion-y-roles.md) |
| Sincronización offline (EDAN, RIDA, SINB) | `api/edan/`, `api/rida/` | [docs/03](03-offline-y-sincronizacion.md) |
| Indicadores y reportes existentes | `api/edan/`, `api/sinb/`, `api/shared/` | [docs/04](04-indicadores-y-reportes.md) |
| Despliegue e infraestructura | `deploy/`, `scripts/` | [docs/01 §2.4](01-componentes-y-arquitectura.md) |
| Frontend web y app móvil | **Externos** al repositorio | [docs/01 §3](01-componentes-y-arquitectura.md) |

## 4. Artefactos entregados

### 4.1 Documentación del sistema (`docs/`)

| Fichero | Líneas aprox. | Contenido |
|---|---|---|
| `docs/README.md` | 87 | Índice maestro, cifras verificadas, convenciones |
| `docs/01-componentes-y-arquitectura.md` | 170 | Arquitectura, módulos, BD, infra, clientes externos |
| `docs/02-autenticacion-y-roles.md` | 173 | JWT, tablas de permisos, 11 roles, alcance geográfico, auditoría, hallazgos de seguridad |
| `docs/03-offline-y-sincronizacion.md` | 155 | Identificadores offline, endpoints de sync, LWW, tombstones, conflictos |
| `docs/04-indicadores-y-reportes.md` | 121 | Catálogo completo de indicadores y reportes existentes |

### 4.2 Documentación RIDA (raíz, actualizada)

| Fichero | Antes | Ahora |
|---|---|---|
| `Documentacion-Base-Datos-RIDA.md` | 815 líneas describiendo **esquema legado inexistente** (24 tablas `evento`, `formulariorida`, `atencionevento`…) | Esquema **real**: 35 tablas `rida.*`, ER, columnas, índices offline, workflow de 17 etapas, migraciones v2.17.0–v2.35.0 |
| `Arquitectura_RIDA.md` | 301 líneas de propuesta sin contraste con la realidad | Parte A (propuesta original conservada) + **Parte B: estado implementado**, mapeo propuesta→realidad, 9 decisiones divergentes, 8 brechas y estado de las 6 fases |

### 4.3 Manual interactivo (`docs/manual/`)

| Capítulo | Cubre |
|---|---|
| `README.md` | Portal: rutas por perfil y por tarea, los 5 pasos del sistema |
| `01-acceso-y-roles.md` | Login, token, vigencia por rol, qué puede cada rol, alcance geográfico |
| `02-empadronamiento.md` | Formularios → familias → integrantes → ubicaciones, con payloads y errores |
| `03-eventos.md` | Habilitar/cerrar/anular eventos RIDA, ciclo de vida |
| `04-necesidades.md` | Necesidades, catálogos de ayuda y rehabilitación, sync |
| `05-solicitudes-workflow.md` | 4 modalidades, 17 etapas, 5 niveles de aprobación, requisitos e instancias |
| `06-indicadores.md` | Consulta de indicadores por dominio |
| `07-reportes.md` | Reportes disponibles hoy y estado del pendiente de exportación |
| `08-offline-y-sincronizacion.md` | Guía de campo: pull/push, orden de lote, conflictos, buenas prácticas |
| `09-administracion.md` | Usuarios, roles, matriz de permisos, sesiones, auditoría |
| `10-faq-y-problemas.md` | Formatos de error y 40 síntomas con solución |

### 4.4 Informe de entrega

`docs/INFORME_ENTREGA.md` — este documento.

## 5. Verificación realizada

### 5.1 Método

Revisión **solo lectura** del repositorio y consulta directa a la base de datos de desarrollo y a la API en ejecución (`http://localhost:8000`), sin modificar código ni datos.

### 5.2 Evidencias

| Verificación | Resultado | Fuente |
|---|---|---|
| Conteo de rutas OpenAPI v1 | **125 rutas / 189 operaciones** | `GET /openapi.v1.json` |
| Conteo de rutas OpenAPI v2 | **268 rutas / 423 operaciones** | `GET /openapi.v2.json` |
| Endpoints del prefijo `/rida` | **85 rutas / 124 operaciones** | `GET /openapi.v2.json` |
| Grupos (tags) Swagger v2 | **77** | `GET /openapi.v2.json` |
| Tablas del esquema `rida` | **35** | `information_schema.tables` |
| Tablas por esquema | edan 24 · rea 4 · repositorio 2 · rida 35 · shared 7 · sinb 36 · usuarios 7 · public 3 | `information_schema.tables` |
| Roles activos | **11** (ids 1–9, 12, 13) | `SELECT * FROM usuarios.rol` |
| Permisos por rol | Matriz completa leída y documentada | `usuarios.permiso` ⋈ `aplicacion` ⋈ `accion` |
| Catálogo de etapas | **17 etapas** con orden coherente con `TRANSICIONES` del código | `rida.cat_etapa_solicitud` vs `api/rida/solicitudes/service.py:279` |
| Modalidades | 4 activas | `rida.cat_modalidad` |
| Categorías de ayuda | 7 activas + 5 inactivas (v2.35.0) | `rida.cat_categoria_ayuda` |
| Geografía base | 9 departamentos, 113 provincias, 343 municipios | `shared.*` |
| Estado del servicio | `{"status":"ok"}` | `GET /health` |
| Correspondencia código ↔ documentación | Referencias `archivo:línea` comprobadas una a una | Revisión manual |

### 5.3 Hallazgos durante la verificación

1. `cat_estado_evento` contiene un registro residual `HABILITAR` junto a `HABILITADO`.
2. Las columnas `id_familia_off`, `id_integrante_off`, `id_ubicacion_off` **no tienen índice** pese a usarse como clave de upsert.
3. El endpoint `/debug/routes` devuelve un conteo (34) que no corresponde a las rutas realmente montadas; la fuente fiable es `/openapi.v*.json`.
4. `rea` es un esquema con 4 tablas sin router en la API; las rutas de auditoría mapeadas a `/rea/` en `api/audit.py:4,12` nunca se disparan.

## 6. Cumplimiento de requisitos

| # | Requisito | Estado | Evidencia / motivo |
|---|---|---|---|
| R1 | Documentación inicial sobre funcionalidades y componentes del repositorio | ✅ **Cumplido** | `docs/01`–`docs/04` + `docs/README.md` |
| R2 | Considerar el **sistema web y móvil** | ✅ **Cumplido (documentación)** | `docs/01 §3`: la web (`sat.climbat.net`) y la app Flutter son componentes **externos**; se documenta su relación y el contrato API que consumen. No hay código de frontend en el repositorio |
| R3 | **Funcionamiento offline con sincronización** | ✅ **Cumplido (documentación)** | `docs/03` + `docs/manual/08`: identificadores offline, 8 endpoints de sync, resolución de conflictos LWW/tombstones, guía de campo |
| R4 | **Autenticación y roles** | ✅ **Cumplido (documentación)** | `docs/02` + `docs/manual/01`: JWT HS256, 11 roles, matriz de permisos, 4 mecanismos de autorización, alcance geográfico, auditoría |
| R5 | **Consultas de indicadores** | ⚠️ **Parcial** | Se documentan los indicadores existentes (`docs/04`, `docs/manual/06`). El endpoint agregado `GET /api/v2/rida/indicadores` **no se implementó** → **P-1** |
| R6 | **Generación automática de al menos 3 reportes** | ❌ **No cumplido** | No existe generación de ficheros (PDF/Excel) ni publicación automática; solo reportes agregados en JSON → **P-2** |
| R7 | **Manual interactivo** | ✅ **Cumplido** | `docs/manual/` con 11 capítulos, checklists, flujos Mermaid, ejemplos ejecutables y autoevaluaciones |
| R8 | **Informe de entrega aprobado** | ✅ **Presentado** | Este documento, pendiente de firma (§8) |
| R9 | Documentación complementada progresivamente durante el desarrollo | ✅ **Proceso establecido** | `docs/README.md §7` define la convención de actualización incremental |

**Resumen:** 6 cumplidos · 1 parcial · 1 no cumplido · 1 presentado a firma.

## 7. Pendientes registrados

| ID | Pendiente | Prioridad | Responsable sugerido | Esfuerzo estimado |
|---|---|---|---|---|
| **P-1** | `GET /api/v2/rida/indicadores` — KPIs agregados de RIDA | Alta | Backend | Bajo |
| **P-2** | Generación de **3 reportes** descargables (empadronamiento, necesidades, eventos) en Excel + PDF, con `format=xlsx\|pdf` y publicación opcional por cron | **Alta (requisito contractual)** | Backend | Medio (dependencia nueva: `fpdf2`; `openpyxl` ya disponible) |
| **P-3** | Hallazgos de seguridad: `POST /auth/cambiar-contrasena` sin token; CORS `*` con credenciales; `JWT_SECRET` por defecto; sin rate limiting; escritura de catálogos abierta en v2 | **Alta** | Backend + infra | Bajo–medio |
| **P-4** | README raíz: ~30 enlaces rotos a `docs/*` eliminados en `de381c6`; migraciones listadas solo hasta v2.28.0 | Media | Documentación | Bajo |
| **P-5** | Sin suite de tests, linter ni CI (`.github/workflows` solo dispara un agente) | Media | Backend | Medio |
| **P-6** | Trabajo sin commitear en el árbol de trabajo: migraciones `v2.29.0`–`v2.35.0`, `api/rida/solicitudes/`, `DOCUMENTACION_SINB.md`, `SINB/sinb_20260714.sql` | **Alta (riesgo de pérdida)** | Equipo | Bajo |
| **P-7** | 35 documentos técnicos eliminados en `de381c6` (incluido `INFORME_ENTREGA_4_2.md`) sin sustituto íntegro; recuperables con `git show de381c6^:docs/<fichero>.md` | Media | Documentación | Variable |
| **P-8** | API logística de RIDA ausente: `comando_incidente`, `requerimiento_umee`, `proforma`, `contratacion`, `proyecto`, `entrega*` existen en BD sin endpoints (etapas 10–17 no operables por API) | Media | Backend | Alto |
| **P-9** | Índices offline ausentes: `id_familia_off`, `id_integrante_off`, `id_ubicacion_off` | Media | Backend/BD | Bajo |
| **P-10** | Registro residual `HABILITAR` en `rida.cat_estado_evento` | Baja | BD | Bajo |
| **P-11** | Sin `CHANGELOG.md`, `LICENSE`, `CONTRIBUTING.md` ni `AGENTS.md` | Baja | Documentación | Bajo |

## 8. Criterios de aceptación propuestos

Para aprobar esta entrega, el área receptora debe verificar:

- [ ] **CA-1** — `docs/README.md` refleja correctamente el índice de la documentación y todos sus enlaces funcionan.
- [ ] **CA-2** — `Documentacion-Base-Datos-RIDA.md` describe el esquema vigente: el revisor puede contrastar ≥3 tablas contra la BD (`psql` o DBeaver) sin discrepancias.
- [ ] **CA-3** — `Arquitectura_RIDA.md` distingue con claridad propuesta (Parte A) y estado real (Parte B).
- [ ] **CA-4** — El manual permite a un usuario de rol 6 o 7 completar el circuito **habilitar evento → empadronar → necesidades → solicitud → aprobación** sin asistencia, usando solo `docs/manual/`.
- [ ] **CA-5** — Los endpoints citados en la documentación responden en `/docs/v2` (muestra aleatoria de ≥10 endpoints).
- [ ] **CA-6** — Se acepta el estado de los pendientes P-1 a P-11 con las prioridades y responsables indicados en §7, o se ajustan en esta acta.

**Observación sobre R6:** el requisito de generación automática de reportes (P-2) queda expresamente **pendiente de entrega**. Su aceptación como parte de esta entrega exige su implementación previa o la suscripción formal de un plan con fecha.

## 9. Aprobación

| Rol | Nombre | Firma | Fecha |
|---|---|---|---|
| Elaboró (documentación y revisión técnica) | | | |
| Revisó (técnico del proyecto) | | | |
| Aprobó (área receptora) | | | |

---

## Anexo A · Cómo verificar lo entregado

```bash
# 1. Arrancar la API
bash start_api.sh

# 2. Verificar servicio y versionado
curl -s http://localhost:8000/health        # {"status":"ok"}
curl -s http://localhost:8000/ | python3 -m json.tool

# 3. Verificar cifras de la §5.2
curl -s http://localhost:8000/openapi.v2.json -o /tmp/v2.json
python3 -c "import json;d=json.load(open('/tmp/v2.json'));\
print('rutas',len(d['paths']),'ops',sum(len(v) for v in d['paths'].values()))"

# 4. Verificar esquema RIDA en la BD
psql -h 127.0.0.1 -U sinagersat -d db_sinagersat -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='rida';"   # 35

# 5. Verificar el workflow de etapas
psql ... -c "SELECT codigo, orden FROM rida.cat_etapa_solicitud ORDER BY orden;" # 17

# 6. Documentación
ls docs/ docs/manual/
```

## Anexo B · Índice de la documentación entregada

- [docs/README.md](README.md) — índice maestro
- [docs/01-componentes-y-arquitectura.md](01-componentes-y-arquitectura.md)
- [docs/02-autenticacion-y-roles.md](02-autenticacion-y-roles.md)
- [docs/03-offline-y-sincronizacion.md](03-offline-y-sincronizacion.md)
- [docs/04-indicadores-y-reportes.md](04-indicadores-y-reportes.md)
- [docs/manual/README.md](manual/README.md) — manual interactivo (11 capítulos)
- [Documentacion-Base-Datos-RIDA.md](../Documentacion-Base-Datos-RIDA.md)
- [Arquitectura_RIDA.md](../Arquitectura_RIDA.md)
