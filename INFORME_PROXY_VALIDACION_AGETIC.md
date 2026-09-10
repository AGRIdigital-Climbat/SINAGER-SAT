# Documentación: Proxy de Validación de Firmas Digitales — AGETIC

**Proyecto:** SINAGER-SAT (sat.climbat.net)  
**Fecha:** 10 de septiembre de 2026  
**Estado:** Pendiente implementación en `api.climbat.net`

---

## 1. Problema

La aplicación web `sat.climbat.net` necesita validar firmas digitales en PDFs usando la API pública de AGETIC (`validar.firmadigital.bo`). Sin embargo, existe un bloqueo CORS:

- **Peticiones GET** → Funcionan (`Access-Control-Allow-Origin: *`)
- **Peticiones POST (preflight OPTIONS)** → Retornan **403 Forbidden** sin headers CORS

Esto impide que el navegador JavaScript realice llamadas POST directamente a la API de AGETIC.

### ¿Por qué falla?

```
sat.climbat.net (HTTPS) → POST → validar.firmadigital.bo/backend/validador/pdf
                                         ↑
                              OPTIONS preflight retorna 403
                              (servidor no maneja CORS en OPTIONS)
```

Chrome requiere que el servidor responda al preflight OPTIONS con headers `Access-Control-Allow-Origin` y `Access-Control-Allow-Methods`. AGETIC no los configura.

---

## 2. Solución: Proxy en `api.climbat.net`

Agregar un endpoint proxy en el servidor de producción (`api.climbat.net`) que reenvíe las peticiones de validación a la API de AGETIC. Como es una comunicación **servidor-a-servidor**, no hay restricciones CORS.

```
sat.climbat.net (navegador)
       │
       ▼ POST /api/v1/firma-digital/validar-pdf
api.climbat.net (nuestro servidor)
       │
       ▼ POST https://validar.firmadigital.bo/backend/validador/pdf
AGETIC (servidor público)
       │
       ▼ Respuesta JSON
api.climbat.net (transforma respuesta)
       │
       ▼ Responde al navegador
sat.climbat.net (muestra resultado)
```

---

## 3. API de AGETIC — Endpoints Descubiertos

### Base URL
```
https://validar.firmadigital.bo/backend
```

### Endpoints de Validación

| Método | Path | Body (JSON) | Descripción |
|--------|------|-------------|-------------|
| `POST` | `/validador/pdf` | `{ pdfFirmadoBase64, contrasenia? }` | Validar PDF local |
| `POST` | `/validador/pdf/url` | `{ urlArchivoFirmado }` | Validar PDF desde URL |
| `POST` | `/validador/p7s` | `{ archivoFirmadoBase64 }` | Validar archivo P7S |
| `POST` | `/validador/p7s/url` | `{ urlArchivoFirmado }` | Validar P7S desde URL |
| `POST` | `/validador/xml` | `{ xmlFirmadoBase64, fecFirma? }` | Validar XML firmado |
| `POST` | `/validador/xml/url` | `{ urlArchivoFirmado, fecFirma? }` | Validar XML desde URL |
| `POST` | `/validador/jws` | `{ jsonFirmadoBase64, fecFirma? }` | Validar JWS |
| `POST` | `/validador/jws/url` | `{ urlArchivoFirmado, fecFirma? }` | Validar JWS desde URL |

### Formato del Body

El campo de datos debe contener **solo el base64 puro**, sin prefijo `data:...`:

```json
{
  "pdfFirmadoBase64": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlL1hPYmplY3Qv...",
  "contrasenia": ""
}
```

**IMPORTANTE:** Si el PDF está protegido con contraseña, enviar el campo `contrasenia`. Si no, omitirlo o enviarlo vacío.

### Respuesta de AGETIC (formato nativo actual)

> Verificado en producción (sept 2026). AGETIC responde `{tipoRespuesta, exito, mensaje,
> objeto: {codigoHash, firmas: [...]}}`. Un formato anterior usaba `finalizado`/`datos`;
> el proxy soporta ambos.

```json
{
  "tipoRespuesta": "Exito",
  "exito": true,
  "mensaje": "1 firma(s) digital(es) identificada(s).",
  "objeto": {
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
          "periodoValidezValidacion": "EXITO",
          "periodoValidezEstado": "Firmado en el periodo de vigencia",
          "revocacionValidacion": "EXITO",
          "revocacionEstado": "Firmado con certificado no revocado"
        }
      }
    ]
  }
}
```

### Respuesta de Error (PDF sin firmas)

