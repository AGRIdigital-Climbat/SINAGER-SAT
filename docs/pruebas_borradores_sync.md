# Pruebas de Sincronización de Borradores EDAN

## Contexto del Problema

**Reporte:** Cuando se llena el formulario EDAN y se envía directamente, funciona correctamente (fotos y coordenadas se sincronizan). Pero cuando se **guarda como borrador** primero y luego se intenta sincronizar, no se envía nada.

**Hipótesis:** El problema está en la app Flutter, NO en el backend. Las pruebas demuestran que el backend acepta y procesa borradores correctamente.

---

## Escenarios de Prueba Ejecutados

### Escenario 1: Borrador con solo secciones 1:1

**Descripción:** Crear una localidad en estado borrador con únicamente la sección de primera respuesta (1:1), sin secciones 1:N.

**Payload:**
```json
{
  "localidades": [{
    "id_local": "test-borrador-001",
    "id_usuario": 30,
    "id_tipo_localidad": 1,
    "id_edan_localidad_estado": 1,
    "id_municipio": 70101,
    "localidad": "Borrador Test Solo PR",
    "fecha_llenado": "2026-08-25",
    "total_poblacion_afectada": 10,
    "necesidad_primera_respuesta": {
      "id_seccion": "pr_1693012345_test001",
      "busqueda": true,
      "salvamento": false,
      "evacuacion": true,
      "observaciones": "Borrador parcial"
    }
  }]
}
```

**Resultado:** ✅ **PASÓ**
- `id_edan_localidad`: 211
- `aplicado`: true
- `conflicto`: false
- Sección 1:1 guardada con `id_seccion`

**Estado en BD:**
```sql
SELECT 'primera_respuesta' as tabla, id_seccion, busqueda, evacuacion 
FROM edan.edan_localidades_primera_respuesta WHERE id_edan_localidad = 211;

-- Resultado:
-- tabla              | id_seccion              | busqueda | evacuacion
-- primera_respuesta  | pr_1693012345_test001   | t        | t
```

---

### Escenario 2: Borrador con secciones 1:N sin fotos

**Descripción:** Crear borrador con secciones 1:N (servicios básicos, daños viales) pero sin fotos.

**Payload:**
```json
{
  "localidades": [{
    "id_local": "test-borrador-002",
    "id_usuario": 30,
    "id_tipo_localidad": 1,
    "id_edan_localidad_estado": 1,
    "id_municipio": 70101,
    "localidad": "Borrador Test Con 1:N",
    "fecha_llenado": "2026-08-25",
    "total_poblacion_afectada": 25,
    "necesidad_primera_respuesta": {
      "id_seccion": "pr_1693012345_test002",
      "busqueda": true,
      "salvamento": true,
      "evacuacion": false,
      "observaciones": "Borrador con 1:N"
    },
    "servicios_basicos": [
      {
        "id_seccion": "sb_1693012345_test002a",
        "tipo": "energia_electrica",
        "dano_parcial": true,
        "dano_total": false,
        "necesidades_inmediatas": "Postes caidos"
      },
      {
        "id_seccion": "sb_1693012345_test002b",
        "tipo": "agua_potable",
        "dano_parcial": false,
        "dano_total": true,
        "necesidades_inmediatas": "Tuberia rota"
      }
    ],
    "danos_viales": [{
      "id_seccion": "dv_1693012345_test002",
      "via": true,
      "puente": false,
      "tramo": "Av. Principal km 5",
      "dano_parcial": true,
      "dano_total": false,
      "km_danio": 2.5
    }]
  }]
}
```

**Resultado:** ✅ **PASÓ**
- `id_edan_localidad`: 212
- 3 secciones 1:N creadas con `id_seccion`

**Estado en BD:**
```sql
SELECT tabla, id_seccion, tipo, dano_parcial FROM (
  SELECT 'servicios_basicos' as tabla, id_seccion, tipo, dano_parcial FROM edan.edan_localidades_servicios_basicos WHERE id_edan_localidad = 212
  UNION ALL
  SELECT 'danos_viales', id_seccion, NULL, dano_parcial FROM edan.edan_localidades_danos_viales WHERE id_edan_localidad = 212
  UNION ALL
  SELECT 'primera_respuesta', id_seccion, NULL, NULL FROM edan.edan_localidades_primera_respuesta WHERE id_edan_localidad = 212
) ORDER BY tabla;

-- Resultado: 4 filas con id_seccion correcto
```

