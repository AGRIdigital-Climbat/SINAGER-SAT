# DOCUMENTACIÓN TÉCNICA: ARQUITECTURA Y ESTRUCTURA DE BASE DE DATOS PARA LA GESTIÓN DE AYUDA HUMANITARIA Y ATENCIÓN DE EMERGENCIAS (GRD)

---

## 1. INTRODUCCIÓN Y CONTEXTO DEL CASO

En eventos de desastre de gran magnitud, la atención efectiva exige una respuesta articulada entre distintos niveles de gobierno (**Municipal**, **Departamental**, **Nacional**) e instancias de **Cooperación Internacional**. La presente arquitectura de base de datos ha sido diseñada para responder operativamente a las necesidades identificadas en el **Análisis del Caso**, estructurando la información sobre un modelo relacional descentralizado, ágil y transparente.

### 1.1 Cobertura de Mecanismos de Atención
El sistema contempla el ciclo operativo integral a través de cuatro mecanismos normativos y funcionales:
1. **Respuesta Inmediata:** Atención de salvamento, evacuación y dotación de equipamiento e insumos a unidades militares y equipos de primera respuesta.
2. **Ayuda Humanitaria:** Entrega directa de insumos de techo, abrigo, alimentación, agua, salud e higiene a familias **damnificadas** (pérdida de vivienda/bienes) y **afectadas** (pérdida de medios de vida/transitabilidad).
3. **Rehabilitación:** Gestión de proyectos de corto/mediano plazo para la restitución de la transitabilidad y servicios básicos (ej. contratación de horas máquina para habilitar pasos vehiculares y puentes colapsados).
4. **Reconstrucción:** Formulación y seguimiento de proyectos de inversión pública de mediano/largo plazo donde el municipio actúa como beneficiario principal para la reposición de infraestructura física y viviendas resilientes.

---

## 2. MAPEO DE REQUERIMIENTOS DEL CASO VS. ENTIDADES DEL SISTEMA

| Requerimiento del Caso | Desafío Operativo | Solución en la Arquitectura de Datos |
| :--- | :--- | :--- |
| **Caracterización Demográfica Especial** | Identificar mujeres gestantes, lactantes, personas con discapacidad y enfermos crónicos. | Tabla `INTEGRANTE_FAMILIA` con banderas relacionales y atributos específicos de vulnerabilidad biológica y salud. |
| **Población en Situación Crítica** | Registrar personas ilesas sin vivienda, heridos, fallecidos y desaparecidos. | Atributo `estado_salud_post_evento` dentro del registro censal de cada integrante. |
| **Motor de Cálculo Automático** | Establecer paquetes de alimento según $N_{\text{integrantes}} \times D_{\text{días}}$ y prendas por género/edad. | Módulo de Parámetros y Tablas `REGLA_CALCULO_KIT` y `DETALLE_PARAMETRO_KIT`. |
| **Provisión de Medios de Vida (Semillas)** | Balance entre stock en almacén e insuficiencia que detona compras públicas. | Flujo de control entre `INVENTARIO_STOCK`, `SOLICITUD_COMPRA_LICITACION` y `ORDEN_COMPRA_PROVEEDOR`. |
| **Infraestructura y Transitabilidad** | Puente caído y afectación a familias no damnificadas en vivienda pero sí en medios de vida. | Distinción del tipo de afectado en `FAMILIA_BENEFICIARIA` y proyectos de maquinaria en `PROYECTO_RECUPERACION`. |
| **Agregación Financiera Multinivel** | Visibilidad de brechas presupuestarias para aportes según capacidad de cada nivel. | Módulo de Aprobaciones Tripartitas (`APROBACION_SOLICITUD`) y tableros consolidados por `NIVEL_TERRITORIAL`. |

---

## 3. MODELO DE DATOS Y DICCIONARIO DE TABLAS

La base de datos se compone de **18 tablas relacionales** agrupadas en 6 módulos operativos:

```
+-----------------------------------------------------------------------------------+
|                                  ESQUEMA GENERAL                                  |
+-----------------------------------------------------------------------------------+

[NIVEL_TERRITORIAL] ──1:N──> [ENTIDAD_ORGANIZACION] ──1:N──> [ALMACEN]
                                     │                            │
                                     │ 1:N                        │ 1:N
                                     ▼                            ▼
                        [FAMILIA_BENEFICIARIA]            [INVENTARIO_STOCK]
                                     │                            ▲
                                     │ 1:N                        │
                                     ▼                            │
                        [INTEGRANTE_FAMILIA]                      │
                                     │                            │ (Consumo)
                                     │ 1:N                        │
                                     ▼                            │
                       [EVALUACION_NECESIDAD] ──1:N──> [DESPACHO_ENTREGA]
                                     │
                                     ├─1:N──> [APROBACION_SOLICITUD]
                                     │
                                     └─1:N──> [SOLICITUD_COMPRA_LICITACION]
```

---

### MÓDULO A: Gobernanza Territorial y Descentralización

#### 1. Tabla: `NIVEL_TERRITORIAL`
Clasifica los escalones de gobierno y cooperación.
* `id_nivel` (`INT`, PK, Auto): Identificador único del nivel.
* `codigo_nivel` (`VARCHAR(20)`, Unique): Código abreviado (`MUN`, `DEP`, `NAC`, `INT_COOP`).
* `nombre_nivel` (`VARCHAR(50)`): Descripción (`Municipal`, `Departamental/Regional`, `Gobierno Central/Nacional`, `Cooperación Internacional`).

#### 2. Tabla: `ENTIDAD_ORGANIZACION`
Registra cada institución actuante de forma independiente.
* `id_entidad` (`INT`, PK, Auto): Identificador de la entidad.
* `id_nivel` (`INT`, FK -> `NIVEL_TERRITORIAL.id_nivel`): Nivel al que pertenece.
* `nombre_entidad` (`VARCHAR(150)`): Nombre oficial (ej. *Gobierno Autónomo Municipal*, *VIDECI*, *Ministerio de Desarrollo Rural*).
* `codigo_ubigeo_ine` (`VARCHAR(20)`): Código geográfico territorial oficial.
* `contacto_principal` (`VARCHAR(100)`): Nombre del responsable de GRD.
* `correo_telefono` (`VARCHAR(100)`): Datos de contacto oficial.

#### 3. Tabla: `ALMACEN`
Puntos de acopio físicos controlados por cada entidad.
* `id_almacen` (`INT`, PK, Auto): Identificador del almacén.
* `id_entidad` (`INT`, FK -> `ENTIDAD_ORGANIZACION.id_entidad`): Entidad propietaria/administradora.
* `nombre_almacen` (`VARCHAR(100)`): Nombre del centro de acopio (ej. *Almacén Central Municipal*, *Almacén Avanzado de Frontera*).
* `capacidad_peso_max_kg` (`DECIMAL(12,2)`): Capacidad portante máxima expresada en $kg$.
* `capacidad_volumen_max_m3` (`DECIMAL(12,2)`): Capacidad volumétrica expresada en $m^3$.
* `coordenadas_lat_long` (`VARCHAR(50)`): Georeferenciación (Latitud, Longitud).

---

### MÓDULO B: Catálogo Estandarizado de Bienes y Equipamiento

#### 4. Tabla: `CATEGORIA_BIEN`
Clasificación temática de insumos y equipos.
* `id_categoria` (`INT`, PK, Auto): Identificador de la categoría.
* `nombre_categoria` (`VARCHAR(100)`): Valores: `Techo y Abrigo`, `Alimentación y Agua`, `Salud e Higiene`, `Medios de Vida`, `Equipamiento Fuerzas Armadas / Respuesta Inmediata`.
* `descripcion_mecanismo` (`TEXT`): Explicación del destino operativo.

