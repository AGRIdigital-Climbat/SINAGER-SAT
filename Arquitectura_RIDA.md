## Propuesta de arquitectura de base de datos para el Sistema RIDA Integral (VIDECI)

### 1. Lectura de los insumos disponibles

Los documentos analizados permiten identificar cuatro bloques que deben converger en una plataforma única:

| Insumo | Aporte principal | Implicación para la BD |
|---|---|---|
| **RIDA Guía Rápida** | RIDA nace para registrar eventos adversos, formularios RIDA por localidad/campamento, familias, integrantes, necesidades, atención municipal/departamental y documentación digital. | Núcleo operativo actual: evento → formulario RIDA → familia → integrante → necesidad → atención → documento. |
| **MD_Empadronamiento_Necesidades_DA** | Define módulos de identificación, ubicación, condición de afectación, vulnerabilidades demográficas y necesidades específicas por categoría de ayuda. | Amplía el modelo familiar con variables de vulnerabilidad y catálogos de ayuda humanitaria. |
| **MD_Rehabilitación_Reconstrucción** | Diferencia rehabilitación y reconstrucción, instrumentos EDAN/FIBE, mesas sectoriales, inventarios de infraestructura, monitoreo, rendición de cuentas y flujo de 3 instancias. | Requiere módulos de proyectos, evaluación de daños, infraestructura, indicadores y workflow de aprobación. |
| **Procesos VIDECI.xlsx** | Compara cuatro rutas: ayuda humanitaria, rehabilitación y reconstrucción, rehabilitación-insumos y respuesta inmediata UMEE, con 25 fases homologadas. | Obliga a un motor de workflow configurable, con rutas, pasos, instancias y estados. |

La evolución deseada es pasar de un RIDA centrado en ayuda humanitaria a un **RIDA Integral** que cubra: primera respuesta, ayuda humanitaria, rehabilitación y reconstrucción.

---

### 2. Principios de diseño

1. **Integralidad:** un solo evento adverso debe poder ramificarse hacia respuesta inmediata, ayuda humanitaria, rehabilitación o reconstrucción.
2. **Modularidad:** esquemas separados por dominio funcional, con catálogos compartidos.
3. **Trazabilidad:** cada familia, necesidad, atención, proyecto y documento debe tener historial de usuario, fecha y estado.
4. **Georreferenciación:** uso de PostGIS para evento, localidad/campamento, familia, infraestructura y proyecto.
5. **Multinivel:** datos asociados a nivel municipal, departamental y nacional.
6. **Workflow configurable:** las rutas y fases del Excel no deben quedar “hardcodeadas”, sino modeladas como procesos, rutas, fases y pasos.
7. **Interoperabilidad:** APIs para SINPAD, SINAGER-SAT/GEOSINAGER, SICOES, sistemas sectoriales y visores geográficos.
8. **Auditoría y seguridad:** RBAC por rol, entidad territorial y evento; bitácora de cambios.
9. **Escalabilidad tecnológica:** PostgreSQL + PostGIS, almacenamiento documental S3/MinIO, APIs REST, analítica separada.

---

### 3. Arquitectura por capas y esquemas propuestos

**Capas:**

- Presentación: web responsive, app móvil para campo, panel GIS.
- API/Servicios: REST/GraphQL, autenticación OAuth2/JWT, workflow, reglas de negocio.
- Datos: PostgreSQL/PostGIS, catálogos, documental, analítica, integraciones.
- Integración: ETL/ELT, colas, conectores con sistemas externos.

**Esquemas de base de datos sugeridos:**

