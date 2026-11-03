## Página 1

Preguntas para alinear APIs de Almacenes con ARQUITECTURA_ALMACENES.md
(Sección 14) Fecha: 2025-10-29 Objetivo: Afinar lo que falta para dejar
el backend 100% alineado con la arquitectura propuesta. Instrucción:
Completar el campo Respuesta: con la opción elegida o con la respuesta
específica solicitada. 1) Flujo: Solicitud -\> Aprobación -\> PECOSA \#
Pregunta Opciones sugeridas Respuesta 1.1 ¿Debe ser obligatorio pasar
por almacen_solicitu d para generar una PECOSA, o se puede crear una
PECOSA directa desde el almacén? Obligatorio / Opcional (solo en
emergencias) / Siempre directo Debe ser obligatorio en emergencias

------------------------------------------------------------------------

## Página 2

1.2 ¿Quiénes pueden crear la solicitud de salida? ¿Quiénes pueden
aprobar/rechaza r? Especificar roles (ej. UGR, Coordinador, Jefe de
Almacén, DGR, VIDECI, Almacén - Rol 14, etc.) La solicitud de salida la
deben aprobar/ rechazar los VIDECI nacional La. Or ¿Al aprobar la
solicitud, se can modificar las cantidades ( cantidad_aproba da) por
artículo, or se debe aprobar tal como fue solicitada? Solo autorizar lo
solicitado / Permitir ajustar cantidades / Solo with justificación
\_\_\_\_\_\_\_\_\_\_\_\_\_ **solo con justificacion 1.4 ¿Debe vincularse
almacen_solicitu d with rida.solicitud (expediente RIDA) de forma
obligatoria en esta fase, or lo dejamos opcional? Obligatorio / Opcional
/ Solo cuando venga desde RIDA **\_\_\_\_\_\_\_\_\_\_\_ \_\_ debe
vincularse solo cuando venga desde rida0 2) Despacho, Lotes y FEFO

------------------------------------------------------------------------

## Página 3

# 

Pregunta Opciones sugeridas Respuesta 2.1 ¿Aplicamos FEFO estricto
(menor fecha_vencimien to primero) sin importar lo que envíe the body, o
lo sugerimos and permitimos que el usuario elija otro lote? Estricto
(sistema asigna lotes) / Sugerido (permite elegir) / Mixto
\_\_\_\_\_\_\_\_\_\_\_\_\_ **estricto sistema asigna lotes 2.2 ¿Si un
artículo tiene varios lotes y con uno solo no se cubre la cantidad, se
permite consumir varios lotes en la misma PECOSA? Si / No
**\_\_\_\_\_\_\_\_\_\_\_ \_\_ si

------------------------------------------------------------------------

## Página 4

2.3 ¿Para artículos with controla_lote = FALSE permitimos despachar sin
lote ni fecha de vencimiento? Si / No \_\_\_\_\_\_\_\_\_\_\_\_\_ \_\_ si
2.4 ¿Validamos stock antes of insertar en almacen_movimi ento with an
error 409/400 entendible, or dejamos que el trigger siga lanzando su
excepción? Validar pre-insert (recomendado) / Solo trigger / Ambos
\_\_\_\_\_\_\_\_\_\_\_\_\_ \_\_ validar preinsert 3) Entrega a
Beneficiarios (Familias) \# Pregunta Opciones sugeridas Respuesta

------------------------------------------------------------------------

## Página 5

3.1 ¿Usamos obligatoriament e rida.almacen_ent rega_beneficiario
*detalle for guardar qué artículo/lote entregó cada familia, or basta
with actualizar rida.entrega_det alle.cantidad_ent regada_acumula da?
Obligatorio detalle por familia / Solo actualizar acumulado / Ambos
*\_\_\_\_\_\_\_\_\_\_\_\_ \_\_ solo actualizar acumulado ambos 3.2 ¿El
Acta de Entrega firmada ( id_documento_li sta_firmada or nuevo
id_acta_entrega) must be obligatorio al registrar la entrega? Si / No
\_\_\_\_\_\_\_\_\_\_\_\_\_ \_\_si

