# Migración v2.9.0: id_seccion para secciones de localidad

## Resumen

La migración v2.9.0 agrega el campo `id_seccion` a todas las tablas de secciones 1:N para permitir identificación única en modo offline y evitar duplicados durante la sincronización.

---

## Problema resuelto

**Antes:** Las secciones (ej: `infra_productiva`, `damo_vial`, `establecimientos_salud`) se duplicaban al sincronizar ediciones offline porque el backend no tenía forma de identificar que era la misma sección.

**Después:** Cada sección tiene un `id_seccion` único generado por el cliente que permite hacer UPSERT (actualizar si existe, insertar si es nuevo).

---

## Cambios en la Base de Datos

### Tablas modificadas (11 tablas 1:N)

| Tabla | Columna agregada | Índice único |
|-------|------------------|--------------|
| `edan_localidades_impacto_poblacion` | `id_seccion VARCHAR(50)` | `idx_seccion_impacto_poblacion` |
| `edan_localidades_salud_establecimientos` | `id_seccion VARCHAR(50)` | `idx_seccion_salud_establecimientos` |
| `edan_localidades_danos_viales` | `id_seccion VARCHAR(50)` | `idx_seccion_danos_viales` |
| `edan_localidades_danos_infra_publica` | `id_seccion VARCHAR(50)` | `idx_seccion_danos_infra_publica` |
| `edan_localidades_servicios_basicos` | `id_seccion VARCHAR(50)` | `idx_seccion_servicios_basicos` |
| `edan_localidades_unidades_educativas` | `id_seccion VARCHAR(50)` | `idx_seccion_unidades_educativas` |
| `edan_localidades_danos_vivienda` | `id_seccion VARCHAR(50)` | `idx_seccion_danos_vivienda` |
| `edan_localidades_danos_agricultura` | `id_seccion VARCHAR(50)` | `idx_seccion_danos_agricultura` |
| `edan_localidades_danos_pecuario` | `id_seccion VARCHAR(50)` | `idx_seccion_danos_pecuario` |
| `edan_localidades_infra_productiva` | `id_seccion VARCHAR(50)` | `idx_seccion_infra_productiva` |
| `edan_localidades_proteccion` | `id_seccion VARCHAR(50)` | `idx_seccion_proteccion` |

### Tablas NO modificadas (1:1 - usan `id_edan_localidad` como PK)

- `edan_localidades_primera_respuesta`
- `edan_localidades_salud_necesidades`
- `edan_localidades_necesidades_humanitarias`

---

## Formato de `id_seccion`

| Atributo | Valor |
|----------|-------|
| **Genera** | Cliente (app móvil/web) |
| **Cuándo** | Al crear la sección por primera vez |
| **Formato** | `{timestamp_base32}-{uuid_short}` |
| **Ejemplo** | `"1a0357323cb-659d0c9c3d415"` |
| **Longitud** | ~24 caracteres |
| **Único** | Sí (índice único parcial) |

### Generación en JavaScript/TypeScript

```javascript
function generarIdSeccion() {
  const timestamp = Date.now().toString(32);  // ~10 chars (base32)
  const uuidShort = crypto.randomUUID().replace(/-/g, '').slice(0, 13);  // 13 chars
  return `${timestamp}-${uuidShort}`;  // Total: 24 chars
}

// Ejemplo: "1a0357323cb-659d0c9c3d415"
```

---

## Cambios en Schemas (api/edan/schemas.py)

Se agregó `id_seccion: str | None` a las siguientes clases:

1. `ImpactoPoblacion`
2. `EstablecimientoSalud`
3. `DanoVial`
4. `DanoInfraPublica`
5. `ServicioBasicoDetalle`
6. `UnidadEducativa`
7. `DanoVivienda`
8. `DanoAgricultura`
9. `DanoPecuario`
10. `InfraProductiva`
11. `GrupoVulnerable`

