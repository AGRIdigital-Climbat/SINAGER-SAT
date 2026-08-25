# Guía de `id_seccion` para Flutter (v2.10.0)

## Resumen

`id_seccion` es un ID único que identifica cada fila en las tablas de secciones del EDAN.
Se genera en el cliente (Flutter) y se usa para deduplicación durante la sincronización offline.

## Por qué es importante

Sin `id_seccion`:
1. El backend no puede distinguir si una fila es nueva o existente
2. Se crean duplicados al sincronizar
3. Las fotos se pierden o se asocian a filas incorrectas

Con `id_seccion`:
1. El backend usa UPSERT: si la fila existe, la actualiza; si no, la crea
2. No hay duplicados
3. Las fotos se asocian correctamente

## Formato Recomendado

```
{tipo_seccion}_{timestamp}_{uuid_corto}
```

Ejemplos:
```
pr_1693012345_abc123def    # Primera Respuesta
sn_1693012345_ghi456jkl    # Salud Necesidades
nh_1693012345_mno789pqr    # Necesidades Humanitarias
sb_1693012345_stu123vwx    # Servicios Básicos
sv_1693012345_yza456bcd    # Salud Establecimientos
dv_1693012345_efg789hij    # Daños Viales
di_1693012345_klm123nop    # Daños Infraestructura Pública
ue_1693012345_qrs456tuv    # Unidades Educativas
vv_1693012345_wxy789zab    # Daños Vivienda
da_1693012345_cde123fgh    # Daños Agricultura
dp_1693012345_ijk456lmn    # Daños Pecuario
ip_1693012345_opq789rst    # Infraestructura Productiva
po_1693012345_uvw123xyz    # Protección
im_1693012345_abc456def    # Impacto Población
```

## Cuándo Generar

**UNA VEZ** al crear la sección. **NUNCA** regenerar al editar.

```dart
// ✅ CORRECTO: Generar al crear
final seccion = EdanServicioBasico(
  idSeccion: generarIdSeccion('sb'),  // Se genera UNA VEZ
  tipo: 'energia_electrica',
);

// ❌ INCORRECTO: Regenerar al editar
void editarSeccion(EdanServicioBasico seccion) {
  seccion.idSeccion = generarIdSeccion('sb');  // NUNCA hacer esto
  seccion.tipo = 'agua_potable';
}
```

## Ejemplo de Código

### Generador de ID

```dart
String generarIdSeccion(String tipo) {
  final timestamp = DateTime.now().millisecondsSinceEpoch;
  final uuid = Uuid().v4().substring(0, 8);
  return '${tipo}_${timestamp}_$uuid';
}
```

### Modelo con id_seccion (EJEMPLO: Servicio Básico 1:N)

```dart
class EdanServicioBasico {
  String? idSeccion;  // ← Agregar este campo
  String tipo;
  bool danoParcial;
  bool danoTotal;
  String? fotografia;
  // ...

  Map<String, dynamic> toApiJson() => {
    'id_seccion': idSeccion,  // ← Incluir en serialización
    'tipo': tipo,
    'dano_parcial': danoParcial,
    'dano_total': danoTotal,
    'fotografia': fotografia,  // ← 1:N SÍ incluye fotografia
  };
}
```

### Modelo con id_seccion (EJEMPLO: Primera Respuesta 1:1)

```dart
class EdanNecesidadPrimeraRespuesta {
  String? idSeccion;  // ← Agregar este campo
  bool busqueda;
  bool salvamento;
  bool evacuacion;
  String observaciones;
  // ⚠️ NO incluir fotografia, coordenada_lat, coordenada_lon
  //    Las tablas 1:1 NO tienen estas columnas en BD

  Map<String, dynamic> toApiJson() => {
    'id_seccion': idSeccion,  // ← Incluir
    'busqueda': busqueda,
    'salvamento': salvamento,
    'evacuacion': evacuacion,
    'observaciones': observaciones,
    // NO incluir fotografia aquí
  };
}
```

## Diferencia: 1:N vs 1:1

| Característica | 1:N (servicios_basicos, danos_viales, etc.) | 1:1 (primera_respuesta, salud_necesidades, necesidad_humanitaria) |
|----------------|----------------------------------------------|-------------------------------------------------------------------|
| Filas por localidad | Múltiples | Una sola |
| Tiene `fotografia` | ✅ SÍ | ❌ NO |
| Tiene `coordenada_lat/lon` | ✅ SÍ | ❌ NO |
| Tiene `id_seccion` | ✅ SÍ | ✅ SÍ (v2.10.0+) |
| Se puede crear con con-foto | ✅ SÍ | ❌ NO |
| JSON key en payload | `servicios_basicos: [{...}]` | `necesidad_primera_respuesta: {...}` |

