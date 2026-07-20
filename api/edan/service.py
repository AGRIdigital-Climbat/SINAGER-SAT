from sqlalchemy.orm import Session
from sqlalchemy import text


# ── EDAN PRINCIPAL ──

SQL_EDAN = """
    SELECT e.*,
           d.id as d_id, d.codigo_ine as d_codigo_ine, d.nombre as d_nombre,
           m.id as m_id, m.codigo_ine as m_codigo_ine, m.nombre as m_nombre
    FROM edan.edan e
    LEFT JOIN shared.departamento d ON e.id_departamento = d.id
    LEFT JOIN shared.municipio m ON e.id_municipio = m.id
"""


def _build_edan(row):
    data = dict(row)
    data["departamento"] = {
        "id": data.pop("d_id"),
        "codigo_ine": data.pop("d_codigo_ine"),
        "nombre": data.pop("d_nombre"),
    } if data.get("d_id") else None
    data["municipio"] = {
        "id": data.pop("m_id"),
        "codigo_ine": data.pop("m_codigo_ine"),
        "nombre": data.pop("m_nombre"),
    } if data.get("m_id") else None
    return data


def get_edans(db: Session, skip: int = 0, limit: int = 50):
    rows = db.execute(
        text(f"{SQL_EDAN} ORDER BY e.id_edan DESC LIMIT :limit OFFSET :skip"),
        {"limit": limit, "skip": skip},
    ).mappings().all()
    return [_build_edan(r) for r in rows]


def get_edan(db: Session, id: int):
    row = db.execute(
        text(f"{SQL_EDAN} WHERE e.id_edan = :id"), {"id": id}
    ).mappings().first()
    return _build_edan(row) if row else None


def get_edan_completo(db: Session, id: int):
    edan = get_edan(db, id)
    if not edan:
        return None
    result = dict(edan)
    tables = {
        "poblacion_grupo": """
            SELECT pg.*, ge.nombre as ge_nombre, ge.descripcion as ge_descripcion
            FROM edan.edan_poblacion_grupo pg
            LEFT JOIN edan.grupo_etario ge ON pg.id_grupo_etario = ge.id_grupo_etario
            WHERE pg.id_edan = :id ORDER BY pg.id_poblacion_grupo""",
        "tipos_evento": """
            SELECT te.*, t.tipo_nombre as t_nombre, t.descripcion as t_descripcion
            FROM edan.edan_tipo_evento te
            LEFT JOIN (SELECT id_tipo_evento, nombre as tipo_nombre, descripcion FROM edan.tipo_evento) t ON te.id_tipo_evento = t.id_tipo_evento
            WHERE te.id_edan = :id ORDER BY te.id_tipo_evento_edan""",
        "primera_respuesta": "SELECT * FROM edan.edan_primera_respuesta WHERE id_edan = :id",
        "salud_establecimientos": "SELECT * FROM edan.edan_salud_establecimiento WHERE id_edan = :id",
        "salud_necesidades": "SELECT * FROM edan.edan_salud_necesidades WHERE id_edan = :id",
        "infraestructura_vial": "SELECT * FROM edan.edan_infraestructura_vial WHERE id_edan = :id",
        "infraestructura_publica": "SELECT * FROM edan.edan_infraestructura_publica WHERE id_edan = :id",
        "servicios_basicos": """
            SELECT sb.*,
                   sb_cat.nombre as sb_nombre
            FROM edan.edan_servicio_basico sb
            LEFT JOIN edan.servicio_basico sb_cat ON sb.id_servicio_basico = sb_cat.id_servicio_basico
            WHERE sb.id_edan = :id ORDER BY sb.id_servicio_basico_edan""",
        "educacion_dano": "SELECT * FROM edan.edan_educacion_dano WHERE id_edan = :id",
        "educacion_afectacion": "SELECT * FROM edan.edan_educacion_afectacion WHERE id_edan = :id",
        "vivienda": "SELECT * FROM edan.edan_vivienda WHERE id_edan = :id",
        "agricultura": "SELECT * FROM edan.edan_agricultura WHERE id_edan = :id",
        "pecuaria": "SELECT * FROM edan.edan_pecuaria WHERE id_edan = :id",
        "infraestructura_productiva": "SELECT * FROM edan.edan_infraestructura_productiva WHERE id_edan = :id",
        "proteccion": """
            SELECT p.*,
                   cp.nombre as cp_nombre
            FROM edan.edan_proteccion p
            LEFT JOIN edan.categoria_proteccion cp ON p.id_categoria_proteccion = cp.id_categoria_proteccion
            WHERE p.id_edan = :id ORDER BY p.id_proteccion""",
        "ayuda_humanitaria": """
            SELECT ah.*,
                   ah_cat.nombre as ah_nombre
            FROM edan.edan_ayuda_humanitaria ah
            LEFT JOIN edan.ayuda_humanitaria ah_cat ON ah.id_ayuda_humanitaria = ah_cat.id_ayuda_humanitaria
            WHERE ah.id_edan = :id ORDER BY ah.id_ayuda_edan""",
        "comunidades": "SELECT * FROM edan.edan_comunidad WHERE id_edan = :id ORDER BY id_comunidad",
    }

    for key, query in tables.items():
        rows = db.execute(text(query), {"id": id}).mappings().all()
        result[key] = [dict(r) for r in rows]

    if result.get("poblacion_grupo"):
        for r in result["poblacion_grupo"]:
            r["grupo_etario"] = {
                "id_grupo_etario": r.pop("id_grupo_etario"),
                "nombre": r.pop("ge_nombre", None),
                "descripcion": r.pop("ge_descripcion", None),
            } if r.get("id_grupo_etario") else None

    if result.get("tipos_evento"):
        for r in result["tipos_evento"]:
            r["tipo_evento"] = {
                "id_tipo_evento": r.pop("id_tipo_evento"),
                "nombre": r.pop("t_nombre", None),
                "descripcion": r.pop("t_descripcion", None),
            } if r.get("id_tipo_evento") else None

    if result.get("servicios_basicos"):
        for r in result["servicios_basicos"]:
            r["servicio_basico"] = {
                "id_servicio_basico": r.pop("id_servicio_basico"),
                "nombre": r.pop("sb_nombre", None),
            } if r.get("id_servicio_basico") else None

    if result.get("proteccion"):
        for r in result["proteccion"]:
            r["categoria_proteccion"] = {
                "id_categoria_proteccion": r.pop("id_categoria_proteccion"),
                "nombre": r.pop("cp_nombre", None),
            } if r.get("id_categoria_proteccion") else None

    if result.get("ayuda_humanitaria"):
        for r in result["ayuda_humanitaria"]:
            r["ayuda_humanitaria"] = {
                "id_ayuda_humanitaria": r.pop("id_ayuda_humanitaria"),
                "nombre": r.pop("ah_nombre", None),
            } if r.get("id_ayuda_humanitaria") else None

    return result