**NO se modificaron** (clases 1:1):
- `PrimeraRespuesta`
- `NecesidadSalud`
- `NecesidadHumanitaria`

---

## Ejemplos JSON: ANTES vs DESPUÉS

### 1. InfraProductiva

**ANTES (v2.8.0):**
```json
{
  "infra_productiva": [
    {
      "tipo": "Molino",
      "dano_parcial": 1,
      "dano_total": 0,
      "fotografia": "/uploads/edan/infra/molino_001.jpg",
      "coordenada_lat": -16.5,
      "coordenada_lon": -68.15
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "infra_productiva": [
    {
      "id_seccion": "1a0357323cb-659d0c9c3d415",  // ← NUEVO
      "tipo": "Molino",
      "dano_parcial": 1,
      "dano_total": 0,
      "fotografia": "/uploads/edan/infra/molino_001.jpg",
      "coordenada_lat": -16.5,
      "coordenada_lon": -68.15
    }
  ]
}
```

---

### 2. EstablecimientoSalud

**ANTES (v2.8.0):**
```json
{
  "establecimientos_salud": [
    {
      "nombre_establecimiento": "Centro de Salud Las Lomas",
      "comunidad": "Las Lomas",
      "nivel_atencion": "1er Nivel",
      "dano_parcial": true,
      "dano_total": false,
      "medicos_afectados": 2,
      "enfermeras_afectadas": 3,
      "fotografia": "/uploads/edan/salud/cs_lomas.jpg"
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "establecimientos_salud": [
    {
      "id_seccion": "1a03585d82d-659d112d47367",  // ← NUEVO
      "nombre_establecimiento": "Centro de Salud Las Lomas",
      "comunidad": "Las Lomas",
      "nivel_atencion": "1er Nivel",
      "dano_parcial": true,
      "dano_total": false,
      "medicos_afectados": 2,
      "enfermeras_afectadas": 3,
      "fotografia": "/uploads/edan/salud/cs_lomas.jpg"
    }
  ]
}
```

---

### 3. DanoVial

**ANTES (v2.8.0):**
```json
{
  "danos_viales": [
    {
      "via": true,
      "puente": false,
      "tramo": "Km 15-20 Ruta Nacional 4",
      "dano_parcial": true,
      "dano_total": false,
      "km_danio": 5.5,
      "necesidades_inmediatas": "Maquinaria pesada",
      "observaciones": "Derrumbe bloquea vía"
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "danos_viales": [
    {
      "id_seccion": "1a03444d63b-659cc2ce4d99a",  // ← NUEVO
      "via": true,
      "puente": false,
      "tramo": "Km 15-20 Ruta Nacional 4",
      "dano_parcial": true,
      "dano_total": false,
      "km_danio": 5.5,
      "necesidades_inmediatas": "Maquinaria pesada",
      "observaciones": "Derrumbe bloquea vía"
    }
  ]
}
```

---

### 4. DanoInfraPublica

**ANTES (v2.8.0):**
```json
{
  "danos_infra_publica": [
    {
      "comunidad": "La Paz",
      "tipo_estructura": "Alcaldía",
      "dano_parcial": true,
      "dano_total": false,
      "observaciones": "Grietas en paredes"
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "danos_infra_publica": [
    {
      "id_seccion": "1a03590a1ef-659d155e7a8b2",  // ← NUEVO
      "comunidad": "La Paz",
      "tipo_estructura": "Alcaldía",
      "dano_parcial": true,
      "dano_total": false,
      "observaciones": "Grietas en paredes"
    }
  ]
}
```

---

### 5. ServicioBasicoDetalle

**ANTES (v2.8.0):**
```json
{
  "servicios_basicos": [
    {
      "tipo": "energia_electrica",
      "dano_parcial": true,
      "dano_total": false,
      "necesidades_inmediatas": "Reparación de postes"
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "servicios_basicos": [
    {
      "id_seccion": "1a035a2b4cd-659d1a8f9c3d1",  // ← NUEVO
      "tipo": "energia_electrica",
      "dano_parcial": true,
      "dano_total": false,
      "necesidades_inmediatas": "Reparación de postes"
    }
  ]
}
```

