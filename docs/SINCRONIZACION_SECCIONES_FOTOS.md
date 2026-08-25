# Sincronización de Secciones con Fotografías

## Resumen ejecutivo

La versión v2.9.0 implementa `id_seccion` + UPSERT para permitir edición de secciones offline sin duplicados, incluyendo manejo completo de fotografías.

---

## Problema resuelto

### Antes (v2.8.0)

```
1. App crea "Molino" offline con foto → INSERT (id=1, foto="a.jpg")
2. App edita "Molino" offline → INSERT nuevo (id=2, foto="a.jpg") ← DUPLICADO!
```

**Resultado:** 2 filas idénticas en `edan_localidades_infra_productiva`.

### Después (v2.9.0)

```
1. App crea "Molino" offline con foto → INSERT (id_seccion="x", foto="a.jpg")
2. App edita "Molino" offline → UPDATE (id_seccion="x", foto="a.jpg")
```

**Resultado:** 1 fila actualizada (NO duplica).

---

## Mecanismo técnico

### UPSERT por `id_seccion`

```sql
INSERT INTO edan.edan_localidades_servicios_basicos
    (id_edan_localidad, id_seccion, tipo, dano_parcial, fotografia, ...)
VALUES (:id, :id_seccion, :tipo, :dano_parcial, :fotografia, ...)
ON CONFLICT (id_seccion) DO UPDATE SET
    tipo = EXCLUDED.tipo,
    dano_parcial = EXCLUDED.dano_parcial,
    fotografia = EXCLUDED.fotografia,  -- ← Foto se actualiza SIEMPRE
    ...
```

### Comportamiento del UPSERT

| Valor enviado | Backend hace | Resultado en BD |
|--------------|-------------|-----------------|
| `fotografia: "/path.jpg"` | `fotografia = EXCLUDED.fotografia` | Actualiza path |
| `fotografia: null` | `fotografia = EXCLUDED.fotografia` | **Borra** foto (setea NULL) |
| `fotografia: undefined` (omitido) | `fotografia = EXCLUDED.fotografia` | **Borra** foto (setea NULL) |

⚠️ **IMPORTANTE:** El backend SIEMPRE actualiza `fotografia` con el valor recibido. Si el cliente omite el campo, la foto existente se pierde.

---

## Flujos completos con ejemplos

### Flujo 1: Crear sección con foto

**Cliente (offline):**
```typescript
const energia = {
  id_seccion: generarIdSeccion(),  // "1a0357323cb-659d0c9c3d415"
  tipo: "energia_electrica",
  dano_parcial: true,
  fotografia: "/uploads/energia_001.jpg"  // ← Foto subida previamente
};

await sync({ servicios_basicos: [energia] });
```

**Backend:** INSERT

**BD:**
```
 id_seccion           | tipo             | fotografia
----------------------+------------------+------------------------
 1a0357323cb-659d... | energia_electrica | /uploads/energia_001.jpg
```

---

### Flujo 2: Editar sección (manteniendo foto)

**Cliente (offline):**
```typescript
const energiaEditada = {
  id_seccion: "1a0357323cb-659d0c9c3d415",  // ← MISMO id_seccion
  tipo: "energia_electrica",
  dano_parcial: false,  // ← Cambia daño
  fotografia: "/uploads/energia_001.jpg"  // ← REENVIAR path existente
};

await sync({ servicios_basicos: [energiaEditada] });
```

**Backend:** UPDATE por `id_seccion`

**BD:**
```
 id_seccion           | tipo             | fotografia                  | dano_parcial
----------------------+------------------+----------------------------+--------------
 1a0357323cb-659d... | energia_electrica | /uploads/energia_001.jpg   | false (actualizado)
```

✅ Foto preservada, daño actualizado.

---

### Flujo 3: Editar sección (cambiando foto)

**Cliente (offline):**
```typescript
const energiaNuevaFoto = {
  id_seccion: "1a0357323cb-659d0c9c3d415",  // ← MISMO id_seccion
  tipo: "energia_electrica",
  dano_parcial: false,
  fotografia: "/uploads/energia_002.jpg"  // ← NUEVA foto (upload previo)
};

await sync({ servicios_basicos: [energiaNuevaFoto] });
```

