from sqlalchemy.orm import Session
from sqlalchemy import text


# ── EDAN PRINCIPAL ──

def get_edans(db: Session, skip: int = 0, limit: int = 50):
    return db.execute(
        text("SELECT * FROM edan.edan ORDER BY id_edan DESC LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip},
    ).mappings().all()


def get_edan(db: Session, id: int):
    return db.execute(
        text("SELECT * FROM edan.edan WHERE id_edan = :id"), {"id": id}
    ).mappings().first()


def get_edan_completo(db: Session, id: int):
    edan = get_edan(db, id)
    if not edan:
        return None
    result = dict(edan)
    tables = {
        "poblacion_grupo": "SELECT * FROM edan.edan_poblacion_grupo WHERE id_edan = :id",
        "tipos_evento": "SELECT * FROM edan.edan_tipo_evento WHERE id_edan = :id",
        "primera_respuesta": "SELECT * FROM edan.edan_primera_respuesta WHERE id_edan = :id",
        "salud_establecimientos": "SELECT * FROM edan.edan_salud_establecimiento WHERE id_edan = :id",
        "salud_necesidades": "SELECT * FROM edan.edan_salud_necesidades WHERE id_edan = :id",
        "infraestructura_vial": "SELECT * FROM edan.edan_infraestructura_vial WHERE id_edan = :id",
        "infraestructura_publica": "SELECT * FROM edan.edan_infraestructura_publica WHERE id_edan = :id",
        "servicios_basicos": "SELECT * FROM edan.edan_servicio_basico WHERE id_edan = :id",
        "educacion_dano": "SELECT * FROM edan.edan_educacion_dano WHERE id_edan = :id",
        "educacion_afectacion": "SELECT * FROM edan.edan_educacion_afectacion WHERE id_edan = :id",
        "vivienda": "SELECT * FROM edan.edan_vivienda WHERE id_edan = :id",
        "agricultura": "SELECT * FROM edan.edan_agricultura WHERE id_edan = :id",
        "pecuaria": "SELECT * FROM edan.edan_pecuaria WHERE id_edan = :id",
        "infraestructura_productiva": "SELECT * FROM edan.edan_infraestructura_productiva WHERE id_edan = :id",
        "proteccion": "SELECT * FROM edan.edan_proteccion WHERE id_edan = :id",
        "ayuda_humanitaria": "SELECT * FROM edan.edan_ayuda_humanitaria WHERE id_edan = :id",
        "comunidades": "SELECT * FROM edan.edan_comunidad WHERE id_edan = :id",
    }
    for key, query in tables.items():
        rows = db.execute(text(query), {"id": id}).mappings().all()
        result[key] = [dict(r) for r in rows]
    return result


def create_edan(db: Session, data: dict) -> int:
    result = db.execute(
        text("""
            INSERT INTO edan.edan (codigo_edan, id_departamento, id_municipio, nombre_alcalde,
                telefono_alcalde, fecha_llenado, fecha_evento, hora_evento, localidades_afectadas,
                total_poblacion_afectada, total_familias_afectadas, total_familias_damnificadas,
                nombre_responsable, cargo_responsable, telefono_responsable, email_responsable,
                usuario_registro, id_reporte_rea)
            VALUES (:codigo_edan, :id_departamento, :id_municipio, :nombre_alcalde,
                :telefono_alcalde, :fecha_llenado, :fecha_evento, :hora_evento, :localidades_afectadas,
                :total_poblacion_afectada, :total_familias_afectadas, :total_familias_damnificadas,
                :nombre_responsable, :cargo_responsable, :telefono_responsable, :email_responsable,
                :usuario_registro, :id_reporte_rea)
            RETURNING id_edan
        """),
        data,
    )
    db.commit()
    return result.scalar()


def update_edan(db: Session, id: int, data: dict) -> dict | None:
    fields = {k: v for k, v in data.items() if v is not None}
    if not fields:
        return get_edan(db, id)
    fields["id_edan"] = id
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(text(f"UPDATE edan.edan SET {set_clause}, fecha_actualizacion = NOW() WHERE id_edan = :id_edan"), fields)
    db.commit()
    return get_edan(db, id)


def delete_edan(db: Session, id: int) -> bool:
    result = db.execute(text("DELETE FROM edan.edan WHERE id_edan = :id"), {"id": id})
    db.commit()
    return result.rowcount > 0


# ── CATÁLOGOS GENÉRICOS ──

def _catalog_crud(table: str, pk: str):
    def get_all(db: Session):
        return db.execute(text(f"SELECT * FROM edan.{table} ORDER BY {pk}")).mappings().all()

    def get_one(db: Session, id: int):
        return db.execute(text(f"SELECT * FROM edan.{table} WHERE {pk} = :id"), {"id": id}).mappings().first()

    def create(db: Session, data: dict) -> int:
        cols = ", ".join(data.keys())
        vals = ", ".join(f":{k}" for k in data.keys())
        result = db.execute(text(f"INSERT INTO edan.{table} ({cols}) VALUES ({vals}) RETURNING {pk}"), data)
        db.commit()
        return result.scalar()

    def update(db: Session, id: int, data: dict) -> dict | None:
        fields = {k: v for k, v in data.items() if v is not None}
        if not fields:
            return get_one(db, id)
        fields["id"] = id
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        db.execute(text(f"UPDATE edan.{table} SET {set_clause} WHERE {pk} = :id"), fields)
        db.commit()
        return get_one(db, id)

    def delete(db: Session, id: int) -> bool:
        result = db.execute(text(f"DELETE FROM edan.{table} WHERE {pk} = :id"), {"id": id})
        db.commit()
        return result.rowcount > 0

    return get_all, get_one, create, update, delete


tipo_evento_crud = _catalog_crud("tipo_evento", "id_tipo_evento")
grupo_etario_crud = _catalog_crud("grupo_etario", "id_grupo_etario")
servicio_basico_cat_crud = _catalog_crud("servicio_basico", "id_servicio_basico")
categoria_proteccion_cat_crud = _catalog_crud("categoria_proteccion", "id_categoria_proteccion")
ayuda_humanitaria_cat_crud = _catalog_crud("ayuda_humanitaria", "id_ayuda_humanitaria")


# ── SUB-TABLAS GENÉRICAS ──

def _subtable_crud(table: str, pk: str):
    def get_all(db: Session, id_edan: int):
        return db.execute(
            text(f"SELECT * FROM edan.{table} WHERE id_edan = :id ORDER BY {pk}"), {"id": id_edan}
        ).mappings().all()

    def get_one(db: Session, id: int):
        return db.execute(text(f"SELECT * FROM edan.{table} WHERE {pk} = :id"), {"id": id}).mappings().first()

    def create(db: Session, data: dict) -> int:
        cols = ", ".join(data.keys())
        vals = ", ".join(f":{k}" for k in data.keys())
        result = db.execute(text(f"INSERT INTO edan.{table} ({cols}) VALUES ({vals}) RETURNING {pk}"), data)
        db.commit()
        return result.scalar()

    def update(db: Session, id: int, data: dict) -> dict | None:
        fields = {k: v for k, v in data.items() if v is not None}
        if not fields:
            return get_one(db, id)
        fields["id"] = id
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        db.execute(text(f"UPDATE edan.{table} SET {set_clause} WHERE {pk} = :id"), fields)
        db.commit()
        return get_one(db, id)

    def delete(db: Session, id: int) -> bool:
        result = db.execute(text(f"DELETE FROM edan.{table} WHERE {pk} = :id"), {"id": id})
        db.commit()
        return result.rowcount > 0

    def delete_by_edan(db: Session, id_edan: int) -> bool:
        result = db.execute(text(f"DELETE FROM edan.{table} WHERE id_edan = :id"), {"id": id_edan})
        db.commit()
        return result.rowcount > 0

    return get_all, get_one, create, update, delete, delete_by_edan


poblacion_grupo_crud = _subtable_crud("edan_poblacion_grupo", "id_poblacion_grupo")
edan_tipo_evento_crud = _subtable_crud("edan_tipo_evento", "id_tipo_evento_edan")
primera_respuesta_crud = _subtable_crud("edan_primera_respuesta", "id_primera_respuesta")
salud_establecimiento_crud = _subtable_crud("edan_salud_establecimiento", "id_salud_establecimiento")
salud_necesidades_crud = _subtable_crud("edan_salud_necesidades", "id_salud_necesidad")
infraestructura_vial_crud = _subtable_crud("edan_infraestructura_vial", "id_infraestructura_vial")
infraestructura_publica_crud = _subtable_crud("edan_infraestructura_publica", "id_infraestructura_publica")
servicio_basico_edan_crud = _subtable_crud("edan_servicio_basico", "id_servicio_basico_edan")
educacion_dano_crud = _subtable_crud("edan_educacion_dano", "id_educacion_dano")
educacion_afectacion_crud = _subtable_crud("edan_educacion_afectacion", "id_educacion_afectacion")
vivienda_crud = _subtable_crud("edan_vivienda", "id_vivienda")
agricultura_crud = _subtable_crud("edan_agricultura", "id_agricultura")
pecuaria_crud = _subtable_crud("edan_pecuaria", "id_pecuaria")
infra_productiva_crud = _subtable_crud("edan_infraestructura_productiva", "id_infra_productiva")
proteccion_crud = _subtable_crud("edan_proteccion", "id_proteccion")
ayuda_humanitaria_edan_crud = _subtable_crud("edan_ayuda_humanitaria", "id_ayuda_edan")
comunidad_crud = _subtable_crud("edan_comunidad", "id_comunidad")