**IMPORTANTE**: El nombre del campo en el JSON del sync es `necesidad_primera_respuesta` (NO `primera_respuesta`).

## Crear sección offline

### 1:N (ej: servicios_basicos)

```dart
// 1. Generar id_seccion UNA VEZ
final idSeccion = generarIdSeccion('sb');

// 2. Crear sección con id_seccion
final servicio = EdanServicioBasico(
  idSeccion: idSeccion,
  tipo: 'energia_electrica',
  danoParcial: true,
  danoTotal: false,
);

// 3. Guardar en SQLite
await db.insert('servicios_basicos', {
  'id_seccion': idSeccion,
  'tipo': 'energia_electrica',
  // ...
});
```

### 1:1 (ej: primera_respuesta)

```dart
// 1. Generar id_seccion UNA VEZ
final idSeccion = generarIdSeccion('pr');

// 2. Crear sección con id_seccion
final pr = EdanNecesidadPrimeraRespuesta(
  idSeccion: idSeccion,
  busqueda: true,
  salvamento: false,
  evacuacion: true,
);

// 3. Guardar en SQLite
await db.insert('primera_respuesta', {
  'id_seccion': idSeccion,
  'busqueda': true,
  // ...
});
```

## Editar sección offline

```dart
// 1. Buscar sección por id_seccion (NO regenerar)
final servicio = await db.query(
  'servicios_basicos',
  where: 'id_seccion = ?',
  whereArgs: [idSeccion],
);

// 2. Actualizar campos (mantener id_seccion)
servicio.tipo = 'agua_potable';
servicio.danoParcial = false;

// 3. Guardar en SQLite
await db.update('servicios_basicos', servicio.toMap(),
  where: 'id_seccion = ?',
  whereArgs: [idSeccion],
);
```

## Sync payload - Ejemplo completo

```json
{
  "id_usuario": 55,
  "codigo_ine": "70101",
  "localidades": [{
    "id_local": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "localidad": "Las Lomas",
    "id_tipo_localidad": 1,
    "id_municipio": 70101,
    "coordenada_lat": -17.783,
    "coordenada_lon": -63.182,
    "fecha_hora_ingreso": "2026-08-25T12:00:00",
    "total_poblacion_afectada": 50,
    "total_familias_afectadas": 10,
    "total_familias_damnificadas": 5,

    "necesidad_primera_respuesta": {
      "id_seccion": "pr_1693012345_abc123def",
      "busqueda": true,
      "salvamento": false,
      "evacuacion": true,
      "observaciones": "Se necesita búsqueda inmediata"
    },

    "necesidad_salud": {
      "id_seccion": "sn_1693012345_ghi456jkl",
      "numero_personas": 25,
      "otras_necesidades": "Medicinas urgentes",
      "observaciones": "Hay heridos"
    },

    "necesidad_humanitaria": {
      "id_seccion": "nh_1693012345_mno789pqr",
      "alimentos": true,
      "refugio_vivienda": true,
      "ropa_cama": false,
      "observaciones": "Falta albergue"
    },

    "servicios_basicos": [
      {
        "id_seccion": "sb_1693012345_stu123vwx",
        "tipo": "energia_electrica",
        "dano_parcial": true,
        "dano_total": false,
        "observaciones": "Postes caídos",
        "fotografia": "/uploads/reports/70101/70101_55_1693012345.jpg",
        "coordenada_lat": -17.783,
        "coordenada_lon": -63.182
      }
    ],

    "danos_viales": [
      {
        "id_seccion": "dv_1693012345_efg789hij",
        "via": true,
        "puente": false,
        "tramo": "Av. Principal",
        "dano_parcial": true,
        "dano_total": false,
        "km_danio": 1.5,
        "observaciones": "Pavimento agrietado",
        "fotografia": "/uploads/reports/70101/70101_55_1693012346.jpg",
        "coordenada_lat": -17.784,
        "coordenada_lon": -63.183
      }
    ],

    "danos_infra_publica": [],
    "unidades_educativas": [],
    "danos_vivienda": [],
    "danos_agricultura": [],
    "danos_pecuarios": [],
    "infra_productiva": [],
    "proteccion": [],
    "establecimientos_salud": [],
    "impacto_poblacion": []
  }]
}
```

## Sync sin id_seccion (backward compat)

El backend ACEPTA sync sin `id_seccion` (fallback a `id_edan_localidad` para 1:1).
Esto es para compatibilidad con versiones anteriores de Flutter.