**Backend:** UPDATE

**BD:**
```
 id_seccion           | tipo             | fotografia                 | dano_parcial
----------------------+------------------+---------------------------+--------------
 1a0357323cb-659d... | energia_electrica | /uploads/energia_002.jpg  | false
```

✅ Foto actualizada correctamente.

---

### Flujo 4: Editar sección (eliminando foto)

**Cliente (offline):**
```typescript
const energiaSinFoto = {
  id_seccion: "1a0357323cb-659d0c9c3d415",  // ← MISMO id_seccion
  tipo: "energia_electrica",
  dano_parcial: false,
  fotografia: null  // ← NULL explícito para eliminar foto
};

await sync({ servicios_basicos: [energiaSinFoto] });
```

**Backend:** UPDATE

**BD:**
```
 id_seccion           | tipo             | fotografia | dano_parcial
----------------------+------------------+------------+--------------
 1a0357323cb-659d... | energia_electrica | NULL       | false
```

✅ Foto eliminada (path borrado).

---

### Flujo 5: Editar sección (SIN enviar campo fotografia) ⚠️

**Cliente (offline):**
```typescript
const energiaSinCampo = {
  id_seccion: "1a0357323cb-659d0c9c3d415",
  tipo: "energia_electrica",
  dano_parcial: false
  // fotografia: omitido completamente
};

await sync({ servicios_basicos: [energiaSinCampo] });
```

**Backend:** UPDATE con `fotografia = NULL`

**BD:**
```
 id_seccion           | tipo             | fotografia | dano_parcial
----------------------+------------------+------------+--------------
 1a0357323cb-659d... | energia_electrica | NULL       | false
```

❌ **Foto existente se pierde** porque el campo no fue enviado.

**Conclusión:** El cliente SIEMPRE debe enviar `fotografia` completo.

---

### Flujo 6: Servicios básicos mixtos (3 tipos de foto)

**Cliente (offline):**
```typescript
const servicios = [
  {
    id_seccion: "s-001",
    tipo: "energia_electrica",
    dano_parcial: true,
    fotografia: "/uploads/energia.jpg"  // ← CON foto
  },
  {
    id_seccion: "s-002",
    tipo: "agua_potable",
    dano_parcial: false,
    fotografia: null  // ← SIN foto (null explícito)
  },
  {
    id_seccion: "s-003",
    tipo: "gas_domiciliario",
    dano_total: true
    // fotografia: omitido ← treated as NULL
  }
];

await sync({ servicios_basicos: servicios });
```

**Backend:** 3 INSERTs

**BD:**
```
 id_seccion |       tipo        |      fotografia       
------------+-------------------+-----------------------
 s-001      | energia_electrica | /uploads/energia.jpg
 s-002      | agua_potable      | NULL
 s-003      | gas_domiciliario  | NULL
```

✅ Todos los casos soportados.

---

### Flujo 7: Editar mixto (agregar/eliminar/cambiar fotos)

**Estado inicial en BD:**
```
 id_seccion | tipo  | fotografia
------------+-------+------------------------
 s-001      | gas   | /uploads/gas.jpg
 s-002      | agua  | NULL
```

**Cliente (offline) - Editar:**
```typescript
const serviciosEditados = [
  {
    id_seccion: "s-001",
    tipo: "gas_domiciliario",
    fotografia: "/uploads/gas.jpg"  // ← Mantener misma foto
  },
  {
    id_seccion: "s-002",
    tipo: "agua_potable",
    fotografia: "/uploads/agua_nueva.jpg"  // ← AGREGAR foto
  },
  {
    id_seccion: "s-003",
    tipo: "energia_electrica",
    fotografia: "/uploads/energia.jpg"  // ← NUEVO servicio con foto
  }
];

await sync({ servicios_basicos: serviciosEditados });
```

