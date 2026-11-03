# Arquitectura del Sistema RIDA

> **Documento de arquitectura: propuesta original y estado implementado.**
> Revisión: octubre de 2026 · Rama `v1.4.0` · API `1.4.0` · Esquema hasta `v2.35.0`

Este documento tiene dos partes:

- **Parte A** — la propuesta de arquitectura original (insumos, principios, modelo propuesto). Se conserva como referencia del diseño de partida.
- **Parte B** — **estado real implementado**, con el mapeo propuesta → implementación y las brechas abiertas.

> ⚠️ La versión anterior de este fichero contenía únicamente la Parte A, lo que podía leerse como si los 12 esquemas propuestos (`core`, `catalogo`, `evento`, `empadronamiento`, …) estuvieran implementados. **No lo están**: hoy existe **un único esquema `rida`** con 35 tablas.

---

# PARTE A · Propuesta original

## A.1 Insumos de partida

| Insumo | Aporte principal | Implicación para la BD |
|---|---|---|
| **RIDA Guía Rápida** | Eventos adversos, formularios RIDA por localidad/campamento, familias, integrantes, necesidades, atención municipal/departamental y documentación digital | Núcleo operativo: evento → formulario → familia → integrante → necesidad → atención → documento |
| **MD_Empadronamiento_Necesidades_DA** | Módulos de identificación, ubicación, condición de afectación, vulnerabilidades demográficas y necesidades por categoría de ayuda | Amplía el modelo familiar con vulnerabilidades y catálogos de ayuda humanitaria |
| **MD_Rehabilitación_Reconstrucción** | Rehabilitación vs reconstrucción, instrumentos EDAN/FIBE, mesas sectoriales, monitoreo, flujo de 3 instancias | Proyectos, evaluación de daños, infraestructura, indicadores y workflow |
| **Procesos VIDECI.xlsx** | Cuatro rutas (ayuda humanitaria, rehab-recon, rehab-insumos, respuesta inmediata UMEE) con 25 fases homologadas | Motor de workflow configurable: rutas, pasos, instancias y estados |

## A.2 Principios de diseño

1. **Integralidad** — un evento adverso se ramifica en respuesta inmediata, ayuda humanitaria, rehabilitación o reconstrucción.
2. **Modularidad** — esquemas separados por dominio, con catálogos compartidos.
3. **Trazabilidad** — historial de usuario, fecha y estado en cada entidad.
4. **Georreferenciación** — PostGIS para evento, localidad, familia, infraestructura y proyecto.
5. **Multinivel** — municipal, departamental y nacional.
6. **Workflow configurable** — las fases del Excel no se "hardcodean": se modelan como procesos, rutas, fases y pasos.
7. **Interoperabilidad** — APIs hacia SINPAD, GEOSINAGER, SICOES y sistemas sectoriales.
8. **Auditoría y seguridad** — RBAC por rol, entidad territorial y evento.
9. **Escalabilidad** — PostgreSQL + PostGIS, documental externo, APIs REST, analítica separada.

## A.3 Esquemas propuestos (12)

`core` · `catalogo` · `evento` · `empadronamiento` · `necesidad` · `ayuda_humanitaria` · `primera_respuesta` · `rehab_recon` · `workflow` · `documento` · `monitoreo` · `analitica`

## A.4 Modelo propuesto (resumen)

- **`evento.evento_adverso`** 1→N **`evento.formulario_rida`** (una localidad/campamento por formulario) → 1→N **`empadronamiento.familia`** → 1→N **`empadronamiento.integrante_familia`** (enlaza con `persona`).
- **`necesidad.necesidad`** asociable a familia, formulario o evento; con categoría, artículo, cantidad, prioridad, estado y fecha requerida.
- **`ayuda_humanitaria`**: atenciones, detalles de atención, solicitudes y entregas.
- **`primera_respuesta`**: comando de incidentes, requerimiento UMEE y distribución a unidades militares.
- **`rehab_recon`**: proyecto (con `geom`, monto, fuente, criterios de prospectiva/correctiva), evaluación de daño, infraestructura pública, mesa sectorial, indicador y rendición de cuentas.
- **`workflow`**: `proceso` → `ruta` → `fase` (25 homologadas) → `paso_ruta`; expedientes con instancia actual.
  - Instancia 1: Local/Municipal · Instancia 2: Departamental/Regional · Instancia 3: Nacional/Central.
