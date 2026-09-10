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
  "mensaje": "1 firma(s) digital(es) identificada(s).",
  "codigoHash": "0b41a3ae797067a962f5acdec6b88bbbd453e022",
  "firmas": [
    {
      "noModificado": true,
      "cadenaConfianza": true,
      "firmadoDuranteVigencia": true,
      "firmadoAntesRevocacion": true,
      "versionado": false,
      "timeStamp": false,
      "fechaFirma": "2026-07-21T13:15:18.000-04:00",
      "certificado": {
        "numeroSerie": "2D258484D893ABA9",
        "ciSignatario": "3394847",
        "nombreSignatario": "ELEODORO BALDIVIEZO ESTRADA",
        "organizacionSignatario": "",
        "unidadSignatario": "",
        "cargoSignatario": "",
        "correoElectronicoSignatario": "prosuco.elio@gmail.com",
        "nitSignatario": "",
        "paisECA": "BO",
        "nombreECA": "Entidad Certificadora Publica ADSIB",
        "organizacionECA": "ADSIB",
        "inicioValidez": "2026-07-01T16:54:00.000+00:00",
        "finValidez": "2027-06-29T20:27:00.000+00:00",
        "revocado": "Certificado no revocado",
        "tipoCertificado": "Certificado de Persona Natural",
        "nivelSeguridad": "Nivel de Seguridad Normal (Emitido por Software)",
        "tipoUso": "Firma Simple"
      },
      "detalleValidacion": {
        "certificadoValidacion": "EXITO",
        "certificadoTitular": "ELEODORO BALDIVIEZO ESTRADA",
        "documentoValidacion": "EXITO",
        "documentoEstado": "Documento auténtico",
        "documentoDescripcion": "El documento no ha sido modificado después de la firma.",
        "cadenaConfianzaValidacion": "EXITO",
        "cadenaConfianzaEstado": "Cadena de confianza",
        "cadenaConfianzaDescripcion": "La cadena de confianza está bajo la ICP de Bolivia, y tiene valor legal.",
        "periodoValidezValidacion": "EXITO",
        "periodoValidezEstado": "Firmado en el periodo de vigencia",
        "revocacionValidacion": "EXITO",
        "revocacionEstado": "Firmado con certificado no revocado"
      }
    }
  ],
  "cantidad_firmas": 1
}
```

> Estructura devuelta por AGETIC: AGETIC responde `{tipoRespuesta, exito, mensaje,
> objeto: {codigoHash, firmas: [...]}}`; el proxy la normaliza a los campos de arriba.
> `tipoRespuesta = "Exito"` → al menos 1 firma válida; `"Error"` → 0 firmas o PDF no firmado.

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

Formato `SuccessResponse` v2 (los 3 endpoints devuelven esta estructura en `data`):

```json
{
  "success": true,
  "message": "1 firma(s) digital(es) identificada(s).",
  "data": {
    "finalizado": true,
    "tipoRespuesta": "Exito",
    "mensaje": "1 firma(s) digital(es) identificada(s).",
    "codigoHash": "0b41a3ae797067a962f5acdec6b88bbbd453e022",
    "firmas": [ ... ],
    "cantidad_firmas": 1
  }
}
```

- `tipoRespuesta` = `"Exito"` (firma válida) | `"Error"` (0 firmas / sin firmar).
- En `documento/{id}/validar` `data` además trae `id_documento`, `tiene_firma_digital`
  y `guardado_en_bd: false`.

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