---

### Escenario 3: Re-sync del mismo borrador (UPSERT)

**Descripción:** Editar un borrador existente y re-sincronizar para verificar que NO se duplican las secciones.

**Payload:** Mismo `id_local` pero con datos modificados.

**Resultado:** ✅ **PASÓ**
- `aplicado`: true
- `conflicto`: false
- **Sin duplicados** en BD

**Verificación en BD:**
```sql
SELECT COUNT(*) as total_sb FROM edan.edan_localidades_servicios_basicos WHERE id_edan_localidad = 212;
-- Resultado: 2 (mismo número que antes del re-sync)

SELECT id_seccion, tipo, dano_total, observaciones FROM edan.edan_localidades_servicios_basicos WHERE id_edan_localidad = 212;
-- Resultado: Datos actualizados, NO duplicados
```

---

### Escenario 4: Borrador sin secciones (solo cabecera)

**Descripción:** Crear localidad en estado borrador sin ninguna sección (formulario recién iniciado).

**Payload:**
```json
{
  "localidades": [{
    "id_local": "test-borrador-003",
    "id_usuario": 30,
    "id_tipo_localidad": 1,
    "id_edan_localidad_estado": 1,
    "id_municipio": 70101,
    "localidad": "Borrador Vacio",
    "fecha_llenado": "2026-08-25",
    "total_poblacion_afectada": 0
  }]
}
```

**Resultado:** ✅ **PASÓ**
- `id_edan_localidad`: 213
- Localidad creada sin secciones
- Backend NO crea filas 1:1 vacías si no se envían

---

### Escenario 5: Upload de foto con endpoint con-foto + id_seccion

**Descripción:** Subir foto para una sección 1:N existente usando el endpoint con-foto con `id_seccion`.

**Comando:**
```bash
curl http://127.0.0.1:8000/api/v1/edan/localidades/212/servicios-basicos/con-foto \
  -X POST \
  -F "file=@/tmp/test_photo.jpg" \
  -F "tipo=energia_electrica" \
  -F "dano_parcial=true" \
  -F "dano_total=true" \
  -F "coordenada_lat=-17.783" \
  -F "coordenada_lon=-63.182" \
  -F "id_seccion=sb_1693012345_test002a"
```

**Resultado:** ✅ **PASÓ**
- `fotografia`: `/uploads/reports/070101/070101_30_8769479332e4.jpg`
- `id_seccion`: `sb_1693012345_test002a` (se mantuvo)
- Coordenadas guardadas correctamente

---

### Escenario 6: Re-sync con foto existente

**Descripción:** Re-sincronizar un borrador que YA tiene fotos subidas para verificar que no se pierden.

**Payload:** Incluye `fotografia` y `coordenadas` en el payload de sync.

**Resultado:** ✅ **PASÓ**
- Foto se mantiene después del re-sync
- `servicios_basicos[0].fotografia`: `/uploads/reports/070101/070101...`
- `servicios_basicos[1].fotografia`: null (sin foto)

---

### Escenario 7: Pull de sincronización (recuperar borradores)

**Descripción:** Verificar que el endpoint de pull devuelve borradores correctamente.

**Comando:**
```bash
curl "http://127.0.0.1:8000/api/v1/edan/localidades/sync/pull?id_usuario=30&limit=5"
```

**Resultado:** ✅ **PASÓ**
- Borradores se recuperan correctamente
- Todos los campos incluidos (estado, secciones, etc.)

**Respuesta:**
```
  ID: 213, Localidad: Borrador Vacio, Estado: Borrador, SB: 0
  ID: 211, Localidad: Borrador Test Solo PR, Estado: Borrador, SB: 0
  ID: 212, Localidad: Borrador Test Con 1:N - EDITADO, Estado: Borrador, SB: 2
  ID: 199, Localidad: San Jacinto, Estado: En revision UGR, SB: 0
  ID: 204, Localidad: Bernardo, Estado: En revision UGR, SB: 5
```

