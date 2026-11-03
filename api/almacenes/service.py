from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


class AlmacenesService:
    def __init__(self, db: Session):
        self.db = db

    def _es_admin(self, usuario: dict) -> bool:
        rol = usuario.get("id_rol")
        return rol in (1, 2)

    def _es_videci_nacional(self, usuario: dict) -> bool:
        rol = usuario.get("id_rol")
        return rol in (1, 2)  # VIDECI nacional / admin

    def listar_almacenes(self, usuario: dict, limit: int = 100, skip: int = 0, todos: bool = False,
                         nivel: Optional[str] = None, estado: Optional[str] = None, q: Optional[str] = None,
                         id_municipio: Optional[int] = None, id_departamento: Optional[int] = None) -> tuple[list, int]:
        where = ["1=1"]
        p = {}
        if not self._es_admin(usuario):
            rol = usuario.get("id_rol")
            if rol == 14:  # Almacén - solo su territorio
                if usuario.get("id_municipio"):
                    where.append("(a.id_municipio = :um)")
                    p["um"] = usuario["id_municipio"]
                elif usuario.get("id_departamento"):
                    where.append("(a.id_departamento = :ud)")
                    p["ud"] = usuario["id_departamento"]
            else:
                if usuario.get("id_municipio"):
                    where.append("(a.id_municipio = :um)")
                    p["um"] = usuario["id_municipio"]
                elif usuario.get("id_departamento"):
                    where.append("(a.id_departamento = :ud)")
                    p["ud"] = usuario["id_departamento"]
        if nivel:
            where.append("a.nivel = :nivel")
            p["nivel"] = nivel
        if estado:
            where.append("a.estado = :estado")
            p["estado"] = estado
        if q:
            where.append("(LOWER(a.nombre) LIKE LOWER(:q) OR LOWER(a.codigo) LIKE LOWER(:q))")
            p["q"] = f"%{q}%"
        if id_municipio:
            where.append("a.id_municipio = :id_municipio")
            p["id_municipio"] = id_municipio
        if id_departamento:
            where.append("a.id_departamento = :id_departamento")
            p["id_departamento"] = id_departamento

        w = " AND ".join(where)
        total = self.db.execute(text(f"SELECT COUNT(*) AS total FROM rida.almacen a WHERE {w}"), p).scalar() or 0

        page = "" if todos else " LIMIT :limit OFFSET :skip"
        qp = {**p, "limit": limit, "skip": skip} if not todos else p
        sql = f"SELECT a.* FROM rida.almacen a WHERE {w} ORDER BY a.fecha_creacion DESC, a.id_almacen DESC {page}"
        rows = self.db.execute(text(sql), qp).mappings().all()
        return [dict(r) for r in rows], total

    def obtener_almacen(self, id_almacen: int) -> dict:
        row = self.db.execute(text("SELECT * FROM rida.almacen WHERE id_almacen = :id"), {"id": id_almacen}).mappings().first()
        return dict(row) if row else None

    def crear_almacen(self, data: dict, usuario: dict) -> dict:
        maxid = self.db.execute(text("SELECT COALESCE(MAX(id_almacen),0)+1 FROM rida.almacen")).scalar()
        codigo = data.get("codigo") or f"ALM-{datetime.now().year}-{maxid:06d}"
        sql = text("""
            INSERT INTO rida.almacen (codigo,nombre,descripcion,nivel,id_municipio,id_departamento,direccion,lat,lon,capacidad_m2,estado,id_responsable_operativo,creado_por,fecha_creacion,fecha_modificacion)
            VALUES (:codigo,:nombre,:descripcion,:nivel,:id_municipio,:id_departamento,:direccion,:lat,:lon,:capacidad_m2,:estado,:id_responsable_operativo,:creado_por,NOW(),NOW())
            RETURNING *
        """)
        row = self.db.execute(sql, {**data, "codigo": codigo, "creado_por": usuario.get("id_usuario")}).mappings().first()
        self.db.commit()
        return dict(row)

    def actualizar_almacen(self, id_almacen: int, data: dict, usuario: dict) -> dict:
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            return self.obtener_almacen(id_almacen)
        sets = ", ".join([f"{k}=:{k}" for k in data.keys()])
        sql = text(f"UPDATE rida.almacen SET {sets}, fecha_modificacion=NOW() WHERE id_almacen=:id_almacen RETURNING *")
        row = self.db.execute(sql, {**data, "id_almacen": id_almacen}).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def eliminar_almacen(self, id_almacen: int) -> bool:
        res = self.db.execute(text("UPDATE rida.almacen SET estado='INACTIVO', fecha_modificacion=NOW() WHERE id_almacen=:id"), {"id": id_almacen})
        self.db.commit()
        return res.rowcount > 0

    # Solicitudes
    def crear_solicitud_salida(self, id_almacen: int, data: dict, usuario: dict) -> dict:
        maxid = self.db.execute(text("SELECT COALESCE(MAX(id_solicitud_salida),0)+1 FROM rida.almacen_solicitud")).scalar()
        nro = f"SOL-SAL-{datetime.now().year}-{maxid:06d}"
        sql = text("""
            INSERT INTO rida.almacen_solicitud (nro_solicitud,id_solicitud,id_almacen,id_municipio,id_departamento,tipo,motivo,id_usuario_solicita,estado,observaciones,fecha_solicitud)
            VALUES (:nro_solicitud,:id_solicitud,:id_almacen,:id_municipio,:id_departamento,:tipo,:motivo,:id_usuario_solicita,'SOLICITADA',:observaciones,NOW())
            RETURNING id_solicitud_salida
        """)
        id_sol = self.db.execute(sql, {**data, "nro_solicitud": nro, "id_almacen": id_almacen, "id_usuario_solicita": usuario.get("id_usuario")}).scalar()
        for d in data.get("detalle", []):
            self.db.execute(text("""
                INSERT INTO rida.almacen_solicitud_detalle (id_solicitud_salida,id_articulo,cantidad_solicitada,observaciones)
                VALUES (:id_solicitud_salida,:id_articulo,:cantidad_solicitada,:observaciones)
            """), {"id_solicitud_salida": id_sol, **d})
        self.db.commit()
        return {"id_solicitud_salida": id_sol, "nro_solicitud": nro, "estado": "SOLICITADA"}

    def listar_solicitudes_salida(self, id_almacen: int, limit: int = 100, skip: int = 0, todos: bool = False, estado: Optional[str] = None) -> tuple[list, int]:
        where = ["s.id_almacen = :id"]
        p = {"id": id_almacen}
        if estado:
            where.append("s.estado = :estado")
            p["estado"] = estado
        w = " AND ".join(where)
        total = self.db.execute(text(f"SELECT COUNT(*) FROM rida.almacen_solicitud s WHERE {w}"), p).scalar() or 0
        page = "" if todos else " LIMIT :limit OFFSET :skip"
        qp = {**p, "limit": limit, "skip": skip} if not todos else p
        sql = f"SELECT s.* FROM rida.almacen_solicitud s WHERE {w} ORDER BY s.fecha_solicitud DESC {page}"
        rows = self.db.execute(text(sql), qp).mappings().all()
        return [dict(r) for r in rows], total

    def aprobar_solicitud_salida(self, id_solicitud_salida: int, data: dict, usuario: dict) -> dict:
        if not self._es_videci_nacional(usuario):
            raise Exception("Solo VIDECI nacional puede aprobar/rechazar solicitudes")
        sql = text("UPDATE rida.almacen_solicitud SET estado='APROBADA', id_usuario_autoriza=:u, fecha_autorizacion=NOW(), observaciones=COALESCE(:obs, observaciones) WHERE id_solicitud_salida=:id RETURNING *")
        row = self.db.execute(sql, {"u": usuario.get("id_usuario"), "obs": data.get("motivo_justificacion"), "id": id_solicitud_salida}).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def rechazar_solicitud_salida(self, id_solicitud_salida: int, data: dict, usuario: dict) -> dict:
        if not self._es_videci_nacional(usuario):
            raise Exception("Solo VIDECI nacional puede aprobar/rechazar solicitudes")
        sql = text("UPDATE rida.almacen_solicitud SET estado='RECHAZADA', id_usuario_autoriza=:u, fecha_autorizacion=NOW(), motivo_rechazo=:m WHERE id_solicitud_salida=:id RETURNING *")
        row = self.db.execute(sql, {"u": usuario.get("id_usuario"), "m": data.get("motivo_rechazo"), "id": id_solicitud_salida}).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def cobertura_necesidades_rida(self, params: dict) -> list:
        where = ["1=1"]
        p = {}
        if params.get("id_municipio"):
            where.append("f.id_municipio = :id_municipio")
            p["id_municipio"] = params["id_municipio"]
        if params.get("id_departamento"):
            where.append("f.id_departamento = :id_departamento")
            p["id_departamento"] = params["id_departamento"]
        if params.get("id_solicitud"):
            where.append("s.id_solicitud = :id_solicitud")
            p["id_solicitud"] = params["id_solicitud"]
        sql = f"""
        SELECT n.id_articulo, a.nombre, a.unidad_de_medida,
               COALESCE(SUM(n.cantidad),0) as necesidad_total,
               COALESCE((SELECT SUM(st.cantidad_disponible) FROM rida.almacen_stock st WHERE st.id_articulo = n.id_articulo),0) as disponible_total
        FROM rida.necesidad n
        JOIN rida.familia f ON f.id_familia = n.id_familia
        LEFT JOIN rida.formulario_rida fr ON fr.id_formulario = f.id_formulario
        LEFT JOIN rida.solicitud s ON s.id_formulario_rida = fr.id_formulario
        JOIN rida.cat_articulo a ON a.id_articulo = n.id_articulo
        WHERE {' AND '.join(where)}
        GROUP BY n.id_articulo, a.nombre, a.unidad_de_medida
        ORDER BY n.id_articulo
        """
        rows = self.db.execute(text(sql), p).mappings().all()
        res = []
        for r in rows:
            need = float(r['necesidad_total'] or 0)
            disp = float(r['disponible_total'] or 0)
            res.append({**dict(r), 'faltante': max(0, need - disp), 'cobertura_pct': round((disp/need*100) if need>0 else 100, 2)})
        return res

    def crear_nea(self, id_almacen: int, data: dict, usuario: dict) -> dict:
        maxid = self.db.execute(text("SELECT COALESCE(MAX(id_entrada),0)+1 FROM rida.almacen_entrada")).scalar()
        nro = f"NEA-{datetime.now().year}-{maxid:06d}"
        sql = text("""
            INSERT INTO rida.almacen_entrada (nro_nea,id_almacen,tipo,proveedor_donante,id_documento_soporte,fecha_entrada,hora_entrada,observaciones,id_usuario_registra,estado,fecha_creacion,fecha_modificacion)
            VALUES (:nro_nea,:id_almacen,:tipo,:proveedor_donante,:id_documento_soporte,:fecha_entrada,:hora_entrada,:observaciones,:id_usuario_registra,'REGISTRADA',NOW(),NOW())
            RETURNING id_entrada
        """)
        id_ent = self.db.execute(sql, {**data, "nro_nea": nro, "id_almacen": id_almacen, "id_usuario_registra": usuario.get("id_usuario")}).scalar()
        for d in data.get("detalle", []):
            cantidad = float(d.get("cantidad") or 0)
            self.db.execute(text("""
                INSERT INTO rida.almacen_entrada_detalle (id_entrada,id_articulo,cantidad,lote,fecha_vencimiento,valor_unitario_bs,valor_total_bs)
                VALUES (:id_entrada,:id_articulo,:cantidad,:lote,:fecha_vencimiento,:valor_unitario_bs,:valor_total_bs)
            """), {"id_entrada": id_ent, **d, "valor_total_bs": float(d.get("valor_unitario_bs") or 0)*cantidad})
            self.db.execute(text("""
                INSERT INTO rida.almacen_movimiento (id_almacen,id_articulo,lote,fecha_vencimiento,tipo_movimiento,cantidad_signed,cantidad_abs,referencia_tipo,referencia_id,nro_documento,id_usuario,fecha_movimiento)
                VALUES (:id_almacen,:id_articulo,:lote,:fecha_vencimiento,'ENTRADA',:cantidad,:cantidad,'NEA',:id_entrada,:nro_nea,:id_usuario,NOW())
            """), {"id_almacen": id_almacen, "id_usuario": usuario.get("id_usuario"), "nro_nea": nro, "cantidad": cantidad, **{k:v for k,v in d.items() if k in ['id_articulo','lote','fecha_vencimiento']}})
        self.db.commit()
        return {"id_entrada": id_ent, "nro_nea": nro}

    def crear_pecosa(self, id_almacen: int, data: dict, usuario: dict) -> dict:
        maxid = self.db.execute(text("SELECT COALESCE(MAX(id_entrega),0)+1 FROM rida.entrega")).scalar()
        nro = f"PECOSA-{datetime.now().year}-{maxid:06d}"
        sql = text("""
            INSERT INTO rida.entrega (id_solicitud, id_solicitud_salida, id_almacen, tipo, responsable, fecha_salida, estado, nro_orden, estado_despacho, id_usuario_despacha, fecha_despacho, id_usuario_crea, fecha_creacion, fecha_modificacion)
            VALUES (:id_solicitud,:id_solicitud_salida,:id_almacen,'AYUDA_HUMANITARIA',:responsable,:fecha_salida,'DESPACHADA',:nro_orden,'DESPACHADA',:id_usuario_despacha,NOW(),:id_usuario_crea,NOW(),NOW())
            RETURNING id_entrega
        """)
        id_ent = self.db.execute(sql, {
            "id_solicitud": data.get("id_solicitud"),
            "id_solicitud_salida": data.get("id_solicitud_salida"),
            "id_almacen": id_almacen,
            "responsable": data.get("nombre_quien_recibe"),
            "fecha_salida": data.get("fecha_salida"),
            "nro_orden": nro,
            "id_usuario_despacha": usuario.get("id_usuario"),
            "id_usuario_crea": usuario.get("id_usuario")
        }).scalar()
        for d in data.get("detalle", []):
            cantidad = float(d.get("cantidad") or 0)
            id_art = d.get("id_articulo")
            lote_req = d.get("lote")
            fv_req = d.get("fecha_vencimiento")
            # obtener info articulo
            art = self.db.execute(text("SELECT controla_lote FROM rida.cat_articulo WHERE id_articulo=:id"), {"id": id_art}).mappings().first()
            if art and art.get("controla_lote") and (not lote_req):
                raise Exception(f"Articulo {id_art} requiere lote")
            # FEFO estricto: validar stock pre-insert
            if lote_req:
                stock = self.db.execute(text("SELECT COALESCE(SUM(cantidad_disponible),0) as disp FROM rida.almacen_stock WHERE id_almacen=:a AND id_articulo=:art AND COALESCE(lote,'')=COALESCE(:lote,'')"), {"a": id_almacen, "art": id_art, "lote": lote_req}).scalar() or 0
                if float(stock) < cantidad:
                    raise Exception(f"Stock insuficiente para articulo {id_art} lote {lote_req}. Disponible: {stock}")
            else:
                # consumir por lotes FEFO si hay varios lotes
                lotes = self.db.execute(text("SELECT lote, fecha_vencimiento, cantidad_disponible FROM rida.almacen_stock WHERE id_almacen=:a AND id_articulo=:art AND cantidad_disponible>0 ORDER BY fecha_vencimiento ASC NULLS LAST"), {"a": id_almacen, "art": id_art}).mappings().all()
                pend = cantidad
                for lt in lotes:
                    if pend <= 0: break
                    tomar = min(float(lt['cantidad_disponible']), pend)
                    # insertar detalle/movimiento por lote
                    self.db.execute(text("""
                        INSERT INTO rida.entrega_detalle (id_entrega,id_articulo,cantidad,lote,fecha_vencimiento,cantidad_despachada,cantidad_entregada_acumulada,fecha_creacion)
                        VALUES (:id_entrega,:id_articulo,:cantidad,:lote,:fv,:cantidad,0,NOW())
                    """), {"id_entrega": id_ent, "id_articulo": id_art, "cantidad": tomar, "lote": lt['lote'], "fv": lt['fecha_vencimiento']})
                    self.db.execute(text("""
                        INSERT INTO rida.almacen_movimiento (id_almacen,id_articulo,lote,fecha_vencimiento,tipo_movimiento,cantidad_signed,cantidad_abs,referencia_tipo,referencia_id,nro_documento,id_usuario,fecha_movimiento)
                        VALUES (:id_almacen,:id_articulo,:lote,:fv,'SALIDA',:neg,:cantidad,'PECOSA',:id_entrega,:nro_orden,:id_usuario,NOW())
                    """), {"id_almacen": id_almacen, "id_usuario": usuario.get("id_usuario"), "nro_orden": nro, "neg": -tomar, "cantidad": tomar, "id_articulo": id_art, "lote": lt['lote'], "fv": lt['fecha_vencimiento']})
                    pend -= tomar
                if pend > 0:
                    raise Exception(f"Stock insuficiente para articulo {id_art}")
                continue
            self.db.execute(text("""
                INSERT INTO rida.entrega_detalle (id_entrega,id_articulo,cantidad,lote,fecha_vencimiento,cantidad_despachada,cantidad_entregada_acumulada,fecha_creacion)
                VALUES (:id_entrega,:id_articulo,:cantidad,:lote,:fecha_vencimiento,:cantidad,0,NOW())
            """), {"id_entrega": id_ent, **d})
            self.db.execute(text("""
                INSERT INTO rida.almacen_movimiento (id_almacen,id_articulo,lote,fecha_vencimiento,tipo_movimiento,cantidad_signed,cantidad_abs,referencia_tipo,referencia_id,nro_documento,id_usuario,fecha_movimiento)
                VALUES (:id_almacen,:id_articulo,:lote,:fecha_vencimiento,'SALIDA',:neg,:cantidad,'PECOSA',:id_entrega,:nro_orden,:id_usuario,NOW())
            """), {"id_almacen": id_almacen, "id_usuario": usuario.get("id_usuario"), "nro_orden": nro, "neg": -cantidad, "cantidad": cantidad, **{k:v for k,v in d.items() if k in ['id_articulo','lote','fecha_vencimiento']}})
        self.db.commit()
        return {"id_entrega": id_ent, "nro_orden": nro}

    def entregar_beneficiario(self, id_entrega: int, data: dict, usuario: dict) -> dict:
        # validar estado
        ent = self.db.execute(text("SELECT estado, nro_orden FROM rida.entrega WHERE id_entrega=:id"), {"id": id_entrega}).mappings().first()
        if not ent:
            raise Exception("PECOSA no encontrada")
        if ent.get('estado') == 'ENTREGADA_TOTAL' or ent.get('estado') == 'CERRADA':
            raise Exception("PECOSA ya entregada/cerrada")
        # bloquear misma familia misma PECOSA
        fam = data.get('id_familia')
        exists = self.db.execute(text("SELECT 1 FROM rida.entrega_beneficiario WHERE id_entrega=:e AND id_familia=:f"), {"e": id_entrega, "f": fam}).first()
        if exists:
            raise Exception("Esta familia ya fue registrada en esta PECOSA")
        # validar contra rida.familia solo si viene codigo_familia
        if data.get('codigo_familia'):
            f = self.db.execute(text("SELECT id_familia FROM rida.familia WHERE id_familia=:f AND codigo_familia=:c"), {"f": fam, "c": data.get('codigo_familia')}).first()
            if not f:
                # seguir pero logico; segun respuesta solo validar si viene codigo_familia
                pass
        sql = text("""
            INSERT INTO rida.entrega_beneficiario (id_entrega,id_familia,codigo_familia,ci_jefe_familia,nombre_jefe_familia,metodo_verificacion,id_usuario_entrega,fecha_hora_entrega,id_acta_entrega,id_documento_lista_firmada,testigo_nombre,testigo_ci,parentesco,tipo_documento,observaciones,id_usuario_crea,fecha_creacion,fecha_modificacion)
            VALUES (:id_entrega,:id_familia,:codigo_familia,:ci_jefe_familia,:nombre_jefe_familia,:metodo_verificacion,:id_usuario_entrega,COALESCE(:fecha_hora_entrega,NOW()),:id_acta_entrega,:id_documento_lista_firmada,:testigo_nombre,:testigo_ci,:parentesco,:tipo_documento,:observaciones,:id_usuario_crea,NOW(),NOW())
            RETURNING id_entrega_beneficiario
        """)
        id_eb = self.db.execute(sql, {**data, "id_entrega": id_entrega, "id_usuario_entrega": data.get('id_usuario_entrega') or usuario.get("id_usuario"), "id_usuario_crea": usuario.get("id_usuario"), "fecha_hora_entrega": data.get('fecha_hora_entrega')}).scalar()
        total_pend = 0
        for d in data.get("detalle", []):
            cantidad = float(d.get("cantidad") or 0)
            # validar pendiente
            rowd = self.db.execute(text("SELECT COALESCE(cantidad_despachada,0) as desp, COALESCE(cantidad_entregada_acumulada,0) as ent FROM rida.entrega_detalle WHERE id_entrega=:e AND id_articulo=:a AND COALESCE(lote,'')=COALESCE(:lote,'')"), {"e": id_entrega, "a": d['id_articulo'], "lote": d.get('lote')}).mappings().first()
            if not rowd:
                raise Exception("Detalle no encontrado en PECOSA")
            if cantidad > float(rowd['desp']) - float(rowd['ent']):
                raise Exception("Cantidad excede pendiente por entregar")
            # insertar detalle
            self.db.execute(text("""
                INSERT INTO rida.almacen_entrega_beneficiario_detalle (id_entrega_beneficiario,id_articulo,lote,fecha_vencimiento,cantidad_entregada)
                VALUES (:id_eb,:id_articulo,:lote,:fecha_vencimiento,:cantidad)
            """), {"id_eb": id_eb, **d})
            # actualizar acumulado
            self.db.execute(text("""
                UPDATE rida.entrega_detalle SET cantidad_entregada_acumulada = COALESCE(cantidad_entregada_acumulada,0) + :cantidad
                WHERE id_entrega = :id_entrega AND id_articulo = :id_articulo AND COALESCE(lote,'') = COALESCE(:lote,'')
            """), {"id_entrega": id_entrega, "cantidad": cantidad, **{k:v for k,v in d.items() if k in ['id_articulo','lote','fecha_vencimiento']}})
            total_pend += float(rowd['desp']) - float(rowd['ent']) - cantidad
        # actualizar estado
        if total_pend <= 0:
            self.db.execute(text("UPDATE rida.entrega SET estado='ENTREGADA_TOTAL', estado_despacho='DESPACHADA' WHERE id_entrega=:id"), {"id": id_entrega})
        else:
            self.db.execute(text("UPDATE rida.entrega SET estado='ENTREGADA_PARCIAL' WHERE id_entrega=:id AND estado!='ENTREGADA_TOTAL'"), {"id": id_entrega})
        self.db.commit()
        return {"id_entrega_beneficiario": id_eb}

    def pendiente_entregar(self, id_entrega: int) -> list:
        sql = text("""
        SELECT ed.id_articulo, a.nombre, ed.lote, ed.fecha_vencimiento, COALESCE(ed.cantidad_despachada,ed.cantidad) as despachado, COALESCE(ed.cantidad_entregada_acumulada,0) as entregado_acumulado, (COALESCE(ed.cantidad_despachada,ed.cantidad)-COALESCE(ed.cantidad_entregada_acumulada,0)) as pendiente
        FROM rida.entrega_detalle ed
        LEFT JOIN rida.cat_articulo a ON a.id_articulo=ed.id_articulo
        WHERE ed.id_entrega=:id AND (COALESCE(ed.cantidad_despachada,ed.cantidad)-COALESCE(ed.cantidad_entregada_acumulada,0)) > 0
        ORDER BY a.nombre
        """)
        rows = self.db.execute(sql, {"id": id_entrega}).mappings().all()
        return [dict(r) for r in rows]

    def cerrar_pecosa(self, id_entrega: int, usuario: dict) -> dict:
        if not self._es_videci_nacional(usuario):
            raise Exception("Solo VIDECI nacional puede cerrar la PECOSA")
        row = self.db.execute(text("UPDATE rida.entrega SET estado='CERRADA' WHERE id_entrega=:id RETURNING *"), {"id": id_entrega}).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def listar_stock(self, id_almacen: int, limit: int = 100, skip: int = 0, todos: bool = False,
                     q: Optional[str] = None, id_articulo: Optional[int] = None) -> tuple[list, int]:
        where = ["s.id_almacen = :id"]
        p = {"id": id_almacen}
        if id_articulo:
            where.append("s.id_articulo = :id_articulo")
            p["id_articulo"] = id_articulo
        if q:
            where.append("(LOWER(a.nombre) LIKE LOWER(:q) OR LOWER(COALESCE(s.lote,'')) LIKE LOWER(:q))")
            p["q"] = f"%{q}%"
        w = " AND ".join(where)
        total = self.db.execute(text(f"SELECT COUNT(*) FROM rida.almacen_stock s LEFT JOIN rida.cat_articulo a ON a.id_articulo=s.id_articulo WHERE {w}"), p).scalar() or 0
        page = "" if todos else " LIMIT :limit OFFSET :skip"
        qp = {**p, "limit": limit, "skip": skip} if not todos else p
        sql = f"""
        SELECT s.*, a.nombre as articulo_nombre, a.unidad_de_medida
        FROM rida.almacen_stock s
        LEFT JOIN rida.cat_articulo a ON a.id_articulo=s.id_articulo
        WHERE {w}
        ORDER BY a.nombre, s.fecha_vencimiento NULLS LAST {page}
        """
        rows = self.db.execute(text(sql), qp).mappings().all()
        return [dict(r) for r in rows], total

    def listar_kardex(self, id_almacen: int, limit: int = 100, skip: int = 0, todos: bool = False,
                      id_articulo: Optional[int] = None, tipo_movimiento: Optional[str] = None,
                      referencia_tipo: Optional[str] = None, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> tuple[list, int]:
        where = ["m.id_almacen = :id"]
        p = {"id": id_almacen}
        if id_articulo:
            where.append("m.id_articulo = :id_articulo")
            p["id_articulo"] = id_articulo
        if tipo_movimiento:
            where.append("m.tipo_movimiento = :tipo_movimiento")
            p["tipo_movimiento"] = tipo_movimiento
        if referencia_tipo:
            where.append("m.referencia_tipo = :referencia_tipo")
            p["referencia_tipo"] = referencia_tipo
        if fecha_desde:
            where.append("m.fecha_movimiento >= :fecha_desde::date")
            p["fecha_desde"] = fecha_desde
        if fecha_hasta:
            where.append("m.fecha_movimiento < (:fecha_hasta::date + interval '1 day')")
            p["fecha_hasta"] = fecha_hasta
        w = " AND ".join(where)
        total = self.db.execute(text(f"SELECT COUNT(*) FROM rida.almacen_movimiento m WHERE {w}"), p).scalar() or 0
        page = "" if todos else " LIMIT :limit OFFSET :skip"
        qp = {**p, "limit": limit, "skip": skip} if not todos else p
        sql = f"""
        SELECT m.*, a.nombre as articulo_nombre, a.unidad_de_medida
        FROM rida.almacen_movimiento m
        LEFT JOIN rida.cat_articulo a ON a.id_articulo=m.id_articulo
        WHERE {w}
        ORDER BY m.fecha_movimiento DESC, m.id_movimiento DESC {page}
        """
        rows = self.db.execute(text(sql), qp).mappings().all()
        return [dict(r) for r in rows], total
