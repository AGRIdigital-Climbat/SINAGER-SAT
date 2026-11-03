# 08 · Offline y sincronización

> Trabajar sin internet y sincronizar después. Pensado para **equipos de campo** y para los **desarrolladores de la app móvil**.
> Detalle técnico: [../03-offline-y-sincronizacion.md](../03-offline-y-sincronizacion.md)

## 1. Principios

1. **Puedes trabajar sin red.** Los registros se guardan localmente con un identificador propio del dispositivo (`*_off`).
2. **Al volver la conexión, sincronizas en lote.** Una sola petición con todo lo capturado.
3. **Nada se pierde por un error parcial.** Si un registro del lote falla, el resto se aplica y el error se reporta individualmente.
4. **Gana el más reciente.** Ante conflictos se conserva la versión con marca de tiempo más nueva (LWW).
5. **Los roles 6 y 7 tienen sesión de larga duración** para no perder la autenticación en campo.

## 2. Checklist para salir a campo

- [ ] Iniciar sesión **con conexión** y verificar que el token quedó guardado.
- [ ] Descargar los datos que necesitarás (`pull`): localidades, formularios, catálogos.
- [ ] Verificar GPS activo (para ubicaciones).
- [ ] Probar que la captura local funciona en modo avión.
- [ ] Llevar batería/energía: la sincronización posterior consume datos, no antes.

## 3. Qué se sincroniza

| Bloque | Endpoint | Identificadores locales |
|---|---|---|
| Formularios, familias, integrantes, ubicaciones | `POST /api/v2/rida/empadronamiento/sync` | `id_edan_localidad`, `id_familia_off`, `id_integrante_off`, `id_ubicacion_off` |
| Necesidades | `POST /api/v2/rida/necesidades/sync` | `id_necesidad_off` + `id_familia_off` |
| Localidades EDAN | `POST /api/v2/edan/localidades/sync` | `id_local`, `id_seccion` |
| EDAN completos | `POST /api/v2/edan/sync` | `id_local` |
| Descarga de cambios | `GET .../sync/pull?fecha_desde=...` | — |

## 4. Cómo funciona el lote (empadronamiento)

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "formularios": [{"id_edan_localidad": 42, "id_estado": 1}],
    "familias":    [{"id_familia_off": "fam-1", "id_edan_localidad": 42,
                     "observacion": "casa dañada"}],
    "integrantes": [{"id_integrante_off": "int-1", "id_familia_off": "fam-1",
                     "nombre": "Ana", "apellido": "Quispe", "sexo": "F",
                     "fecha_nacimiento": "1990-05-01", "es_jefe": true}],
    "ubicaciones": [{"id_ubicacion_off": "ubi-1", "id_familia_off": "fam-1",
                     "coordenada_lat": -14.83, "coordenada_lon": -64.90}]
  }' \
  http://localhost:8000/api/v2/rida/empadronamiento/sync
```

**Respuesta:**

```json
{
  "success": true,
  "data": {
    "formularios": [{"id_edan_localidad": 42, "id_formulario": 35, "aplicado": true}],
    "familias":    [{"id_familia_off": "fam-1", "id_familia": 10, "aplicado": true}],
    "integrantes": [{"id_integrante_off": "int-1", "id_integrante": 12, "aplicado": true}],
    "ubicaciones": [{"id_ubicacion_off": "ubi-1", "id_ubicacion_familia": 3, "aplicado": true}],
    "errores": []
  }
}
```

**Interpretación:**

- Cada ítem trae `aplicado: true` y el **mapeo `off → server`**: el dispositivo debe guardar esos IDs nuevos para futuras referencias.
- Si `errores[]` no está vacío, revisa cada entrada: `{"tipo": "familia", "id": "...", "detalle": "..."}` y reintenta **solo esos** registros.

## 5. Resolución de vínculos

El servidor resuelve las referencias que el cliente hizo con identificadores locales:

| El cliente envía... | El servidor resuelve... |
|---|---|
| `id_edan_localidad` (en familia) | `id_formulario` |
| `id_familia_off` (en integrante/ubicación/necesidad) | `id_familia` |
| `id_familia_off` + `id_edan_localidad` en distintos ítems | Orden de proceso: primero formularios → familias → integrantes/ubicaciones |

**Orden obligatorio en el lote:** si envías todo junto, el servidor lo procesa en ese orden; si envías una familia antes que su formulario, recibirás el error `No se pudo resolver id_formulario`.

## 6. Descargar cambios (`pull`)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v2/edan/localidades/sync/pull?fecha_desde=2026-10-01T00:00:00&limit=200"
```

Guarda la última fecha sincronizada y usa ese valor la próxima vez (sincronización incremental). `limit` máximo: **1000**.

## 7. Conflictos

| Situación | Qué pasa |
|---|---|
| El servidor tiene un registro **más nuevo** que tu lote | El servidor **no lo sobrescribe**: responde `{"aplicado": false, "conflicto": true, "data": <versión del servidor>}` y el cliente debe mostrar la versión del servidor |
| El registro fue marcado para eliminar (`pendiente_eliminacion`) | Se aplica el borrado solo si tu marca de tiempo es igual o más reciente |
| Estado cambiado por el UGR en oficina | **Se preserva**: una re-sincronización del móvil no revierte la aprobación |

> El sistema no mezcla versiones automáticamente: ante un conflicto se muestra la versión ganadora y una persona decide.

## 8. Borrado desde el dispositivo

No se envía un `DELETE` directo: el cliente marca el registro con `pendiente_eliminacion = true` y lo incluye en el siguiente lote. El servidor lo elimina (tombstone) respetando el orden de fechas.

## 9. Buenas prácticas

- [ ] Sincroniza **al menos al finalizar cada jornada**.
- [ ] Revisa siempre `errores[]` después de cada lote.
- [ ] Guarda los IDs devueltos (`off → server`): sin ellos no podrás editar esos registros después.
- [ ] No edites un registro en dos dispositivos sin sincronizar: decidirá el reloj.
- [ ] Si cambias de cuenta, cierra sesión con conexión para invalidar la anterior.

## 10. Problemas típicos de sincronización

| Síntoma | Causa | Solución |
|---|---|---|
| `No se pudo resolver id_formulario` | La familia llegó antes que su formulario | Reenvía el lote con los formularios primero |
| `No se pudo resolver id_familia` | Falta el `id_familia_off` o la familia aún no existe | Envía la familia en el mismo lote, antes |
| Un registro aparece duplicado | Se reenvió sin el `*_off` original | Usa siempre el mismo `*_off` por registro |
| El conflicto devuelve la versión del servidor | El servidor tenía datos más nuevos | Revisa `data` y decide manualmente |
| `401` después de varios días | Token expirado (roles ≠ 6, 7) | Vuelve a iniciar sesión con conexión |

Más errores: [Cap. 10](10-faq-y-problemas.md).

---

**Anterior:** [07 · Reportes](07-reportes.md) · **Siguiente:** [09 · Administración](09-administracion.md)