---

### Escenario 8: Borrador completo (3x 1:1 + 1x 1:N)

**Descripción:** Crear borrador con TODAS las secciones 1:1 (PR, SN, NH) + 1 sección 1:N.

**Payload:**
```json
{
  "localidades": [{
    "id_local": "test-borrador-004",
    "id_usuario": 30,
    "id_tipo_localidad": 1,
    "id_edan_localidad_estado": 1,
    "id_municipio": 70101,
    "localidad": "Borrador Completo 1:1",
    "total_poblacion_afectada": 50,
    "necesidad_primera_respuesta": {
      "id_seccion": "pr_test_borrador_004",
      "busqueda": true,
      "observaciones": "Borrador con PR"
    },
    "necesidad_salud": {
      "id_seccion": "sn_test_borrador_004",
      "numero_personas": 15,
      "otras_necesidades": "Medicinas"
    },
    "necesidad_humanitaria": {
      "id_seccion": "nh_test_borrador_004",
      "alimentos": true,
      "refugio_vivienda": true
    },
    "danos_viales": [{
      "id_seccion": "dv_test_borrador_004",
      "via": true,
      "tramo": "Ruta 4",
      "dano_parcial": true
    }]
  }]
}
```

**Resultado:** ✅ **PASÓ**
- `id_edan_localidad`: 214
- Todas las secciones creadas con `id_seccion`

**Verificación en BD:**
```sql
SELECT tabla, id_seccion FROM (
  SELECT 'primera_respuesta' as tabla, id_seccion FROM edan.edan_localidades_primera_respuesta WHERE id_edan_localidad = 214
  UNION ALL SELECT 'salud_necesidades', id_seccion FROM edan.edan_localidades_salud_necesidades WHERE id_edan_localidad = 214
  UNION ALL SELECT 'necesidades_humanitarias', id_seccion FROM edan.edan_localidades_necesidades_humanitarias WHERE id_edan_localidad = 214
  UNION ALL SELECT 'danos_viales', id_seccion FROM edan.edan_localidades_danos_viales WHERE id_edan_localidad = 214
) ORDER BY tabla;

-- Resultado:
-- tabla              | id_seccion
-- primera_respuesta  | pr_test_borrador_004
-- salud_necesidades  | sn_test_borrador_004
-- necesidades_humanitarias | nh_test_borrador_004
-- danos_viales       | dv_test_borrador_004
```

---

## Tabla Resumen de Resultados

| # | Escenario | Resultado | Observaciones |
|---|-----------|-----------|---------------|
| 1 | Borrador solo 1:1 (PR) | ✅ PASÓ | Backend acepta borradores parciales |
| 2 | Borrador con 1:N sin fotos | ✅ PASÓ | Fotos NO son obligatorias en sync |
| 3 | Re-sync (UPSERT) | ✅ PASÓ | No hay duplicados, datos se actualizan |
| 4 | Borrador vacío | ✅ PASÓ | Solo cabecera sin secciones |
| 5 | Upload foto con-foto + id_seccion | ✅ PASÓ | id_seccion se mantiene |
| 6 | Re-sync con foto existente | ✅ PASÓ | Fotos no se pierden |
| 7 | Pull de borradores | ✅ PASÓ | Backend devuelve borradores |
| 8 | Borrador completo (3x1:1 + 1x1:N) | ✅ PASÓ | Todas las secciones con id_seccion |

---

## Conclusión: Backend Funciona Correctamente

**✅ El backend acepta, procesa y almacena borradores sin problemas.**

**❌ El problema está en la app Flutter.**

---

## 🔍 Prioridades de Revisión en Flutter App

### 1. `getUnsyncedLocalidades()` en `database_helper.dart` (CRÍTICO)

**Qué buscar:**
```dart
// ¿Hay un filtro que excluye borradores?
// ❌ INCORRECTO:
WHERE es_borrador = 0 OR id_edan_localidad_estado > 1

// ✅ CORRECTO:
WHERE sincronizado = 0  // Sin filtro de estado
```

