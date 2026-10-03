# SINB · Propuesta de mejora de la herramienta

**Sistema de Información de Bioclimática y Pronósticos**
VIDECI · con apoyo del PMA · operadores militares

> Esta propuesta **no describe un sistema nuevo desde cero**. Describe cómo **mejorar el SINB que ya está desplegado en la VIDECI**, conservando su modelo de dominio —que está bien construido— y corrigiendo lo que le impide funcionar fuera de una red de oficina.

---

## 1. Contexto verificado

| Dato | Valor | Fuente |
|---|---|---|
| Nombre | Sistema de Información de Bioclimática y Pronósticos | `docs/FUNCIONALIDAD.md` |
| Aplicación | Laravel 5.8 sobre PHP | `web/composer.json` |
| Base de datos | MariaDB 10.3.39, esquema `sinb` | `sinb_20260714.sql` |
| Tablas | 46, todas con prefijo `t_` | `sinb_20260714.sql` |
| Rutas web | 75, en un solo archivo de 231 líneas | `web/routes/web.php` |
| Vistas | 59 Blade | `web/resources/views` |
| Despliegue | VIDECI, operado por personal militar | Contexto institucional |
| Apoyo | PMA | Contexto institucional |
| Instituciones en la interfaz | PROSUCO, VIDECI, MINDEF | `web/resources/views/partials` |
| Aplicación móvil | `[ACTUAL]` **Ninguna**. No hay API, ni PWA, ni app | `docs/FUNCIONALIDAD.md §8` |

> **Nota de contraste (estructura actual del repositorio).** Las fuentes anteriores (`web/`, `sinb_20260714.sql`) corresponden al **SINB legado desplegado en la VIDECI y no están incluidas en este repositorio**. Lo que este repositorio aporta y donde se aplica esta propuesta es:
>
> | Elemento | Estado real verificado en este repositorio |
> |---|---|
> | Base de datos | **PostgreSQL 16 + PostGIS 3.4**, base `db_sinagersat`, esquemas `shared`, `usuarios`, `edan`, `rea`, `repositorio`, `rida`, **`sinb` (vacío)**, `recursos` |
> | API | **FastAPI** (`api/`), rutas `/api/v1` y `/api/v2`, JWT y auditoría (`AuditMiddleware`) |
> | Dominios vecinos | `edan` y `rida` son módulos **independientes** del SINB |
>
> **Regla de integración**: todo el contenido de esta propuesta se encaja en el esquema **`sinb.*`**, **sin tocar** `edan.*` ni `rida.*`. Se reutilizan `usuarios`, `shared` y `repositorio` **solo si el diseño lo requiere**. Las marcas `[ACTUAL]`/`[DEFECTO]` del texto se refieren al SINB legado, salvo indicación en la sección §0 de cada documento.

El SINB funciona y tiene usuarios reales: **279 usuarios**, **243 observaciones**, 18.331 comunidades, 77 indicadores naturales. Lo que falta es todo lo que hace que un dato capturado en un cerro llegue al servidor, y lo que hace que se pueda saber quién lo cambió.

---

## 2. La convención de este documento

Cada afirmación técnica de los 14 documentos lleva una marca. Sin excepción: o está verificada en el código, o está marcada como nueva.

| Marca | Significado | Cómo se verifica |
|---|---|---|
| `[ACTUAL]` | Existe hoy en el SINB desplegado | Leyendo el código, el dump o las rutas citadas |
| `[DEFECTO]` | Existe hoy y está verificado que está mal | Con la evidencia citada |
| `[NUEVO]` | **Idea nueva.** No existe en el SINB. Es una mejora propuesta | Se marca en cada documento donde aparece |
| `[MEJORA]` | Ya existe, pero se propone cambiar su comportamiento | Con el motivo en la misma línea |
| `[DECIDIR]` | Hay dos caminos y hace falta firma | Con las dos opciones y su coste |
| `[OPCIONAL]` | Exploración fuera del alcance base: **no bloquea nada** y se puede descartar sin efecto | Con su nota de viabilidad ([14 §13](14-RESUMEN-EJECUTIVO.md)) |