**BD resultante:**
```
 id_seccion | tipo  | fotografia
------------+-------+------------------------
 s-001      | gas   | /uploads/gas.jpg       (mantenida)
 s-002      | agua  | /uploads/agua_nueva.jpg (agregada)
 s-003      | energia | /uploads/energia.jpg (nuevo)
```

✅ Todos los casos combinados funcionan.

---

## Reglas de oro para el cliente

### 1. Generar `id_seccion` UNA VEZ

```typescript
// ✅ CORRECTO
const seccion = {
  id_seccion: generarIdSeccion(),  // UUID al crear
  tipo: "energia_electrica",
  fotografia: "/uploads/foto.jpg"
};

// ❌ INCORRECTO - no generar id_seccion
const seccion = {
  tipo: "energia_electrica",
  fotografia: "/uploads/foto.jpg"
  // id_seccion falta → INSERT cada vez → DUPLICADO
};
```

---

### 2. Reusar `id_seccion` al editar

```typescript
// ✅ CORRECTO
const seccionEditada = {
  id_seccion: "1a0357323cb-659d0c9c3d415",  // MISMO que al crear
  tipo: "energia_electrica",
  fotografia: "/uploads/foto.jpg"
};

// ❌ INCORRECTO - nuevo id_seccion en cada edición
const seccionEditada = {
  id_seccion: generarIdSeccion(),  // NUEVO → INSERT nuevo → DUPLICADO
  tipo: "energia_electrica",
  fotografia: "/uploads/foto.jpg"
};
```

---

### 3. SIEMPRE enviar `fotografia` completo

```typescript
// ✅ CORRECTO - reenviar path existente
const seccion = {
  id_seccion: "s-001",
  tipo: "energia_electrica",
  fotografia: "/uploads/existente.jpg"  // Path ya guardado en BD
};

// ❌ INCORRECTO - omitir fotografia
const seccion = {
  id_seccion: "s-001",
  tipo: "energia_electrica"
  // fotografia omitida → backend setea NULL → foto se pierde
};
```

---

### 4. NULL explícito para eliminar foto

```typescript
// ✅ CORRECTO - eliminar foto explícitamente
const seccion = {
  id_seccion: "s-001",
  tipo: "energia_electrica",
  fotografia: null  // NULL explícito borra path en BD
};

// ⚠️ INCORRECTO - omitir campo (también borra, pero es menos claro)
const seccion = {
  id_seccion: "s-001",
  tipo: "energia_electrica"
  // fotografia omitido → también borra, pero es menos explícito
};
```

---

## Implementación en el cliente

### Clase de ejemplo (TypeScript)