---

### 6. UnidadEducativa

**ANTES (v2.8.0):**
```json
{
  "unidades_educativas": [
    {
      "nombre_establecimiento": "Unidad Educativa Bolivia",
      "comunidad": "Centro",
      "dano_parcial": true,
      "dano_total": false,
      "estudiantes": 450,
      "profesores": 28
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "unidades_educativas": [
    {
      "id_seccion": "1a035b3c5de-659d1f9a0b4e2",  // ← NUEVO
      "nombre_establecimiento": "Unidad Educativa Bolivia",
      "comunidad": "Centro",
      "dano_parcial": true,
      "dano_total": false,
      "estudiantes": 450,
      "profesores": 28
    }
  ]
}
```

---

### 7. DanoVivienda

**ANTES (v2.8.0):**
```json
{
  "danos_vivienda": [
    {
      "comunidad": "Zona Sur",
      "dano_parcial": 15,
      "dano_total": 3,
      "necesidades_inmediatas": "Láminas de zinc"
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "danos_vivienda": [
    {
      "id_seccion": "1a035c4d6ef-659d24ab1c5f3",  // ← NUEVO
      "comunidad": "Zona Sur",
      "dano_parcial": 15,
      "dano_total": 3,
      "necesidades_inmediatas": "Láminas de zinc"
    }
  ]
}
```

---

### 8. DanoAgricultura

**ANTES (v2.8.0):**
```json
{
  "danos_agricultura": [
    {
      "tipo_cultivo": "Papa",
      "hectareas_afectadas": 50,
      "hectareas_perdidas": 12,
      "necesidades_inmediatas": "Semillas"
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "danos_agricultura": [
    {
      "id_seccion": "1a035d5e7f0-659d29bc2d6g4",  // ← NUEVO
      "tipo_cultivo": "Papa",
      "hectareas_afectadas": 50,
      "hectareas_perdidas": 12,
      "necesidades_inmediatas": "Semillas"
    }
  ]
}
```

---

### 9. DanoPecuario

**ANTES (v2.8.0):**
```json
{
  "danos_pecuarios": [
    {
      "especie": "Bovino",
      "raza": "Holstein",
      "animales_afectados": 25,
      "animales_muertos": 3
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "danos_pecuarios": [
    {
      "id_seccion": "1a035e6f8g1-659d2ecd3e7h5",  // ← NUEVO
      "especie": "Bovino",
      "raza": "Holstein",
      "animales_afectados": 25,
      "animales_muertos": 3
    }
  ]
}
```

---

### 10. ImpactoPoblacion

**ANTES (v2.8.0):**
```json
{
  "impacto_poblacion": [
    {
      "rango": "Niño 0-5",
      "fallecidos": 2,
      "heridos": 5,
      "desaparecidos": 0
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "impacto_poblacion": [
    {
      "id_seccion": "1a035f7g9h2-659d33de4f8i6",  // ← NUEVO
      "rango": "Niño 0-5",
      "fallecidos": 2,
      "heridos": 5,
      "desaparecidos": 0
    }
  ]
}
```

---

### 11. GrupoVulnerable (Proteccion)

**ANTES (v2.8.0):**
```json
{
  "proteccion": [
    {
      "id_grupo_vulnerable_catalogo": 1,
      "grupo": {"id": 1, "nombre": "Adultos mayores"},
      "mujeres": 15,
      "hombres": 12,
      "total": 27
    }
  ]
}
```

**DESPUÉS (v2.9.0):**
```json
{
  "proteccion": [
    {
      "id_seccion": "1a03608hai3-659d38ef5g9j7",  // ← NUEVO
      "id_grupo_vulnerable_catalogo": 1,
      "grupo": {"id": 1, "nombre": "Adultos mayores"},
      "mujeres": 15,
      "hombres": 12,
      "total": 27
    }
  ]
}
```

