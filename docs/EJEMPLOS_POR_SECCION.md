# Ejemplos por Sección - id_seccion, Foto y Coordenadas

> **Nota (v1.3.2):** existe la V2 de sync por secciones (sin fotografía) en `/api/v2/edan/localidades/{id}/<seccion>`, que acepta objeto único o array, hace UPSERT por `id_seccion` y es no destructiva. Este doc cubre los endpoints v1 con foto/coordenadas. Ver [SINCRONIZACION.md](SINCRONIZACION.md#sincronización-incremental-por-secciones-v2--apiv2).

## Reglas de Negocio

### 1. Foto + Coordenadas
| Caso | ¿Foto? | ¿Coordenadas? | ¿Válido? |
|------|--------|---------------|----------|
| A | ✅ Sí | ✅ Sí | ✅ Válido (recomendado) |
| B | ❌ No | ✅ Sí | ✅ Válido (ubicación sin foto) |
| C | ❌ No | ❌ No | ✅ Válido (solo datos) |
| D | ✅ Sí | ❌ No | ❌ **NO VÁLIDO** (foto requiere coordenadas) |

### 2. id_seccion
- **Obligatorio** en sync para edición offline
- **Opcional** en endpoints `con-foto` (se genera NULL si no se envía)
- **Único**: índice único parcial `WHERE id_seccion IS NOT NULL`

### 3. Estados posibles

| Estado | id_seccion | fotografia | coordenadas | dano_* | Ejemplo |
|--------|-----------|------------|-------------|--------|---------|
| Completo | ✅ `"abc-123"` | ✅ `"/uploads/x.jpg"` | ✅ `-16.5, -68.1` | ✅ `true` | Daño documentado con foto |
| Sin foto | ✅ `"def-456"` | ❌ `null` | ✅ `-16.5, -68.1` | ✅ `true` | Daño reportado sin foto |
| Sin daño | ✅ `"ghi-789"` | ❌ `null` | ✅ `-16.5, -68.1` | ❌ `false` | Existe, está bien |
| No reportado | ❌ omitido | ❌ | ❌ | ❌ | No se visitó |

---

## 1. Servicios Básicos

**Tabla:** `edan.edan_localidades_servicios_basicos`

**Tipos válidos:** `energia_electrica`, `agua_potable`, `alcantarillado`, `gas_domiciliario`, `telecomunicaciones`

### 1.1 Con foto + coordenadas (completo)

```json
{
  "id_seccion": "1a0357323cb-659d0c9c3d415",
  "tipo": "energia_electrica",
  "dano_parcial": true,
  "dano_total": false,
  "fotografia": "/uploads/reports/070101/070101_28_87630357a80b.jpg",
  "coordenada_lat": -16.5045,
  "coordenada_lon": -68.1532,
  "necesidades_inmediatas": "Reparación de postes",
  "observaciones": "3 postes caídos"
}
```

**Endpoint con-foto:**
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/136/servicios-basicos/con-foto" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@foto.jpg" \
  -F "tipo=energia_electrica" \
  -F "dano_parcial=true" \
  -F "id_seccion=1a0357323cb-659d0c9c3d415" \
  -F "coordenada_lat=-16.5045" \
  -F "coordenada_lon=-68.1532"
```

---

### 1.2 Sin foto (solo coordenadas)

```json
{
  "id_seccion": "1a03585d82d-659d112d47367",
  "tipo": "agua_potable",
  "dano_parcial": true,
  "dano_total": false,
  "fotografia": null,
  "coordenada_lat": -16.51,
  "coordenada_lon": -68.16,
  "necesidades_inmediatas": "Tubería rota",
  "observaciones": "Fuga en kilómetro 5"
}
```

---

### 1.3 Sin daño (existe pero está bien)

```json
{
  "id_seccion": "1a03444d63b-659cc2ce4d99a",
  "tipo": "alcantarillado",
  "dano_parcial": false,
  "dano_total": false,
  "fotografia": null,
  "coordenada_lat": -16.52,
  "coordenada_lon": -68.17,
  "necesidades_inmediatas": "",
  "observaciones": "En buen estado"
}
```

---

### 1.4 POST con-foto (validación)

```bash
# ✅ VÁLIDO: Con foto + coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "file=@foto.jpg" \
  -F "tipo=energia_electrica" \
  -F "coordenada_lat=-16.5045" \
  -F "coordenada_lon=-68.1532"

# ✅ VÁLIDO: Sin foto + coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "tipo=agua_potable" \
  -F "coordenada_lat=-16.51" \
  -F "coordenada_lon=-68.16"

# ❌ NO VÁLIDO: Con foto + SIN coordenadas
curl -X POST ".../servicios-basicos/con-foto" \
  -F "file=@foto.jpg" \
  -F "tipo=energia_electrica"
# Response: 422 - "Foto requiere coordenadas GPS"
```

---

## 2. Infraestructura Productiva

**Tabla:** `edan.edan_localidades_infra_productiva`

**Tipos comunes:** `Molino`, `Almacén`, `Tienda comunitaria`, `Centro de acopio`

### 2.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a035a1b2c3-659d1a2b3c4d5",
  "tipo": "Molino",
  "dano_parcial": 1,
  "dano_total": 0,
  "fotografia": "/uploads/edan/infra/molino_001.jpg",
  "coordenada_lat": -16.5,
  "coordenada_lon": -68.15
}
```

### 2.2 POST con-foto

```bash
curl -X POST ".../infra-productiva/con-foto" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@molino.jpg" \
  -F "tipo=Molino" \
  -F "dano_parcial=1" \
  -F "id_seccion=1a035a1b2c3-659d1a2b3c4d5" \
  -F "coordenada_lat=-16.5" \
  -F "coordenada_lon=-68.15"
```

---

## 3. Establecimientos de Salud

**Tabla:** `edan.edan_localidades_salud_establecimientos`

**Niveles de atención:** `1er Nivel`, `2do Nivel`, `3er Nivel`

### 3.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a035c3d4e5-659d3c4d5e6f7",
  "nombre_establecimiento": "Centro de Salud Las Lomas",
  "comunidad": "Las Lomas",
  "nivel_atencion": "1er Nivel",
  "dano_parcial": true,
  "dano_total": false,
  "medicos_afectados": 2,
  "enfermeras_afectadas": 3,
  "otros_afectados": 1,
  "fotografia": "/uploads/edan/salud/cs_lomas.jpg",
  "coordenada_lat": -16.52,
  "coordenada_lon": -68.17
}
```

### 3.2 POST con-foto

```bash
curl -X POST ".../salud-establecimientos/con-foto" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@centro_salud.jpg" \
  -F "nombre_establecimiento=Centro de Salud Las Lomas" \
  -F "comunidad=Las Lomas" \
  -F "nivel_atencion=1er Nivel" \
  -F "dano_parcial=true" \
  -F "medicos_afectados=2" \
  -F "enfermeras_afectadas=3" \
  -F "id_seccion=1a035c3d4e5-659d3c4d5e6f7" \
  -F "coordenada_lat=-16.52" \
  -F "coordenada_lon=-68.17"