| Esquema | Contenido |
|---|---|
| `core` | Usuarios, roles, instituciones, entidades territoriales, auditoría. |
| `catalogo` | Tipos de evento, categorías de ayuda, artículos, parentescos, discapacidades, enfermedades, sectores, fases, instancias. |
| `evento` | Evento adverso, formulario RIDA, localidad/campamento, documentos del evento. |
| `empadronamiento` | Familia, persona, integrante familiar, vulnerabilidades. |
| `necesidad` | Necesidades por familia, formulario, evento o proyecto. |
| `ayuda_humanitaria` | Solicitudes, atenciones municipales/departamentales, entregas, distribuciones. |
| `primera_respuesta` | Comando de incidentes, requerimientos UMEE, distribución a unidades militares. |
| `rehab_recon` | Proyectos, evaluación de daños, infraestructura pública, mesas sectoriales, indicadores, rendición de cuentas. |
| `workflow` | Procesos, rutas, fases, pasos, expedientes, instancias de aprobación. |
| `documento` | Metadatos documentales y enlaces a almacenamiento externo. |
| `monitoreo` | Indicadores, avances, alertas, seguimiento. |
| `analitica` | Vistas materializadas, cubos, reportes agregados. |

---

### 4. Modelo lógico propuesto

#### 4.1 `core` y `catalogo`

**`core.usuario`**: `id`, `nombres`, `apellidos`, `email`, `username`, `password_hash`, `activo`, `institucion_id`.
**`core.rol`**: `id`, `codigo`, `nombre` (Técnico UGR, Responsable departamental, VIDECI nacional, DGEA, DGPR, UMEE, Administrador).
**`core.institucion`**: `id`, `nombre`, `nivel` (municipal, departamental, nacional), `entidad_territorial_id`.
**`core.entidad_territorial`**: `id`, `tipo` (departamento, municipio, localidad), `nombre`, `padre_id`, `geom`.
**`core.auditoria`**: `id`, `entidad`, `entidad_id`, `accion`, `usuario_id`, `fecha`, `datos_antes`, `datos_despues`.

**Catálogos clave:**

- `catalogo.tipo_evento`: inundación, sequía, incendio, deslizamiento, etc.
- `catalogo.categoria_ayuda`: Techo/Abrigo/Enseres, Alimentación/Agua, Salud/Higiene, Medios de Vida.
- `catalogo.articulo`: harina, carpa, frazada, kit higiene, pañales, etc. Campos: `categoria_id`, `unidad_medida`, `peso_unitario`, `costo_referencia`.
- `catalogo.parentesco`: jefe/a de hogar, cónyuge, hijo(a), otro.
- `catalogo.tipo_discapacidad`: física, sensorial, intelectual, ninguna.
- `catalogo.enfermedad_cronica`: diabetes, hipertensión, VIH, diálisis, etc.
- `catalogo.sector`: salud, educación, vivienda, infraestructura, medios de vida.
- `catalogo.fase_homologada`: activación, organización operativa, clasificación, evaluación y evidencias, etc.
- `catalogo.instancia_aprobacion`: local/municipal, departamental/regional, nacional.

#### 4.2 `evento`

**`evento.evento_adverso`**
- `id`, `codigo`, `fecha`, `tipo_evento_id`
- `descripcion`, `departamento_id`, `municipio_id`
- `n_localidades_afectadas`, `n_familias_afectadas`, `n_familias_damnificadas`
- `geom` (Point/Polígono, SRID 4326)
- `estado`, `usuario_reporta_id`, `created_at`

**`evento.formulario_rida`**
- `id`, `evento_id`, `localidad_id`, `nombre_localidad`
- `tipo_asentamiento` (localidad, campamento, albergue)
- `n_carpa`, `lat`, `lon`, `geom`
- `estado`, `fecha_creacion`

> Un evento tiene N formularios RIDA; cada formulario representa una localidad/campamento.

#### 4.3 `empadronamiento`

**`empadronamiento.persona`**
- `id`, `nombres`, `apellidos`, `sexo`, `fecha_nacimiento`
- `numero_cedula`, `ci_complemento`, `telefono`
- `estado`

