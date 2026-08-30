# Ejemplos de Prueba - id_seccion

## Tests realizados (v2.9.0)

Todos los tests se ejecutaron contra `POST /api/v1/edan/localidades/sync`

---

## Test 1: INSERT con id_seccion

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-local-001",
      "localidad": "Test",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "infra_productiva": [
        {"id_seccion": "test-infra-001", "tipo": "Molino", "dano_parcial": 1, "dano_total": 0}
      ]
    }]
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "EDAN localidades sincronizadas correctamente",
  "data": [{
    "id_local": "test-local-001",
    "id_edan_localidad": 130,
    "aplicado": true,
    "conflicto": false,
    "data": {
      "infra_productiva": [
        {
          "id_infra_productiva": 9,
          "id_seccion": "test-infra-001",
          "tipo": "Molino",
          "dano_parcial": 1
        }
      ]
    }
  }]
}
```

**Resultado:** ✓ INSERT exitoso

---

## Test 2: UPDATE mismo id_seccion

**Request:** (mismo `id_seccion`, datos modificados)
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-local-001",
      "localidad": "Test",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "infra_productiva": [
        {"id_seccion": "test-infra-001", "tipo": "Molino EDITADO", "dano_parcial": 2, "dano_total": 1}
      ]
    }]
  }'
```

**Response:**
```json
{
  "success": true,
  "data": [{
    "aplicado": true,
    "data": {
      "infra_productiva": [
        {
          "id_infra_productiva": 9,
          "id_seccion": "test-infra-001",
          "tipo": "Molino EDITADO",
          "dano_parcial": 2,
          "dano_total": 1
        }
      ]
    }
  }]
}
```

**Verificación en BD:**
```sql
SELECT id_infra_productiva, id_seccion, tipo, dano_parcial, dano_total
FROM edan.edan_localidades_infra_productiva
WHERE id_seccion = 'test-infra-001';
```

**Resultado:**
```
 id_infra_productiva |   id_seccion   |      tipo      | dano_parcial | dano_total 
---------------------+----------------+----------------+--------------+------------
                   9 | test-infra-001 | Molino EDITADO |            2 |          1
(1 row)
```

✓ UPDATE exitoso - **1 registro** (NO se duplicó)

---

## Test 3: MIXTO - 2 existentes + 1 nuevo

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-local-001",
      "localidad": "Test",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "infra_productiva": [
        {"id_seccion": "test-infra-001", "tipo": "Molino FINAL", "dano_parcial": 0},
        {"id_seccion": "test-infra-002", "tipo": "Almacen", "dano_parcial": 1},
        {"id_seccion": "test-infra-003", "tipo": "Nueva", "dano_parcial": 1}
      ]
    }]
  }'
```

**Response:**
```json
{
  "success": true,
  "data": [{
    "aplicado": true,
    "data": {
      "infra_productiva": [
        {"id_seccion": "test-infra-001", "tipo": "Molino FINAL"},
        {"id_seccion": "test-infra-002", "tipo": "Almacen"},
        {"id_seccion": "test-infra-003", "tipo": "Nueva"}
      ]
    }
  }]
}
```

**Verificación en BD:**
```sql
SELECT COUNT(*) FROM edan.edan_localidades_infra_productiva 
WHERE id_seccion LIKE 'test-infra-%';
```

**Resultado:** `3` registros (1 actualizado + 2 nuevos)

✓ MIXTO exitoso

---

## Test 4: Múltiples tipos de secciones

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-full-001",
      "localidad": "Test Completa",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "infra_productiva": [
        {"id_seccion": "s-infra-01", "tipo": "Molino", "dano_parcial": 1},
        {"id_seccion": "s-infra-02", "tipo": "Almacen", "dano_parcial": 0}
      ],
      "establecimientos_salud": [
        {"id_seccion": "s-salud-01", "nombre_establecimiento": "Posta A", "dano_parcial": true}
      ],
      "danos_viales": [
        {"id_seccion": "s-vial-01", "via": true, "tramo": "Camino 1", "dano_parcial": false}
      ],
      "danos_infra_publica": [
        {"id_seccion": "s-infra-pub-01", "comunidad": "Centro", "tipo_estructura": "Alcaldía", "dano_parcial": true}
      ],
      "servicios_basicos": [
        {"id_seccion": "s-serv-01", "tipo": "energia_electrica", "dano_parcial": true}
      ],
      "unidades_educativas": [
        {"id_seccion": "s-edu-01", "nombre_establecimiento": "Escuela A", "dano_parcial": false}
      ],
      "danos_vivienda": [
        {"id_seccion": "s-viv-01", "comunidad": "Zona 1", "dano_parcial": 5, "dano_total": 1}
      ],
      "danos_agricultura": [
        {"id_seccion": "s-agro-01", "tipo_cultivo": "Papa", "hectareas_afectadas": 10}
      ],
      "danos_pecuarios": [
        {"id_seccion": "s-pec-01", "especie": "Bovino", "animales_afectados": 20}
      ],
      "proteccion": [
        {"id_seccion": "s-prot-01", "id_grupo_vulnerable_catalogo": 1, "mujeres": 10, "hombres": 8}
      ]
    }]
  }'
```

**Response:**
```json
{
  "success": true,
  "data": [{
    "aplicado": true,
    "conflicto": false,
    "data": {
      "infra_productiva": [...],
      "establecimientos_salud": [...],
      "danos_viales": [...],
      "danos_infra_publica": [...],
      "servicios_basicos": [...],
      "unidades_educativas": [...],
      "danos_vivienda": [...],
      "danos_agricultura": [...],
      "danos_pecuarios": [...],
      "proteccion": [...]
    }
  }]
}
```