> **Regla de este documento**: si algo no lleva marca `[ACTUAL]` o `[DEFECTO]`, es propuesta. Ninguna capacidad se presenta como existente si no lo está.

### 2.1 La fuente de insumos

`docs/Sistema Biocultural.md` es un documento de **ideas** del método. Aporta el vocabulario real de los indicadores (zorro, liqi liqi, qariwa, sank'ayu, ch'illiwa) y la intuición del método biocultural.

**No describe el SINB.** Sus términos —«Pachagrama», «Yapuchiri», «seña»— **no aparecen ni en el código, ni en las 46 tablas, ni en las 75 rutas**. Verificado sobre 10.580 archivos.

Por eso, en esta propuesta:

| Elemento del insumo | Qué se hace |
|---|---|
| Los **nombres** de los indicadores (`Zorro`, `Liqi liqi`) | Se conservan: ya están en `t_indicador_natural` |
| La **cadena de 5 niveles** que describe el conocimiento | Se **reforza**: es el modelo de dominio del SINB |
| El **monitoreo diario** | Se propone como `[NUEVO]`, con su tabla y su flujo |
| La **voz** como captura | Se propone como `[NUEVO]` |
| La **confiabilidad a la vista** (confianza + índice del observador + aciertos) | Se propone como `[NUEVO]` |
| El **cruce satelital** | Se propone como `[NUEVO]` |
| Los idiomas aimara, quechua, tsimane | **Se descartan.** Todo en español: los nombres de especies se escriben como los conoce cada persona |
| Los actores «Yapuchiri», «Observador Comunitario» | **Se descartan.** Los roles reales son los 4 de `t_rol`, más el nuevo `usuario-supramunicipal` |

---

## 3. Los actores reales

Extraídos de `t_rol`. Los cuatro de hoy se conservan **con sus slugs intactos**; la propuesta les asigna mejor las tareas y añade un quinto rol, `usuario-supramunicipal`, sin tocar los legados.

| `slug` | Nombre en la base | Qué hace hoy | Qué hace con la mejora |
|---|---|---|---|
| `administrador` | Administrador del sistema | Configura usuarios, roles, permisos, menús y geografía | Igual, más auditoría y configuración de traducciones |
| `usuario-municipal` | Administrador de datos Municipales | Captura y edita observaciones y pronósticos del municipio | Igual, más el consolidado municipal y la validación comunitaria |
| `usuario-recolector` | Recolección de datos comunidades | Recolecta datos de comunidades | Igual, y pasa a ser el actor principal del trabajo sin conexión |
| `observador-local` | Generador de datos comunidad | Registra observaciones y pronósticos de su comunidad | Igual, pero captura desde el teléfono y sin internet |
| `usuario-supramunicipal` `[NUEVO]` | — (no existe) | — | Gestión y reportes de **toda su región**; valida y gestiona usuarios de su ámbito; no publica a nivel nacional ([04 §8.1](04-BASE-DE-DATOS.md)) |

| Dato verificado | Valor |
|---|---|
| Permisos por rol | 69 / 48 / 26 / 18 (legados) + `[NUEVO]` para el supra |
| Menús por rol | 15 / 10 / 5 / 4 |
| `solo-municipal` | En los roles 2, 3 y 4. **Nunca** en el administrador |
| Filas de `t_permiso` | 70 |
| Filas de `t_menu` | 18 |

**Decisión que se respeta**: el administrador **no** lleva `solo-municipal` porque ve todo el país. Ese comportamiento se conserva exactamente. Ver [09-SEGURIDAD.md §3](09-SEGURIDAD.md).

---

## 4. Lo que se conserva y lo que se rompe

### 4.1 Se conserva intacto