def create_edan(db: Session, data: dict) -> int:
    result = db.execute(
        text("""
            INSERT INTO edan.edan (codigo_edan, id_departamento, id_municipio, nombre_alcalde,
                telefono_alcalde, fecha_llenado, fecha_evento, hora_evento, localidades_afectadas,
                total_poblacion_afectada, total_familias_afectadas, total_familias_damnificadas,
                nombre_responsable, cargo_responsable, telefono_responsable, email_responsable,
                usuario_registro, id_reporte_rea, fotografia)
            VALUES (:codigo_edan, :id_departamento, :id_municipio, :nombre_alcalde,
                :telefono_alcalde, :fecha_llenado, :fecha_evento, :hora_evento, :localidades_afectadas,
                :total_poblacion_afectada, :total_familias_afectadas, :total_familias_damnificadas,
                :nombre_responsable, :cargo_responsable, :telefono_responsable, :email_responsable,
                :usuario_registro, :id_reporte_rea, :fotografia)
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
        rows = db.execute(text(f"SELECT * FROM edan.{table} ORDER BY {pk}")).mappings().all()
        return [dict(r) for r in rows]

    def get_one(db: Session, id: int):
        row = db.execute(text(f"SELECT * FROM edan.{table} WHERE {pk} = :id"), {"id": id}).mappings().first()
        return dict(row) if row else None

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

def _subtable_crud(table: str, pk: str, sql_get_all: str | None = None, sql_get_one: str | None = None):
    def get_all(db: Session, id_edan: int):
        if sql_get_all:
            return db.execute(text(sql_get_all), {"id": id_edan}).mappings().all()
        return db.execute(
            text(f"SELECT * FROM edan.{table} WHERE id_edan = :id ORDER BY {pk}"), {"id": id_edan}
        ).mappings().all()

    def get_one(db: Session, id: int):
        if sql_get_one:
            row = db.execute(text(sql_get_one), {"id": id}).mappings().first()
        else:
            row = db.execute(text(f"SELECT * FROM edan.{table} WHERE {pk} = :id"), {"id": id}).mappings().first()
        return dict(row) if row else None

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


SQL_POBLACION_GRUPO = """
    SELECT pg.*, ge.nombre as ge_nombre, ge.descripcion as ge_descripcion
    FROM edan.edan_poblacion_grupo pg
    LEFT JOIN edan.grupo_etario ge ON pg.id_grupo_etario = ge.id_grupo_etario
    WHERE pg.id_edan = :id ORDER BY pg.id_poblacion_grupo"""

SQL_EDAN_TIPO_EVENTO = """
    SELECT te.*, te2.nombre as te_nombre, te2.descripcion as te_descripcion
    FROM edan.edan_tipo_evento te
    LEFT JOIN edan.tipo_evento te2 ON te.id_tipo_evento = te2.id_tipo_evento
    WHERE te.id_edan = :id ORDER BY te.id_tipo_evento_edan"""

SQL_SERVICIO_BASICO_EDAN = """
    SELECT sb.*, sb_cat.nombre as sb_nombre
    FROM edan.edan_servicio_basico sb
    LEFT JOIN edan.servicio_basico sb_cat ON sb.id_servicio_basico = sb_cat.id_servicio_basico
    WHERE sb.id_edan = :id ORDER BY sb.id_servicio_basico_edan"""

SQL_PROTECCION = """
    SELECT p.*, cp.nombre as cp_nombre
    FROM edan.edan_proteccion p
    LEFT JOIN edan.categoria_proteccion cp ON p.id_categoria_proteccion = cp.id_categoria_proteccion
    WHERE p.id_edan = :id ORDER BY p.id_proteccion"""

SQL_AYUDA_HUM = """
    SELECT ah.*, ah_cat.nombre as ah_nombre
    FROM edan.edan_ayuda_humanitaria ah
    LEFT JOIN edan.ayuda_humanitaria ah_cat ON ah.id_ayuda_humanitaria = ah_cat.id_ayuda_humanitaria
    WHERE ah.id_edan = :id ORDER BY ah.id_ayuda_edan"""


poblacion_grupo_crud = _subtable_crud("edan_poblacion_grupo", "id_poblacion_grupo", SQL_POBLACION_GRUPO)
edan_tipo_evento_crud = _subtable_crud("edan_tipo_evento", "id_tipo_evento_edan", SQL_EDAN_TIPO_EVENTO)
primera_respuesta_crud = _subtable_crud("edan_primera_respuesta", "id_primera_respuesta")
salud_establecimiento_crud = _subtable_crud("edan_salud_establecimiento", "id_salud_establecimiento")
salud_necesidades_crud = _subtable_crud("edan_salud_necesidades", "id_salud_necesidad")
infraestructura_vial_crud = _subtable_crud("edan_infraestructura_vial", "id_infraestructura_vial")
infraestructura_publica_crud = _subtable_crud("edan_infraestructura_publica", "id_infraestructura_publica")
servicio_basico_edan_crud = _subtable_crud("edan_servicio_basico", "id_servicio_basico_edan", SQL_SERVICIO_BASICO_EDAN)
educacion_dano_crud = _subtable_crud("edan_educacion_dano", "id_educacion_dano")
educacion_afectacion_crud = _subtable_crud("edan_educacion_afectacion", "id_educacion_afectacion")
vivienda_crud = _subtable_crud("edan_vivienda", "id_vivienda")
agricultura_crud = _subtable_crud("edan_agricultura", "id_agricultura")
pecuaria_crud = _subtable_crud("edan_pecuaria", "id_pecuaria")
infra_productiva_crud = _subtable_crud("edan_infraestructura_productiva", "id_infra_productiva")
proteccion_crud = _subtable_crud("edan_proteccion", "id_proteccion", SQL_PROTECCION)
ayuda_humanitaria_edan_crud = _subtable_crud("edan_ayuda_humanitaria", "id_ayuda_edan", SQL_AYUDA_HUM)
comunidad_crud = _subtable_crud("edan_comunidad", "id_comunidad")