**`empadronamiento.familia`**
- `id`, `formulario_rida_id`, `codigo_ficha` (FAM-001)
- `jefe_integrante_id`
- `ubicacion_original` (departamento, municipio, barrio/comunidad, dirección)
- `ubicacion_actual` (albergue temporal, casa de acogida, predio dañado, calle)
- `condicion_hogar`: damnificado / afectado
- `tipo_afectacion`, `detalle_perdida`
- `estado`, `created_at`

**`empadronamiento.integrante_familia`**
- `id`, `familia_id`, `persona_id`, `parentesco_id`
- `es_jefe` (boolean)
- `gestante_semanas`, `lactante_meses`
- `tipo_discapacidad_id`, `requiere_movilidad` (silla de ruedas, muletas)
- `enfermedad_cronica_id`, `medicacion_continua`
- `observaciones`

> El rango de edad/etapa de vida se calcula desde `fecha_nacimiento`; no es necesario almacenarlo, pero puede persistirse en vistas o columnas calculadas.

#### 4.4 `necesidad`

**`necesidad.necesidad`**
- `id`, `evento_id`, `formulario_rida_id`, `familia_id`
- `categoria_id`, `articulo_id`
- `cantidad`, `unidad_medida`
- `prioridad`, `estado`
- `justificacion`, `fecha_requerida`, `costo_estimado`

Esta tabla reemplaza el registro simple de “necesidades” del RIDA actual y permite asociar necesidades a familia, localidad o evento.

#### 4.5 `ayuda_humanitaria`

**`ayuda_humanitaria.atencion`**
- `id`, `evento_id`, `nivel` (municipal, departamental, nacional)
- `entidad_id`, `tipo_atencion`, `fecha`, `estado`, `usuario_id`

**`ayuda_humanitaria.atencion_detalle`**
- `id`, `atencion_id`, `categoria_id`, `articulo_id`
- `cantidad`, `peso_kg`, `valor_bs`, `fecha_entrega`
- `beneficiario_familia_id`

**`ayuda_humanitaria.solicitud_ayuda`**
- `id`, `evento_id`, `municipio_id`, `documentacion`, `estado`, `fecha`

**`ayuda_humanitaria.entrega_ayuda`**
- `id`, `solicitud_id`, `familia_id`, `articulo_id`, `cantidad`, `fecha`, `responsable_id`

#### 4.6 `primera_respuesta`

**`primera_respuesta.comando_incidentes`**
- `id`, `evento_id`, `fecha_conformacion`, `responsable_id`, `estado`

**`primera_respuesta.requerimiento_umee`**
- `id`, `evento_id`, `comando_id`, `informe_necesidades`, `prioridad`, `estado`

**`primera_respuesta.distribucion_umee`**
- `id`, `requerimiento_id`, `unidad_militar_id`, `articulo_id`, `cantidad`, `fecha`, `estado`

#### 4.7 `rehab_recon`

**`rehab_recon.proyecto`**
- `id`, `evento_id`, `tipo_proyecto` (rehabilitación, reconstrucción, insumos)
- `sector_id`, `nombre`, `descripcion`, `geom`
- `monto_estimado`, `moneda`, `fuente_financiamiento`
- `estado`, `instancia_actual_id`, `prioridad`
- `incorpora_gestion_riesgo` (boolean), `criterios_prospectiva`, `criterios_correctiva`
- `codigo_sicoes`, `estado_sicoes`, `fecha_cierre_sicoes`

**`rehab_recon.evaluacion_dano`**
- `id`, `evento_id`, `proyecto_id`, `instrumento_id` (EDAN/FIBE, mesa sectorial, inventario)
- `sector_id`, `descripcion`, `cuantificacion`, `perdidas`
- `fuente`, `fecha`, `usuario_id`

**`rehab_recon.infraestructura_publica`**
- `id`, `evento_id`, `tipo_id`, `nombre`, `codigo`
- `geom`, `estado_dano`, `requiere_intervencion`, `prioridad`, `costo_estimado`