- **`documento`** con hash, **`monitoreo`** (indicadores, avances, alertas) y **`analitica`** (vistas materializadas).

## A.5 Módulos funcionales propuestos

Administración y seguridad · Gestión de eventos · Formularios/empadronamiento · Evaluación de necesidades · Ayuda humanitaria · Primera respuesta UMEE · Rehabilitación y reconstrucción · Workflow y aprobaciones · Documental · Monitoreo · Reportes y analítica · Interoperabilidad.

## A.6 Rutas de proceso VIDECI

| Ruta | Pasos | Workflow propuesto |
|---|---|---|
| Ayuda humanitaria | 21 | `workflow.ruta` ayuda_humanitaria |
| Rehabilitación y reconstrucción | 15 | `workflow.ruta` rehab_recon |
| Rehabilitación-insumos | 13 | `workflow.ruta` rehab_insumos |
| Respuesta inmediata UMEE | 22 | `workflow.ruta` primera_respuesta_umee |

## A.7 Fases de implementación propuestas

1. Núcleo RIDA (evento, formulario, familia, integrante, necesidad, atención, documento)
2. Empadronamiento ampliado con vulnerabilidades
3. Ayuda humanitaria completa y workflow de 3 instancias
4. Primera respuesta UMEE
5. Rehabilitación y reconstrucción (proyectos, EDAN/FIBE, SICOES, pago)
6. Monitoreo, analítica e interoperabilidad

---

# PARTE B · Estado implementado (octubre 2026)

## B.1 Arquitectura real

```
Clientes externos (web institucional, app móvil Flutter, Swagger)
        │  Bearer JWT
        ▼
FastAPI api/main.py  ──  /api/v1 (125 rutas)  ·  /api/v2 (268 rutas)
        │  módulos: auth · shared · usuarios · upload · repositorio
        │           edan · firma_digital · rida · sinb · ndvi
        ▼
PostgreSQL 16 + PostGIS
  shared · usuarios · edan · rida(35) · sinb · repositorio · rea
```

Detalle en [docs/01-componentes-y-arquitectura.md](docs/01-componentes-y-arquitectura.md) y [Documentacion-Base-Datos-RIDA.md](Documentacion-Base-Datos-RIDA.md).

## B.2 Mapeo: propuesto → implementado

