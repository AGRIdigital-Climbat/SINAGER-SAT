# Sincronización de Fotos — Ejemplos Prácticos

## Regla Fundamental

**Las fotos SIEMPRE se suben ANTES de sincronizar el JSON.**

```
1. POST /upload        → sube archivo, retorna path server
2. POST /localidades/sync → envía JSON con el path server
```

El sync endpoint **solo acepta JSON** (no archivos). La foto debe existir en el servidor antes del sync.

---

## Endpoint POST /upload

### Parámetros

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `file` | File | ✅ | JPEG, PNG, WEBP o GIF. Max 5 MB |
| `id_municipio` | int | ❌ | Código INE del municipio (para nombre del archivo) |
| `id_usuario` | int | ❌ | ID del usuario (auto-asignado si no se envía) |

### Respuesta exitosa (201)

```json
{
  "status": "success",
  "message": "Archivo subido correctamente",
  "data": {
    "path": "/uploads/reports/70101/70101_123_abc12345def6.jpg"
  }
}
```

### Formato del path

```
/uploads/reports/{codigo_ine}/{codigo_ine}_{id_usuario}_{timestamp}{ext}
```

Ejemplo: `/uploads/reports/70101/70101_7051296_1693012345_ab12.jpg`

---

## Caso 1: Crear Localidad con Foto (Online)

### Flujo paso a paso

```
Paso 1: Subir foto → obtener path server
Paso 2: Sync con JSON → incluir path
```

### Paso 1 — Subir la foto

```bash
TOKEN="eyJhbGciOiJIUzI1NiIs..."

curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@foto_energia.jpg" \
  -F "id_municipio=70101"
```

Respuesta:
```json
{
  "status": "success",
  "data": {
    "path": "/uploads/reports/70101/70101_7051296_1693012345_ab12.jpg"
  }
}
```

### Paso 2 — Crear la localidad con el path

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "EDAN-LP-001",
      "localidad": "Villa Esperanza",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "servicios_basicos": [
        {
          "id_seccion": "1a0357323cb-659d0c9c3d415",
          "tipo": "energia_electrica",
          "dano_parcial": true,
          "dano_total": false,
          "fotografia": "/uploads/reports/70101/70101_7051296_1693012345_ab12.jpg",
          "coordenada_lat": -16.5045,
          "coordenada_lon": -68.1532
        }
      ],
      "infra_productiva": [
        {
          "id_seccion": "1a0357323cb-659d0c9c3d416",
          "tipo": "establecimiento_salud",
          "dano_parcial": false,
          "dano_total": false,
          "fotografia": null
        }
      ]
    }]
  }'
```

**Resultado:**
```
servicios_basicos[0]: INSERT con foto ✅
infra_productiva[0]: INSERT sin foto ✅
```

---

## Caso 2: Editar Localidad, Agregar Foto

### Flujo

```
Estado actual: localidad tiene servicios_basicos sin foto
Objetivo: editar servicio y agregar foto
```

### Paso 1 — Subir la nueva foto

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@foto_nueva_agua.jpg" \
  -F "id_municipio=70101"
```

Respuesta:
```json
{
  "data": {
    "path": "/uploads/reports/70101/70101_7051296_1693045678_cd34.jpg"
  }
}
```

### Paso 2 — Sync con el servicio actualizado

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "EDAN-LP-001",
      "servicios_basicos": [
        {
          "id_seccion": "s-agua-001",
          "tipo": "agua_potable",
          "dano_parcial": false,
          "dano_total": false,
          "fotografia": "/uploads/reports/70101/70101_7051296_1693045678_cd34.jpg",
          "coordenada_lat": -16.5100,
          "coordenada_lon": -68.1600
        }
      ]
    }]
  }'
```

**Resultado:**
```
s-agua-001: UPSERT → foto actualizada ✅
```

---

## Caso 3: Editar Sin Cambiar Foto

**Clave:** reenviar el path existente. Si lo omites, la foto se pierde.

### Estado actual en BD
```
id_seccion: "s-energia-001"
fotografia: "/uploads/reports/70101/70101_7051296_1693012345_ab12.jpg"
```

### Sync — reenviar el mismo path

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "EDAN-LP-001",
      "servicios_basicos": [
        {
          "id_seccion": "s-energia-001",
          "tipo": "energia_electrica",
          "dano_parcial": false,
          "dano_total": false,
          "fotografia": "/uploads/reports/70101/70101_7051296_1693012345_ab12.jpg"
        }
      ]
    }]
  }'
```

**Resultado:**
```
s-energia-001: UPSERT → foto preservada ✅
```

### ❌ INCORRECTO — omitir fotografia

```json
{
  "id_seccion": "s-energia-001",
  "tipo": "energia_electrica",
  "dano_parcial": false
  // fotografia OMITIDO → backend setea NULL → foto PERDIDA
}
```

---

## Caso 4: Offline-First (Foto Local → Sync)