**Verificación en BD:**
```sql
SELECT 
  (SELECT COUNT(*) FROM edan.edan_localidades_infra_productiva WHERE id_seccion LIKE 's-infra-%') as infra,
  (SELECT COUNT(*) FROM edan.edan_localidades_salud_establecimientos WHERE id_seccion LIKE 's-salud-%') as salud,
  (SELECT COUNT(*) FROM edan.edan_localidades_danos_viales WHERE id_seccion LIKE 's-vial-%') as vial,
  (SELECT COUNT(*) FROM edan.edan_localidades_danos_infra_publica WHERE id_seccion LIKE 's-infra-pub-%') as infra_pub,
  (SELECT COUNT(*) FROM edan.edan_localidades_servicios_basicos WHERE id_seccion LIKE 's-serv-%') as serv,
  (SELECT COUNT(*) FROM edan.edan_localidades_unidades_educativas WHERE id_seccion LIKE 's-edu-%') as edu,
  (SELECT COUNT(*) FROM edan.edan_localidades_danos_vivienda WHERE id_seccion LIKE 's-viv-%') as viv,
  (SELECT COUNT(*) FROM edan.edan_localidades_danos_agricultura WHERE id_seccion LIKE 's-agro-%') as agro,
  (SELECT COUNT(*) FROM edan.edan_localidades_danos_pecuario WHERE id_seccion LIKE 's-pec-%') as pec,
  (SELECT COUNT(*) FROM edan.edan_localidades_proteccion WHERE id_seccion LIKE 's-prot-%') as prot
```

**Resultado:**
```
 infra | salud | vial | infra_pub | serv | edu | viv | agro | pec | prot 
-------+-------+------+-----------+------+------+-----+------+------+------
     2 |     1 |    1 |         1 |    1 |   1 |   1 |    1 |   1 |    1
```

✓ Múltiples secciones exitoso

---

## Test 5: Secciones 1:1 (NO usan id_seccion)

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/edan/localidades/sync" \
  -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{
    "localidades": [{
      "id_local": "test-1a1-001",
      "localidad": "Test 1:1",
      "id_tipo_localidad": 1,
      "id_edan_localidad_estado": 1,
      "id_municipio": 70101,
      "id_departamento": 7,
      "id_provincia": 701,
      "necesidad_primera_respuesta": {
        "busqueda": true,
        "salvamento": true,
        "evacuacion": false
      },
      "necesidad_salud": {
        "numero_personas": 100,
        "otras_necesidades": "Medicamentos"
      },
      "necesidad_humanitaria": {
        "alimentos": true,
        "refugio_vivienda": true,
        "obs_alimentos": "Arroz, aceite"
      }
    }]
  }'
```

**Response:**
```json
{
  "success": true,
  "data": [{
    "aplicado": true,
    "data": {
      "necesidad_primera_respuesta": {...},
      "necesidad_salud": {...},
      "necesidad_humanitaria": {...}
    }
  }]
}
```

✓ Secciones 1:1 exitoso (UPSERT por `id_edan_localidad`)

---

## Resumen de resultados

| Test | Descripción | Resultado |
|------|-------------|-----------|
| 1 | INSERT con id_seccion | ✓ PASS |
| 2 | UPDATE mismo id_seccion | ✓ PASS (sin duplicados) |
| 3 | MIXTO (2 existentes + 1 nuevo) | ✓ PASS |
| 4 | Múltiples tipos de secciones | ✓ PASS (10 tipos) |
| 5 | Secciones 1:1 (sin id_seccion) | ✓ PASS |

---

## Script de limpieza (post-tests)

```sql
DELETE FROM edan.edan_localidades_infra_productiva WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_salud_establecimientos WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_danos_viales WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_danos_infra_publica WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_servicios_basicos WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_unidades_educativas WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_danos_vivienda WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_danos_agricultura WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_danos_pecuario WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades_proteccion WHERE id_seccion LIKE 'test-%' OR id_seccion LIKE 's-%';
DELETE FROM edan.edan_localidades WHERE id_local LIKE 'test-%';
```

---

## Código de ejemplo para cliente (JavaScript/TypeScript)

```typescript
// Generar id_seccion único
function generarIdSeccion(): string {
  const timestamp = Date.now().toString(32);
  const uuidShort = crypto.randomUUID().replace(/-/g, '').slice(0, 13);
  return `${timestamp}-${uuidShort}`;
}

// Crear sección
const nuevaInfra = {
  id_seccion: generarIdSeccion(),  // Generar UNA VEZ
  tipo: "Molino",
  dano_parcial: 1,
  dano_total: 0
};

// Editar sección (REUSAR id_seccion)
const infraEditada = {
  id_seccion: nuevaInfra.id_seccion,  // ← REUSAR
  tipo: "Molino",
  dano_parcial: 2  // Solo cambiar lo necesario
};

// Sync
await fetch('/api/v1/edan/localidades/sync', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    localidades: [{
      id_local: "mi-local-id",
      localidad: "Mi Localidad",
      id_tipo_localidad: 1,
      id_edan_localidad_estado: 1,
      id_municipio: 70101,
      id_departamento: 7,
      id_provincia: 701,
      infra_productiva: [infraEditada]
    }]
  })
});
```