| Bloque propuesto (Parte A) | Implementado hoy | Estado |
|---|---|---|
| `core` (usuarios, roles, auditoría) | Esquema **`usuarios`**: `usuario`, `rol`, `aplicacion`, `accion`, `permiso`, `sesion`, `auditoria`; JWT + RBAC | ✅ Implementado (esquema propio, no `core`) |
| `catalogo` (catálogos) | `rida.cat_*` (17 tablas) + `shared.*` (geografía, cultivos, pecuario) + `edan.*_catalogo` | ✅ Implementado |
| `evento.evento_adverso` | **`edan.edan`** (el EDAN es el evento adverso) | ✅ Implementado en esquema `edan` |
| `evento.formulario_rida` | **`rida.formulario_rida`** (1:1 con `edan.edan_localidades`, `id_evento_rida` como FK) | ✅ Implementado |
| `evento` como padre de RIDA | **`rida.evento_rida`** (v2.24.0): 1:1 con `edan.edan`, estados HABILITADO/CERRADO/anulado | ✅ Implementado (posterior a la propuesta) |
| `empadronamiento.familia` | **`rida.familia`** (simplificada en v2.19.0) | ✅ Implementado (columnas reducidas) |
| `empadronamiento.integrante_familia` + `persona` | **`rida.integrante`** (persona y vínculo en una sola tabla; sin `persona` separada) | ⚠️ Simplificado |
| `empadronamiento.persona` (entidad independiente) | **No existe**: la unicidad se garantiza con `idx_integrante_unico_persona` | ❌ No implementado |
| `necesidad.necesidad` | **`rida.necesidad`** (familia o formulario, categoría, artículo, prioridad) | ✅ Implementado |
| `ayuda_humanitaria.atencion` / `atencion_detalle` | Parcial: **`rida.entrega` + `entrega_detalle` + `entrega_beneficiario`** | ⚠️ Parcial (tablas creadas, API sin exponer) |
| `ayuda_humanitaria.solicitud_ayuda` | **`rida.solicitud`** con `cat_modalidad` (4 rutas) | ✅ Implementado |
| `ayuda_humanitaria.entrega_ayuda` | **`rida.entrega_beneficiario`** (incluye `firma_digital`) | ⚠️ Tabla creada, API sin exponer |
| `primera_respuesta.comando_incidentes` | **`rida.comando_incidente`** | ⚠️ Tabla creada, API sin exponer |
| `primera_respuesta.requerimiento_umee` | **`rida.requerimiento_umee`** | ⚠️ Tabla creada, API sin exponer |
| `primera_respuesta.distribucion_umee` | **`rida.entrega`** con `id_unidad_militar` | ⚠️ Tabla creada, API sin exponer |
| `rehab_recon.proyecto` | **`rida.proyecto`** (con `geom`, montos, criterios prospectiva/correctiva) | ⚠️ Tabla creada, API sin exponer |
| `rehab_recon.evaluacion_dano` | **`edan.edan` + 14 sub-tablas de secciones** | ✅ Implementado en `edan` |
| `rehab_recon.infraestructura_publica` | `edan.edan_localidades_danos_infra_publica`, `..._unidades_educativas`, `..._servicios_basicos` | ✅ Implementado en `edan` |
| `rehab_recon.mesa_sectorial` | No existe | ❌ No implementado |
| `rehab_recon.indicador` / `rendicion_cuenta` | No existen | ❌ No implementado |
| `workflow.proceso/ruta/fase/paso_ruta` genérico | **Sustituido** por `rida.cat_etapa_solicitud` (17 etapas) + `TRANSICIONES` en código + `cat_requisito` (3 instancias) (v2.34.0) | ⚠️ Implementado de forma **fija**, no configurable por datos |
| `workflow.expediente` / `expediente_paso` | **`rida.solicitud`** + **`rida.bitacora`** | ✅ Implementado |
| `documento.documento` | **`repositorio.documentos`** + `rida.solicitud_documento` (v2.22.0) | ✅ Implementado |
| `monitoreo.indicador/avance/alerta` | No existen como tablas; hay endpoints agregados (ver [docs/04-indicadores-y-reportes.md](docs/04-indicadores-y-reportes.md)) | ❌ Parcial |
| `analitica` (vistas materializadas, cubos) | Solo vistas puntuales en `sinb` (`vw_alertas_ndvi`) | ❌ No implementado |
| Interoperabilidad (SINPAD, SICOES…) | Solo proxy de firma AGETIC | ❌ No implementado |
| Frontend web responsive + app móvil + panel GIS | **Fuera de este repositorio** (web `sat.climbat.net`, app Flutter) | ⚠️ Externo |

**Leyenda:** ✅ implementado · ⚠️ parcial o simplificado · ❌ no implementado

## B.3 Decisiones de arquitectura adoptadas (diferentes de la propuesta)