| Pieza | Por qué |
|---|---|
| La cadena grupo → indicador → característica → comportamiento → significado | Es el modelo de dominio. Está bien pensado: separa *qué se observa* de *cómo se observa* de *qué significa*. Aplanarla sería una pérdida |
| Los cuatro niveles territoriales con tablas pivote | Funciona. Sin `parent_id` es rígido, pero no está mal |
| Los dos tipos de pronóstico | Estacional y temporal responden a horizontes distintos |
| `t_campo_pronosticos` → `t_escenarios` | Separa el campo del pronóstico de sus valores posibles. Es correcto |
| La recomendación local con comportamientos | `Epoca de siembra`, `Lugar de siembra`, con `Adelantada/Tardia` |
| Los 7 grupos de indicadores | Animales, Plantas, Condiciones meteorológicas, Astros, Constelaciones, Eventos atmosféricos, Eventos tradicionales |
| La importación desde Excel | Los técnicos ya la usan |

### 4.2 Se rompe, con motivo

| Pieza actual | Problema verificado | Qué se hace |
|---|---|---|
| `t_comportamiento` es global | 523 filas que valen para cualquier característica. «Mayor a lo normal» de *altura de planta* y de *canto del liqi liqi* son la misma cadena de texto | `[MEJORA]` Se le añade `caracteristica_id` para que el comportamiento dependa de la característica |
| `t_pronostico_temporal.pronostico` es texto | El catálogo `t_categorias_pronostico_temporal` tiene 12 filas, pero el campo guarda el texto. No se puede validar ni agrupar | `[MEJORA]` Se convierte en FK |
| La comunidad solo tiene lat/long `DOUBLE` | Un mapa necesita geometría. Y el punto exacto se elige a mano | `[MEJORA]` Se añade `geography(Point,4326)` con índice `GiST` |
| `t_zona_geografica` no tiene FK a comunidad | La zona Andina/Subandina/Oriental **no está en ninguna columna de comunidad**. La relación es solo lógica y se pierde | `[MEJORA]` Se añade `zona_geografica_id` a `comunidad` |
| La jerarquía vive en 3 tablas pivote | Una comunidad en `t_comunidad` no apunta a su municipio. Un borrado mal hecho la deja huérfana | `[MEJORA]` Se añaden triggers de integridad y una función de materializado |
| `t_login.password` | El alta deja la contraseña en `123` y no la hashea hasta el reset | `[DEFECTO]` Ver [09-SEGURIDAD.md §2](09-SEGURIDAD.md) |
| `Gate::define` siempre devuelve `true` | 70 Gates que conceden siempre. La decisión real la toma `loginModel::permisos()` | `[DEFECTO]` Ver [09-SEGURIDAD.md §3](09-SEGURIDAD.md) |
| `GET /excel` fuera del middleware `auth` | Lista usuarios sin contraseña | `[DEFECTO]` Ver [09-SEGURIDAD.md §2](09-SEGURIDAD.md) |
| Dos convenciones de `estado` | `smallint(6)` en unas tablas y `enum('ACTIVO','INACTIVO')` en otras | `[MEJORA]` Se unifica |
| `DEFAULT CHARSET=utf8` | `utf8` en MariaDB es de 3 bytes. Un nombre en aimara con caracteres de 4 bytes se corta | `[MEJORA]` UTF-8 de 4 bytes |
| No hay bitácora | No se sabe quién cambió qué ni cuándo | `[NUEVO]` Tabla `auditoria` |
| No hay API | Solo 75 rutas HTML | `[NUEVO]` API REST |
| No hay PWA | No se puede capturar sin internet | `[NUEVO]` PWA offline-first |
| No hay cálculo | Todo es captura manual. El sistema **no genera pronósticos** | `[NUEVO]` Índice de confiabilidad |

---

## 5. Las ideas nuevas

Todas marcadas `[NUEVO]`. Todas factibles con la base actual. Ninguna requiere cambiar el modelo de dominio.