#### 5. Tabla: `CATALOGO_ARTICULO`
Maestro único de artículos homologados con métricas logísticas unitarias.
* `id_articulo` (`INT`, PK, Auto): Identificador del artículo.
* `id_categoria` (`INT`, FK -> `CATEGORIA_BIEN.id_categoria`): Categoría del bien.
* `codigo_sku` (`VARCHAR(30)`, Unique): Código estandarizado de inventario.
* `nombre_articulo` (`VARCHAR(150)`): Descripción (ej. *Carpa Familiar 6 Personas*, *Kit de Herramientas de Rescate*, *Semilla de Maíz Certificada*).
* `unidad_medida` (`VARCHAR(20)`): Unidad de despacho (`Unidad`, `Kilogramo`, `Caja`, `Kit`, `Bolsa 50kg`).
* `peso_unitario_kg` (`DECIMAL(8,3)`): Peso neto unitario ($kg$).
* `volumen_unitario_m3` (`DECIMAL(8,4)`): Volumen de empaque unitario ($m^3$).
* `costo_referencial_usd` (`DECIMAL(10,2)`): Precio estimado unitario en $\text{USD}$.

---

### MÓDULO C: Empadronamiento de Familias, Personas y Vulnerabilidades

#### 6. Tabla: `FAMILIA_BENEFICIARIA`
Cabecera del registro censal de la población afectada.
* `id_familia` (`INT`, PK, Auto): Identificador único de la familia.
* `codigo_ficha_edan` (`VARCHAR(50)`, Unique): Identificador de la Ficha EDAN / censo de campo.
* `id_entidad_empadronadora` (`INT`, FK -> `ENTIDAD_ORGANIZACION.id_entidad`): Entidad que levantó el dato.
* `tipo_poblacion` (`ENUM`): `Damnificada` (pérdida de vivienda/bienes directos), `Afectada` (pérdida indirecta / medios de vida / conectividad).
* `comunidad_barrio` (`VARCHAR(150)`): Nombre de la comunidad o sector afectado.
* `ubicacion_actual` (`VARCHAR(200)`): Ubicación tras el evento (ej. *Albergue Temporal N° 2*, *Casa de Parientes*, *In Situ*).
* `fecha_registro` (`DATETIME`): Fecha y hora del empadronamiento.

#### 7. Tabla: `INTEGRANTE_FAMILIA`
Detalle censal individual para detección de vulnerabilidades biológicas y estado de salud post-evento.
* `id_integrante` (`INT`, PK, Auto): Identificador de la persona.
* `id_familia` (`INT`, FK -> `FAMILIA_BENEFICIARIA.id_familia`): Familia a la que pertenece.
* `nombres_apellidos` (`VARCHAR(150)`): Nombre completo.
* `documento_identidad` (`VARCHAR(30)`): Cédula de identidad / RUT / DNI.
* `sexo` (`ENUM`): `Femenino`, `Masculino`.
* `fecha_nacimiento` (`DATE`): Fecha de nacimiento para derivación automática de rango etario (Lactante, Niño, Adulto, Adulto Mayor).
* `estado_post_evento` (`ENUM`): `Ileso`, `Herido_Leve`, `Herido_Grave`, `Fallecido`, `Desaparecido`.
* `es_gestante` (`BOOLEAN`): Indicador de embarazo.
* `semanas_gestacion` (`INT`): Semanas de gestación (si aplica).
* `es_lactante` (`BOOLEAN`): Indicador de madre en periodo de lactancia.
* `tiene_discapacidad` (`BOOLEAN`): Indicador de condición de discapacidad.
* `tipo_discapacidad` (`VARCHAR(100)`): Descripción de la discapacidad (`Física`, `Sensorial`, `Intelectual`).
* `enfermedad_cronica` (`VARCHAR(150)`): Padecimiento crónico que requiere medicación continua (ej. *Diabetes*, *Hipertensión*, *Insuficiencia Renal*).

---

### MÓDULO D: Motor de Cálculo y Reglas de Dosificación Automática

#### 8. Tabla: `REGLA_CALCULO_KIT`
Definición de parámetros para el cálculo automatizado de necesidades.
* `id_regla` (`INT`, PK, Auto): Identificador de la regla.
* `nombre_regla` (`VARCHAR(100)`): Nombre de la fórmula (ej. *Ración Alimentaria Familiar Estándar*, *Kit de Ropa Femenina*, *Kit Higiene Lactante*).
* `criterio_aplicacion` (`ENUM`): `Por_Familia`, `Por_Integrante`, `Por_Condicion_Especial`.
* `rango_edad_min_dias` (`INT`): Edad mínima en días para aplicar.
* `rango_edad_max_dias` (`INT`): Edad máxima en días para aplicar.
* `requiere_gestante` (`BOOLEAN`): Si aplica exclusivamente a gestantes.
* `requiere_discapacidad` (`BOOLEAN`): Si aplica exclusivamente a personas con discapacidad.