```json
{
  "localidades": [{
    "id_local": "otro-uuid",
    "necesidad_primera_respuesta": {
      "busqueda": true,
      "salvamento": false,
      "evacuacion": false,
      "observaciones": "Sin id_seccion"
    }
  }]
}
```

**PERO**: Sin `id_seccion`, si el cliente reenvía la misma sección, se DUPLICA en la BD.
Siempre es mejor enviar `id_seccion`.

## Tablas que Requieren `id_seccion`

### 1:N (múltiples filas por localidad) — SÍ tienen `fotografia`

| Tabla | JSON key | Prefijo | Ejemplo |
|-------|----------|---------|---------|
| `servicios_basicos` | `servicios_basicos` | `sb` | `sb_1693012345_abc123def` |
| `salud_establecimientos` | `establecimientos_salud` | `sv` | `sv_1693012345_ghi456jkl` |
| `danos_viales` | `danos_viales` | `dv` | `dv_1693012345_mno789pqr` |
| `danos_infra_publica` | `danos_infra_publica` | `di` | `di_1693012345_qrs456tuv` |
| `unidades_educativas` | `unidades_educativas` | `ue` | `ue_1693012345_wxy789zab` |
| `danos_vivienda` | `danos_vivienda` | `vv` | `vv_1693012345_cde123fgh` |
| `danos_agricultura` | `danos_agricultura` | `da` | `da_1693012345_ijk456lmn` |
| `danos_pecuario` | `danos_pecuarios` | `dp` | `dp_1693012345_opq789rst` |
| `infra_productiva` | `infra_productiva` | `ip` | `ip_1693012345_opq789rst` |
| `impacto_poblacion` | `impacto_poblacion` | `im` | `im_1693012345_abc456def` |
| `proteccion` | `proteccion` | `po` | `po_1693012345_uvw123xyz` |

### 1:1 (una fila por localidad) — NO tienen `fotografia`

| Tabla | JSON key | Prefijo | Ejemplo |
|-------|----------|---------|---------|
| `primera_respuesta` | `necesidad_primera_respuesta` | `pr` | `pr_1693012345_klm123nop` |
| `salud_necesidades` | `necesidad_salud` | `sn` | `sn_1693012345_stu123vwx` |
| `necesidades_humanitarias` | `necesidad_humanitaria` | `nh` | `nh_1693012345_yza456bcd` |

## Flujo Completo

```
┌─────────────────────────────────────────────────────────────────┐
│ FASE 1: OFFLINE - Crear sección                                │
│                                                                 │
│ 1. Generar id_seccion: generarIdSeccion('sb')                  │
│ 2. Crear objeto con id_seccion                                  │
│ 3. Guardar en SQLite                                            │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE 2: OFFLINE - Editar sección                               │
│                                                                 │
│ 1. Buscar por id_seccion (NO regenerar)                        │
│ 2. Actualizar campos (mantener id_seccion)                      │
│ 3. Guardar en SQLite                                            │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ FASE 3: ONLINE - Sync                                          │
│                                                                 │
│ 1. Subir fotos locales (1:N) → obtener paths server            │
│ 2. Incluir id_seccion en payload (TODAS las secciones)          │
│ 3. Incluir fotografia (path server) en secciones 1:N           │
│ 4. NO incluir fotografia en secciones 1:1 (no tienen columna)  │
│ 5. POST /edan/localidades/sync                                  │
│ 6. Backend: UPSERT por id_seccion                               │
└─────────────────────────────────────────────────────────────────┘
```

## Reglas de Oro

1. **Generar id_seccion UNA VEZ** al crear la sección
2. **NUNCA regenerar** al editar
3. **SIEMPRE enviar** id_seccion en el sync payload
4. **SIEMPRE enviar** fotografia en secciones 1:N (aunque sea null o path existente)
5. **NO enviar** fotografia en secciones 1:1 (no tienen columna en BD)
6. **Subir fotos ANTES** del sync (via POST /upload)
7. **Nombre correcto**: `necesidad_primera_respuesta` (NO `primera_respuesta`)

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Duplicados en BD | No se envía id_seccion | Siempre enviar id_seccion |
| Foto se pierde | No se envía fotografia | Siempre enviar fotografia en 1:N |
| Sync falla "column fotografia does not exist" | Enviar fotografia en 1:1 | NO incluir fotografia en 1:1 |
| Sync falla "no unique constraint matching" | Índice parcial con WHERE | Backend: usar índice sin WHERE |
| 422 "Foto requiere coordenadas" | Foto sin coordenadas | Incluir coordenada_lat/lon |
| Nombre de campo incorrecto | Usar `primera_respuesta` | Usar `necesidad_primera_respuesta` |
