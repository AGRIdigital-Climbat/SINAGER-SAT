# Guía de `id_seccion` para Flutter

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

### Modelo con id_seccion

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
    // NO incluir fotografia aquí (se sube por separado)
  };
}
```

### Crear sección offline

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

### Editar sección offline

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

### Sync con id_seccion

```dart
// El sync payload incluye id_seccion para cada sección
final payload = {
  'localidades': [{
    'id_local': 'abc-123',
    'servicios_basicos': [
      {
        'id_seccion': 'sb_1693012345_abc123def',  // ← Incluir
        'tipo': 'energia_electrica',
        'dano_parcial': true,
        'fotografia': '/uploads/reports/70101/...',  // ← Path server
      }
    ],
    'primera_respuesta': {
      'id_seccion': 'pr_1693012345_ghi456jkl',  // ← Incluir
      'busqueda': true,
      'salvamento': false,
    }
  }]
};
```

## Tablas que Requieren `id_seccion`

### 1:N (múltiples filas por localidad)

| Tabla | Prefijo | Ejemplo |
|-------|---------|---------|
| `servicios_basicos` | `sb` | `sb_1693012345_abc123def` |
| `salud_establecimientos` | `sv` | `sv_1693012345_ghi456jkl` |
| `danos_viales` | `dv` | `dv_1693012345_mno789pqr` |
| `danos_infra_publica` | `di` | `di_1693012345_qrs456tuv` |
| `unidades_educativas` | `ue` | `ue_1693012345_wxy789zab` |
| `danos_vivienda` | `vv` | `vv_1693012345_cde123fgh` |
| `danos_agricultura` | `da` | `da_1693012345_ijk456lmn` |
| `danos_pecuario` | `dp` | `dp_1693012345_opq789rst` |
| `infra_productiva` | `ip` | `ip_1693012345_uvw123xyz` |
| `impacto_poblacion` | `im` | `im_1693012345_abc456def` |
| `proteccion` | `po` | `po_1693012345_efg789hij` |

### 1:1 (una fila por localidad)

| Tabla | Prefijo | Ejemplo |
|-------|---------|---------|
| `primera_respuesta` | `pr` | `pr_1693012345_klm123nop` |
| `salud_necesidades` | `sn` | `sn_1693012345_stu123vwx` |
| `necesidades_humanitarias` | `nh` | `nh_1693012345_yza456bcd` |

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
│ 1. Subir fotos (si hay locales) → obtener paths server         │
│ 2. Incluir id_seccion en payload                                │
│ 3. Incluir fotografia (path server) en payload                 │
│ 4. POST /localidades/sync                                       │
│ 5. Backend: UPSERT por id_seccion                               │
└─────────────────────────────────────────────────────────────────┘
```

## Reglas de Oro

1. **Generar id_seccion UNA VEZ** al crear la sección
2. **NUNCA regenerar** al editar
3. **SIEMPRE enviar** id_seccion en el sync payload
4. **SIEMPRE enviar** fotografia (aunque sea null o path existente)
5. **Subir fotos ANTES** del sync (via POST /upload)

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Duplicados en BD | No se envía id_seccion | Siempre enviar id_seccion |
| Foto se pierde | No se envía fotografia | Siempre enviar fotografia |
| Sync falla | id_seccion duplicado | Nunca regenerar id_seccion |
| 422 "Foto requiere coordenadas" | Foto sin coordenadas | Incluir coordenada_lat/lon |