**`rehab_recon.mesa_sectorial`**
- `id`, `evento_id`, `sector_id`, `fecha`, `participantes`, `conclusiones`, `requerimientos`

**`rehab_recon.indicador`**
- `id`, `proyecto_id`, `nombre`, `linea_base`, `meta`, `valor_actual`, `fecha_medicion`, `fuente`

**`rehab_recon.rendicion_cuenta`**
- `id`, `proyecto_id`, `informe`, `gastos`, `metas_fisicas`, `fecha`, `estado`

#### 4.8 `workflow`

**`workflow.proceso`**: `id`, `codigo`, `nombre`, `tipo` (ayuda_humanitaria, rehab_recon, rehab_insumos, primera_respuesta_umee).
**`workflow.ruta`**: `id`, `proceso_id`, `nombre`, `version`.
**`workflow.fase`**: `id`, `codigo`, `nombre`, `criterio` (las 25 fases homologadas).
**`workflow.paso_ruta`**: `id`, `ruta_id`, `orden`, `fase_id`, `nombre`, `instancia_id`, `obligatorio`, `documento_requerido`.
**`workflow.expediente`**: `id`, `evento_id`, `ruta_id`, `codigo`, `estado`, `instancia_actual_id`, `fecha_inicio`, `fecha_fin`.
**`workflow.expediente_paso`**: `id`, `expediente_id`, `paso_id`, `estado`, `usuario_id`, `fecha`, `observaciones`, `documento_id`.

Esto permite modelar las cuatro rutas del Excel y el flujo de 3 instancias:

- **Instancia 1:** Local/Municipal → empadronamiento EDAN, informe técnico-legal, declaratoria municipal.
- **Instancia 2:** Departamental/Regional → consolidación, dictamen de capacidad, aprobación intermedia.
- **Instancia 3:** Nacional/Central → evaluación técnica-financiera, Decreto Supremo, asignación de fondos.

#### 4.9 `documento`, `monitoreo` y `analitica`

**`documento.documento`**
- `id`, `evento_id`, `formulario_rida_id`, `proyecto_id`, `expediente_id`
- `tipo_documento_id`, `nombre`, `url`, `hash`, `fecha_carga`, `usuario_id`, `estado`

**`monitoreo.indicador`**: indicadores de desempeño e impacto.
**`monitoreo.avance`**: avance físico/financiero por proyecto o evento.
**`monitoreo.alerta`**: alertas por retraso, duplicidad o riesgo.

**`analitica`**: vistas materializadas para reportes por evento, municipio, categoría de ayuda, vulnerabilidad, proyecto y estado de workflow.

---

### 5. Relaciones clave

```
evento_adverso 1──N formulario_rida
formulario_rida 1──N familia
familia 1──N integrante_familia
persona 1──N integrante_familia
familia 1──N necesidad
formulario_rida 1──N necesidad
evento_adverso 1──N atencion
atencion 1──N atencion_detalle
evento_adverso 1──N proyecto
proyecto 1──N evaluacion_dano
proyecto 1──N indicador
proyecto 1──N rendicion_cuenta
evento_adverso 1──N expediente
expediente 1──N expediente_paso
documento N──1 evento_adverso / formulario_rida / proyecto / expediente
```

---

### 6. Módulos funcionales del sistema