```json
{
  "tipoRespuesta": "Error",
  "exito": false,
  "mensaje": "0 firma(s) digital(es) identificada(s).",
  "objeto": {
    "codigoHash": "0b41a3ae797067a962f5acdec6b88bbbd453e022",
    "firmas": []
  }
}
```

---

## 4. Transformación Requerida en el Proxy

El proxy normaliza el nativo de AGETIC al formato `SuccessResponse.data` v2:

| Campo AGETIC | Campo Frontend (data) | Transformación |
|-------------|----------------------|----------------|
| `tipoRespuesta` / `exito` | `finalizado` + `tipoRespuesta` | `exito` → `finalizado` (bool); `tipoRespuesta` se mantiene (`"Exito"`/`"Error"`) |
| `objeto` (o `datos` en formato anterior) | `firmas`, `cantidad_firmas`, `codigoHash` | Extraer `objeto.firmas` → `firmas`; `len(firmas)` → `cantidad_firmas`; `objeto.codigoHash` → `codigoHash` |
| `mensaje` | `mensaje` | Mantener igual |

### Respuesta Transformada (lo que recibe el frontend)

```json
{
  "finalizado": true,
  "tipoRespuesta": "Exito",
  "mensaje": "1 firma(s) digital(es) identificada(s).",
  "codigoHash": "0b41a3ae797067a962f5acdec6b88bbbd453e022",
  "firmas": [...],
  "cantidad_firmas": 1
}
```

### Respuesta de Error Transformada

```json
{
  "finalizado": false,
  "tipoRespuesta": "Error",
  "mensaje": "0 firma(s) digital(es) identificada(s).",
  "codigoHash": "0b41a3ae797067a962f5acdec6b88bbbd453e022",
  "firmas": [],
  "cantidad_firmas": 0
}
```

---

## 5. Implementación del Proxy

### 5.1. Endpoint Propuesto

```
POST https://api.climbat.net/api/v1/firma-digital/validar-pdf
```

### 5.2. Código de Ejemplo (Node.js/Express)

```javascript
// routes/firmaDigital.js
const express = require('express');
const router = express.Router();
const fetch = require('node-fetch'); // o usar fetch nativo de Node 18+

const AGETIC_BASE_URL = 'https://validar.firmadigital.bo/backend';

// POST /api/v1/firma-digital/validar-pdf
router.post('/validar-pdf', async (req, res) => {
  try {
    const { pdfFirmadoBase64, contrasenia } = req.body;

    if (!pdfFirmadoBase64) {
      return res.status(400).json({
        tipoRespuesta: 'Error',
        mensaje: 'Debe enviar el campo pdfFirmadoBase64.',
        objeto: null,
      });
    }

    // Construir body para AGETIC
    const bodyAgetic = { pdfFirmadoBase64 };
    if (contrasenia) {
      bodyAgetic.contrasenia = contrasenia;
    }

    // Reenviar a AGETIC
    const response = await fetch(`${AGETIC_BASE_URL}/validador/pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bodyAgetic),
    });

    const data = await response.json();

    // Transformar respuesta
    res.json({
      tipoRespuesta: data.finalizado ? 'Exito' : 'Error',
      mensaje: data.mensaje || '',
      objeto: data.datos || null,
    });
  } catch (error) {
    console.error('[Validar PDF] Error:', error.message);
    res.status(502).json({
      tipoRespuesta: 'Error',
      mensaje: 'Error al conectar con el servicio de validación de AGETIC.',
      objeto: null,
    });
  }
});