| # | Idea | Qué resuelve | Dónde |
|---|---|---|---|
| 1 | **Captura sin conexión** en PWA | El 80 % del problema: un cerro no tiene señal | [08](08-OFFLINE-SINCRONIZACION.md) |
| 2 | **Bitácora de auditoría** | Hoy no se sabe quién cambió una observación | [09](09-SEGURIDAD.md) |
| 3 | **Verificación de pronósticos**: al vencer el periodo, ¿acertó o no? | Hoy nadie comprueba si el pronóstico acertó | [04 §14](04-BASE-DE-DATOS.md), [07 §9A](07-FLUJOS-BIOCULTURALES.md), [10 §10](10-INTEROPERABILIDAD.md) |
| 4 | **Calificación de bioindicadores** (3 niveles) | Distingue lo usable, lo que se está verificando y lo que hay que revisar | [04 §14.3](04-BASE-DE-DATOS.md), [07 §9A.3](07-FLUJOS-BIOCULTURALES.md) |
| 5 | **Confiabilidad a la vista**: confianza + índice del observador + aciertos | Convierte 243 observaciones aisladas en evidencia acumulable | [04 §9.4](04-BASE-DE-DATOS.md), [06 §12A.5](06-FRONTEND.md) |
| 6 | **Geometría real** y consultas espaciales | El mapa actual dibuja 18.331 puntos sin ningún filtro por zona | [04](04-BASE-DE-DATOS.md) |
| 7 | **API REST** | Sin API no hay PWA, ni app, ni integración | [05](05-APIS.md) |
| 9 | **Cruce satelital** Sentinel-2 y Open-Meteo | El dato de campo nunca se compara con el de satélite | [10](10-INTEROPERABILIDAD.md) |

### 5.1 La idea que sostiene a las demás

`[NUEVO]` **La verificación** es la diferencia central de esta propuesta. Un pronóstico emitido se comprueba después: al vencer su periodo, acertó o no acertó, y con esa evidencia se decide si el indicador sigue usable.

| Pieza | Función |
|---|---|
| `verificacion_pronostico` | El resultado de cada pronóstico: acertó / no acertó / sin dato |
| `observador_indice` | El índice automático del observador, separado LARGO / CORTO |
| `calificacion_indicador` | El nivel de cada indicador por ámbito: `EN_VERIFICACION`, `USABLE`, `REVISAR` |

`[NUEVO]` El efecto: el sistema **muestra por sí mismo lo que deja de sostenerse** (nivel `REVISAR` con su nota), y publica con la misma claridad lo que funciona y lo que no. Eso protege la credibilidad de todo lo demás.

Detalle en [14 §6](14-RESUMEN-EJECUTIVO.md), que es el documento de exposición.

### 5.1 Cómo se ejecuta sin perder nada

`[DECIDIR]` **Estrategia de corte.** Hay dos caminos y hace falta firma.

| Opción | Qué implica | Duración | Riesgo |
|---|---|---|---|
| **A · Convivencia** | La app Laravel sigue capturando en MariaDB. La nueva API en PostgreSQL se alimenta por CDC. Ambos sistemas sirven | 2 años | Bajo. El SINB nunca se cae |
| **B · Corte único** | Exportar, convertir, cargar en PostgreSQL, apagar Laravel | 3 meses | Alto. Si algo sale mal, no hay a dónde volver |

La propuesta técnica asume la **A**. El motivo: los operadores son militares, el sistema está en producción con 279 usuarios, y una plataforma que sostiene validación comunitaria no puede depender de un corte único. Ver [13-ROADMAP.md §2](13-ROADMAP.md).

---

## 6. Índice