```

---

## 4. Daños Viales

**Tabla:** `edan.edan_localidades_danos_viales`

### 4.1 Con foto + coordenadas (vía)

```json
{
  "id_seccion": "1a035d4e5f6-659d4d5e6f7g8",
  "via": true,
  "puente": false,
  "tramo": "Km 15-20 Ruta Nacional 4",
  "dano_parcial": true,
  "dano_total": false,
  "km_danio": 5.5,
  "necesidades_inmediatas": "Maquinaria pesada",
  "observaciones": "Derrumbe bloquea vía",
  "fotografia": "/uploads/edan/viales/derrumbe_001.jpg",
  "coordenada_lat": -16.53,
  "coordenada_lon": -68.18
}
```

### 4.2 POST con-foto (puente)

```bash
curl -X POST ".../danos-viales/con-foto" \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@puente.jpg" \
  -F "via=false" \
  -F "puente=true" \
  -F "tramo=Puente Río Grande" \
  -F "dano_parcial=false" \
  -F "dano_total=true" \
  -F "coordenada_lat=-16.54" \
  -F "coordenada_lon=-68.19" \
  -F "id_seccion=1a035e5f6g7-659d5e6f7g8h9"
```

---

## 5. Daños Infraestructura Pública

**Tabla:** `edan.edan_localidades_danos_infra_publica`

**Tipos de estructura:** `Alcaldía`, `Iglesia`, `Plaza`, `Mercado`, `Centro comunitario`

### 5.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a035f6g7h8-659d6f7g8h9i0",
  "comunidad": "La Paz",
  "tipo_estructura": "Alcaldía",
  "dano_parcial": true,
  "dano_total": false,
  "observaciones": "Grietas en paredes",
  "fotografia": "/uploads/edan/infra_publica/alcaldia_001.jpg",
  "coordenada_lat": -16.55,
  "coordenada_lon": -68.20
}
```