Este es el caso más importante: usuario toma foto sin internet, luego sincroniza.

### Flujo completo

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: OFFLINE (sin internet)                             │
│                                                             │
│ 1. Usuario toma foto de la energía eléctrica                │
│ 2. App guarda foto en: /data/user/0/com.app/files/foto.jpg │
│ 3. App guarda en SQLite:                                    │
│    {                                                       │
│      id_seccion: "1a0357323cb-659d0c9c3d415",              │
│      tipo: "energia_electrica",                             │
│      fotografia: "/data/user/0/com.app/files/foto.jpg",    │
│      sincronizado: false                                    │
│    }                                                       │
│ 4. App genera id_seccion UNA VEZ y lo guarda               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: ONLINE (viene internet)                            │
│                                                             │
│ 5. App detecta: foto local → necesita upload               │
│ 6. App lee archivo local                                   │
│ 7. POST /upload con el archivo                             │
│ 8. Respuesta: path server = "/uploads/reports/70101/..."   │
│ 9. App actualiza SQLite:                                    │
│    UPDATE ... SET fotografia="/uploads/reports/70101/..."  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: SYNC                                               │
│                                                             │
│ 10. POST /localidades/sync con JSON                        │
│ 11. fotografia = path server (ya existe en servidor)       │
│ 12. Backend: UPSERT por id_seccion                         │
│ 13. Resultado: foto sincronizada correctamente ✅          │
└─────────────────────────────────────────────────────────────┘
```

### Código Flutter (pseudocódigo)

```dart
// FASE 1: Usuario toma foto (offline)
Future<void> tomarFoto(String idSeccion) async {
  final image = await ImagePicker().pickImage(source: ImageSource.camera);
  if (image == null) return;

  // Guardar foto localmente
  final localPath = await copiarArchivoLocal(image.path);

  // Guardar en SQLite
  await db.insert('servicios_basicos', {
    'id_seccion': idSeccion,
    'tipo': 'energia_electrica',
    'fotografia': localPath,           // ← path LOCAL
    'sincronizado': 0,                 // ← flag pendiente
  });
}

// FASE 2: Subir foto cuando hay internet
Future<String> subirFoto(String localPath, int idMunicipio) async {
  final file = File(localPath);
  final formData = FormData.fromMap({
    'file': await MultipartFile.fromFile(file.path),
    'id_municipio': idMunicipio,
  });

  final response = await dio.post('/api/v1/upload', data: formData);
  return response.data['data']['path'];  // ← path SERVER
}

// FASE 3: Sync
Future<void> sincronizar() async {
  // 1. Buscar fotos pendientes
  final pendientes = await db.rawQuery(
    "SELECT * FROM servicios_basicos WHERE sincronizado = 0"
  );

  for (final row in pendientes) {
    final foto = row['fotografia'];
    if (foto != null && foto.startsWith('/data/')) {
      // 2. Subir foto local
      final serverPath = await subirFoto(foto, idMunicipio);
      // 3. Actualizar SQLite
      await db.rawUpdate(
        'UPDATE servicios_basicos SET fotografia = ? WHERE id_seccion = ?',
        [serverPath, row['id_seccion']]
      );
    }
  }

  // 4. Sync JSON
  final payload = armarPayload();
  await dio.post('/api/v1/edan/localidades/sync', data: payload);
}
```

---

## Convención de Paths

| Tipo | Ejemplo | Estado |
|------|---------|--------|
| **Local** | `/data/user/0/com.app/files/foto.jpg` | ❌ NO sincronizada |
| **Local** | `file:///data/user/0/.../foto.jpg` | ❌ NO sincronizada |
| **Local** | `/storage/emulated/0/DCIM/foto.jpg` | ❌ NO sincronizada |
| **Server** | `/uploads/reports/70101/70101_7051296_abc.jpg` | ✅ YA sincronizada |

### Detección automática

```dart
bool fotoNecesitaSync(String? fotografia) {
  if (fotografia == null || fotografia.isEmpty) return false;
  // Si empieza con /uploads/ → ya está en el servidor
  return !fotografia.startsWith('/uploads/');
}
```

---

## Caso 5: Múltiples Fotos en Un Solo Sync

Subir varias fotos antes del sync:

```bash
# Foto 1: energía
FOTO1=$(curl -s -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@energia.jpg" \
  -F "id_municipio=70101" | jq -r '.data.path')

# Foto 2: agua
FOTO2=$(curl -s -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@agua.jpg" \
  -F "id_municipio=70101" | jq -r '.data.path')

# Foto 3: vial
FOTO3=$(curl -s -X POST "http://localhost:8000/api/v1/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@vial.jpg" \
  -F "id_municipio=70101" | jq -r '.data.path')

# Sync con todas las fotos
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"localidades\": [{
      \"id_local\": \"EDAN-LP-002\",
      \"localidad\": \"Villa Nueva\",
      \"id_tipo_localidad\": 1,
      \"id_edan_localidad_estado\": 1,
      \"id_municipio\": 70101,
      \"id_departamento\": 7,
      \"id_provincia\": 701,
      \"servicios_basicos\": [
        {
          \"id_seccion\": \"s-001\",
          \"tipo\": \"energia_electrica\",
          \"dano_parcial\": true,
          \"fotografia\": \"$FOTO1\",
          \"coordenada_lat\": -16.50,
          \"coordenada_lon\": -68.15
        },
        {
          \"id_seccion\": \"s-002\",
          \"tipo\": \"agua_potable\",
          \"fotografia\": \"$FOTO2\",
          \"coordenada_lat\": -16.51,
          \"coordenada_lon\": -68.16
        }
      ],
      \"danos_viales\": [
        {
          \"id_seccion\": \"s-003\",
          \"via\": true,
          \"tramo\": \"Av. Principal\",
          \"km_danio\": 0,
          \"fotografia\": \"$FOTO3\",
          \"coordenada_lat\": -16.52,
          \"coordenada_lon\": -68.17
        }
      ]
    }]
  }"
```

---

## Caso 6: Reintentar Sync (Falla Parcial)

Si el sync falla después de subir fotos, las fotos ya están en el servidor. No hay que volver a subirlas.

```dart
Future<void> reintentarSync() async {
  // Buscar localidades pendientes
  final pendientes = await db.rawQuery(
    "SELECT * FROM localidades WHERE sincronizado = 0"
  );

  for (final loc in pendientes) {
    // Verificar si las fotos ya están subidas
    final secciones = await db.rawQuery(
      "SELECT * FROM servicios_basicos WHERE id_local = ?",
      [loc['id_local']]
    );

    for (final sec in secciones) {
      final foto = sec['fotografia'];
      if (foto != null && foto.startsWith('/data/')) {
        // Foto LOCAL → subir
        final serverPath = await subirFoto(foto, loc['id_municipio']);
        await db.rawUpdate(
          'UPDATE servicios_basicos SET fotografia = ? WHERE id_seccion = ?',
          [serverPath, sec['id_seccion']]
        );
      }
      // Foto SERVER → skip (ya subida)
    }

    // Sync
    final payload = armarPayload(loc);
    try {
      await dio.post('/api/v1/edan/localidades/sync', data: payload);
      await db.rawUpdate(
        'UPDATE localidades SET sincronizado = 1 WHERE id_local = ?',
        [loc['id_local']]
      );
    } catch (e) {
      // Error en sync → reintentar después
      print('Sync falló para ${loc['id_local']}: $e');
    }
  }
}
```

---

## Resumen: Flujo Correcto

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO CORRECTO                               │
│                                                                 │
│  1. ¿Hay fotos nuevas?                                          │
│     → SÍ: POST /upload (por cada foto)                         │
│     → NO: pasar al paso 2                                      │
│                                                                 │
│  2. Actualizar paths locales con paths server en SQLite         │
│     → UPDATE ... SET fotografia = '/uploads/...'               │
│                                                                 │
│  3. POST /localidades/sync (JSON con paths server)             │
│     → Backend: UPSERT por id_seccion                           │
│     → Backend: guardar path string tal cual                    │
│                                                                 │
│  4. Actualizar flags de sincronizado                           │
│     → UPDATE ... SET sincronizado = 1                          │
└─────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO INCORRECTO                             │
│                                                                 │
│  ❌ Enviar path LOCAL en el sync endpoint                      │
│     → Foto nunca llega al servidor                             │
│                                                                 │
│  ❌ Omitir campo fotografia en el JSON                         │
│     → Backend setea NULL, foto se pierde                        │
│                                                                 │
│  ❌ Subir foto Y sincronizar en el mismo paso                  │
│     → El sync endpoint no acepta archivos                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| Foto desaparece después de sync | Campo `fotografia` omitido en JSON | Siempre enviar el campo (aunque sea `null`) |
| Foto nunca en servidor | Path local enviado en sync | Subir foto ANTES con `POST /upload` |
| 422 "Foto requiere coordenadas" | Foto sin coordenadas GPS | Enviar `coordenada_lat` y `coordenada_lon` |
| Duplicados de sección | Nuevo `id_seccion` en cada edición | Reusar `id_seccion` existente |
| Sync falla "unique constraint" | Índice parcial incompatible | Ejecutar migración `v2.9.1_fix_indexes.sql` |

---

## Checklist para el Cliente

- [ ] `POST /upload` antes de sync si hay fotos locales
- [ ] Actualizar SQLite con path server después de upload
- [ ] Siempre incluir campo `fotografia` en JSON (aunque sea `null`)
- [ ] Reenviar path existente si la foto no cambió
- [ ] Generar `id_seccion` UNA VEZ al crear sección
- [ ] Reusar `id_seccion` al editar sección
- [ ] Si hay foto → incluir `coordenada_lat` y `coordenada_lon`
- [ ] Detectar path local vs server: `fotografia.startsWith('/uploads/')`