| Decisión | Propuesta A | Implementado B |
|---|---|---|
| Esquemas | 12 esquemas lógicos | **1 esquema `rida`** + reutilización de `edan`, `shared`, `usuarios`, `repositorio` |
| Backend | Java Spring / .NET / NestJS | **Python + FastAPI** |
| ORM / migraciones | — | **SQL crudo** con SQLAlchemy Core; migraciones SQL planas (sin Alembic) |
| Workflow | Motor configurable (procesos/rutas/fases en BD) | **Matriz de transiciones en código** (`api/rida/solicitudes/service.py:279`) + catálogo de etapas |
| Autenticación | Keycloak / OAuth2 | **JWT HS256 propio** con tabla de sesiones |
| Documental | MinIO/S3 con hash | **Disco local** `uploads/` + `repositorio.documentos` (hash al subir) |
| Colas / ETL | RabbitMQ/Kafka | **Ninguna**; todo síncrono |
| Analítica | Metabase/Superset | **No**; endpoints JSON |
| Frontend | React/Vue con MapLibre | **No en este repo** (externo) |
| Contenedores / CI-CD | Docker/Kubernetes + pipeline | **Sin Docker ni CI** (solo scripts bash y systemd) |

## B.4 Brechas abiertas

Priorizadas por impacto funcional:

1. **API logística ausente** — `comando_incidente`, `requerimiento_umee`, `proforma`, `contratacion`, `proyecto`, `entrega*` están en BD sin endpoints. Sin esto, las etapas 10–17 del workflow (EN_SUMINISTROS → ENTREGADA) no se pueden operar por API.
2. **Workflow no configurable** — las 25 fases homologadas de VIDECI se sustituyeron por 17 etapas fijas; no hay tabla de rutas/pasos.
3. **Sin reportes descargables** — no hay exportación a Excel/PDF ni generación automática (ver [docs/04-indicadores-y-reportes.md](docs/04-indicadores-y-reportes.md)).
4. **Sin endpoint de indicadores RIDA** — no hay KPIs agregados del dominio.
5. **Monitoreo y analítica** — no existen tablas de indicadores de proyecto ni vistas materializadas.
6. **Interoperabilidad** — sin conectores hacia SICOES/SINPAD más allá del proxy AGETIC.
7. **Índices offline incompletos** — `id_familia_off`, `id_integrante_off`, `id_ubicacion_off` sin índice (ver [Documentacion-Base-Datos-RIDA.md](Documentacion-Base-Datos-RIDA.md) §9).
8. **Frontend** — fuera del alcance de este repositorio; la propuesta `propuesta/06-FRONTEND.md` no está implementada aquí.

## B.5 Fases de la propuesta: estado

| Fase propuesta | Estado |
|---|---|
| 1. Núcleo RIDA | ✅ Completa |
| 2. Empadronamiento ampliado | ✅ Completa (v2.18.0–v2.21.0) |
| 3. Ayuda humanitaria + workflow 3 instancias | ⚠️ Workflow implementado (v2.34.0); logística sin API |
| 4. Primera respuesta UMEE | ⚠️ Tablas creadas, sin API |
| 5. Rehabilitación y reconstrucción | ⚠️ Catálogos (v2.35.0) y `proyecto` en BD; sin API |
| 6. Monitoreo, analítica e interoperabilidad | ❌ No iniciada |

---

## Referencias

- Esquema de datos: [Documentacion-Base-Datos-RIDA.md](Documentacion-Base-Datos-RIDA.md)
- Componentes: [docs/01-componentes-y-arquitectura.md](docs/01-componentes-y-arquitectura.md)
- Roles y permisos: [docs/02-autenticacion-y-roles.md](docs/02-autenticacion-y-roles.md)
- Offline: [docs/03-offline-y-sincronizacion.md](docs/03-offline-y-sincronizacion.md)
- Manual: [docs/manual/README.md](docs/manual/README.md)
- Informe de entrega: [docs/INFORME_ENTREGA.md](docs/INFORME_ENTREGA.md)