---

## 6. Unidades Educativas

**Tabla:** `edan.edan_localidades_unidades_educativas`

### 6.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a03607h8i9-659d7g8h9i0j1",
  "nombre_establecimiento": "Unidad Educativa Bolivia",
  "comunidad": "Centro",
  "dano_parcial": true,
  "dano_total": false,
  "suspension_clases": true,
  "perdida_material": false,
  "funciona_albergue": false,
  "estudiantes": 450,
  "profesores": 28,
  "administrativos": 5,
  "observaciones": "Aulas dañadas",
  "fotografia": "/uploads/edan/educacion/ue_bolivia.jpg",
  "coordenada_lat": -16.56,
  "coordenada_lon": -68.21
}
```

---

## 7. Daños Vivienda

**Tabla:** `edan.edan_localidades_danos_vivienda`

**Nota:** `dano_parcial` y `dano_total` son **CANTIDADES** (enteros), no booleanos.

### 7.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a03618i9j0-659d8h9i0j1k2",
  "comunidad": "Zona Sur",
  "dano_parcial": 15,
  "dano_total": 3,
  "necesidades_inmediatas": "Láminas de zinc",
  "observaciones": "Techos dañados por granizo",
  "fotografia": "/uploads/edan/vivienda/zona_sur.jpg",
  "coordenada_lat": -16.57,
  "coordenada_lon": -68.22
}
```

---

## 8. Daños Agricultura

**Tabla:** `edan.edan_localidades_danos_agricultura`