**Ubicación esperada:** `lib/services/database_helper.dart`

---

### 2. `EdanLocalidad.toApiJson()` (CRÍTICO)

**Qué buscar:**
```dart
// ¿Incluye id_edan_localidad_estado SIEMPRE?
Map<String, dynamic> toApiJson() => {
  'id_edan_localidad_estado': idEdanLocalidadEstado,  // ✅ Debe incluirse
  // ...
};
```

**Problema potencial:** Si `idEdanLocalidadEstado` es null o 0, el backend puede rechazar o asignar estado por defecto.

**Ubicación esperada:** `lib/models/edan.dart` (clase `EdanLocalidad`)

---

### 3. `_pushLocalidades()` en `localidad_sync_service.dart` (ALTA)

**Qué buscar:**
```dart
// ¿Filtra localidades por estado antes de enviar?
// ❌ INCORRECTO:
if (loc.estadoLocalidad == UgrLocalidadEstado.borrador) continue;

// ✅ CORRECTO: No filtrar por estado
for (final loc in pendientes) {
  // Enviar TODAS las localidades pendientes
}
```

**Ubicación esperada:** `lib/services/localidad_sync_service.dart`

---

### 4. Generación de `id_seccion` para borradores (MEDIA)

**Qué verificar:**
- Cuando se guarda como borrador, ¿se genera `id_seccion` para cada sección?
- El fallback en `_construirLocalidad()` debe incluir borradores

**Ubicación esperada:** `lib/screens/role_screens/resp/resp_edan_form_screen.dart`

---

## Flujo Esperado vs Flujo Actual

### Flujo Esperado (Direct Send - Funciona ✅)

```
Usuario llena formulario
       ↓
Usuario presiona "Enviar" (no guarda como borrador)
       ↓
_construirLocalidad() genera id_seccion para todas las secciones
       ↓
toApiJson() serializa con id_edan_localidad_estado = 2 (Enviado UGR)
       ↓
_pushLocalidades() envía al backend
       ↓
Backend recibe y procesa (id_edan_localidad_estado = 2)
       ↓
✅ Sincronización exitosa
```

### Flujo Actual (Borrador - Falla ❌)

```
Usuario llena formulario parcialmente
       ↓
Usuario presiona "Guardar Borrador"
       ↓
?? ¿Se genera id_seccion para las secciones marcadas?
       ↓
?? ¿toApiJson() incluye id_edan_localidad_estado = 1?
       ↓
?? ¿getUnsyncedLocalidades() incluye borradores?
       ↓
?? ¿_pushLocalidades() envía borradores?
       ↓
❌ Sincronización NO se ejecuta
```

---

## 🔧 Acciones Recomendadas

### Inmediatas (hacer YA):

1. **Revisar `getUnsyncedLocalidades()`** en Flutter
   - Verificar que NO hay filtro por `id_edan_localidad_estado`
   - Asegurar que solo filtra por `sincronizado = false`

2. **Revisar `toApiJson()` de `EdanLocalidad`**
   - Verificar que `id_edan_localidad_estado` se incluye SIEMPRE
   - Para borradores: debe ser `1`

3. **Agregar logging temporal** en Flutter:
   ```dart
   debugPrint('Borradores pendientes: ${pendientes.where((l) => l.idEdanLocalidadEstado == 1).length}');
   debugPrint('Payload sync: ${jsonEncode(localidadesJson)}');
   ```

### Secundarias (después de fix):

4. **Revisar generación de `id_seccion`** para borradores
5. **Verificar `_pushLocalidades()`** no filtra por estado
6. **Tests unitarios** para borradores en Flutter

---

## Referencias

- Backend: `api/edan/service.py` - Función `localidad_sync_upsert()` (línea 1572)
- Backend: `api/edan/schemas.py` - Clase `LocalidadCreate` (línea 225)
- Flutter: `lib/services/localidad_sync_service.dart` - Método `sincronizar()`
- Flutter: `lib/models/edan.dart` - Clase `EdanLocalidad.toApiJson()`
- Flutter: `lib/services/database_helper.dart` - Método `getUnsyncedLocalidades()`