------------------------------------------------------------------------

## Página 6

3.3 ¿Qué datos are obligatorios for entregar-benefici ario? Marcar
opciones: ci_jefe_familia, nombre_jefe_fa milia, codigo_familia,
metodo_verificac ion', id_usuario_entre ga , fecha_hira_entre ga',
\`id_acta_entrega' , 'testigo_nombre', 'testigo_ci'
\_\_\_\_\_\_\_\_\_\_\_\_\_ \_ acá podríamos mantener todos los campos
3.4 ¿Permitimos entregar a alguien distinto al jefe/a de familia? If Si,
¿qué exigimos? (CI of quien recibe, parentesco, autorización written)
Solo jefe de familia / Permitir with autorización escrita' / Permitir
with CI + parentesco + testigo' / Otro (especificar)
\_\_\_\_\_\_\_\_\_\_\_\_\_ **permitir solo al jefe de familia 3.3b? Or
better adjust 3.3 N/A N/A **\_\_\_\_\_\_\_\_\_\_\_ \_\_

------------------------------------------------------------------------

## Página 7

3.5 ¿Validamos against rida.familia that esa familia exista y pertenezca
al ámbito of esa PECOSA? Si / No / Solo si viene codigo_familia
\_\_\_\_\_\_\_\_\_\_\_\_\_ **solo si viene código familia 3.6 ¿Puede la
misma familia recibir por the misma PECOSA más de una vez? No (bloquear)
/ Si (permitir entregas parciales) **\_\_\_\_\_\_\_\_\_\_\_ \_\_no,
bloquear 4) Estados, Parciales and Cierre \# Pregunta Opciones sugeridas
Respuesta

------------------------------------------------------------------------

## Página 8

4.1 ¿Pasamos rida.entrega a usar estados claros: BORRADOR / DESPACHADA /
ENTREGADA_P ARCIAL / ENTREGTAGA\_ TOTAL / CERRADA / ANULADA? Or
mantenemos estado +
`estado_despach o' as hoy? Unificar a un solo campo / Mantener ambos /`Migrar
a nuevos estados' \_\_\_\_\_\_\_\_\_\_\_\_\_ **migrar a nuevos estados
4.2 ¿Al llegar to ENTREGADA_T OTAL', **bloqueamos** cualquier nuevo POST
/salidas/{id_entre ga}/entregar-ben eficiario'? Si / No
**\_\_\_\_\_\_\_\_\_\_\_ \_ si\_

------------------------------------------------------------------------

## Página 9

4.3 ¿Necesitamos el endpoint
`GET /api/v2/almacene s/{id_almacen}/s alidas/{id_entreg a}/pendiente-entr egar' exactly as lo pide la arquitectura? Si /`No'
/ 'With leves ajustes' (especificar) \_\_\_\_\_\_\_\_\_\_\_\_\_ **si 4.4
¿Quién can mark/cerrar una PECOSA as
`CERRADA'? Especificar roles (ej. Jefe de Almacén, DGR, VIDECI, Admin, Almacén) _____________ __ VIDECI nacional 5) Habilitación por Municipio / Alcance # Pregunta Opciones sugeridas Respuesta 5.1 ¿Es correcto el criterio: for operar a municipio se requiere a rida.almacen ACTIVO with nivel='municipa l' and its id_municipio'?`Si'
/ 'Ajustar' (especificar) **\_\_\_\_\_\_\_\_\_\_\_ \_\_ hay que ajustar

------------------------------------------------------------------------

## Página 10

5.2 ¿Los almacenes migrados from
`rida.cat_almace n' (v2.62.0) should be immediatament e operativos with that same criterio, or there is some extra adjustment?`Ya
operativos' / 'Requieren revisión' / 'Hay que re-apuntar something'
(especificar) \_\_\_\_\_\_\_\_\_\_\_\_\_ \_\_hay que re apuntar(debemo s
definir con ellos los almacenes 5.3 ¿Los usuarios with rol Almacén (14)
must be able to operate únicamente the/los almacenes of their territory
though they are not the creators? \`Si' / 'No' si