// POST /api/v1/firma-digital/validar-pdf-url
router.post('/validar-pdf-url', async (req, res) => {
  try {
    const { urlArchivoFirmado } = req.body;

    if (!urlArchivoFirmado) {
      return res.status(400).json({
        tipoRespuesta: 'Error',
        mensaje: 'Debe enviar el campo urlArchivoFirmado.',
        objeto: null,
      });
    }

    const response = await fetch(`${AGETIC_BASE_URL}/validador/pdf/url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urlArchivoFirmado }),
    });

    const data = await response.json();

    res.json({
      tipoRespuesta: data.finalizado ? 'Exito' : 'Error',
      mensaje: data.mensaje || '',
      objeto: data.datos || null,
    });
  } catch (error) {
    console.error('[Validar PDF URL] Error:', error.message);
    res.status(502).json({
      tipoRespuesta: 'Error',
      mensaje: 'Error al conectar con el servicio de validación de AGETIC.',
      objeto: null,
    });
  }
});

module.exports = router;
```

### 5.3. Registro de Rutas (app.js o server principal)

```javascript
const firmaDigitalRoutes = require('./routes/firmaDigital');

// Agregar antes de los middleware de error
app.use('/api/v1/firma-digital', firmaDigitalRoutes);
```

### 5.4. Límite de Tamaño

La API de AGETIC acepta archivos de hasta **20 MB**. Configurar el límite del body parser:

```javascript
// Si usa express.json()
app.use(express.json({ limit: '25mb' }));

// Si usa body-parser
app.use(bodyParser.json({ limit: '25mb' }));
```

---

## 6. Seguridad

### 6.1. Rate Limiting

Recomendado: limitar llamadas para abuso:

```javascript
const rateLimit = require('express-rate-limit');

const validarLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutos
  max: 100, // máximo 100 requests por ventana
  message: {
    tipoRespuesta: 'Error',
    mensaje: 'Demasiadas solicitudes. Intente más tarde.',
    objeto: null,
  },
});

router.post('/validar-pdf', validarLimiter, async (req, res) => { ... });
```

### 6.2. Validación de Input

Siempre validar antes de reenviar:

```javascript
// Validar que el base64 sea válido
const base64Regex = /^[A-Za-z0-9+/]+={0,2}$/;
if (!base64Regex.test(pdfFirmadoBase64)) {
  return res.status(400).json({
    tipoRespuesta: 'Error',
    mensaje: 'El campo pdfFirmadoBase64 no es válido.',
    objeto: null,
  });
}
```

### 6.3. Autenticación (Opcional)

Si desea proteger el endpoint con token JWT:

```javascript
const { verificarToken } = require('../middleware/auth');

router.post('/validar-pdf', verificarToken, validarLimiter, async (req, res) => { ... });
```

---

## 7. Flujo de Uso del Usuario

### Flujo Completo: Guía de Firma + Validación

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO ABRE sat.climbat.net/firma-digital                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  SECCIÓN A: GUÍA DE FIRMA (pasos con imágenes)             │
│                                                             │
│  1. Conectar token USB                                      │
│  2. Abrir Jacobitus Escritorio                              │
│  3. Seleccionar certificado                                 │
│  4. Ingresar contraseña del token                           │
│  5. Seleccionar PDF a firmar                                │
│  6. Guardar PDF firmado                                     │
│                                                             │
│  [Botón: Descargar Jacobitus]  [Botón: Ver video tutorial]  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  SECCIÓN B: VALIDAR PDF FIRMADO                             │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────┐    │
│  │  Arrastre un archivo │    │  O seleccione un archivo│    │
│  │  PDF aquí            │    │  [Seleccionar archivo]  │    │
│  │  (máx. 20 MB)       │    │                         │    │
│  └─────────────────────┘    └─────────────────────────┘    │
│                                                             │
│  [Botón: Validar Firmas]                                    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  RESULTADO DE VALIDACIÓN                             │    │
│  │                                                      │    │
│  │  ✓ Firma 1: Juan Perez (CI: 1234567)               │    │
│  │    • Cadena de confianza: VÁLIDA                     │    │
│  │    • Periodo de validez: VÁLIDO                      │    │
│  │    • No modificado: SÍ                               │    │
│  │    • Fecha de firma: 25/05/2018 19:46               │    │
│  │                                                      │    │
│  │  ✓ Firma 2: Maria Lopez (CI: 7654321)               │    │
│  │    • Cadena de confianza: VÁLIDA                     │    │
│  │    • Periodo de validez: VÁLIDO                      │    │
│  │    • No modificado: SÍ                               │    │
│  │    • Fecha de firma: 26/05/2018 10:15               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  SECCIÓN C: ENLACES ÚTILES                                  │
│                                                             │
│  • Descargar Jacobitus Escritorio                           │
│  • Guía de instalación de Jacobitus                         │
│  • Página oficial de AGETIC                                  │
│  • Validador oficial de AGETIC                               │
│  • Soporte técnico SINAGER                                   │
└─────────────────────────────────────────────────────────────┘
```

### Diagrama de Secuencia: Validación de PDF

```
Usuario                Navegador (sat.climbat.net)      api.climbat.net         AGETIC
  │                           │                              │                     │
  │  Selecciona archivo PDF   │                              │                     │
  │ ─────────────────────────►│                              │                     │
  │                           │  Convierte a base64          │                     │
  │                           │  (sin prefijo data:)         │                     │
  │                           │                              │                     │
  │  Hace clic en "Validar"   │                              │                     │
  │ ─────────────────────────►│                              │                     │
  │                           │  POST /api/v1/               │                     │
  │                           │  firma-digital/validar-pdf   │                     │
  │                           │  { pdfFirmadoBase64 }        │                     │
  │                           │ ────────────────────────────►│                     │
  │                           │                              │  POST /backend/     │
  │                           │                              │  validador/pdf      │
  │                           │                              │  { pdfFirmadoBase64 }│
  │                           │                              │ ───────────────────►│
  │                           │                              │                     │
  │                           │                              │  ◄──────────────────│
  │                           │                              │  { finalizado,      │
  │                           │                              │    datos, mensaje } │
  │                           │                              │                     │
  │                           │  ◄───────────────────────────│                     │
  │                           │  { tipoRespuesta: "Exito",   │                     │
  │                           │    objeto: { firmas: [...] } }│                     │
  │                           │                              │                     │
  │  Muestra resultado        │                              │                     │
  │ ◄─────────────────────────│                              │                     │
  │  (firmas, certificados,   │                              │                     │
  │   estados de validación)  │                              │                     │
```

---

## 8. Estructura de Datos: `FirmaDto` (Respuesta)

Cada firma en el array `objeto.firmas` contiene:

```typescript
interface FirmaDto {
  // Estado de validación
  noModificado: boolean;          // El documento no fue alterado después de firmar
  cadenaConfianza: boolean;       // El certificado pertenece a la PKI de Bolivia
  firmadoDuranteVigencia: boolean; // Se firmó dentro del periodo de validez del certificado
  firmadoAntesRevocacion: boolean; // Se firmó antes de la revocación del certificado
  timeStamp: boolean;             // La firma incluye sello de tiempo

  // Fecha
  fechaFirma: string;             // ISO 8601: "2018-05-25T23:46:42.000Z"

  // Certificado del firmante
  certificado: CertificadoDto;
}

interface CertificadoDto {
  ci: string;                     // CI del firmante
  nombreSignatario: string;       // Nombre completo
  cargoSignatario: string;        // Cargo o título
  organizacionSignatario: string; // Organización
  emailSignatario: string;        // Correo electrónico
  nombreECA: string;              // Entidad Certificadora (ej: "ADSIB")
  descripcionECA: string;         // Descripción de la ECA
  inicioValidez: string;          // Inicio de validez (ISO 8601)
  finValidez: string;             // Fin de validez (ISO 8601)
  revocado?: string;              // Fecha de revocación (opcional)
}
```

### Estados de Visualización

El frontend muestra cada validación con un estado visual:

| Estado | Color | Significado |
|--------|-------|-------------|
| `EXITO` | Verde | La validación pasó correctamente |
| `PRECAUCION` | Amarillo | Advertencia (ej: certificado cerca de vencer) |
| `ERROR` | Rojo | La validación falló |

---

## 9. Endpoints Futuros (Opcional)

Si en el futuro se necesita validar otros formatos, agregar endpoints equivalentes:

```javascript
// Validar P7S
router.post('/validar-p7s', async (req, res) => {
  const { archivoFirmadoBase64 } = req.body;
  // POST → AGETIC /validador/p7s
  // Body: { archivoFirmadoBase64 }
});

// Validar XML
router.post('/validar-xml', async (req, res) => {
  const { xmlFirmadoBase64, fecFirma } = req.body;
  // POST → AGETIC /validador/xml
  // Body: { xmlFirmadoBase64, fecFirma }
});

// Validar JWS
router.post('/validar-jws', async (req, res) => {
  const { jsonFirmadoBase64, fecFirma } = req.body;
  // POST → AGETIC /validador/jws
  // Body: { jsonFirmadoBase64, fecFirma }
});

// Validar desde URL
router.post('/validar-pdf-url', async (req, res) => {
  const { urlArchivoFirmado } = req.body;
  // POST → AGETIC /validador/pdf/url
  // Body: { urlArchivoFirmado }
});
```

---

## 10. Referencias

| Recurso | URL |
|---------|-----|
| Validador oficial AGETIC | https://validar.firmadigital.bo/ |
| API de AGETIC (backend) | https://validar.firmadigital.bo/backend/ |
| Documentación API (Redoc) | https://validar.firmadigital.bo/backend/apidoc |
| OpenAPI Spec (JSON) | https://validar.firmadigital.bo/backend/apidoc/openapi/validador-web.json |
| Jacobitus Escritorio (ADSIB) | https://jacobitus.digitales.gob.bo/ |
| Jacobitus Servidor (Docker) | https://gitlab.softwarelibre.gob.bo/adsib/jacobitus-total/jacobitus-servidor |
| GitHub AGETIC | https://github.com/AGETIC-Bolivia |

---

## 11. Pruebas

### Test 1: Conectividad con AGETIC

```bash
curl -s https://validar.firmadigital.bo/backend/configuraciones | jq .
```

### Test 2: Validación de PDF (desde el servidor)

```bash
curl -X POST https://validar.firmadigital.bo/backend/validador/pdf \
  -H "Content-Type: application/json" \
  -d '{"pdfFirmadoBase64": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlL1hPYmplY3Qv..."}' \
  | jq .
```

### Test 3: Proxy funcional

```bash
curl -X POST https://api.climbat.net/api/v1/firma-digital/validar-pdf \
  -H "Content-Type: application/json" \
  -d '{"pdfFirmadoBase64": "JVBERi0xLjQKJeLjz9MKMyAwIG9iago8PC9UeXBlL1hPYmplY3Qv..."}' \
  | jq .
```

---

## 12. Checklist de Implementación

- [x] Agregar ruta `/api/v2/firma-digital/validar-pdf` en el servidor
- [x] Agregar ruta `/api/v2/firma-digital/validar-pdf-url` en el servidor
- [x] Agregar ruta `/api/v2/firma-digital/documento/{id}/validar` (valida PDF del repositorio, NO guarda)
- [x] Configurar límite de tamaño (20 MB, límite de AGETIC)
- [x] Implementar transformación de respuesta AGETIC → Frontend (SuccessResponse v2)
- [x] Agregar manejo de errores (timeout, AGETIC offline, respuesta inválida)
- [x] Rate limiting: NO implementado (decisión: protección vía JWT + permiso REPOSITORIO)
- [ ] Probar con PDFs firmados reales (pendiente, requiere documento firmado)
- [ ] Probar con PDFs sin firmas (validado: responde "0 firma(s) identificada(s)")
- [ ] Probar con PDFs protegidos con contraseña (endpoint implementado, pendiente prueba real)
- [x] Probar límite de tamaño (20 MB) — validación en `_validar_base64` y `leer_pdf_repositorio`
- [ ] Desplegar en `api.climbat.net` (reiniciar uvicorn para cargar el módulo)
- [ ] Actualizar frontend para usar el nuevo endpoint

### Notas de implementación (v2 / Python / FastAPI)

- El código se implementó en **Python/FastAPI** (no Node.js como en §5.2 del borrador) en `api/firma_digital/`.
- Migración: `database/migrations/v2.11.0_firma_digital.sql` agrega a `repositorio.documentos`:
  - `tiene_firma_digital BOOLEAN DEFAULT FALSE`
  - `resultado_firma JSONB` (metadatos completos: firmas, certificados, CI, ECA, cadena de confianza, fechas)
  - `fecha_validacion_firma TIMESTAMP`
- Configuración en `.env`: `AGETIC_BASE_URL`, `AGETIC_TIMEOUT`, `AGETIC_MAX_SIZE_MB`.
- Endpoints protegidos: `module_permiso("REPOSITORIO")` (POST→CREATE).
- Respuesta usa el formato `SuccessResponse` v2: `{success, message, data}`; `data` incluye
  `finalizado`, `tipoRespuesta`, `mensaje`, `firmas`, `cantidad_firmas`.
- Dependencia nueva: `httpx`.
- El endpoint `documento/{id}/validar` rechaza documentos > 20 MB (límite de AGETIC) aunque el
  repositorio permite hasta 50 MB.
- La subida de documentos (`POST /repositorio/edan/{id}/documentos`) **valida la firma
  automáticamente** al recibir el archivo y guarda los metadatos en la misma operación
  (`tiene_firma_digital`, `resultado_firma`, `fecha_validacion_firma`). Si AGETIC está caído o
  el PDF supera 20 MB, el documento se guarda igual y `resultado_firma` registra el motivo.
- Los 3 endpoints `/firma-digital/*` (`validar-pdf`, `validar-pdf-url`, `documento/{id}/validar`)
  son **solo de validación**: no escriben en la base de datos. El único endpoint que guarda es
  la subida del repositorio.
- Guía de uso para Web/App: `docs/GUIA_FIRMA_DIGITAL.md`.
- Los endpoints de validación se documentan en Swagger v2 bajo **Repositorio > Documentos**
  (`/docs/v2#/Repositorio_Documentos`), junto al resto de endpoints del repositorio.
- Los GET del repositorio devuelven los campos nuevos (`tiene_firma_digital`,
  `resultado_firma`, `fecha_validacion_firma`).
- Referencia: el servicio local de Jacobitus (`https://localhost:9000`) también expone validación
  (`/api/validar_pdf`) con la misma estructura; el proxy está diseñado para apuntar solo a AGETIC,
  pero se puede adaptar fácilmente a futuro (solo cambia URL y nombre de campo base64).

---

**Contacto:** CLIMBAT / SINAGER-SAT  
**Última actualización:** 10 de septiembre de 2026