### 8.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a03629j0k1-659d9i0j1k2l3",
  "tipo_cultivo": "Papa",
  "id_cultivo": 1,
  "hectareas_afectadas": 50,
  "hectareas_perdidas": 12,
  "necesidades_inmediatas": "Semillas",
  "observaciones": "Granizo destruyó cultivo",
  "fotografia": "/uploads/edan/agricultura/papa_001.jpg",
  "coordenada_lat": -16.58,
  "coordenada_lon": -68.23
}
```

---

## 9. Daños Pecuario

**Tabla:** `edan.edan_localidades_danos_pecuario`

### 9.1 Con foto + coordenadas

```json
{
  "id_seccion": "1a0363ak1l2-659daj1k2l3m4",
  "especie": "Bovino",
  "id_especie": 1,
  "raza": "Holstein",
  "animales_afectados": 25,
  "animales_muertos": 3,
  "necesidades_inmediatas": "Alimento concentrado",
  "fotografia": "/uploads/edan/pecuario/bovinos_001.jpg",
  "coordenada_lat": -16.59,
  "coordenada_lon": -68.24
}
```

---

## 10. Impacto Población

**Tabla:** `edan.edan_localidades_impacto_poblacion`

**⚠️ SIN foto, SIN coordenadas** - Solo datos estadísticos por rango etario.

### 10.1 Ejemplo (sin foto)

```json
{
  "id_seccion": "1a0364bl2m3-659dbk2l3m4n5",
  "rango": "Niño 0-5",
  "fallecidos": 2,
  "heridos": 5,
  "desaparecidos": 0,
  "observaciones": "La mayoría por derrumbe"
}
```

### 10.2 Múltiples rangos

```json
{
  "impacto_poblacion": [
    {
      "id_seccion": "1a0364bl2m3-659dbk2l3m4n5",
      "rango": "Niño 0-5",
      "fallecidos": 2,
      "heridos": 5,
      "desaparecidos": 0
    },
    {
      "id_seccion": "1a0365cm3n4-659dcl3m4n5o6",
      "rango": "Adulto 19-60",
      "fallecidos": 5,
      "heridos": 15,
      "desaparecidos": 2
    },
    {
      "id_seccion": "1a0366dn4o5-659ddm4n5o6p7",
      "rango": "Adulto mayor 60+",
      "fallecidos": 3,
      "heridos": 8,
      "desaparecidos": 1
    }
  ]
}
```

---

## 11. Protección (Grupos Vulnerables)

**Tabla:** `edan.edan_localidades_proteccion`

**⚠️ SIN foto, SIN coordenadas** - Datos de grupos vulnerables vinculados a catálogo.

### 11.1 Con FK a catálogo

```json
{
  "id_seccion": "1a0367eo5p6-659den5o6p7q8",
  "id_grupo_vulnerable_catalogo": 1,
  "grupo": {
    "id": 1,
    "nombre": "Adultos mayores",
    "codigo": "adultos_mayores"
  },
  "mujeres": 15,
  "hombres": 12,
  "total": 27,
  "apoyo_psicologico": true,
  "reposicion_documentos": false,
  "observaciones": "Requieren medicamentos"
}
```

### 11.2 Múltiples grupos

```json
{
  "proteccion": [
    {
      "id_seccion": "1a0367eo5p6-659den5o6p7q8",
      "id_grupo_vulnerable_catalogo": 1,
      "mujeres": 15,
      "hombres": 12,
      "total": 27
    },
    {
      "id_seccion": "1a0368fp6q7-659dfo6p7q8r9",
      "id_grupo_vulnerable_catalogo": 2,
      "mujeres": 8,
      "hombres": 5,
      "total": 13
    }
  ]
}
```

### 11.3 Endpoints dedicados (CRUD individual)

Para crear, editar o eliminar grupos vulnerables individualmente:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `GET /edan/localidades/{id}/proteccion` | GET | Lista todos los grupos |
| `POST /edan/localidades/{id}/proteccion` | POST | Crea/actualiza grupo (JSON, UPSERT por `id_seccion`) |
| `PUT /edan/localidades/{id}/proteccion/{id_grupo}` | PUT | Actualiza grupo específico |
| `DELETE /edan/localidades/{id}/proteccion/{id_grupo}` | DELETE | Elimina grupo específico |

**Ejemplo crear con `id_seccion`:**
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/199/proteccion" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id_seccion": "po_1693012345_abc12345",
    "id_grupo_vulnerable_catalogo": 1,
    "mujeres": 15,
    "hombres": 12,
    "total": 27,
    "apoyo_psicologico": true
  }'
```

**Documentación completa:** [ENDPOINTS_PROTECCION.md](ENDPOINTS_PROTECCION.md)

---

## Tabla de Referencia Rápida

| Sección | Foto | Coordenadas | id_seccion | Campos clave |
|---------|------|-------------|------------|--------------|
| `servicios_basicos` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | tipo (5 valores) |
| `infra_productiva` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | tipo (string libre) |
| `salud_establecimientos` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | nivel_atencion, medicos |
| `danos_viales` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | via, puente, km_danio |
| `danos_infra_publica` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | tipo_estructura |
| `unidades_educativas` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | estudiantes, profesores |
| `danos_vivienda` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | dano_parcial (int) |
| `danos_agricultura` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | hectareas, id_cultivo |
| `danos_pecuario` | ⚠️ Opcional* | ⚠️ Oblig. si hay foto | ✅ Opcional | animales, id_especie |
| `impacto_poblacion` | ❌ No | ❌ No | ✅ Opcional | rango, fallecidos |
| `proteccion` | ❌ No | ❌ No | ✅ Opcional | id_grupo_vulnerable_catalogo |