---

### Secciones 1:1 (NO requieren id_seccion)

Estas secciones usan `id_edan_localidad` como primary key y ya tienen UPSERT:

#### PrimeraRespuesta

```json
{
  "necesidad_primera_respuesta": {
    "busqueda": true,
    "salvamento": true,
    "evacuacion": false,
    "observaciones": "Equipo de rescate en camino"
  }
}
```

#### NecesidadSalud

```json
{
  "necesidad_salud": {
    "numero_personas": 150,
    "otras_necesidades": "Medicamentos para hipertensos",
    "observaciones": "Prioritario"
  }
}
```

#### NecesidadHumanitaria

```json
{
  "necesidad_humanitaria": {
    "alimentos": true,
    "refugio_vivienda": true,
    "ropa_cama": false,
    "obs_alimentos": "Arroz, fideos, aceite",
    "obs_refugio_vivienda": "Albergue temporal"
  }
}
```

---

## Ejemplo completo de sincronización

### Payload POST /edan/localidades/sync

```json
{
  "localidades": [
    {
      "id_local": "1a0357323cb-659d0c9c3d415",
      "localidad": "Las Lomas",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 3,
      "fecha_modificacion": "2026-08-24T18:05:33.971Z",
      "infra_productiva": [
        {
          "id_seccion": "1a035a1b2c3-659d1a2b3c4d5",
          "tipo": "Molino",
          "dano_parcial": 1,
          "dano_total": 0,
          "fotografia": "/uploads/edan/infra/molino_001.jpg"
        },
        {
          "id_seccion": "1a035b2c3d4-659d2b3c4d5e6",
          "tipo": "Almacén",
          "dano_parcial": 0,
          "dano_total": 1,
          "fotografia": null
        }
      ],
      "establecimientos_salud": [
        {
          "id_seccion": "1a035c3d4e5-659d3c4d5e6f7",
          "nombre_establecimiento": "Posta de Salud",
          "comunidad": "Las Lomas",
          "nivel_atencion": "1er Nivel",
          "dano_parcial": true,
          "dano_total": false
        }
      ],
      "danos_viales": [
        {
          "id_seccion": "1a035d4e5f6-659d4d5e6f7g8",
          "via": true,
          "puente": false,
          "tramo": "Camino vecinal Las Lomas - La Paz",
          "dano_parcial": true,
          "dano_total": false,
          "km_danio": 2.5
        }
      ],
      "necesidad_primera_respuesta": {
        "busqueda": false,
        "salvamento": true,
        "evacuacion": true
      }
    }
  ]
}
```

---

## Comportamiento del UPSERT

### Escenario 1: Primera vez (INSERT)

**Cliente envía:**
```json
{
  "id_seccion": "1a0357323cb-659d0c9c3d415",
  "tipo": "Molino",
  "dano_parcial": 1
}
```

**Backend:** INSERT nuevo registro

---

### Escenario 2: Editar existente (UPDATE)

**Cliente envía** (mismo `id_seccion`, diferente dato):
```json
{
  "id_seccion": "1a0357323cb-659d0c9c3d415",
  "tipo": "Molino",
  "dano_parcial": 2  // ← Cambiado de 1 a 2
}
```

**Backend:** UPDATE del registro existente (NO duplica)

---

### Escenario 3: Sin id_seccion (INSERT siempre)

**Cliente envía** (sin `id_seccion`):
```json
{
  "tipo": "Molino",
  "dano_parcial": 1
}
```

**Backend:** INSERT nuevo registro (puede generar duplicado)

⚠️ **Importante:** El cliente SIEMPRE debe generar `id_seccion` al crear una sección.

---

## Guía para el cliente (app móvil/web)

### Reglas de uso

