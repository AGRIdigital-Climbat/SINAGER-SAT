# Motor de cálculo de necesidades RIDA (v2.61.0)

> Estado: **implementado**. Sustituye la captura manual de necesidades por
> reglas evaluadas sobre la población de cada familia. Documentación de uso:
> `docs/manual/04-necesidades.md` §7; contrato del motor de Ayuda Humanitaria:
> `AYUDA_HUMANITARIA_BACKEND.md` §2.7 y §5.4.

## 1. Problema

Las necesidades se cargaban a mano por familia. Eso impide aplicar criterios
homogéneos (p. ej. un kit por gestante, alimentos por integrante) y obliga a
recalcular cuando cambia la composición familiar o la duración del evento.

## 2. Modelo

`rida.regla_necesidad` (una fila = un artículo de una categoría):

| Campo | Semántica |
|---|---|
| `criterio_aplicacion` | `POR_FAMILIA`, `POR_INTEGRANTE`, `POR_CONDICION_ESPECIAL` |
| `cantidad_base` | Cantidad por unidad de población |
| `dias_duracion` | Días cubiertos (NULL = 1) |
| `condiciones` | JSONB: `gestante`, `discapacidad`, `edad_min_dias`, `edad_max_dias`, `sexo` (`M`/`F`) |
| `prioridad` / `orden` | Prelación y desempate al sumar por artículo |
| `activo` | Solo las activas se evalúan |

`rida.necesidad` gana `fuente` (`manual`/`motor`) e `id_regla_necesidad`
(trazabilidad). Índice único parcial `(id_familia, id_articulo)` donde
`fuente='motor'`.

## 3. Cálculo

```
poblacion_familia = 1                         (POR_FAMILIA)
                  = integrantes que cumplen   (POR_INTEGRANTE / POR_CONDICION_ESPECIAL)
cantidad          = ceil(cantidad_base × (dias_duracion or 1) × poblacion_familia)
```

Sin mínimos ni máximos. Si varias reglas producen el mismo artículo en una
familia, se suman y la fila conserva el `id_regla_necesidad` de la regla de
menor `(prioridad, orden, id)`.

Validaciones: `POR_FAMILIA` exige `condiciones = {}`; `POR_CONDICION_ESPECIAL`
exige ≥ 1 filtro; claves desconocidas → 422.

## 4. Persistencia

- **Preview** (`POST .../motor-necesidades/preview`): evalúa y devuelve sin
  escribir; disponible en cualquier etapa.
- **Persistencia** (`POST .../motor-necesidades`): solo `ENVIADA` y
  `EN_APROBACION`.
- El motor manda: por cada familia, reemplaza las necesidades manuales de las
  categorías cubiertas por alguna regla (aunque cambien artículo o cantidad).
  Las categorías sin regla se conservan.
- La edición manual posterior deja `fuente='manual'`; la siguiente ejecución
  del motor la reemplaza si su categoría está cubierta.

Respuesta (`data`): `familias`, `articulos_distintos`, `unidades`,
`manuales_reemplazadas`, `motoras_eliminadas`.

## 5. API

| Método | Ruta |
|---|---|
| `GET/POST` | `/api/v2/ayuda-humanitaria/reglas-necesidad` |
| `GET/PUT/DELETE` | `/api/v2/ayuda-humanitaria/reglas-necesidad/{id}` (DELETE → 409 si ya generó necesidades) |
| `POST` | `/api/v2/ayuda-humanitaria/expedientes/{id}/motor-necesidades/preview` |
| `POST` | `/api/v2/ayuda-humanitaria/expedientes/{id}/motor-necesidades` |

Escritura de reglas: roles 1/2. Scope geográfico del expediente: el habitual
(403 fuera del departamento/municipio).

## 6. Migración

`database/migrations/v2.61.0_motor_necesidades.sql` (idempotente): crea
`regla_necesidad`, añade `fuente`/`id_regla_necesidad` a `necesidad` y sus
índices. No siembra reglas: la configuración inicial es responsabilidad de
operaciones.

## 7. Verificación

Suite E2E `e2e_necesidades.py`: 37 comprobaciones (CRUD y validaciones de
reglas, preview sin escritura, persistencia con reemplazo de manuales,
idempotencia, edición manual→motor, desactivación de regla, scope 403, etapa
inválida 409, DELETE de regla referenciada 409).