1. **Administración y seguridad:** usuarios, roles, permisos, entidades territoriales, auditoría.
2. **Gestión de eventos adversos:** registro, georreferenciación, tipología, cuantificación.
3. **Formularios RIDA / empadronamiento:** localidad/campamento, familias, integrantes, vulnerabilidades.
4. **Evaluación de necesidades:** catálogo de artículos, priorización, cuantificación.
5. **Ayuda humanitaria:** solicitudes, atención municipal/departamental, entregas, descargos.
6. **Primera respuesta UMEE:** comando de incidentes, requerimientos, distribución a unidades militares.
7. **Rehabilitación y reconstrucción:** proyectos, EDAN/FIBE, mesas sectoriales, infraestructura, SICOES, pago.
8. **Workflow y aprobaciones:** rutas, fases, pasos, 3 instancias, expedientes.
9. **Documental:** carga, clasificación, verificación y descarga de documentos.
10. **Monitoreo y seguimiento:** indicadores, avances, alertas, rendición de cuentas.
11. **Reportes y analítica:** tableros por evento, municipio, categoría, vulnerabilidad y proyecto.
12. **Interoperabilidad:** APIs con SINPAD, SINAGER-SAT/GEOSINAGER, SICOES, sistemas sectoriales.

---

### 7. Mapeo con los procesos VIDECI

| Ruta | Entidades principales | Workflow |
|---|---|---|
| Ayuda humanitaria (21 pasos) | evento, formulario RIDA, familia, necesidad, atención, entrega, descargo | `workflow.ruta` ayuda_humanitaria |
| Rehabilitación y reconstrucción (15 pasos) | proyecto, evaluación, cotización, contratación, ejecución, SICOES, pago | `workflow.ruta` rehab_recon |
| Rehabilitación-insumos (13 pasos) | necesidad, autorización salida, entrega al municipio, descargo | `workflow.ruta` rehab_insumos |
| Respuesta inmediata UMEE (22 pasos) | comando de incidentes, requerimiento UMEE, distribución a unidades militares | `workflow.ruta` primera_respuesta_umee |

Las 25 fases homologadas se cargan en `workflow.fase` y se reutilizan en las cuatro rutas.

---

### 8. Actualización tecnológica recomendada

- **Base de datos:** PostgreSQL 15+ con PostGIS, `pgcrypto`, `uuid-ossp`, JSONB para extensiones.
- **Backend:** Java Spring Boot, .NET o NestJS; API REST/GraphQL.
- **Frontend:** React/Vue; mapa con MapLibre/Leaflet.
- **GIS:** GeoServer o mapas vectoriales; índices GIST.
- **Autenticación:** Keycloak/OAuth2/JWT; RBAC por nivel territorial.
- **Documentos:** MinIO/S3; metadatos en BD; hash SHA-256.
- **Workflow:** motor propio o Camunda/BPMN si se requiere mayor formalización.
- **Analítica:** Metabase/Superset; vistas materializadas.
- **Integración:** colas RabbitMQ/Kafka; ETL para SINPAD/SINAGER/SICOES.
- **Despliegue:** contenedores Docker/Kubernetes; CI/CD.

---

### 9. Implementación por fases

1. **Fase 1:** núcleo RIDA actual (evento, formulario, familia, integrante, necesidad, atención, documento).
2. **Fase 2:** empadronamiento ampliado con vulnerabilidades y catálogos de ayuda.
3. **Fase 3:** ayuda humanitaria completa y workflow de 3 instancias.
4. **Fase 4:** primera respuesta UMEE.
5. **Fase 5:** rehabilitación y reconstrucción (proyectos, EDAN/FIBE, SICOES, pago).
6. **Fase 6:** monitoreo, analítica e interoperabilidad.

---

### 10. Conclusión

La evolución del RIDA hacia una plataforma integral exige separar el núcleo transaccional de eventos y familias, ampliar el modelo de necesidades y atenciones, incorporar un motor de workflow configurable y crear módulos específicos para primera respuesta, ayuda humanitaria, rehabilitación y reconstrucción. La arquitectura propuesta permite reutilizar los datos actuales del RIDA, integrar los formularios de empadronamiento y los instrumentos EDAN/FIBE, y soportar el flujo institucional de tres instancias definido por VIDECI. Con PostgreSQL/PostGIS, APIs modernas y esquemas modulares, el sistema queda preparado para escalar, interoperar y generar información oportuna para la toma de decisiones.