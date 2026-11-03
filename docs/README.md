# Documentación SINAGERSAT — Sistema RIDA

> **Versión de la API:** 1.4.0 (`api/main.py:99`) · **Rama:** `v1.4.0` · **Última migración:** `v2.35.0` · **Revisión:** octubre 2026

Índice maestro de la documentación técnica y funcional del sistema. Todo lo aquí recogido ha sido **verificado contra el código del repositorio y contra la base de datos viva** (esquemas `rida`, `edan`, `usuarios`, `shared`, `sinb`, `repositorio`).

---

## 1. Documentación del sistema

| Documento | Contenido |
|---|---|
| [01-componentes-y-arquitectura.md](01-componentes-y-arquitectura.md) | Qué compone el sistema: backend, base de datos, frontends externos, infraestructura, scripts y módulos de la API |
| [02-autenticacion-y-roles.md](02-autenticacion-y-roles.md) | JWT, tablas de usuarios/permisos, los 11 roles activos, alcance geográfico y mecanismos de autorización |
| [03-offline-y-sincronizacion.md](03-offline-y-sincronizacion.md) | Modo offline: identificadores locales, endpoints de sincronización, resolución de conflictos y tombstones |
| [04-indicadores-y-reportes.md](04-indicadores-y-reportes.md) | Catálogo de indicadores y reportes disponibles hoy (JSON agregados, GeoJSON) y su estado |

## 2. Documentación RIDA específica

| Documento | Contenido |
|---|---|
| [../Documentacion-Base-Datos-RIDA.md](../Documentacion-Base-Datos-RIDA.md) | **Esquema real** de `rida.*`: 35 tablas, relaciones, estados y catálogos |
| [../Arquitectura_RIDA.md](../Arquitectura_RIDA.md) | Arquitectura: propuesta original frente a lo implementado |

## 3. Manual interactivo

Suite navegable de uso por rol y proceso: **[manual/README.md](manual/README.md)**

```
manual/
├── README.md                 Portal y ruta de lectura recomendada
├── 01-acceso-y-roles.md      Inicio de sesión, permisos, qué ve cada rol
├── 02-empadronamiento.md     Formularios, familias, integrantes, ubicaciones
├── 03-eventos.md             Habilitar, cerrar y anular eventos RIDA
├── 04-necesidades.md         Necesidades humanitarias y rehabilitación
├── 05-solicitudes-workflow.md Flujo de las 17 etapas y aprobaciones
├── 06-indicadores.md         Consultas e indicadores
├── 07-reportes.md            Reportes disponibles y cómo obtenerlos
├── 08-offline-y-sincronizacion.md  Trabajo sin conexión y sincronización
├── 09-administracion.md      Usuarios, roles, permisos y auditoría
└── 10-faq-y-problemas.md     Síntomas, causas y solución
```

## 4. Informe de entrega

| Documento | Contenido |
|---|---|
| [INFORME_ENTREGA.md](INFORME_ENTREGA.md) | Informe formal de entrega: alcance, cumplimiento, verificación y pendientes |

---

## 5. Otros documentos del repositorio

| Archivo | Estado |
|---|---|
| `README.md` | Guía de instalación y despliegue de la API. **Contiene enlaces a `docs/` que ya no existen** (ver [INFORME_ENTREGA.md](INFORME_ENTREGA.md) § pendientes) |
| `DOCUMENTACION_SINB.md` | Documentación técnica del módulo SINB (15 capítulos) |
| `Documentacion-Base-Datos-RIDA.md` | Esquema de datos RIDA (actualizado en esta revisión) |
| `Arquitectura_RIDA.md` | Arquitectura RIDA: propuesta y estado real (actualizado en esta revisión) |
| `propuesta/` | 20 documentos de propuesta de mejora del SINB (diseño, no implementación) |
| `docs/pronostico_digital_16_dias.md` | Implementación del pronóstico digital a 16 días |
| `INFORME_PROXY_VALIDACION_AGETIC.md` | Proxy de validación de firma digital AGETIC |

---

## 6. Cifras verificadas (octubre 2026)

| Métrica | Valor | Fuente |
|---|---|---|
| Rutas OpenAPI v1 | 125 rutas / 189 operaciones | `GET /openapi.v1.json` |
| Rutas OpenAPI v2 | 268 rutas / 423 operaciones | `GET /openapi.v2.json` |
| **Total** | **393 rutas / 612 operaciones** | suma de ambas versiones |
| Endpoints RIDA (prefijo `/rida` + ayuda humanitaria + repositorio) | 85 rutas / 124 operaciones | `GET /openapi.v2.json` |
| Grupos (tags) Swagger v2 | 77 | `GET /openapi.v2.json` |
| Esquemas PostgreSQL | `edan` (24), `rea` (4), `repositorio` (2), `rida` (35), `shared` (7), `sinb` (36), `usuarios` (7) | `information_schema.tables` |
| Migraciones | `database/migration_v*.sql` (v1.2.0–v2.8.0) + `database/migrations/` (v2.9.0–v2.35.0) | sistema de ficheros |
| Roles activos | 11 (ids 1–9, 12, 13) | `usuarios.rol` |
| Municipios / departamentos / provincias | 343 / 9 / 113 | `shared.*` |

---

## 7. Convenciones de esta documentación

- Las referencias `archivo:línea` apuntan al código fuente real y se han comprobado en la revisión.
- Todo lo que se describe como **"propuesta"** está en `propuesta/` o en las secciones marcadas y **no está implementado**.
- Los datos de ejemplo provienen de la base de datos de desarrollo; no reproduzca credenciales en producción.
- Esta documentación se **complementa progresivamente** durante el desarrollo: al añadir funcionalidad, actualizar el documento correspondiente y esta tabla.