```typescript
interface ServicioBasico {
  id_seccion?: string;
  tipo: 'energia_electrica'|'agua_potable'|'alcantarillado'|'gas_domiciliario'|'telecomunicaciones';
  dano_parcial: boolean;
  dano_total: boolean;
  fotografia: string | null;
  coordenada_lat?: number | null;
  coordenada_lon?: number | null;
}

class ServiciosManager {
  private servicios: ServicioBasico[] = [];

  // CREAR nuevo servicio
  async crearServicio(tipo: ServicioBasico['tipo'], fotoFile?: File): Promise<ServicioBasico> {
    let fotoPath: string | null = null;
    
    if (fotoFile) {
      fotoPath = await this.uploadFoto(fotoFile);
    }
    
    const servicio: ServicioBasico = {
      id_seccion: this.generarIdSeccion(),  // ← Generar UNA VEZ
      tipo,
      dano_parcial: false,
      dano_total: false,
      fotografia: fotoPath  // ← null si no hay foto
    };
    
    this.servicios.push(servicio);
    return servicio;
  }

  // EDITAR servicio existente
  async editarServicio(
    idSeccion: string,
    cambios: Partial<ServicioBasico>,
    nuevaFoto?: File
  ): Promise<void> {
    const servicio = this.servicios.find(s => s.id_seccion === idSeccion);
    if (!servicio) throw new Error('Servicio no encontrado');

    // Si hay nueva foto, subirla y reemplazar path
    if (nuevaFoto) {
      servicio.fotografia = await this.uploadFoto(nuevaFoto);
    }

    // Si no hay nueva foto, MANTENER path existente
    // (no cambiar servicio.fotografia)

    // Aplicar otros cambios
    Object.assign(servicio, cambios);

    // id_seccion NO cambia
  }

  // ELIMINAR foto de servicio
  eliminarFoto(idSeccion: string): void {
    const servicio = this.servicios.find(s => s.id_seccion === idSeccion);
    if (servicio) {
      servicio.fotografia = null;  // ← NULL explícito
    }
  }

  // SINCRONIZAR
  async sincronizar() {
    const payload = {
      localidades: [{
        id_local: this.idLocal,
        id_tipo_localidad: 1,
        id_edan_localidad_estado: 1,
        id_municipio: this.idMunicipio,
        id_departamento: this.idDepartamento,
        id_provincia: this.idProvincia,
        servicios_basicos: this.servicios.map(s => ({
          id_seccion: s.id_seccion,        // ← SIEMPRE incluir
          tipo: s.tipo,
          dano_parcial: s.dano_parcial,
          dano_total: s.dano_total,
          fotografia: s.fotografia,        // ← SIEMPRE incluir (aunque no cambió)
          coordenada_lat: s.coordenada_lat,
          coordenada_lon: s.coordenada_lon
        }))
      }]
    };

    const response = await fetch('/api/v1/edan/localidades/sync', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();
    
    // Manejar conflictos si los hay
    if (!result.data[0].aplicado) {
      // Conflicto: servidor tiene versión más reciente
      // Adoptar versión del servidor
      this.servicios = result.data[0].data.servicios_basicos;
    }
  }

  private generarIdSeccion(): string {
    const timestamp = Date.now().toString(32);
    const uuidShort = crypto.randomUUID().replace(/-/g, '').slice(0, 13);
    return `${timestamp}-${uuidShort}`;
  }

  private async uploadFoto(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/upload', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.token}` },
      body: formData
    });
    
    const result = await response.json();
    return result.data.path_archivo;  // Ej: "/uploads/edan/..."
  }
}
```

---

## Tablas con fotografía (11 tablas 1:N)

| Tabla | Campo `fotografia` | Notas |
|-------|-------------------|-------|
| `edan_localidades_infra_productiva` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_salud_establecimientos` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_danos_viales` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_danos_infra_publica` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_servicios_basicos` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_unidades_educativas` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_danos_vivienda` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_danos_agricultura` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_danos_pecuario` | `fotografia VARCHAR` | Path completo |
| `edan_localidades_impacto_poblacion` | ❌ NO tiene | - |
| `edan_localidades_proteccion` | ❌ NO tiene | - |

**Secciones 1:1** (sin `id_seccion`, UPSERT por `id_edan_localidad`):
- `edan_localidades_primera_respuesta` - ❌ NO tiene
- `edan_localidades_salud_necesidades` - ❌ NO tiene
- `edan_localidades_necesidades_humanitarias` - ❌ NO tiene

---

## Tests verificados

### Test A: INSERT mixto (con/sin foto)

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-servicios-001",
      "localidad": "Test",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "servicios_basicos": [
        {"id_seccion": "s-001", "tipo": "energia_electrica", "fotografia": "/uploads/e1.jpg"},
        {"id_seccion": "s-002", "tipo": "agua_potable", "fotografia": null},
        {"id_seccion": "s-003", "tipo": "gas_domiciliario"}
      ]
    }]
  }'
```

**Resultado:** ✅ 3 registros creados (1 con foto, 2 sin foto)

---

### Test B: UPDATE agregando foto

```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-servicios-001",
      "servicios_basicos": [
        {"id_seccion": "s-001", "tipo": "energia_electrica", "fotografia": "/uploads/e1.jpg"},
        {"id_seccion": "s-002", "tipo": "agua_potable", "fotografia": "/uploads/a2.jpg"},
        {"id_seccion": "s-003", "tipo": "gas_domiciliario", "fotografia": null}
      ]
    }]
  }'
```

**Resultado:** ✅ 3 registros actualizados (foto agregada a s-002, eliminada de s-003)

---

### Test C: UPSERT verifica no duplicados