| # | Documento | Qué resuelve |
|---|---|---|
| 01 | [Arquitectura](01-ARQUITECTURA.md) | Qué se construye y por qué; los 10 defectos |
| 02 | [Componentes visuales](02-COMPONENTES-VISUALES.md) | La interfaz, sobre los componentes que ya existen |
| 03 | [Backend](03-BACKEND.md) | FastAPI, Celery, y la tarea diaria de verificación |
| 04 | [Base de datos](04-BASE-DE-DATOS.md) | Las 46 tablas, el DDL nuevo, y **§14 verificación y calificación** |
| 05 | [APIs](05-APIS.md) | Los contratos REST, tokens y evidencias |
| 06 | [Frontend](06-FRONTEND.md) | Vue 3, PWA, y **§12A cómo se ve la verificación en pantalla** |
| 07 | [Flujos bioculturales](07-FLUJOS-BIOCULTURALES.md) | **3 niveles de flujo**, **§9A verificación y calificación**, cambio climático |
| 08 | [Offline y sincronización](08-OFFLINE-SINCRONIZACION.md) | El protocolo de sincronización |
| 09 | [Seguridad](09-SEGURIDAD.md) | Autenticación, RLS, auditoría |
| 10 | [Interoperabilidad](10-INTEROPERABILIDAD.md) | Sentinel-2, NDVI, Open-Meteo, verificación y métodos a futuro |
| 11 | [Interculturalidad](11-INTERCULTURALIDAD.md) | Vocabulario, consentimiento, gobernanza (todo en español) |
| 12 | [Infraestructura](12-INFRAESTRUCTURA.md) | Despliegue en VIDECI |
| 13 | [Roadmap](13-ROADMAP.md) | Previo + 4 bloques: tareas, responsables, criterios de aceptación |
| **14** | **[Resumen ejecutivo](14-RESUMEN-EJECUTIVO.md)** | **Documento de exposición: qué hay, qué falta, qué se propone** |

---

## 7. Los tres módulos que no existen

Para que quede claro qué sale del alcance:

| Módulo | Estado | Nota |
|---|---|---|
| **Meteorología operativa** | `[DEFECTO]` | El SINB guarda clima pero **no lo consume**. No hay cálculo |
| **Análisis predictivo / IA** | No existe | El cruce con clima/satélite va en [10](10-INTEROPERABILIDAD.md) como datos, no como modelo. La IA (motor de texto, MCP) queda como **nota opcional** en [14 §13](14-RESUMEN-EJECUTIVO.md): propone, **nunca valida** |
| **Notificaciones** | No existe | `QUEUE_CONNECTION=sync`. Sin correo, sin colas |

---

## 8. Cómo leer esta propuesta

**Para exponer la propuesta**: empiece por [14-RESUMEN-EJECUTIVO.md](14-RESUMEN-EJECUTIVO.md). Es el documento único de exposición — qué hay, qué falta, qué se propone — con tablas, diagramas y comparaciones ANTERIOR/NUEVO, pensado para leerse de una sentada o presentarse ante un comité. Incluye la nota opcional de IA (§13).

**Para decidir**: lea [§3](README.md#3-los-actores-reales), [§4](README.md#4-lo-que-se-conserva-y-lo-que-se-rompe) y las decisiones de [14 §15](14-RESUMEN-EJECUTIVO.md).

**Para implementar**: empiece por [13-ROADMAP.md](13-ROADMAP.md), que organiza el trabajo en un previo y **cuatro bloques** (base de datos → APIs → frontend → scripts), con tareas y criterios de aceptación — sin costes ni cronograma, que se deciden aparte. El previo de corrección es independiente y no bloquea nada.

**Si va a cambiar algo, respete dos cosas**: la cadena de cinco niveles de [§4.1](README.md#41-se-conserva-intacto) y el aislamiento `solo-municipal` de [§3](README.md#3-los-actores-reales). Son el dominio, y los dos están bien hechos.

---

## Ver también

- [docs/FUNCIONALIDAD.md](../docs/FUNCIONALIDAD.md) — lo que el SINB hace hoy, leído del código
- [docs/BASE_DE_DATOS.md](../docs/BASE_DE_DATOS.md) — las 46 tablas actuales
- [docs/AUDITORIA.md](../docs/AUDITORIA.md) — defectos verificados
- [docs/FLUJOS.md](../docs/FLUJOS.md) — el detalle de cada operación