#### 9. Tabla: `DETALLE_PARAMETRO_KIT`
Artículos y cantidades requeridas por unidad de regla y tiempo.
* `id_detalle_regla` (`INT`, PK, Auto): Identificador del detalle.
* `id_regla` (`INT`, FK -> `REGLA_CALCULO_KIT.id_regla`): Regla asociada.
* `id_articulo` (`INT`, FK -> `CATALOGO_ARTICULO.id_articulo`): Artículo a asignar.
* `cantidad_base_diaria` (`DECIMAL(8,3)`): Cantidad consumida/requerida por persona o familia por día.

---

### MÓDULO E: Gestión de Inventarios, Licitaciones y Proyectos

#### 10. Tabla: `INVENTARIO_STOCK`
Disponibilidad física en tiempo real por almacén.
* `id_stock` (`INT`, PK, Auto): Identificador de registro de stock.
* `id_almacen` (`INT`, FK -> `ALMACEN.id_almacen`): Almacén físico.
* `id_articulo` (`INT`, FK -> `CATALOGO_ARTICULO.id_articulo`): Artículo almacenado.
* `cantidad_disponible` (`INT`): Stock físico disponible para despacho.
* `cantidad_comprometida` (`INT`): Stock reservado con orden de despacho emitida.

#### 11. Tabla: `SOLICITUD_COMPRA_LICITACION`
Activación de procesos de compra cuando el stock del nivel nacional o regional es insuficiente (ej. semillas o herramientas).
* `id_licitacion` (`INT`, PK, Auto): Identificador del proceso de compra.
* `id_entidad_compradora` (`INT`, FK -> `ENTIDAD_ORGANIZACION.id_entidad`): Entidad licitante.
* `id_articulo` (`INT`, FK -> `CATALOGO_ARTICULO.id_articulo`): Insumo requerido.
* `cantidad_requerida_faltante` (`INT`): Unidades requeridas que sobrepasan el stock.
* `presupuesto_estimado_usd` (`DECIMAL(12,2)`): Monto reservado para la compra.
* `estado_proceso` (`ENUM`): `Requerido`, `En_Licitacion`, `Adjudicado`, `Recibido_En_Almacen`.

#### 12. Tabla: `PROYECTO_RECUPERACION`
Proyectos de Rehabilitación (ej. alquiler de horas máquina para puentes) y Reconstrucción.
* `id_proyecto` (`INT`, PK, Auto): Identificador del proyecto.
* `mecanismo_asociado` (`ENUM`): `Rehabilitación`, `Reconstrucción`.
* `id_entidad_ejecutora` (`INT`, FK -> `ENTIDAD_ORGANIZACION.id_entidad`): Entidad que financia/ejecuta.
* `id_entidad_beneficiaria` (`INT`, FK -> `ENTIDAD_ORGANIZACION.id_entidad`): Municipio o comunidad beneficiaria.
* `nombre_proyecto` (`VARCHAR(200)`): Nombre formal del proyecto (ej. *Rehabilitación de Transitabilidad Paso Puente Colapsado Sector Norte*).
* `tipo_intervencion` (`VARCHAR(100)`): Categorización (`Horas_Maquinaria`, `Infraestructura_Vial`, `Vivienda_Resiliente`).
* `monto_presupuestado_usd` (`DECIMAL(14,2)`): Costo total asignado.
* `estado_ejecucion` (`ENUM`): `Formulacion`, `Aprobado`, `En_Ejecucion`, `Concluido`.

---

### MÓDULO F: Requerimientos, Aprobaciones Tripartitas y Despacho