```sql
SELECT id_seccion, COUNT(*) as cantidad
FROM edan.edan_localidades_servicios_basicos
WHERE id_seccion LIKE 's-%'
GROUP BY id_seccion
HAVING COUNT(*) > 1;
```

**Resultado:** `0 filas` (NO hay duplicados) ✅

---

## Verificaciones en BD

```sql
-- 1. Verificar que NO hay duplicados por id_seccion
SELECT id_seccion, COUNT(*) as cantidad
FROM edan.edan_localidades_infra_productiva
WHERE id_seccion IS NOT NULL
GROUP BY id_seccion
HAVING COUNT(*) > 1;  -- Debería retornar 0 filas

-- 2. Verificar fotos actualizadas correctamente
SELECT id_seccion, tipo, fotografia, dano_parcial
FROM edan.edan_localidades_servicios_basicos
WHERE id_seccion = 's-001';

-- 3. Verificar fotos NULL (eliminadas)
SELECT id_seccion, tipo
FROM edan.edan_localidades_servicios_basicos
WHERE fotografia IS NULL;
```

---

## Troubleshooting

### Problema: Foto se pierde después de sync

**Causa:** Cliente no envía `fotografia` en el payload.

**Solución:**
```typescript
// ❌ INCORRECTO
const payload = {
  servicios_basicos: [{
    id_seccion: "s-001",
    tipo: "energia_electrica"
    // fotografia omitida
  }]
};

// ✅ CORRECTO
const payload = {
  servicios_basicos: [{
    id_seccion: "s-001",
    tipo: "energia_electrica",
    fotografia: "/uploads/existente.jpg"  // ← Reenviar path existente
  }]
};
```

---

### Problema: Sección se duplica

**Causa:** Cliente genera nuevo `id_seccion` en cada edición.

**Solución:**
```typescript
// ❌ INCORRECTO
const editar = () => {
  seccion.id_seccion = generarIdSeccion();  // ← NUEVO id → INSERT nuevo
  seccion.dano_parcial = true;
};

// ✅ CORRECTO
const editar = () => {
  // id_seccion NO se toca
  seccion.dano_parcial = true;
};
```

---

### Problema: UPSERT falla con "no unique constraint"

**Causa:** Índice único no creado en la BD.

**Solución:** Ejecutar migración `v2.9.0_add_id_seccion.sql`:
```sql
CREATE UNIQUE INDEX idx_seccion_servicios_basicos 
  ON edan.edan_localidades_servicios_basicos (id_seccion);
```

---

## Flujo completo recomendado

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. OFFLINE: Usuario crea sección con foto                     │
│    - App: id_seccion = generarIdSeccion()                     │
│    - App: uploadFoto(file) → "/uploads/x.jpg"                 │
│    - App: guardar localmente {id_seccion, tipo, fotografia}   │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. OFFLINE: Usuario edita sección (SIN cambiar foto)          │
│    - App: mantener id_seccion existente                        │
│    - App: actualizar solo campos editados                      │
│    - App: MANTENER fotografia = "/uploads/x.jpg"              │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. ONLINE: Sync                                                │
│    - App: POST /edan/localidades/sync                          │
│    - Payload: {id_seccion, tipo, fotografia, ...}              │
│    - Backend: UPSERT por id_seccion                            │
│    - Backend: fotografia = EXCLUDED.fotografia                 │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Resultado: 1 registro actualizado (NO duplicado)           │
│    - BD: UPDATE ... SET fotografia = '/uploads/x.jpg'          │
│    - App: recibir respuesta, limpiar flags dirty               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Referencias

- [`docs/MIGRACION_v2.9.0_id_seccion.md`](MIGRACION_v2.9.0_id_seccion.md) - Migración completa con 11 ejemplos JSON
- [`docs/TESTS_ID_SECCION.md`](TESTS_ID_SECCION.md) - Tests verificados de la API
- [`docs/SINCRONIZACION.md`](SINCRONIZACION.md) - Modelo offline-first completo

---

## Changelog