1. **Generar `id_seccion` UNA VEZ** al crear la sección
2. **REUSAR el mismo `id_seccion`** al editar la sección
3. **NUNCA cambiar `id_seccion`** después de creado
4. **Siempre enviar `id_seccion`** en el payload de sync

### Ejemplo en TypeScript

```typescript
interface InfraProductiva {
  id_seccion?: string;
  tipo: string;
  dano_parcial: number;
  dano_total: number;
  fotografia?: string | null;
  coordenada_lat?: number | null;
  coordenada_lon?: number | null;
}

class LocalidadForm {
  private infraList: InfraProductiva[] = [];

  // CREAR nueva sección
  agregarInfra(tipo: string): void {
    const nuevaInfra: InfraProductiva = {
      id_seccion: this.generarIdSeccion(),  // ← Generar UNA VEZ
      tipo,
      dano_parcial: 0,
      dano_total: 0
    };
    this.infraList.push(nuevaInfra);
  }

  // EDITAR sección existente
  actualizarInfra(idSeccion: string, cambios: Partial<InfraProductiva>): void {
    const infra = this.infraList.find(i => i.id_seccion === idSeccion);
    if (infra) {
      // ← NO cambiar id_seccion, solo los datos
      Object.assign(infra, cambios);
    }
  }

  // ELIMINAR sección
  eliminarInfra(idSeccion: string): void {
    this.infraList = this.infraList.filter(i => i.id_seccion !== idSeccion);
  }

  // SYNC
  async sincronizar(): Promise<void> {
    await fetch('/api/v1/edan/localidades/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        localidades: [{
          id_local: this.idLocal,
          infra_productiva: this.infraList  // ← Enviar con id_seccion
        }]
      })
    });
  }

  private generarIdSeccion(): string {
    const timestamp = Date.now().toString(32);
    const uuidShort = crypto.randomUUID().replace(/-/g, '').slice(0, 13);
    return `${timestamp}-${uuidShort}`;
  }
}
```

---

## Respuesta de la API

### Éxito (200 OK)

```json
{
  "success": true,
  "message": "EDAN localidades sincronizadas correctamente",
  "data": [
    {
      "id_local": "1a0357323cb-659d0c9c3d415",
      "id_edan_localidad": 128,
      "aplicado": true,
      "conflicto": false,
      "data": {
        "id_edan_localidad": 128,
        "localidad": "Las Lomas",
        "infra_productiva": [
          {
            "id_infra_productiva": 45,
            "id_seccion": "1a035a1b2c3-659d1a2b3c4d5",  // ← Incluido en respuesta
            "tipo": "Molino",
            "dano_parcial": 1
          }
        ]
      }
    }
  ]
}
```

---

## Migración de datos

Los registros existentes **NO** requieren migración. El campo `id_seccion` es `NULL` para registros antiguos y las consultas funcionan normalmente.

Nuevos registros (creados después de la migración) tendrán `id_seccion` populated.

---

## Rollback

En caso de problema, ejecutar:

```sql
-- Eliminar índices
DROP INDEX IF EXISTS edan.idx_seccion_impacto_poblacion;
DROP INDEX IF EXISTS edan.idx_seccion_salud_establecimientos;
-- ... repetir para los 11 índices ...

-- Eliminar columnas
ALTER TABLE edan.edan_localidades_impacto_poblacion DROP COLUMN IF EXISTS id_seccion;
-- ... repetir para las 11 tablas ...
```

---

## Versionado

| Versión | Cambio |
|---------|--------|
| v2.8.0 | Última versión sin `id_seccion` |
| v2.9.0 | Agrega `id_seccion` a 11 tablas de secciones |

---

## Checklist para actualizar apps

- [ ] Agregar campo `id_seccion` a todos los modelos de secciones
- [ ] Generar `id_seccion` al crear nueva sección
- [ ] Reusar `id_seccion` al editar sección existente
- [ ] Incluir `id_seccion` en payloads de sync
- [ ] Actualizar tests unitarios
- [ ] Probar sync offline → online con ediciones