#### 13. Tabla: `EVALUACION_NECESIDAD`
Registro consolidado de necesidades por familia o por contingencia.
* `id_necesidad` (`INT`, PK, Auto): Identificador de la necesidad.
* `id_familia` (`INT`, FK -> `FAMILIA_BENEFICIARIA.id_familia`): Familia solicitante (si aplica).
* `id_articulo` (`INT`, FK -> `CATALOGO_ARTICULO.id_articulo`): Artículo requerido.
* `cantidad_calculada_motor` (`INT`): Cantidad estimada automáticamente por el motor de cálculo.
* `cantidad_solicitada_final` (`INT`): Cantidad ajustada por el operador técnico.
* `dias_cobertura_atencion` (`INT`): Periodo proyectado de ayuda (ej. $15 \text{ días}$, $30 \text{ días}$).
* `estado_atencion` (`ENUM`): `Pendiente`, `En_Procesamiento`, `Aprobado_Parcial`, `Aprobado_Total`, `Atendido`.

#### 14. Tabla: `APROBACION_SOLICITUD`
Trazabilidad de la validación y asignación de presupuesto por niveles de gobierno.
* `id_aprobacion` (`INT`, PK, Auto): Identificador de la aprobación.
* `id_necesidad` (`INT`, FK -> `EVALUACION_NECESIDAD.id_necesidad`): Requerimiento evaluado.
* `id_entidad_aprobadora` (`INT`, FK -> `ENTIDAD_ORGANIZACION.id_entidad`): Entidad que asume la cobertura.
* `instancia_aprobacion` (`ENUM`): `Municipal`, `Departamental`, `Nacional`, `Cooperación_Internacional`.
* `cantidad_comprometida_entidad` (`INT`): Unidades que la entidad acuerda proveer.
* `fecha_aprobacion` (`DATETIME`): Fecha del dictamen.

#### 15. Tabla: `DESPACHO_ENTREGA`
Registro de la salida real de insumos desde almacén hacia el beneficiario final o unidad militar.
* `id_despacho` (`INT`, PK, Auto): Identificador del despacho.
* `id_almacen_origen` (`INT`, FK -> `ALMACEN.id_almacen`): Almacén de donde sale el stock.
* `id_familia_destino` (`INT`, FK -> `FAMILIA_BENEFICIARIA.id_familia`): Familia receptora (si aplica).
* `unidad_militar_destino` (`VARCHAR(150)`): Unidad militar/equipo de respuesta receptor (si aplica).
* `fecha_despacho` (`DATETIME`): Fecha y hora de salida.
* `peso_total_despacho_kg` (`DECIMAL(10,2)`): Peso total acumulado del viaje en $kg$.
* `volumen_total_despacho_m3` (`DECIMAL(10,2)`): Cubicaje total acumulado en $m^3$.
* `estado_recepcion` (`ENUM`): `En_Transito`, `Entregado_Conforme`, `Observado`.

#### 16. Tabla: `DETALLE_DESPACHO`
Items específicos contenidos en una orden de salida.
* `id_detalle_despacho` (`INT`, PK, Auto): Identificador del ítem despachado.
* `id_despacho` (`INT`, FK -> `DESPACHO_ENTREGA.id_despacho`): Despacho de origen.
* `id_articulo` (`INT`, FK -> `CATALOGO_ARTICULO.id_articulo`): Artículo entregado.
* `cantidad_entregada` (`INT`): Unidades físicas entregadas.
* `peso_subtotal_kg` (`DECIMAL(10,2)`): Calculado: $\text{cantidad} \times \text{peso\_unitario\_kg}$.
* `volumen_subtotal_m3` (`DECIMAL(10,2)`): Calculado: $\text{cantidad} \times \text{volumen\_unitario\_m3}$.

---

## 4. MOTOR DE CÁLCULO LOGÍSTICO Y FÓRMULAS AUTOMATIZADAS

Para garantizar precisión operacional, la base de datos almacena los insumos base y ejecuta procedimientos almacenados o consultas calculadas fundamentadas en las siguientes reglas matemáticas:

### 4.1 Cálculo de Requerimiento de Alimentos y Agua por Familia
El requerimiento total de alimentos para una familia de $N$ integrantes durante $D$ días se calcula mediante:

$$K_{\text{alimento}} = \sum_{i=1}^{N} \left( D \times R_{\text{indiv,i}} \right)$$

Donde:
* $N$: Número total de integrantes de la familia registrados en `INTEGRANTE_FAMILIA`.
* $D$: Días de cobertura (`dias_cobertura_atencion`).
* $R_{\text{indiv,i}}$: Ración diaria por persona según rango de edad y condición biológica (gestante/lactante).