| Versión | Cambio |
|---------|--------|
| v2.8.0 | Última versión sin `id_seccion` - secciones se duplican al editar offline |
| v2.9.0 | Agrega `id_seccion` + UPSERT - edición offline sin duplicados, fotos actualizadas correctamente |


---

## Actualización: Coordenadas Obligatorias con Foto

### Regla de Negocio

**Si hay foto → coordenadas SON OBLIGATORIAS**

| Caso | ¿Foto? | ¿Coordenadas? | ¿Válido? | Response |
|------|--------|---------------|----------|----------|
| A | ✅ Sí | ✅ Sí | ✅ **VÁLIDO** | 201 Creado |
| B | ❌ No | ✅ Sí | ✅ **VÁLIDO** | 201 Creado |
| C | ❌ No | ❌ No | ✅ **VÁLIDO** | 201 Creado |
| D | ✅ Sí | ❌ No | ❌ **NO VÁLIDO** | 422 - "Foto requiere coordenadas GPS" |

### Ejemplos de Validación

```bash
# ✅ CASO A: Con foto + coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "file=@foto.jpg" \
  -F "tipo=energia_electrica" \
  -F "coordenada_lat=-16.5045" \
  -F "coordenada_lon=-68.1532"
# Response: 201 Creado

# ✅ CASO B: Sin foto + coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "tipo=agua_potable" \
  -F "coordenada_lat=-16.51" \
  -F "coordenada_lon=-68.16"
# Response: 201 Creado

# ✅ CASO C: Sin foto + sin coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "tipo=alcantarillado"
# Response: 201 Creado

# ❌ CASO D: Con foto + SIN coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "file=@foto.jpg" \
  -F "tipo=energia_electrica"
# Response: 422 - "Foto requiere coordenadas GPS"
```

---

## Pruebas Realizadas (v2.9.0)

### Tests por Sección

| Sección | Endpoint | Resultado |
|---------|----------|-----------|
| `servicios_basicos` | POST /servicios-basicos/con-foto | ✅ PASS |
| `infra_productiva` | POST /infra-productiva/con-foto | ✅ PASS |
| `salud_establecimientos` | POST /salud-establecimientos/con-foto | ✅ PASS |
| `danos_viales` | POST /danos-viales/con-foto | ✅ PASS* |
| `danos_infra_publica` | POST /danos-infra-publica/con-foto | ✅ PASS |
| `unidades_educativas` | POST /unidades-educativas/con-foto | ✅ PASS |
| `danos_vivienda` | POST /danos-vivienda/con-foto | ✅ PASS |
| `danos_agricultura` | POST /danos-agricultura/con-foto | ✅ PASS |
| `danos_pecuario` | POST /danos-pecuarios/con-foto | ✅ PASS |

*Nota: `danos_viales` requiere `km_danio=0` explícito (no puede ser null implícito)

### Comportamiento Verificado

```
✓ INSERT con id_seccion + foto + coordenadas: OK
✓ INSERT con id_seccion + sin foto + coordenadas: OK
✓ INSERT sin id_seccion + foto + coordenadas: OK (id_seccion = NULL)
✓ Validación foto sin coordenadas: 422 - "Foto requiere coordenadas GPS"
✓ NO duplicados con mismo id_seccion: UPSERT funciona
```

---

## Notas Importantes por Sección

### Daños Viales

El campo `km_danio` requiere valor explícito (0 si no aplica):

```bash
curl -X POST ".../danos-viales/con-foto" \
  -F "file=@foto.jpg" \
  -F "via=true" \
  -F "tramo=Test" \
  -F "km_danio=0" \    # ← Obligatorio (float, no null)
  -F "coordenada_lat=-16.53" \
  -F "coordenada_lon=-68.18"
```

---

## Referencias

- [`docs/EJEMPLOS_POR_SECCION.md`](EJEMPLOS_POR_SECCION.md) - Ejemplos completos para las 11 secciones
- [`docs/MIGRACION_v2.9.0_id_seccion.md`](MIGRACION_v2.9.0_id_seccion.md) - Migración BD
- [`docs/TESTS_ID_SECCION.md`](TESTS_ID_SECCION.md) - Tests de UPSERT
