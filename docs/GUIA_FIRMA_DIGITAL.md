# Guía de uso: Validación de Firma Digital (AGETIC)

**Base URL:** `https://api.climbat.net/api/v2`
**Requiere token JWT** (`Authorization: Bearer <token>`) y **permiso REPOSITORIO** (POST → CREATE).

---

## Flujo para la Web y la App

### 1. Subir el PDF firmado al repositorio (valida al vuelo)

El documento se sube con el endpoint existente del repositorio. **La API valida la firma
automáticamente al recibir el archivo** y guarda los metadatos de validación en la misma
operación (`tiene_firma_digital`, `resultado_firma`, `fecha_validacion_firma`).

```
POST /api/v2/repositorio/edan/{id_edan}/documentos
Content-Type: multipart/form-data
```

Campos requeridos: `file` (PDF), `id_tipo_documento`, `id_departamento`, `id_provincia`,
`id_municipio`, `fecha_documento` (YYYY-MM-DD), `nombre_documento`.

Comportamiento al subir:
- PDF con firma(s) válida(s) → `tiene_firma_digital = true` + resultado completo en
  `resultado_firma`.
- PDF sin firmas → `tiene_firma_digital = false`, `resultado_firma` con `cantidad_firmas: 0`.
- PDF > 20 MB (límite AGETIC) → el documento se guarda igual, pero no se valida;
  `resultado_firma` registra el motivo.
- AGETIC caído (502) → el documento **no** se bloquea; se guarda con `resultado_firma`
  indicando el error de validación.

Para tipo de documento relacionado a firmado usar `edan_firmado` en el catálogo
`repositorio.tipo_documento`.

### 2. Re-validar o consultar la firma de un documento ya subido (no guarda)

Si la validación automática falló por caída de AGETIC, o se quiere revisar de nuevo la firma de
un documento **sin sobreescribir** los metadatos guardados, se usa el endpoint independiente.
**No requiere body** y **no modifica la base de datos**: solo valida y devuelve el resultado.

```
POST /api/v2/firma-digital/documento/{id_documento}/validar
```

Límite: 20 MB (límite de AGETIC). Documentos mayores devuelven 400.

### 3. Leer el resultado

Los endpoints GET del repositorio ya devuelven los campos nuevos:

- `GET /api/v2/repositorio/documentos/filtrar`
- `GET /api/v2/repositorio/edan/{id_edan}/documentos`
- `GET /api/v2/repositorio/documentos/{id_documento}`
- `GET /api/v2/repositorio/documentos/buscar?q=...`

Campo `resultado_firma` (JSONB) de cada documento:

```json
{
  "finalizado": true,
  "tipoRespuesta": "Exito",
  "mensaje": "Se validó las firmas correctamente!",
  "firmas": [
    {
      "noModificado": true,
      "cadenaConfianza": true,
      "firmadoDuranteVigencia": true,
      "firmadoAntesRevocacion": true,
      "timeStamp": false,
      "fechaFirma": "2018-05-25T23:46:42.000Z",
      "certificado": {
        "ci": "1234567",
        "nombreSignatario": "Juan Perez",
        "cargoSignatario": "Director Ejecutivo",
        "organizacionSignatario": "Perez S.A.",
        "emailSignatario": "jperez@mail.com",
        "nombreECA": "ADSIB",
        "descripcionECA": "Entidad Certificadora Publica ADSIB",
        "inicioValidez": "2017-08-04T22:46:42.000Z",
        "finValidez": "2018-08-04T22:46:42.000Z",
        "revocado": "2018-06-01T12:30:02.000Z"
      }
    }
  ],
  "cantidad_firmas": 1
}
```

A nivel de BD (listados):
- `tiene_firma_digital` → `true` si el documento tiene al menos 1 firma válida.
- `fecha_validacion_firma` → cuándo se validó por última vez.

---
# NO guardan en BD

## ¿Cuándo usar `validar-pdf` vs `validar-pdf-url` vs `documento/{id}/validar`?

| Endpoint | ¿Cuándo usarlo? | ¿Guarda en BD? |
|---|---|---|
| `POST /repositorio/edan/{id}/documentos` | Subir el PDF del EDAN. Valida la firma automáticamente y guarda los metadatos. | **SÍ** (sube archivo + metadatos de firma) |
| `POST /firma-digital/validar-pdf` | Tienes el PDF **en binario** (ej. dentro de la Web/App) y quieres validarlo **antes de subirlo**. | NO |
| `POST /firma-digital/validar-pdf-url` | El PDF está **en una URL pública** (ej. en el servidor de la institución, Google Drive público, etc.) y quieres validarlo sin descargarlo. Se usa para previsualizar/verificar un archivo **que aún no se subió**. | NO |
| `POST /firma-digital/documento/{id}/validar` | El PDF **ya está en el repositorio** y quieres re-validar su firma (ej. tras una caída de AGETIC, o para revisar sin tocar los metadatos guardados). | NO |

> **Regla general:** el único endpoint que escribe en la base de datos es la **subida**
> (`POST /repositorio/edan/{id}/documentos` o `POST /repositorio/documentos/{id}`).
> Los 3 endpoints de `firma-digital` son **solo de validación/consulta**.

### Validar un PDF directo (base64) — sin guardar

```
POST /api/v2/firma-digital/validar-pdf
{
  "pdfFirmadoBase64": "JVBERi0xLjQK...",   // base64 puro, sin prefijo data:
  "contrasenia": ""                          // opcional, si PDF protegido
}
```

### Validar un PDF por URL pública — sin guardar

```
POST /api/v2/firma-digital/validar-pdf-url
{
  "urlArchivoFirmado": "https://dominio/archivo.pdf"
}
```

### Validar un PDF ya subido al repositorio — sin guardar

```
POST /api/v2/firma-digital/documento/42/validar
```

### Respuesta común de AGETIC (transformada)

Formato `SuccessResponse` v2:

```json
{
  "success": true,
  "message": "Se validó las firmas correctamente!",
  "data": {
    "finalizado": true,
    "tipoRespuesta": "Exito",
    "mensaje": "Se validó las firmas correctamente!",
    "firmas": [ ... ],
    "cantidad_firmas": 1
  }
}
```

- `tipoRespuesta` = `"Exito"` | `"Error"`.
- Si el PDF no tiene firmas → `tipoRespuesta: "Error"`, `cantidad_firmas: 0`.

---

## Ejemplo de integración (Web)

```
Flujo habitual (guarda):
1. POST /repositorio/edan/{id}/documentos (multipart) → guarda PDF + valida firma + guarda metadatos
2. GET  /repositorio/documentos/{id} → lee resultado_firma guardado

Flujo opcional (solo consulta, no guarda):
3. POST /firma-digital/validar-pdf            → validar un PDF en binario antes de subirlo
4. POST /firma-digital/validar-pdf-url        → validar un PDF en URL pública
5. POST /firma-digital/documento/{id}/validar → re-validar un documento ya subido
```

---

## Notas

- Los endpoints de validación están agrupados en Swagger bajo **Repositorio > Documentos**
  (`/docs/v2#/Repositorio_Documentos`).
- No hay rate limiting; la protección es por JWT + permiso REPOSITORIO.
- En caso de caída de AGETIC, los endpoints responden 502 con mensaje claro.