### 4.2 Cálculo de Cubicaje y Peso para Gestión de Transportes
Para determinar si una flota de transporte (terrestre o aérea) puede movilizar un despacho humanitario, el sistema calcula automáticamente el acumulado de volumen y peso:

$$\text{Peso Total Despacho } (kg) = \sum_{j=1}^{M} \left( Q_j \times W_{\text{unit,j}} \right)$$

$$\text{Volumen Total Despacho } (m^3) = \sum_{j=1}^{M} \left( Q_j \times V_{\text{unit,j}} \right)$$

Donde:
* $Q_j$: Cantidad despachada del artículo $j$.
* $W_{\text{unit,j}}$: Peso unitario registrado en `CATALOGO_ARTICULO` ($kg$).
* $V_{\text{unit,j}}$: Volumen unitario registrado en `CATALOGO_ARTICULO` ($m^3$).
* $M$: Cantidad de artículos distintos incluidos en la orden de despacho.

### 4.3 Detección de Déficit y Activación de Compras (Licitación)
Cuando la solicitud de un municipio para un artículo $i$ supera el stock consolidado en sus almacenes, la brecha presupuestaria e inventarial se calcula como:

$$\text{Déficit}_i = \max \left( 0, \text{Requerimiento Total}_i - \sum_{k=1}^{A} S_{i,k} \right)$$

Donde:
* $\sum_{k=1}^{A} S_{i,k}$: Sumatoria del stock disponible del artículo $i$ en los $A$ almacenes del nivel correspondiente.
* Si $\text{Déficit}_i > 0$, el sistema genera automáticamente un registro en `SOLICITUD_COMPRA_LICITACION`.

---

## 5. FLUJOS OPERATIVOS DE INFORMACIÓN Y REGLAS DE NEGOCIO

```
 +-----------------------------------------------------------------------------------+
 |                             FLUJO CRÍTICO DE ATENCIÓN                             |
 +-----------------------------------------------------------------------------------+

 1. EMPADRONAMIENTO Y REGISTRO EN CAMPO
    [UGR Municipal / Ficha EDAN] ──> Registro en FAMILIA_BENEFICIARIA e INTEGRANTE_FAMILIA
                                             │
 2. EVALUACIÓN Y MOTOR DE CÁLCULO            ▼
    [Motor de Reglas] ────────────> Generación automática en EVALUACION_NECESIDAD
                                             │
 3. VERIFICACIÓN DE STOCK E INSTANCIAS       ▼
    [Consulta INVENTARIO_STOCK] ───> ¿Existe Stock Local?
                                      ├── SÍ ──> Emisión de DESPACHO_ENTREGA
                                      └── NO ──> Escalación a APROBACION_SOLICITUD (Dept/Nac)
                                                     │
 4. COMPRA / PROYECTOS                               ▼
    ¿Existe Stock Nacional? ───> NO ──> Detona SOLICITUD_COMPRA_LICITACION / PROYECTO
```

### Reglas de Negocio Clave:
1. **Priorización de Despacho Diferenciado:** Las familias registradas con gestantes, lactantes o enfermos crónicos en `INTEGRANTE_FAMILIA` generan alertas automáticas de alta prioridad para la asignación de kits de salud e higiene.
2. **Independencia Presupuestaria y de Almacén:** Cada nivel de gobierno (GAM, GAD, VIDECI/Ministerios) mantiene el control exclusivo de edición sobre sus propios registros de `ALMACEN` e `INVENTARIO_STOCK`, garantizando autonomía operativa pero visibilidad agregada mediante vistas del sistema.
3. **Consolidación de Solicitudes:** Las solicitudes no atendidas por el nivel municipal pasan automáticamente al tablero de evaluación del gobierno departamental. Si este agota sus recursos, la brecha escala al nivel nacional para activar compras públicas por licitación o canalización de cooperación internacional.
4. **Trazabilidad de Insumos Especiales:** El equipamiento otorgado a unidades militares para la primera respuesta se registra bajo el catálogo con categoría `Equipamiento Fuerzas Armadas` y su salida queda vinculada a la unidad militar receptora sin requerir asignación a una ficha familiar.