**\* Regla:** Si hay foto → coordenadas SON OBLIGATORIAS

---

## Validación Backend (Endpoints con-foto)

### Regla implementada

```python
# Pseudo-código de validación
if file_present and (coordenada_lat is None or coordenada_lon is None):
    raise HTTPException(422, "Foto requiere coordenadas GPS")
```

### Respuestas de validación

| Request | Response |
|---------|----------|
| `file=@foto.jpg` + `lat=-16.5` + `lon=-68.1` | ✅ 201 Creado |
| Sin file + `lat=-16.5` + `lon=-68.1` | ✅ 201 Creado |
| `file=@foto.jpg` sin coords | ❌ 422 - "Foto requiere coordenadas GPS" |
| Sin file + sin coords | ✅ 201 Creado (datos sin ubicación) |

---

## Código TypeScript para Cliente

```typescript
interface SeccionConFoto {
  id_seccion?: string;
  fotografia: string | null;
  coordenada_lat: number | null;  // Obligatorio si hay foto
  coordenada_lon: number | null;  // Obligatorio si hay foto
}

interface ServicioBasico extends SeccionConFoto {
  tipo: 'energia_electrica' | 'agua_potable' | 'alcantarillado' | 'gas' | 'telecom';
  dano_parcial: boolean;
  dano_total: boolean;
}

class EdanSync {
  // VALIDACIÓN: Foto requiere coordenadas
  async crearServicio(
    tipo: string,
    fotoFile?: File,
    coords?: { lat: number; lon: number }
  ): Promise<ServicioBasico> {
    // VALIDAR: Si hay foto, coordenadas son obligatorias
    if (fotoFile && !coords) {
      throw new Error('Foto requiere coordenadas GPS');
    }
    
    let fotoPath: string | null = null;
    if (fotoFile) {
      fotoPath = await this.uploadFoto(fotoFile);
    }
    
    return {
      id_seccion: this.generarIdSeccion(),  // Generar UNA VEZ
      tipo,
      dano_parcial: false,
      dano_total: false,
      fotografia: fotoPath,
      coordenada_lat: coords?.lat ?? null,
      coordenada_lon: coords?.lon ?? null
    };
  }
  
  // Sincronización
  async sincronizar(servicios: ServicioBasico[]) {
    const payload = {
      localidades: [{
        id_local: this.idLocal,
        // ... otros campos ...
        servicios_basicos: servicios.map(s => ({
          id_seccion: s.id_seccion,  // SIEMPRE incluir
          tipo: s.tipo,
          dano_parcial: s.dano_parcial,
          dano_total: s.dano_total,
          fotografia: s.fotografia,  // SIEMPRE incluir (path o null)
          coordenada_lat: s.coordenada_lat,  // SIEMPRE incluir
          coordenada_lon: s.coordenada_lon   // SIEMPRE incluir
        }))
      }]
    };
    
    await fetch('/api/v1/edan/localidades/sync', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }
}
```

---

## Referencias

- [`docs/MIGRACION_v2.9.0_id_seccion.md`](MIGRACION_v2.9.0_id_seccion.md) - Migración completa
- [`docs/TESTS_ID_SECCION.md`](TESTS_ID_SECCION.md) - Tests verificados
- [`docs/SINCRONIZACION_SECCIONES_FOTOS.md`](SINCRONIZACION_SECCIONES_FOTOS.md) - Flujos con fotografía
- [`docs/SINCRONIZACION.md`](SINCRONIZACION.md) - Modelo offline-first

